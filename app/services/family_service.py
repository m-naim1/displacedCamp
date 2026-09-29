from datetime import date

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, DomainError, NotFoundError, ValidationError
from app.core.scoping import (
    require_block_head_scope,
    require_manager_shelter_id,
    verify_family_scope,
)
from app.models.enums import AuditAction, Gender, UpdateRequestStatus
from app.models.family import Family, FamilyUpdateRequest, Member
from app.models.lookups import ShelterBlock, ShelterCenter
from app.models.user import User, UserRole
from app.repositories.base import (
    IFamilyRepository,
    IMemberRepository,
)
from app.schemas.family import (
    FamilyCreate,
    FamilyUpdate,
    MemberCreate,
    MemberUpdate,
)
from app.schemas.filters import FamilyFilterParams, MemberFilterParams
from app.services.audit_service import AuditService

logger = structlog.getLogger()


def _years_ago(n: int) -> date:
    """Date exactly n years before today (portable across SQLite/Postgres).

    Age bands are expressed as plain date comparisons instead of dialect
    specific functions like Postgres `age()` / `date_part()`.
    """
    today = date.today()
    try:
        return today.replace(year=today.year - n)
    except ValueError:  # Feb 29 in a non-leap target year
        return today.replace(year=today.year - n, day=28)


def _family_scope_condition(current_user: User):
    """SQLAlchemy condition restricting families to the actor's scope, or None."""
    match current_user:
        case User(role=UserRole.MANAGER):
            return Family.current_shelter_center_id == require_manager_shelter_id(
                current_user
            )
        case User(role=UserRole.BLOCK_HEAD):
            _, block_id = require_block_head_scope(current_user)
            return Family.shelter_block_id == block_id
        case _:
            return None


def _member_scope_condition(current_user: User):
    """Restricts members to those belonging to families in the actor's scope."""
    cond = _family_scope_condition(current_user)
    if cond is None:
        return None
    return Member.family_id.in_(select(Family.id).where(cond))


async def get_dashboard_stats(db: AsyncSession, current_user: User) -> dict:
    """
    Aggregates all statistics needed for the admin dashboard in a single service call.

    Results are scoped to the actor: SUPERADMIN sees everything, MANAGER sees
    their shelter, BLOCK_HEAD sees their block.
    """

    async def _count(query) -> int:
        result = await db.execute(query)
        return result.scalar() or 0

    family_scope = _family_scope_condition(current_user)
    member_scope = _member_scope_condition(current_user)

    def _fcount(*where):
        q = select(func.count(Family.id))
        if family_scope is not None:
            q = q.where(family_scope)
        if where:
            q = q.where(*where)
        return q

    def _mcount(*where):
        q = select(func.count(Member.id))
        if member_scope is not None:
            q = q.where(member_scope)
        if where:
            q = q.where(*where)
        return q

    total_families = await _count(_fcount())
    active_families = await _count(_fcount(Family.is_active == True))
    total_members = await _count(_mcount())

    block_query = (
        select(ShelterBlock.name_en, func.count(Family.id).label("cnt"))
        .outerjoin(Family, Family.shelter_block_id == ShelterBlock.id)
        .group_by(ShelterBlock.id)
        .order_by(func.count(Family.id).desc())
    )
    if family_scope is not None:
        block_query = block_query.where(family_scope)
    block_counts = (await db.execute(block_query)).all()

    center_query = (
        select(ShelterCenter.name_en, func.count(Family.id).label("cnt"))
        .outerjoin(Family, Family.current_shelter_center_id == ShelterCenter.id)
        .group_by(ShelterCenter.id)
        .order_by(func.count(Family.id).desc())
    )
    if family_scope is not None:
        center_query = center_query.where(family_scope)
    center_counts = (await db.execute(center_query)).all()

    under_5 = await _count(_mcount(Member.date_of_birth > _years_ago(5)))
    age_5_17 = await _count(
        _mcount(
            Member.date_of_birth <= _years_ago(5),
            Member.date_of_birth > _years_ago(18),
        )
    )
    age_18_59 = await _count(
        _mcount(
            Member.date_of_birth <= _years_ago(18),
            Member.date_of_birth > _years_ago(60),
        )
    )
    age_60_plus = await _count(_mcount(Member.date_of_birth <= _years_ago(60)))

    pending_query = select(func.count(FamilyUpdateRequest.id)).where(
        FamilyUpdateRequest.status == UpdateRequestStatus.PENDING
    )
    if family_scope is not None:
        pending_query = pending_query.where(
            FamilyUpdateRequest.family_id.in_(
                select(Family.id).where(family_scope)
            )
        )
    pending_update_requests = await _count(pending_query)

    return {
        "total_families": total_families,
        "active_families": active_families,
        "archived_families": total_families - active_families,
        "total_members": total_members,
        "avg_per_family": round(total_members / total_families, 1)
        if total_families
        else 0,
        "disabled": await _count(_mcount(Member.disabled == True)),
        "injured": await _count(_mcount(Member.injured == True)),
        "pregnant": await _count(_mcount(Member.pregnant == True)),
        "chronic": await _count(_mcount(Member.has_chronic_disease == True)),
        "block_counts": block_counts,
        "center_counts": center_counts,
        "max_block": max((c for _, c in block_counts), default=1) or 1,
        "under_5": under_5,
        "age_5_17": age_5_17,
        "age_18_59": age_18_59,
        "age_60_plus": age_60_plus,
        "pending_update_requests": pending_update_requests,
    }


class FamilyService:
    def __init__(
        self,
        family_repository: IFamilyRepository,
        member_repository: IMemberRepository,
        audit_service: AuditService | None = None,
    ):
        self.family_repo = family_repository
        self.member_repo = member_repository
        self.audit = audit_service

    async def create_family(
        self, family_in: FamilyCreate, current_user: User
    ) -> Family:
        match current_user:
            case User(role=UserRole.MANAGER):
                family_in.current_shelter_center_id = require_manager_shelter_id(
                    current_user
                )
            case User(role=UserRole.BLOCK_HEAD):
                shelter_center_id, block_id = require_block_head_scope(current_user)
                family_in.current_shelter_center_id = shelter_center_id
                family_in.shelter_block_id = block_id

        family = await self.family_repo.create(family_in)

        try:
            await self.member_repo.create_many(family.id, family_in.members)
        except ConflictError as e:
            await self.member_repo.rollback()
            raise e

        family.head_id = family_in.head_id
        if family_in.spouse_id:
            family.spouse_id = family_in.spouse_id

        family = await self.family_repo.get_by_family_id(family.id)
        if not family:
            await self.family_repo.rollback()
            raise DomainError(
                code="Couldn't_create_family", message="Family did not created."
            )

        logger.info(
            "family_creation_started",
            head_id=family_in.head_id,
            member_count=len(family_in.members),
        )
        await self.family_repo.commit()
        if self.audit:
            await self.audit.log(
                current_user,
                AuditAction.FAMILY_CREATED,
                "family",
                family.id,
                details={"head_id": family_in.head_id, "member_count": len(family_in.members)},
            )
        return family

    async def get_family(self, family_id: int, current_user: User | None) -> Family:
        """
        Retrieves a family by its ID, including all members.
        """

        family = await self.family_repo.get_by_family_id(family_id)
        if not family:
            raise NotFoundError(
                code="Family_not_Found", message=f"Family with id {family_id} not found"
            )
        if current_user:
            verify_family_scope(current_user, family)
        logger.info(
            "family_retrieved",
            family_id=family_id,
            head_id=family.head_id,
            member_count=len(family.members),
        )
        return family

    async def get_families(
        self,
        filters: FamilyFilterParams,
        current_user: User,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Family]:
        match current_user:
            case User(role=UserRole.MANAGER):
                filters.current_shelter_center_id = [
                    require_manager_shelter_id(current_user)
                ]
            case User(role=UserRole.BLOCK_HEAD):
                shelter_center_id, block_id = require_block_head_scope(current_user)
                filters.current_shelter_center_id = [shelter_center_id]
                filters.shelter_block_id = [block_id]
        return await self.family_repo.get_all(filters, skip, limit)

    async def update_family(
        self, family_id: int, family_data: FamilyUpdate, current_user: User
    ) -> Family:
        """
        Updates family-level details (like phone, housing, etc.) without affecting members.
        """
        await self.get_family(family_id, current_user)
        match current_user:
            case User(role=UserRole.MANAGER):
                family_data.current_shelter_center_id = require_manager_shelter_id(
                    current_user
                )
            case User(role=UserRole.BLOCK_HEAD):
                shelter_center_id, block_id = require_block_head_scope(current_user)
                family_data.current_shelter_center_id = shelter_center_id
                family_data.shelter_block_id = block_id
        family = await self.family_repo.update(family_id, family_data)
        if self.audit:
            await self.audit.log(
                current_user,
                AuditAction.FAMILY_UPDATED,
                "family",
                family_id,
                details={"changed": list(family_data.model_dump(exclude_unset=True).keys())},
            )
        return family

    async def deactivate_family(self, family_id: int, current_user: User) -> Family:
        """
        Archive a family without deleting it.
        """
        family = await self.get_family(family_id, current_user)

        result = await self.family_repo.archive(family_id)
        if self.audit:
            await self.audit.log(
                current_user, AuditAction.FAMILY_ARCHIVED, "family", family_id
            )
        return result

    async def activate_family(self, family_id: int, current_user: User) -> Family:
        """
        Restore an archived family back to active status.
        """
        family = await self.get_family(family_id, current_user)
        result = await self.family_repo.activate(family_id=family_id)
        if self.audit:
            await self.audit.log(
                current_user, AuditAction.FAMILY_RESTORED, "family", family_id
            )
        return result


class MemberService:
    def __init__(
        self,
        member_repository: IMemberRepository,
        family_repository: IFamilyRepository,
        audit_service: AuditService | None = None,
    ):
        self.member_repo = member_repository
        self.family_repo = family_repository
        self.audit = audit_service

    async def _get_owning_family(self, family_id: int) -> Family:
        family = await self.family_repo.get_by_family_id(family_id)
        if not family:
            raise NotFoundError(
                code="Family_not_Found", message=f"Family with id {family_id} not found"
            )
        return family

    async def add_member(
        self, family_id: int, member_in: MemberCreate, current_user: User
    ) -> Member:
        """
        Adds a new member to an existing family.
        """
        family = await self._get_owning_family(family_id)
        verify_family_scope(current_user, family)
        member = await self.member_repo.create(family_id, member_in)
        await self.member_repo.commit()
        if self.audit:
            await self.audit.log(
                current_user,
                AuditAction.MEMBER_ADDED,
                "member",
                member.id,
                details={"family_id": family_id},
            )
        return member

    async def update_member(
        self, member_id: int, member_in: MemberUpdate, current_user: User
    ):
        """
        Updates an existing member's details.
        """

        member = await self.get_member(member_id, current_user)

        if member_in.pregnant is not None:
            if member_in.pregnant and member.gender != Gender.FEMALE:
                raise ValidationError(
                    code="Invalid_pregnancy_status",
                    message="Only female members can be pregnant.",
                )
        member = await self.member_repo.update(member_id, member_in)
        if self.audit:
            await self.audit.log(
                current_user,
                AuditAction.MEMBER_UPDATED,
                "member",
                member_id,
                details={
                    "family_id": member.family_id,
                    "changed": list(member_in.model_dump(exclude_unset=True).keys()),
                },
            )
        return member

    async def delete_member(self, member_id: int, current_user: User):
        """
        Deletes a member from the database.
        """
        member = await self.get_member(member_id, current_user)
        await self.member_repo.delete(member_id)
        if self.audit:
            await self.audit.log(
                current_user,
                AuditAction.MEMBER_DELETED,
                "member",
                member_id,
                details={"family_id": member.family_id, "full_name": member.full_name},
            )

    async def get_member(self, member_id: int, current_user: User | None = None) -> Member:
        """
        Retrieves a member by their ID.
        """
        member = await self.member_repo.get_by_id(member_id)
        if not member:
            raise NotFoundError(
                code="Member_not_Found", message=f"Member with id {member_id} not found"
            )
        family = await self._get_owning_family(member.family_id)
        if current_user:
            verify_family_scope(current_user, family)
        return member

    async def get_members(
        self,
        filters: MemberFilterParams,
        current_user: User,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Member]:
        match current_user:
            case User(role=UserRole.MANAGER):
                filters.current_shelter_center_id = [
                    require_manager_shelter_id(current_user)
                ]
            case User(role=UserRole.BLOCK_HEAD):
                shelter_center_id, block_id = require_block_head_scope(current_user)
                filters.current_shelter_center_id = [shelter_center_id]
                filters.shelter_block_id = [block_id]
        return await self.member_repo.get_all(filters, skip, limit)
