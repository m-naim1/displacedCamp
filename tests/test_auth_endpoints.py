"""Endpoint-level tests for the auth router, using the in-memory test DB:

- staff login success/failure
- family login success/failure (national ID + DOB)
- rate limiting kicks in on repeated family-login attempts (429)
"""

from datetime import date

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_family_service,
    get_member_service,
    get_user_service,
)
from app.api.v1.endpoints import auth as auth_endpoints
from app.core.config import settings
from app.models.enums import (
    Gender,
    HousingType,
    MaritalStatus,
    ResidencyStatus,
)
from app.repositories.familyRepository import FamilyRepository
from app.repositories.MemberRepository import MemberRepository
from app.repositories.userrepository import UserRepository
from app.schemas.family import FamilyCreate, MemberCreate
from app.services.family_service import FamilyService, MemberService
from app.services.user_service import UserService

HEAD_ID = 400000006
SPOUSE_ID = 400000014
HEAD_DOB = "1990-01-15"


def _make_app(db: AsyncSession) -> FastAPI:
    """The real auth router on a test app, backed by the in-memory DB."""
    app = FastAPI()
    app.state.limiter = auth_endpoints.limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.include_router(auth_endpoints.router, prefix=settings.API_V1_STR + "/auth")

    app.dependency_overrides[get_user_service] = lambda: UserService(UserRepository(db))
    app.dependency_overrides[get_family_service] = lambda: FamilyService(
        FamilyRepository(db), MemberRepository(db)
    )
    app.dependency_overrides[get_member_service] = lambda: MemberService(
        MemberRepository(db), FamilyRepository(db)
    )
    return app


def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _seed_family(db: AsyncSession):
    svc = FamilyService(FamilyRepository(db), MemberRepository(db))
    return await svc.create_family(
        FamilyCreate(
            head_id=HEAD_ID,
            spouse_id=SPOUSE_ID,
            primary_phone_number="+970599123456",
            residency_status=ResidencyStatus.DISPLACED,
            housing_type=HousingType.TENT,
            original_city_id=1,
            current_shelter_center_id=1,
            shelter_block_id=1,
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
        ),
        # created without audit to keep this test focused on auth
        None,
    )


async def test_staff_login_success_and_failure(db: AsyncSession, admin_user):
    app = _make_app(db)
    async with _client(app) as client:
        ok = await client.post(
            "/api/v1/auth/login", data={"username": "admin", "password": "password123"}
        )
        assert ok.status_code == 200
        body = ok.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]

        bad = await client.post(
            "/api/v1/auth/login", data={"username": "admin", "password": "wrong"}
        )
        assert bad.status_code == 401


async def test_family_login_success_and_failure(db: AsyncSession, sample_lookups):
    await _seed_family(db)
    app = _make_app(db)
    async with _client(app) as client:
        ok = await client.post(
            "/api/v1/auth/family-login",
            json={"national_id": HEAD_ID, "date_of_birth": HEAD_DOB},
        )
        assert ok.status_code == 200
        body = ok.json()
        assert body["token_type"] == "bearer"

        wrong_dob = await client.post(
            "/api/v1/auth/family-login",
            json={"national_id": HEAD_ID, "date_of_birth": "1980-01-01"},
        )
        assert wrong_dob.status_code == 401

        non_head = await client.post(
            "/api/v1/auth/family-login",
            json={"national_id": SPOUSE_ID, "date_of_birth": "1992-04-22"},
        )
        assert non_head.status_code == 401  # spouse is not the head


async def test_family_login_rate_limited(db: AsyncSession, sample_lookups):
    """Repeated failed attempts get cut off with 429 once the limit is hit."""
    await _seed_family(db)
    limit = int(settings.AUTH_RATE_LIMIT.split("/")[0])
    app = _make_app(db)
    async with _client(app) as client:
        statuses = []
        for _ in range(limit + 3):
            resp = await client.post(
                "/api/v1/auth/family-login",
                json={"national_id": HEAD_ID, "date_of_birth": "1980-01-01"},
            )
            statuses.append(resp.status_code)

    assert 401 in statuses  # real attempts were processed first…
    assert statuses[-1] == 429  # …then the limiter took over
    assert statuses.count(429) >= 1
    # The 429s must all come after the last 401
    assert statuses.index(429) > len([s for s in statuses if s == 401]) - 1
