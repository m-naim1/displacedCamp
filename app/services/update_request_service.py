import structlog
from fastapi import HTTPException, status
from pydantic import ValidationError as PydanticValidationError

from app.core.errors import DomainError, NotFoundError, ValidationError
from app.core.scoping import verify_family_scope
from app.models.enums import (
    AuditAction,
    UpdateRequestStatus,
    UpdateRequestType,
    UserRole,
)
from app.models.family import FamilyUpdateRequest
from app.models.user import User
from app.repositories.base import (
    IFamilyRepository,
    IFamilyUpdateRequestRepository,
    IMemberRepository,
)
from app.schemas.family import FamilyUpdate, MemberCreate, UpdateRequestCreate
from app.services.audit_service import AuditService

logger = structlog.getLogger()


class UpdateRequestService:
    def __init__(
        self,
        update_request_repo: IFamilyUpdateRequestRepository,
        family_repo: IFamilyRepository,
        member_repo: IMemberRepository,
        audit_service: AuditService | None = None,
    ):
        self.update_request_repo = update_request_repo
        self.family_repo = family_repo
        self.member_repo = member_repo
        self.audit = audit_service

    async def create_request(
        self,
        family_id: int,
        update_request: UpdateRequestCreate,
        actor: User | dict | None = None,
    ) -> FamilyUpdateRequest:
        try:
            match update_request.request_type:
                case UpdateRequestType.ADD_MEMBER:
                    MemberCreate(**update_request.payload)

                case UpdateRequestType.CHANGE_HEAD:
                    if not update_request.payload.get("head_id"):
                        raise ValidationError(
                            code="Invalid_Payload",
                            message="head_id is required for CHANGE_HEAD",
                        )

                case UpdateRequestType.UPDATE_FAMILY_INFO:
                    FamilyUpdate(**update_request.payload)

                case UpdateRequestType.UPDATE_MEMBER_INFO:
                    member_id = update_request.payload.get("id")
                    if not member_id:
                        raise ValidationError(
                            code="Invalid_Payload",
                            message="Member 'id' is required in payload for UPDATE_MEMBER_INFO",
                        )
                    member = await self.member_repo.get_by_id(member_id)
                    if not member or member.family_id != family_id:
                        raise NotFoundError(
                            code="Member_Not_Found",
                            message="Member not found or does not belong to this family",
                        )

                case _:
                    raise DomainError(
                        code="Unknown_Request_Type",
                        message=f"Unsupported request type: {update_request.request_type}",
                    )
        except PydanticValidationError as e:
            raise ValidationError(code="Invalid_Payload", message=str(e))

        logger.info(
            "update_request_created",
            family_id=family_id,
            type=update_request.request_type,
        )
        req = await self.update_request_repo.create(family_id, update_request)
        if self.audit:
            await self.audit.log(
                actor,
                AuditAction.UPDATE_REQUEST_CREATED,
                "update_request",
                req.id,
                details={"family_id": family_id, "request_type": str(update_request.request_type)},
            )
        return req

    async def get_family_requests(
        self, family_id: int
    ) -> list[FamilyUpdateRequest]:
        return await self.update_request_repo.get_all(
            family_id=family_id, request_status=None, limit=1000
        )

    async def get_scoped_pending_requests(
        self, current_user: User | dict
    ) -> list[FamilyUpdateRequest]:
        match current_user:
            case User(role=UserRole.SUPERADMIN):
                return await self.update_request_repo.get_all(
                    request_status=UpdateRequestStatus.PENDING
                )
            case User(role=UserRole.MANAGER):
                return await self.update_request_repo.get_all(
                    shelter_center_id=current_user.shelter_id,
                    request_status=UpdateRequestStatus.PENDING,
                )
            case User(role=UserRole.BLOCK_HEAD):
                return await self.update_request_repo.get_all(
                    block_id=current_user.block_id,
                    request_status=UpdateRequestStatus.PENDING,
                )
            case _:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid user session",
                )

    async def approve_request(
        self, req_id: int, current_user: User
    ) -> FamilyUpdateRequest:
        req = await self.update_request_repo.get_by_id(req_id)
        if not req:
            raise NotFoundError(
                code="Request_Not_Found", message=f"Update request {req_id} not found"
            )

        if req.status != UpdateRequestStatus.PENDING:
            raise DomainError(
                code="Request_Already_Processed",
                message="This request has already been reviewed.",
            )

        verify_family_scope(current_user, req.family)

        try:
            match req.request_type:
                case UpdateRequestType.ADD_MEMBER:
                    member_data = MemberCreate(**req.payload)
                    await self.member_repo.create(req.family_id, member_data)
                    await self.member_repo.commit()

                case UpdateRequestType.CHANGE_HEAD:
                    new_head_id = req.payload.get("head_id")
                    if not new_head_id:
                        raise DomainError(
                            code="Invalid_Payload",
                            message="head_id is required for CHANGE_HEAD",
                        )
                    req.family.head_id = new_head_id
                    await self.family_repo.commit()

                case UpdateRequestType.UPDATE_FAMILY_INFO:
                    family_data = FamilyUpdate(**req.payload)
                    await self.family_repo.update(req.family_id, family_data)

                case UpdateRequestType.UPDATE_MEMBER_INFO:
                    member_id = req.payload.get("id")
                    if not member_id:
                        raise DomainError(
                            code="Invalid_Payload",
                            message="Member 'id' is required in payload for UPDATE_MEMBER_INFO",
                        )
                    member = await self.member_repo.get_by_id(member_id)
                    if not member or member.family_id != req.family_id:
                        raise NotFoundError(
                            code="Member_Not_Found",
                            message="Member not found or does not belong to this family",
                        )

                    # Safely apply only valid, non-relational fields
                    for key, value in req.payload.items():
                        if hasattr(member, key) and key not in {"id", "family_id"}:
                            setattr(member, key, value)
                    await self.member_repo.commit()

                case _:
                    raise DomainError(
                        code="Unknown_Request_Type",
                        message=f"Unsupported request type: {req.request_type}",
                    )
        except PydanticValidationError as e:
            raise ValidationError(code="Invalid_Payload", message=str(e))

        reviewer_id = current_user.id
        result = await self.update_request_repo.update(
            req.id, UpdateRequestStatus.APPROVED, reviewer_id
        )
        if self.audit:
            await self.audit.log(
                current_user,
                AuditAction.UPDATE_REQUEST_APPROVED,
                "update_request",
                req.id,
                details={"family_id": req.family_id, "request_type": str(req.request_type)},
            )
        return result

    async def reject_request(
        self, req_id: int, current_user: User
    ) -> FamilyUpdateRequest:
        req = await self.update_request_repo.get_by_id(req_id)
        if not req:
            raise NotFoundError(
                code="Request_Not_Found", message=f"Update request {req_id} not found"
            )

        if req.status != UpdateRequestStatus.PENDING:
            raise DomainError(
                code="Request_Already_Processed",
                message="This request has already been reviewed.",
            )

        verify_family_scope(current_user, req.family)

        reviewer_id = current_user.id
        result = await self.update_request_repo.update(
            req.id, UpdateRequestStatus.REJECTED, reviewer_id
        )
        if self.audit:
            await self.audit.log(
                current_user,
                AuditAction.UPDATE_REQUEST_REJECTED,
                "update_request",
                req.id,
                details={"family_id": req.family_id, "request_type": str(req.request_type)},
            )
        return result
