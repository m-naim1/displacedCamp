import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.security import get_password_hash
from app.db.session import Base
from app.models.family import Family, Member  # noqa: F401
from app.models.user import User, BlockHeadPermission  # noqa: F401
from app.models.update_request import UpdateRequest  # noqa: F401
from app.models.lookups import (  # noqa: F401
    Governor, City, RelationshipToHead, ShelterQuality, ShelterBlock, ShelterCenter,
)
from app.models.enums import UserRole

TEST_DB_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestAsyncSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)


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
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with TestAsyncSessionLocal() as session:
        yield session


def _make_user_kwargs(overrides: dict = None) -> dict:
    kwargs = {
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "hashed_password": get_password_hash("password123"),
        "role": UserRole.MANAGER,
        "is_active": True,
    }
    if overrides:
        kwargs.update(overrides)
    return kwargs


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> User:
    u = User(**_make_user_kwargs({"username": "admin", "role": UserRole.SUPERADMIN, "email": "admin@test.com"}))
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest_asyncio.fixture
async def manager_user(db: AsyncSession) -> User:
    u = User(**_make_user_kwargs({"username": "manager", "role": UserRole.MANAGER, "email": "manager@test.com"}))
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest_asyncio.fixture
async def block_head_user(db: AsyncSession) -> User:
    block = ShelterBlock(id=1, code="B1", name_en="Block 1", name_ar="كتلة 1", is_active=True, shelter_center_id=1)
    db.add(block)
    await db.flush()
    u = User(**_make_user_kwargs({
        "username": "blockhead",
        "role": UserRole.BLOCK_HEAD,
        "email": "bh@test.com",
        "block_id": 1,
    }))
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest_asyncio.fixture
async def sample_lookups(db: AsyncSession):
    gov = Governor(id=1, code="GZA", name_en="Gaza", name_ar="غزة", is_active=True)
    city = City(id=1, code="GZA-CITY", name_en="Gaza City", name_ar="مدينة غزة", is_active=True, governor_id=1)
    center = ShelterCenter(id=1, code="C1", name_en="Center 1", name_ar="مركز 1", is_active=True, city_id=1)
    block = ShelterBlock(id=1, code="B1", name_en="Block 1", name_ar="كتلة 1", is_active=True, shelter_center_id=1)
    quality = ShelterQuality(id=1, code="Q1", name_en="Good", name_ar="جيد", is_active=True)
    rel = RelationshipToHead(id=1, code="HEAD", name_en="Head", name_ar="رب الأسرة", is_active=True)
    rel2 = RelationshipToHead(id=2, code="SPOUSE", name_en="Spouse", name_ar="زوج/ة", is_active=True)
    for obj in [gov, city, center, block, quality, rel, rel2]:
        db.add(obj)
    await db.commit()
