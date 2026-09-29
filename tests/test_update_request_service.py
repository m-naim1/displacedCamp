from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError, NotFoundError, ValidationError
from app.models.enums import (
    Gender,
    HousingType,
    MaritalStatus,
    ResidencyStatus,
    UpdateRequestStatus,
    UpdateRequestType,
)
from app.models.user import User
from app.repositories.familyRepository import FamilyRepository
from app.repositories.MemberRepository import MemberRepository
from app.repositories.updateRequestRepository import FamilyUpdateRequestRepository
from app.schemas.family import FamilyCreate, MemberCreate, UpdateRequestCreate
from app.services.family_service import FamilyService
from app.services.update_request_service import UpdateRequestService

pytestmark = pytest.mark.asyncio

HEAD_ID = 400000006
SPOUSE_ID = 400000014
NEW_MEMBER_ID = 400000048


async def _make_family(db: AsyncSession, admin_user: User) -> int:
    family_in = FamilyCreate(
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
        ],
    )
    service = FamilyService(FamilyRepository(db), MemberRepository(db))
    family = await service.create_family(family_in, admin_user)
    return family.id


def _service(db: AsyncSession) -> UpdateRequestService:
    return UpdateRequestService(
        update_request_repo=FamilyUpdateRequestRepository(db),
        family_repo=FamilyRepository(db),
        member_repo=MemberRepository(db),
    )


async def test_create_add_member_request(db: AsyncSession, sample_lookups, admin_user):
    family_id = await _make_family(db, admin_user)
    req_in = UpdateRequestCreate(
        request_type=UpdateRequestType.ADD_MEMBER,
        payload={
            "id": NEW_MEMBER_ID,
            "full_name": "Newborn",
            "gender": "female",
            "marital_status": "single",
            "date_of_birth": "2024-01-01T00:00:00",
            "relationship_to_head_id": 1,
        },
    )
    req = await _service(db).create_request(family_id, req_in)
    assert req.id is not None
    assert req.family_id == family_id
    assert req.status == UpdateRequestStatus.PENDING


async def test_create_change_head_requires_head_id(
    db: AsyncSession, sample_lookups, admin_user
):
    family_id = await _make_family(db, admin_user)
    req_in = UpdateRequestCreate(
        request_type=UpdateRequestType.CHANGE_HEAD, payload={}
    )
    with pytest.raises(ValidationError):
        await _service(db).create_request(family_id, req_in)


async def test_create_update_family_info_request(
    db: AsyncSession, sample_lookups, admin_user
):
    family_id = await _make_family(db, admin_user)
    req_in = UpdateRequestCreate(
        request_type=UpdateRequestType.UPDATE_FAMILY_INFO,
        payload={"primary_phone_number": "+970599111111"},
    )
    req = await _service(db).create_request(family_id, req_in)
    assert req.status == UpdateRequestStatus.PENDING


async def test_create_update_member_info_unknown_member(
    db: AsyncSession, sample_lookups, admin_user
):
    family_id = await _make_family(db, admin_user)
    req_in = UpdateRequestCreate(
        request_type=UpdateRequestType.UPDATE_MEMBER_INFO,
        payload={"id": 999999999, "disabled": True},
    )
    with pytest.raises(NotFoundError):
        await _service(db).create_request(family_id, req_in)


async def test_get_scoped_pending_requests(
    db: AsyncSession, sample_lookups, admin_user
):
    family_id = await _make_family(db, admin_user)
    req_in = UpdateRequestCreate(
        request_type=UpdateRequestType.UPDATE_FAMILY_INFO,
        payload={"primary_phone_number": "+970599111111"},
    )
    await _service(db).create_request(family_id, req_in)

    pending = await _service(db).get_scoped_pending_requests(admin_user)
    assert len(pending) >= 1


async def test_approve_update_family_info(
    db: AsyncSession, sample_lookups, admin_user
):
    family_id = await _make_family(db, admin_user)
    req_in = UpdateRequestCreate(
        request_type=UpdateRequestType.UPDATE_FAMILY_INFO,
        payload={"primary_phone_number": "+970599111111"},
    )
    req = await _service(db).create_request(family_id, req_in)

    approved = await _service(db).approve_request(req.id, admin_user)
    assert approved.status == UpdateRequestStatus.APPROVED
    assert approved.reviewed_by_id == admin_user.id
    assert approved.reviewed_at is not None


async def test_approve_add_member(
    db: AsyncSession, sample_lookups, admin_user
):
    family_id = await _make_family(db, admin_user)
    req_in = UpdateRequestCreate(
        request_type=UpdateRequestType.ADD_MEMBER,
        payload={
            "id": NEW_MEMBER_ID,
            "full_name": "Newborn",
            "gender": "female",
            "marital_status": "single",
            "date_of_birth": "2024-01-01T00:00:00",
            "relationship_to_head_id": 1,
        },
    )
    req = await _service(db).create_request(family_id, req_in)
    approved = await _service(db).approve_request(req.id, admin_user)
    assert approved.status == UpdateRequestStatus.APPROVED

    member_repo = MemberRepository(db)
    member = await member_repo.get_by_id(NEW_MEMBER_ID)
    assert member is not None
    assert member.family_id == family_id


async def test_approve_already_reviewed(
    db: AsyncSession, sample_lookups, admin_user
):
    family_id = await _make_family(db, admin_user)
    req_in = UpdateRequestCreate(
        request_type=UpdateRequestType.UPDATE_FAMILY_INFO,
        payload={"primary_phone_number": "+970599111111"},
    )
    req = await _service(db).create_request(family_id, req_in)
    await _service(db).approve_request(req.id, admin_user)
    with pytest.raises(DomainError):
        await _service(db).approve_request(req.id, admin_user)


async def test_reject_request(db: AsyncSession, sample_lookups, admin_user):
    family_id = await _make_family(db, admin_user)
    req_in = UpdateRequestCreate(
        request_type=UpdateRequestType.UPDATE_FAMILY_INFO,
        payload={"primary_phone_number": "+970599111111"},
    )
    req = await _service(db).create_request(family_id, req_in)

    rejected = await _service(db).reject_request(req.id, admin_user)
    assert rejected.status == UpdateRequestStatus.REJECTED


async def test_review_request_not_found(db: AsyncSession, sample_lookups, admin_user):
    with pytest.raises(NotFoundError):
        await _service(db).approve_request(99999, admin_user)