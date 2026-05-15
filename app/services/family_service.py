from datetime import datetime
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from app.core.errors import ConflictError, DomainError, NotFoundError, ValidationError
from app.logging import logger
from app.models.enums import Gender
from app.models.family import Family, Member
from app.models.lookups import ShelterBlock, ShelterCenter
from app.schemas.family import FamilyCreate, FamilyUpdate, MemberCreate, MemberUpdate


async def get_dashboard_stats(db: AsyncSession) -> dict:
    """
    Aggregates all statistics needed for the admin dashboard in a single service call.
    """

    async def _count(query) -> int:
        result = await db.execute(query)
        return result.scalar() or 0

    total_families = await _count(select(func.count(Family.id)))
    active_families = await _count(
        select(func.count(Family.id)).where(Family.is_active == True)
    )
    total_members = await _count(select(func.count(Member.id)))

    block_result = await db.execute(
        select(ShelterBlock.name_en, func.count(Family.id).label("cnt"))
        .outerjoin(Family, Family.shelter_block_id == ShelterBlock.id)
        .group_by(ShelterBlock.id)
        .order_by(func.count(Family.id).desc())
    )
    block_counts = block_result.all()

    center_result = await db.execute(
        select(ShelterCenter.name_en, func.count(Family.id).label("cnt"))
        .outerjoin(Family, Family.current_shelter_center_id == ShelterCenter.id)
        .group_by(ShelterCenter.id)
        .order_by(func.count(Family.id).desc())
    )
    center_counts = center_result.all()

    return {
        "total_families": total_families,
        "active_families": active_families,
        "archived_families": total_families - active_families,
        "total_members": total_members,
        "avg_per_family": round(total_members / total_families, 1)
        if total_families
        else 0,
        "disabled": await _count(
            select(func.count(Member.id)).where(Member.disabled == True)
        ),
        "injured": await _count(
            select(func.count(Member.id)).where(Member.injured == True)
        ),
        "pregnant": await _count(
            select(func.count(Member.id)).where(Member.pregnant == True)
        ),
        "chronic": await _count(
            select(func.count(Member.id)).where(Member.has_chronic_disease == True)
        ),
        "block_counts": block_counts,
        "center_counts": center_counts,
        "max_block": max((c for _, c in block_counts), default=1) or 1,
    }


async def create_family(db: AsyncSession, family_in: FamilyCreate) -> Family:
    """
    Creates a new family and its members, automatically calculating statistics.
    """

    # 1. Pre-check: Ensure the Head of Family doesn't already exist
    existing_head = await db.execute(
        select(Member).where(Member.id == family_in.head_id)
    )
    if existing_head.scalar_one_or_none():
        raise ConflictError(
            code="member_already_exists",
            message=f"Member with the {family_in.head_id} already exists in another family.",
        )

    db_members = []

    for member_data in family_in.members:
        existing_member = await db.execute(
            select(Member).where(Member.id == member_data.id)
        )
        if existing_member.scalar_one_or_none():
            raise ConflictError(
                code="member_already_exists",
                message=f"Member with the {member_data.id} already exists in another family.",
            )
        db_members.append(Member(**member_data.model_dump()))

    data = family_in.model_dump(exclude={"members"})
    db_family = Family(**data)

    db.add(db_family)
    await db.flush()

    for db_member in db_members:
        db_member.family_id = db_family.id
        db.add(db_member)

    await db.commit()
    await db.refresh(db_family)

    logger.info(
        f"Created family #{db_family.id} with {len(db_members)} members (head: {family_in.head_id})"
    )
    return db_family


async def get_family(db: AsyncSession, family_id: int) -> Family:
    """
    Retrieves a family by its ID, including all members.
    """
    result = await db.execute(select(Family).where(Family.id == family_id))
    family = result.scalar_one_or_none()
    if not family:
        raise NotFoundError(
            code="Family_not_Found", message=f"Family with id {family_id} not found"
        )
    return family


async def get_families(
    db: AsyncSession, skip: int = 0, limit: int = 100, active: bool = True
) -> Sequence[Family]:
    """
    Retrieves a list of families, with optional pagination and active-only filtering.
    """
    query = select(Family)
    if active:
        query = query.where(Family.is_active)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


async def update_family(
    db: AsyncSession, family_id: int, family_data: FamilyUpdate
) -> Family:
    """
    Updates family-level details (like phone, housing, etc.) without affecting members.
    """
    family = await get_family(db, family_id)

    for key, value in family_data.model_dump(exclude_unset=True).items():
        setattr(family, key, value)

    db.add(family)
    await db.commit()
    await db.refresh(family)

    logger.info(f"Updated family #{family_id}")
    return family


async def deactivate_family(db: AsyncSession, family_id: int) -> Family:
    """
    Archive a family without deleting it.
    """
    family = await get_family(db, family_id)
    if not family.is_active:
        raise DomainError(
            code="Family_already_archived",
            message=f"Family with id {family_id} already archived",
        )
    family.is_active = False
    family.archived_at = datetime.now()

    db.add(family)
    await db.commit()
    await db.refresh(family)
    logger.info(f"Archived family #{family_id}")
    return family


async def activate_family(db: AsyncSession, family_id: int) -> Family:
    """
    Restore an archived family back to active status.
    """
    family = await get_family(db, family_id)
    if family.is_active:
        raise DomainError(
            code="Family_already_activated",
            message=f"Family with id {family_id} already activated",
        )
    family.is_active = True
    family.archived_at = None  # type: ignore

    db.add(family)
    await db.commit()
    await db.refresh(family)
    logger.info(f"Restored family #{family_id}")
    return family


async def add_member(
    db: AsyncSession, family_id: int, member_in: MemberCreate
) -> Member:
    """
    Adds a new member to an existing family.
    """
    await get_family(db, family_id)  # raises NotFoundError if missing

    existing = await db.execute(select(Member).where(Member.id == member_in.id))
    if existing.scalar_one_or_none():
        raise ConflictError(
            code="member_already_exists",
            message=f"Member with the {member_in.id} already exists in another family.",
        )

    new_member = Member(**member_in.model_dump(), family_id=family_id)
    db.add(new_member)
    await db.commit()
    await db.refresh(new_member)

    logger.info(f"Added member #{new_member.id} to family #{family_id}")
    return new_member


async def update_member(db: AsyncSession, member_id: int, member_in: MemberUpdate):
    """
    Updates an existing member's details.
    """
    result = await db.execute(select(Member).where(Member.id == member_id))
    member = result.scalar_one_or_none()
    if not member:
        raise NotFoundError(
            code="Member_not_Found", message=f"Member with id {member_id} not found"
        )

    if member_in.pregnant is not None:
        if member_in.pregnant and member.gender != Gender.FEMALE:
            raise ValidationError(
                code="Invalid_pregnancy_status",
                message="Only female members can be pregnant.",
            )

    for key, value in member_in.model_dump(exclude_unset=True).items():
        setattr(member, key, value)

    db.add(member)
    await db.commit()
    await db.refresh(member)

    return member


async def delete_member(db: AsyncSession, member_id: int):
    """
    Deletes a member from the database.
    """
    result = await db.execute(select(Member).where(Member.id == member_id))
    member = result.scalar_one_or_none()
    if not member:
        raise NotFoundError(
            code="Member_not_Found", message=f"Member with id {member_id} not found"
        )

    await db.delete(member)
    await db.commit()
    logger.info(f"Deleted member #{member_id} from family #{member.family_id}")


async def get_member(db: AsyncSession, member_id: int) -> Member:
    """
    Retrieves a member by their ID.
    """
    result = await db.execute(select(Member).where(Member.id == member_id))
    member = result.scalar_one_or_none()
    if not member:
        raise NotFoundError(
            code="Member_not_Found", message=f"Member with id {member_id} not found"
        )
    return member
