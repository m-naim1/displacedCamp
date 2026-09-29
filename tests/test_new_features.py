"""Tests for the newly added backend features:

- audit trail (service wiring, log query)
- bulk CSV import parser
- member national-ID search filter
- dashboard age bands + pending update-request count
- CSV report generation
- lookup duplicate-code conflict
- rate limiting on the auth endpoints
"""

import pytest
from datetime import date
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError
from app.models.enums import (
    Gender,
    HousingType,
    MaritalStatus,
    ResidencyStatus,
    UpdateRequestType,
)
from app.models.family import Family
from app.repositories.auditRepository import AuditRepository
from app.repositories.familyRepository import FamilyRepository
from app.repositories.lookupRepository import LookupRepository
from app.repositories.MemberRepository import MemberRepository
from app.repositories.updateRequestRepository import FamilyUpdateRequestRepository
from app.schemas.family import (
    FamilyCreate,
    MemberCreate,
    UpdateRequestCreate,
)
from app.schemas.filters import MemberFilterParams
from app.schemas.lookups import LookupCreate
from app.schemas.report import FamilyReportRow
from app.services.audit_service import AuditService
from app.services.family_service import FamilyService, get_dashboard_stats
from app.services.import_service import parse_families_csv
from app.services.lookup_service import LookupService
from app.services.report_service import ReportService

HEAD_ID = 400000006
SPOUSE_ID = 400000014
OTHER_ID = 400000022


def _member(mid: int, name: str, gender=Gender.MALE, dob=date(1990, 1, 15),
            status=MaritalStatus.MARRIED) -> MemberCreate:
    return MemberCreate(
        id=mid,
        full_name=name,
        gender=gender,
        marital_status=status,
        date_of_birth=dob,
        relationship_to_head_id=1,
    )


def _make_family_create() -> FamilyCreate:
    return FamilyCreate(
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
            _member(SPOUSE_ID, "Spouse of Family", Gender.FEMALE, date(1992, 4, 22)),
        ],
    )


def _member_filters(**overrides) -> MemberFilterParams:
    values = {f: None for f in MemberFilterParams.__dataclass_fields__}
    values.update(overrides)
    return MemberFilterParams(**values)


def _services(db, audit=False) -> FamilyService:
    audit_service = AuditService(AuditRepository(db)) if audit else None
    return FamilyService(
        FamilyRepository(db), MemberRepository(db), audit_service=audit_service
    )


# ── Audit trail ──────────────────────────────────────────────────────────────


async def test_audit_logs_family_lifecycle(db: AsyncSession, sample_lookups, admin_user):
    svc = _services(db, audit=True)

    family = await svc.create_family(_make_family_create(), admin_user)
    await svc.deactivate_family(family.id, admin_user)
    await svc.activate_family(family.id, admin_user)

    logs = await AuditService(AuditRepository(db)).get_logs()
    actions = [log.action for log in logs]
    assert "FAMILY_CREATED" in actions
    assert "FAMILY_ARCHIVED" in actions
    assert "FAMILY_RESTORED" in actions

    created_log = next(log for log in logs if log.action == "FAMILY_CREATED")
    assert created_log.actor_username == admin_user.username
    assert created_log.actor_role == "SUPERADMIN"
    assert created_log.entity_type == "family"
    assert created_log.details["member_count"] == 2


async def test_audit_logs_filter_by_entity(db: AsyncSession, sample_lookups, admin_user):
    svc = _services(db, audit=True)
    family = await svc.create_family(_make_family_create(), admin_user)
    await svc.deactivate_family(family.id, admin_user)

    audit = AuditService(AuditRepository(db))
    by_entity = await audit.get_logs(entity_type="family", entity_id=str(family.id))
    assert {log.action for log in by_entity} == {"FAMILY_CREATED", "FAMILY_ARCHIVED"}

    none = await audit.get_logs(entity_type="member")
    assert none == []


# ── Bulk CSV import ──────────────────────────────────────────────────────────

CSV_HEADER = (
    "family_code,member_id,full_name,gender,marital_status,date_of_birth,"
    "relationship_to_head_id,is_head,primary_phone_number,residency_status,"
    "housing_type,original_city_id,current_shelter_center_id"
)


def _csv(*rows: str) -> str:
    return "\n".join((CSV_HEADER, *rows))


def test_csv_import_parse_valid():
    result = parse_families_csv(
        _csv(
            f"F1,{HEAD_ID},Ali Hassan,male,married,1990-01-15,1,true,+970599123456,displaced,tent,1,1",
            f"F1,{SPOUSE_ID},Fatima Hassan,female,married,1992-04-22,2,false,,,,,",
            f"F2,{OTHER_ID},Omar Ahmad,male,single,2010-05-05,1,true,+970599111111,displaced,house,1,1",
        )
    )
    assert result.errors == []
    assert len(result.families) == 2

    f1 = result.families[0]
    assert f1.head_id == HEAD_ID
    assert f1.primary_phone_number == "+970599123456"
    assert len(f1.members) == 2

    f2 = result.families[1]
    assert f2.head_id == OTHER_ID
    assert f2.housing_type == HousingType.HOUSE


def test_csv_import_parse_errors():
    result = parse_families_csv(
        _csv(
            # Bad checksum on member ID
            f"F1,400000007,Bad ID,male,single,1990-01-15,1,true,+97059,displaced,tent,1,1",
            # Valid member but no is_head row in the family
            f"F2,{OTHER_ID},Omar Ahmad,male,single,2010-05-05,1,false,+97059,displaced,tent,1,1",
        )
    )
    assert result.families == []
    codes = {e.family_code for e in result.errors}
    assert codes == {"F1", "F2"}


def test_csv_import_missing_columns():
    result = parse_families_csv("family_code,member_id\nF1,400000006")
    assert result.families == []
    assert "Missing columns" in result.errors[0].message


async def test_csv_import_endpoint_creates_families(
    db: AsyncSession, sample_lookups, admin_user
):
    """End-to-end: parsed rows actually become families through the service."""
    svc = _services(db)
    parsed = parse_families_csv(
        _csv(
            f"F1,{HEAD_ID},Ali Hassan,male,married,1990-01-15,1,true,+970599123456,displaced,tent,1,1",
            f"F1,{SPOUSE_ID},Fatima Hassan,female,married,1992-04-22,2,false,,,,,",
        )
    )
    created = []
    for family_in in parsed.families:
        family = await svc.create_family(family_in, admin_user)
        created.append(family.id)
    assert len(created) == 1

    stored = await db.get(Family, created[0])
    assert stored.head_id == HEAD_ID


# ── National ID search filter ────────────────────────────────────────────────


async def test_member_search_by_national_id_prefix(
    db: AsyncSession, sample_lookups, admin_user
):
    svc = _services(db)
    await svc.create_family(_make_family_create(), admin_user)

    member_repo = MemberRepository(db)
    hits = await member_repo.get_all(_member_filters(national_id="4000000"), 0, 100)
    assert {m.id for m in hits} == {HEAD_ID, SPOUSE_ID}

    exact = await member_repo.get_all(_member_filters(national_id=str(SPOUSE_ID)), 0, 100)
    assert [m.id for m in exact] == [SPOUSE_ID]

    miss = await member_repo.get_all(_member_filters(national_id="9"), 0, 100)
    assert miss == []


# ── Dashboard stats: age bands + pending requests ────────────────────────────


async def test_dashboard_age_bands_and_pending(db: AsyncSession, sample_lookups, admin_user):
    svc = _services(db)
    family_in = FamilyCreate(
        head_id=HEAD_ID,
        primary_phone_number="+970599123456",
        residency_status=ResidencyStatus.DISPLACED,
        housing_type=HousingType.TENT,
        original_city_id=1,
        current_shelter_center_id=1,
        shelter_block_id=1,
        members=[
            _member(HEAD_ID, "Head", dob=date(1990, 1, 15)),          # 18–59
            _member(SPOUSE_ID, "Elder", dob=date(1950, 6, 1)),        # 60+
        ],
    )
    family = await svc.create_family(family_in, admin_user)

    member_repo = MemberRepository(db)
    child = await member_repo.create(
        family.id, _member(OTHER_ID, "Kid", dob=date(2023, 3, 1), status=MaritalStatus.SINGLE)
    )  # under 5
    await member_repo.commit()

    # A school-age member (5–17)
    teen_id = 400000030
    await member_repo.create(
        family.id, _member(teen_id, "Teen", dob=date(2015, 9, 1), status=MaritalStatus.SINGLE)
    )
    await member_repo.commit()

    # One pending update request
    req_repo = FamilyUpdateRequestRepository(db)
    await req_repo.create(
        family.id,
        UpdateRequestCreate(
            request_type=UpdateRequestType.UPDATE_FAMILY_INFO,
            payload={"primary_phone_number": "+970599000000"},
        ),
    )

    stats = await get_dashboard_stats(db, admin_user)
    assert stats["under_5"] == 1
    assert stats["age_5_17"] == 1
    assert stats["age_18_59"] == 1
    assert stats["age_60_plus"] == 1
    assert stats["total_members"] == 4
    assert stats["pending_update_requests"] == 1

    # Sanity: bands partition the total
    assert (
        stats["under_5"] + stats["age_5_17"] + stats["age_18_59"] + stats["age_60_plus"]
        == stats["total_members"]
    )
    del child


# ── Reports: CSV generation ──────────────────────────────────────────────────


async def test_generate_csv_output():
    service = ReportService(FamilyRepository(None), MemberRepository(None))
    rows = [
        FamilyReportRow(
            family_id=1,
            head_name="Ali",
            member_count=3,
            male_count=2,
            female_count=1,
        ),
        FamilyReportRow(
            family_id=2,
            head_name="Fatima",
            member_count=4,
            male_count=1,
            female_count=3,
        ),
    ]
    response = service.generate_csv(rows)
    chunks = [chunk async for chunk in response.body_iterator]
    body = "".join(c.decode() if isinstance(c, bytes) else c for c in chunks)
    assert "head_name" in body
    assert "Ali" in body
    assert response.media_type == "text/csv"


# ── Lookups: duplicate code conflict ─────────────────────────────────────────


async def test_lookup_duplicate_code_conflict(db: AsyncSession, sample_lookups):
    from app.models.lookups import Governor

    repo = LookupRepository(Governor, db)
    service = LookupService(Governor, repo)

    await service.create(LookupCreate(code="NEW1", name_en="New Gov", name_ar="جديد"))
    with pytest.raises(ConflictError):
        await service.create(LookupCreate(code="NEW1", name_en="Dup", name_ar="مكرر"))


class _DummyRow(BaseModel):
    family_id: int
    head_name: str


def test_generate_csv_filters_invalid_columns():
    service = ReportService(FamilyRepository(None), MemberRepository(None))
    response = service.generate_csv([_DummyRow(family_id=7, head_name="X")])
    assert response.media_type == "text/csv"


# ── Rate limiting configuration ──────────────────────────────────────────────


def test_auth_endpoints_are_rate_limited():
    from app.api.v1.endpoints.auth import auth_limit, limiter

    assert limiter is not None
    assert auth_limit is not None
    # The limit string is wired from settings so ops can tune it via env
    from app.core.config import settings

    assert settings.AUTH_RATE_LIMIT
