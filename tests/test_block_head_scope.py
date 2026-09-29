from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Gender, HousingType, MaritalStatus, ResidencyStatus
from app.models.user import User
from app.repositories.familyRepository import FamilyRepository
from app.repositories.MemberRepository import MemberRepository
from app.schemas.family import FamilyCreate, MemberCreate
from app.schemas.filters import FamilyFilterParams
from app.services.family_service import FamilyService

pytestmark = pytest.mark.asyncio

HEAD_ID = 400000006


async def _make_family(
    db: AsyncSession, admin_user: User, shelter_center_id: int, block_id: int
) -> int:
    family_in = FamilyCreate(
        head_id=HEAD_ID,
        spouse_id=None,
        female_headed=False,
        child_headed=False,
        primary_phone_number="+970599123456",
        secondary_phone_number=None,
        residency_status=ResidencyStatus.DISPLACED,
        housing_type=HousingType.TENT,
        original_city_id=1,
        current_shelter_center_id=shelter_center_id,
        shelter_block_id=block_id,
        shelter_quality_id=1,
        members=[
            MemberCreate(
                id=HEAD_ID,
                full_name="Head of Family",
                gender=Gender.MALE,
                marital_status=MaritalStatus.MARRIED,
                date_of_birth=date(1990, 1, 15),
                relationship_to_head_id=1,
            ),
        ],
    )
    service = FamilyService(FamilyRepository(db), MemberRepository(db))
    return (await service.create_family(family_in, admin_user)).id


def _filters() -> FamilyFilterParams:
    return FamilyFilterParams(
        is_active=None,
        residency_status=None,
        female_headed=None,
        child_headed=None,
        housing_type=None,
        current_shelter_center_id=None,
        shelter_block_id=None,
        current_city_id=None,
        original_city_id=None,
        shelter_quality_id=None,
        current_governor_id=None,
        original_governor_id=None,
        head_name=None,
        phone_number=None,
        sort_by=None,
        sort_order=None,
    )


async def test_block_head_create_family_scoped_in(
    db: AsyncSession, sample_lookups, admin_user, block_head_user
):
    """A BLOCK_HEAD gets the shelter + block injected by the service."""
    family_in = FamilyCreate(
        head_id=HEAD_ID,
        spouse_id=None,
        female_headed=False,
        child_headed=False,
        primary_phone_number="+970599123456",
        secondary_phone_number=None,
        residency_status=ResidencyStatus.DISPLACED,
        housing_type=HousingType.TENT,
        original_city_id=1,
        current_shelter_center_id=1,
        shelter_block_id=1,
        shelter_quality_id=1,
        members=[
            MemberCreate(
                id=HEAD_ID,
                full_name="Head of Family",
                gender=Gender.MALE,
                marital_status=MaritalStatus.MARRIED,
                date_of_birth=date(1990, 1, 15),
                relationship_to_head_id=1,
            ),
        ],
    )
    # BLOCK_HEAD creating in their own block is allowed.
    service = FamilyService(FamilyRepository(db), MemberRepository(db))
    family_in.current_shelter_center_id = 1
    family_in.shelter_block_id = 1
    family = await service.create_family(family_in, block_head_user)
    assert family.current_shelter_center_id == 1
    assert family.shelter_block_id == 1


async def test_block_head_sees_only_own_block(
    db: AsyncSession, sample_lookups, admin_user, block_head_user
):
    """
    A BLOCK_HEAD (block_id=1) must only see families inside their block.
    The families endpoint list is scope-limited to their shelter+block.
    """
    family_id = await _make_family(db, admin_user, shelter_center_id=1, block_id=1)

    service = FamilyService(FamilyRepository(db), MemberRepository(db))
    families = await service.get_families(_filters(), block_head_user)
    assert any(f.id == family_id for f in families)
    assert all(f.shelter_block_id == block_head_user.block_id for f in families)


async def test_block_head_cannot_access_other_block_family(
    db: AsyncSession, sample_lookups, admin_user, block_head_user
):
    """
    Even though the family list for a BLOCK_HEAD is scoped to their block,
    requesting a family by ID from a different block must be denied.
    """
    service = FamilyService(FamilyRepository(db), MemberRepository(db))
    other_family_id = await _make_family(db, admin_user, 1, 999)

    # BLOCK_HEAD user has block_id=1, so this family in block 999 is out of scope.
    with pytest.raises(HTTPException):
        await service.get_family(other_family_id, block_head_user)