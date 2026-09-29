from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.enums import Gender, HousingType, MaritalStatus, ResidencyStatus
from app.repositories.familyRepository import FamilyRepository
from app.repositories.MemberRepository import MemberRepository
from app.schemas.family import FamilyCreate, FamilyUpdate, MemberCreate, MemberUpdate
from app.schemas.filters import FamilyFilterParams, MemberFilterParams
from app.services.family_service import (
    FamilyService,
    MemberService,
    get_dashboard_stats,
)

pytestmark = pytest.mark.asyncio

HEAD_ID = 400000006
SPOUSE_ID = 400000014
CHILD_ID = 400000022
MEMBER_ID = 400000030


def _make_family_create() -> FamilyCreate:
    return FamilyCreate(
        head_id=HEAD_ID,
        spouse_id=SPOUSE_ID,
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
            MemberCreate(
                id=SPOUSE_ID,
                full_name="Spouse of Family",
                gender=Gender.FEMALE,
                marital_status=MaritalStatus.MARRIED,
                date_of_birth=date(1992, 4, 22),
                relationship_to_head_id=2,
            ),
        ],
    )


def _empty_family_filters() -> FamilyFilterParams:
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


def _empty_member_filters() -> MemberFilterParams:
    return MemberFilterParams(
        family_id=None,
        gender=None,
        marital_status=None,
        relationship_to_head_id=None,
        current_shelter_center_id=None,
        shelter_block_id=None,
        has_chronic_disease=None,
        injured=None,
        disabled=None,
        pregnant=None,
        breastfeeding=None,
        dob_from=None,
        dob_to=None,
        full_name=None,
        sort_by=None,
        sort_order=None,
    )


def _family_service(db: AsyncSession) -> FamilyService:
    return FamilyService(FamilyRepository(db), MemberRepository(db))


def _member_service(db: AsyncSession) -> MemberService:
    return MemberService(MemberRepository(db), FamilyRepository(db))


async def test_create_family(db: AsyncSession, sample_lookups, admin_user):
    family = await _family_service(db).create_family(_make_family_create(), admin_user)
    assert family.id is not None
    assert family.head_id == HEAD_ID
    assert family.spouse_id == SPOUSE_ID
    assert len(family.members) == 2
    assert family.is_active is True


async def test_create_family_duplicate_head(
    db: AsyncSession, sample_lookups, admin_user
):
    service = _family_service(db)
    await service.create_family(_make_family_create(), admin_user)
    with pytest.raises(ConflictError):
        await service.create_family(_make_family_create(), admin_user)


async def test_get_family(db: AsyncSession, sample_lookups, admin_user):
    service = _family_service(db)
    created = await service.create_family(_make_family_create(), admin_user)
    fetched = await service.get_family(created.id, admin_user)
    assert fetched.id == created.id
    assert fetched.head_id == HEAD_ID


async def test_get_family_not_found(db: AsyncSession, sample_lookups, admin_user):
    with pytest.raises(NotFoundError):
        await _family_service(db).get_family(9999, admin_user)


async def test_get_families(db: AsyncSession, sample_lookups, admin_user):
    service = _family_service(db)
    await service.create_family(_make_family_create(), admin_user)
    families = await service.get_families(_empty_family_filters(), admin_user)
    assert len(families) >= 1


async def test_get_families_scoped_to_manager(
    db: AsyncSession, sample_lookups, admin_user, manager_user
):
    service = _family_service(db)
    await service.create_family(_make_family_create(), admin_user)
    families = await service.get_families(_empty_family_filters(), manager_user)
    assert len(families) >= 1
    assert all(f.current_shelter_center_id == manager_user.shelter_id for f in families)


async def test_update_family(db: AsyncSession, sample_lookups, admin_user):
    service = _family_service(db)
    created = await service.create_family(_make_family_create(), admin_user)
    update = FamilyUpdate(primary_phone_number="+970599999999")
    updated = await service.update_family(created.id, update, admin_user)
    assert updated.primary_phone_number == "+970599999999"
    assert updated.head_id == HEAD_ID


async def test_deactivate_activate_family(db: AsyncSession, sample_lookups, admin_user):
    service = _family_service(db)
    created = await service.create_family(_make_family_create(), admin_user)

    archived = await service.deactivate_family(created.id, admin_user)
    assert archived.is_active is False
    assert archived.archived_at is not None

    restored = await service.activate_family(created.id, admin_user)
    assert restored.is_active is True
    assert restored.archived_at is None


async def test_add_member(db: AsyncSession, sample_lookups, admin_user):
    service = _family_service(db)
    created = await service.create_family(_make_family_create(), admin_user)

    member_in = MemberCreate(
        id=CHILD_ID,
        full_name="Child",
        gender=Gender.MALE,
        marital_status=MaritalStatus.SINGLE,
        date_of_birth=date(2015, 5, 10),
        relationship_to_head_id=1,
    )
    member = await _member_service(db).add_member(created.id, member_in, admin_user)
    assert member.id == CHILD_ID
    assert member.family_id == created.id


async def test_add_member_duplicate(db: AsyncSession, sample_lookups, admin_user):
    service = _family_service(db)
    created = await service.create_family(_make_family_create(), admin_user)

    member_in = MemberCreate(
        id=HEAD_ID,
        full_name="Dupe",
        gender=Gender.MALE,
        marital_status=MaritalStatus.SINGLE,
        date_of_birth=date(2000, 1, 1),
        relationship_to_head_id=1,
    )
    with pytest.raises(ConflictError):
        await _member_service(db).add_member(created.id, member_in, admin_user)


async def test_delete_member(db: AsyncSession, sample_lookups, admin_user):
    service = _family_service(db)
    created = await service.create_family(_make_family_create(), admin_user)
    member_service = _member_service(db)

    await member_service.delete_member(HEAD_ID, admin_user)
    assert created is not None

    with pytest.raises(NotFoundError):
        await member_service.delete_member(HEAD_ID, admin_user)


async def test_get_member(db: AsyncSession, sample_lookups, admin_user):
    service = _family_service(db)
    await service.create_family(_make_family_create(), admin_user)
    member = await _member_service(db).get_member(HEAD_ID, admin_user)
    assert member.id == HEAD_ID
    assert member.full_name == "Head of Family"


async def test_get_member_not_found(db: AsyncSession, sample_lookups, admin_user):
    with pytest.raises(NotFoundError):
        await _member_service(db).get_member(999999999, admin_user)


async def test_update_member(db: AsyncSession, sample_lookups, admin_user):
    service = _family_service(db)
    await service.create_family(_make_family_create(), admin_user)
    update = MemberUpdate(injured=True, has_chronic_disease=True)
    updated = await _member_service(db).update_member(HEAD_ID, update, admin_user)
    assert updated.injured is True
    assert updated.has_chronic_disease is True


async def test_update_member_pregnancy_invalid(
    db: AsyncSession, sample_lookups, admin_user
):
    service = _family_service(db)
    await service.create_family(_make_family_create(), admin_user)
    update = MemberUpdate(pregnant=True)
    from app.core.errors import ValidationError

    with pytest.raises(ValidationError):
        await _member_service(db).update_member(HEAD_ID, update, admin_user)


async def test_get_dashboard_stats(db: AsyncSession, sample_lookups, admin_user):
    service = _family_service(db)
    await service.create_family(_make_family_create(), admin_user)
    stats = await get_dashboard_stats(db, admin_user)
    assert "total_families" in stats
    assert "active_families" in stats
    assert "total_members" in stats
    assert "block_counts" in stats
    assert "center_counts" in stats