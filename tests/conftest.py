import asyncio
import re
from collections.abc import AsyncGenerator
from datetime import date, datetime

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import get_password_hash
from app.db.session import Base
from app.models.enums import UserRole
from app.models.family import Family, FamilyUpdateRequest, Member  # noqa: F401
from app.models.lookups import (  # noqa: F401
    City,
    Governor,
    RelationshipToHead,
    ShelterBlock,
    ShelterCenter,
    ShelterQuality,
)
from app.models.user import User  # noqa: F401

TEST_DB_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(
    TEST_DB_URL, connect_args={"check_same_thread": False}
)
TestAsyncSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)


def _to_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").split(" ")[0]
    return date.fromisoformat(text) if text else date(1900, 1, 1)


def _sqlite_age(end, start) -> str:
    """Emulates Postgres `age(x, y)` for SQLite test runs (whole months only)."""
    e, s = _to_date(end), _to_date(start)
    months = (e.year - s.year) * 12 + (e.month - s.month)
    if e.day < s.day:
        months -= 1
    years, months = divmod(max(months, 0), 12)
    return f"{years} years {months} mons 0 days"


def _sqlite_date_part(field, interval) -> float:
    """Emulates Postgres `date_part('year', interval)` for SQLite test runs."""
    if field != "year":
        return 0.0
    match = re.match(r"(\d+) years?", str(interval or "0"))
    return float(match.group(1)) if match else 0.0


@event.listens_for(test_engine.sync_engine, "connect")
def _register_sqlite_date_helpers(dbapi_connection, _record):
    dbapi_connection.create_function("age", 2, _sqlite_age)
    dbapi_connection.create_function("date_part", 2, _sqlite_date_part)


@pytest.fixture(scope="session", autouse=True)
def _dispose_engine():
    yield
    asyncio.run(test_engine.dispose())


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    async with TestAsyncSessionLocal() as session:
        yield session


def _make_user(overrides: dict | None = None) -> User:
    """Builds a User with scope fields assigned BEFORE role so the role
    validator sees block_id / shelter_id."""
    o = overrides or {}
    u = User(
        username=o.get("username", "testuser"),
        email=o.get("email", "test@example.com"),
        full_name=o.get("full_name", "Test User"),
    )
    u.block_id = o.get("block_id")
    u.shelter_id = o.get("shelter_id")
    u.role = o.get("role", UserRole.MANAGER)
    u.is_active = True
    return u


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> User:
    u = _make_user(
        {"username": "admin", "role": UserRole.SUPERADMIN, "email": "admin@test.com"}
    )
    u.hashed_password = await get_password_hash("password123")
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest_asyncio.fixture
async def manager_user(db: AsyncSession, sample_lookups) -> User:
    u = _make_user(
        {
            "username": "manager",
            "role": UserRole.MANAGER,
            "email": "manager@test.com",
            "shelter_id": 1,
        }
    )
    u.hashed_password = await get_password_hash("password123")
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest_asyncio.fixture
async def block_head_user(db: AsyncSession, sample_lookups) -> User:
    u = _make_user(
        {
            "username": "blockhead",
            "role": UserRole.BLOCK_HEAD,
            "email": "bh@test.com",
            "block_id": 1,
        }
    )
    u.hashed_password = await get_password_hash("password123")
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest_asyncio.fixture
async def sample_lookups(db: AsyncSession):
    gov = Governor(id=1, code="GZA", name_en="Gaza", name_ar="غزة", is_active=True)
    city = City(
        id=1,
        code="GZA-CITY",
        name_en="Gaza City",
        name_ar="مدينة غزة",
        is_active=True,
        governor_id=1,
    )
    center = ShelterCenter(
        id=1, code="C1", name_en="Center 1", name_ar="مركز 1", is_active=True, city_id=1
    )
    block = ShelterBlock(
        id=1,
        code="B1",
        name_en="Block 1",
        name_ar="كتلة 1",
        is_active=True,
        shelter_center_id=1,
    )
    quality = ShelterQuality(
        id=1, code="Q1", name_en="Good", name_ar="جيد", is_active=True
    )
    rel = RelationshipToHead(
        id=1, code="HEAD", name_en="Head", name_ar="رب الأسرة", is_active=True
    )
    rel2 = RelationshipToHead(
        id=2, code="SPOUSE", name_en="Spouse", name_ar="زوج/ة", is_active=True
    )
    for obj in [gov, city, center, block, quality, rel, rel2]:
        db.add(obj)
    await db.commit()