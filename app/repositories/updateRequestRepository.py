from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.errors import NotFoundError
from app.models.enums import UpdateRequestStatus, UpdateRequestType
from app.models.family import Family, FamilyUpdateRequest
from app.repositories.base import IFamilyUpdateRequestRepository
from app.schemas.family import UpdateRequestCreate


class FamilyUpdateRequestRepository(IFamilyUpdateRequestRepository):
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_by_id(self, update_request_id: int) -> FamilyUpdateRequest | None:
        result = await self.db.execute(
            select(FamilyUpdateRequest)
            .options(joinedload(FamilyUpdateRequest.family))
            .where(FamilyUpdateRequest.id == update_request_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self, family_id: int, update_request: UpdateRequestCreate
    ) -> FamilyUpdateRequest:

        new_member = FamilyUpdateRequest(
            **update_request.model_dump(),
            family_id=family_id,
            status=UpdateRequestStatus.PENDING,
        )
        self.db.add(new_member)
        await self.db.commit()
        await self.db.refresh(new_member)
        return new_member

    async def get_all(
        self,
        shelter_center_id: int | None = None,
        block_id: int | None = None,
        family_id: int | None = None,
        request_status: UpdateRequestStatus | None = UpdateRequestStatus.PENDING,
        request_type: UpdateRequestType | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[FamilyUpdateRequest]:
        """
        get all family updates request based on shelter_center_id , block_id
            and family_id
        """
        query = select(FamilyUpdateRequest).options(
            joinedload(FamilyUpdateRequest.family)
        )
        if request_status is not None:
            query = query.where(FamilyUpdateRequest.status == request_status)
        if shelter_center_id:
            query = query.where(
                FamilyUpdateRequest.family.has(
                    Family.current_shelter_center_id == shelter_center_id
                )
            )
        if block_id:
            query = query.where(
                FamilyUpdateRequest.family.has(Family.shelter_block_id == block_id)
            )
        if family_id:
            query = query.where(FamilyUpdateRequest.family_id == family_id)
        if request_type:
            query = query.where(FamilyUpdateRequest.request_type == request_type)
        result = await self.db.execute(
            query.order_by(FamilyUpdateRequest.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return [req for req in result.scalars().all()]

    async def update(
        self, update_request_id: int, status: UpdateRequestStatus, user_reviewer_id: int
    ) -> FamilyUpdateRequest:
        update_request = await self.get_by_id(update_request_id)
        if not update_request:
            raise NotFoundError(
                code="update_request_not_found", message="Update request not found"
            )
        update_request.status = status
        update_request.reviewed_at = datetime.now(UTC)
        update_request.reviewed_by_id = user_reviewer_id
        await self.db.commit()
        return update_request
