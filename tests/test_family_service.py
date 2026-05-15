from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ConflictError, DomainError
from app.models.enums import Gender, MaritalStatus, HousingType, ResidencyStatus
from app.schemas.family import FamilyCreate, FamilyUpdate, MemberCreate, MemberUpdate
from app.services import family_service

pytestmark = pytest.mark.asyncio

HEAD_ID = 100000009
SPOUSE_ID = 200000008
CHILD_ID = 300000007
MEMBER_ID = 400000006


async def _make_family_create() -> FamilyCreate:
    return FamilyCreate(
        head_id=HEAD_ID,
        spouse_id=SPOUSE_ID,
        female_headed=False,
        child_headed=False,
        primary_phone_number="+970599123456",
        secondary_phone_number=None,
        residency_status=ResidencyStatus.DISPLACED,
        housing_type=HousingType.TENT,
        original_governor_id=1,
        original_city_id=1,
        current_governor_id=1,
        current_city_id=1,
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


async def test_create_family(db: AsyncSession, sample_lookups):
    family_in = await _make_family_create()
    family = await family_service.create_family(db, family_in)
    await db.refresh(family, ["members"])
    assert family.id is not None
    assert family.head_id == HEAD_ID
    assert family.spouse_id == SPOUSE_ID
    assert len(family.members) >= 1
    assert family.is_active is True


async def test_create_family_duplicate_head(db: AsyncSession, sample_lookups):
    family_in = await _make_family_create()
    await family_service.create_family(db, family_in)
    with pytest.raises(ConflictError):
        await family_service.create_family(db, family_in)


async def test_get_family(db: AsyncSession, sample_lookups):
    family_in = await _make_family_create()
    created = await family_service.create_family(db, family_in)
    fetched = await family_service.get_family(db, created.id)
    assert fetched.id == created.id
    assert fetched.head_id == HEAD_ID


async def test_get_family_not_found(db: AsyncSession, sample_lookups):
    with pytest.raises(NotFoundError):
        await family_service.get_family(db, 9999)


async def test_get_families(db: AsyncSession, sample_lookups):
    family_in = await _make_family_create()
    await family_service.create_family(db, family_in)
    families = await family_service.get_families(db)
    assert len(families) >= 1


async def test_update_family(db: AsyncSession, sample_lookups):
    family_in = await _make_family_create()
    created = await family_service.create_family(db, family_in)
    update = FamilyUpdate(primary_phone_number="+970599999999")
    updated = await family_service.update_family(db, created.id, update)
    assert updated.primary_phone_number == "+970599999999"
    assert updated.head_id == HEAD_ID


async def test_deactivate_activate_family(db: AsyncSession, sample_lookups):
    family_in = await _make_family_create()
    created = await family_service.create_family(db, family_in)

    archived = await family_service.deactivate_family(db, created.id)
    assert archived.is_active is False
    assert archived.archived_at is not None

    with pytest.raises(DomainError):
        await family_service.deactivate_family(db, created.id)

    restored = await family_service.activate_family(db, created.id)
    assert restored.is_active is True
    assert restored.archived_at is None

    with pytest.raises(DomainError):
        await family_service.activate_family(db, created.id)


async def test_add_member(db: AsyncSession, sample_lookups):
    family_in = await _make_family_create()
    created = await family_service.create_family(db, family_in)

    member_in = MemberCreate(
        id=CHILD_ID,
        full_name="Child",
        gender=Gender.MALE,
        marital_status=MaritalStatus.SINGLE,
        date_of_birth=date(2015, 5, 10),
        relationship_to_head_id=1,
    )
    member = await family_service.add_member(db, created.id, member_in)
    assert member.id == CHILD_ID
    assert member.family_id == created.id


async def test_add_member_duplicate(db: AsyncSession, sample_lookups):
    family_in = await _make_family_create()
    created = await family_service.create_family(db, family_in)

    member_in = MemberCreate(
        id=HEAD_ID,
        full_name="Dupe",
        gender=Gender.MALE,
        marital_status=MaritalStatus.SINGLE,
        date_of_birth=date(2000, 1, 1),
        relationship_to_head_id=1,
    )
    with pytest.raises(ConflictError):
        await family_service.add_member(db, created.id, member_in)


async def test_delete_member(db: AsyncSession, sample_lookups):
    family_in = await _make_family_create()
    created = await family_service.create_family(db, family_in)

    await family_service.delete_member(db, HEAD_ID)

    with pytest.raises(NotFoundError):
        await family_service.delete_member(db, HEAD_ID)


async def test_get_member(db: AsyncSession, sample_lookups):
    family_in = await _make_family_create()
    await family_service.create_family(db, family_in)
    member = await family_service.get_member(db, HEAD_ID)
    assert member.id == HEAD_ID
    assert member.full_name == "Head of Family"


async def test_get_member_not_found(db: AsyncSession, sample_lookups):
    with pytest.raises(NotFoundError):
        await family_service.get_member(db, 999999999)


async def test_update_member(db: AsyncSession, sample_lookups):
    family_in = await _make_family_create()
    await family_service.create_family(db, family_in)
    update = MemberUpdate(injured=True, has_chronic_disease=True)
    updated = await family_service.update_member(db, HEAD_ID, update)
    assert updated.injured is True
    assert updated.has_chronic_disease is True


async def test_get_dashboard_stats(db: AsyncSession, sample_lookups):
    stats = await family_service.get_dashboard_stats(db)
    assert "total_families" in stats
    assert "active_families" in stats
    assert "total_members" in stats
    assert "block_counts" in stats
    assert "center_counts" in stats
