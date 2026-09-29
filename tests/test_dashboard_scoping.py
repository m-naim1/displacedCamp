"""Role scoping for the dashboard stats endpoint.

SUPERADMIN sees all data; MANAGER is restricted to their shelter and
BLOCK_HEAD to their block.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.models.enums import (
    Gender,
    HousingType,
    ResidencyStatus,
    UserRole,
)
from app.models.user import User
from app.repositories.familyRepository import FamilyRepository
from app.repositories.MemberRepository import MemberRepository
from app.schemas.family import FamilyCreate
from app.services.family_service import FamilyService, get_dashboard_stats
from tests.test_export import HEAD_ID, SPOUSE_ID, _member


async def _make_scoped_user(
    db: AsyncSession,
    *,
    username: str,
    role: UserRole,
    shelter_id: int | None = None,
    block_id: int | None = None,
) -> User:
    u = User(username=username, email=f"{username}@test.com", full_name=username)
    u.hashed_password = "unused-hash"
    u.block_id = block_id
    u.shelter_id = shelter_id
    u.role = role
    u.is_active = True
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


async def _seed_one_family(db: AsyncSession, admin_user: User) -> int:
    family_in = FamilyCreate(
        head_id=HEAD_ID,
        spouse_id=SPOUSE_ID,
        primary_phone_number="+970599123456",
        residency_status=ResidencyStatus.DISPLACED,
        housing_type=HousingType.TENT,
        original_city_id=1,
        current_shelter_center_id=1,
        shelter_block_id=1,
        shelter_quality_id=1,
        members=[
            _member(HEAD_ID, "Head of Family"),
            _member(SPOUSE_ID, "Spouse", Gender.FEMALE),
        ],
    )
    svc = FamilyService(FamilyRepository(db), MemberRepository(db))
    return (await svc.create_family(family_in, admin_user)).id


async def test_superadmin_sees_all(db: AsyncSession, sample_lookups, admin_user):
    await _seed_one_family(db, admin_user)
    stats = await get_dashboard_stats(db, admin_user)
    assert stats["total_families"] == 1
    assert stats["total_members"] == 2


async def test_manager_scoped_to_shelter(db: AsyncSession, sample_lookups, admin_user):
    await _seed_one_family(db, admin_user)

    same = await _make_scoped_user(
        db, username="mgr_same", role=UserRole.MANAGER, shelter_id=1
    )
    other = await _make_scoped_user(
        db, username="mgr_other", role=UserRole.MANAGER, shelter_id=99
    )

    assert (await get_dashboard_stats(db, same))["total_families"] == 1
    scoped = await get_dashboard_stats(db, other)
    assert scoped["total_families"] == 0
    assert scoped["total_members"] == 0


async def test_block_head_scoped_to_block(db: AsyncSession, sample_lookups, admin_user):
    await _seed_one_family(db, admin_user)

    block_head = await _make_scoped_user(
        db, username="bh", role=UserRole.BLOCK_HEAD, block_id=1
    )
    stats = await get_dashboard_stats(db, block_head)
    assert stats["total_families"] == 1
    assert stats["total_members"] == 2


async def test_manager_without_shelter_raises(
    db: AsyncSession, sample_lookups, admin_user
):
    # Construct a MANAGER without a scope without persisting — the flush-time
    # validator rejects it, so build in-memory and let the guard raise.
    user = User(
        username="mgr_no_shelter",
        email="mgr_no_shelter@test.com",
        hashed_password="unused-hash",
        full_name="No Shelter",
    )
    user.role = UserRole.MANAGER
    with pytest.raises(DomainError):
        await get_dashboard_stats(db, user)