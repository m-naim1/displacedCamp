import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ConflictError
from app.models.user import User
from app.models.enums import UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.services import user_service
from app.core.security import verify_password


pytestmark = pytest.mark.asyncio


async def test_create_user(db: AsyncSession):
    user_in = UserCreate(
        username="newuser",
        email="new@example.com",
        full_name="New User",
        password="testpass123",
        role=UserRole.MANAGER,
    )
    user = await user_service.create_user(db, user_in)
    assert user.id is not None
    assert user.username == "newuser"
    assert user.role == UserRole.MANAGER
    assert user.is_active is True
    assert verify_password("testpass123", user.hashed_password)


async def test_create_user_duplicate(db: AsyncSession):
    user_in = UserCreate(
        username="dupuser",
        email="dup@example.com",
        full_name="Dup",
        password="pass123",
        role=UserRole.MANAGER,
    )
    await user_service.create_user(db, user_in)
    with pytest.raises(ConflictError):
        await user_service.create_user(db, user_in)


async def test_get_user_by_username(db: AsyncSession, manager_user):
    user = await user_service.get_user_by_username(db, "manager")
    assert user is not None
    assert user.username == "manager"

    missing = await user_service.get_user_by_username(db, "nonexistent")
    assert missing is None


async def test_get_active_user_by_username(db: AsyncSession, manager_user):
    user = await user_service.get_active_user_by_username(db, "manager")
    assert user is not None

    user.is_active = False
    await db.commit()

    user = await user_service.get_active_user_by_username(db, "manager")
    assert user is None


async def test_get_user_by_id(db: AsyncSession, manager_user):
    user = await user_service.get_user_by_id(db, manager_user.id)
    assert user.id == manager_user.id

    with pytest.raises(NotFoundError):
        await user_service.get_user_by_id(db, 9999)


async def test_get_users(db: AsyncSession, admin_user, manager_user):
    users = await user_service.get_users(db)
    assert len(users) >= 2


async def test_update_user(db: AsyncSession, manager_user):
    update = UserUpdate(full_name="Updated Name")
    user = await user_service.update_user(db, manager_user.id, update)
    assert user.full_name == "Updated Name"


async def test_authenticate_user(db: AsyncSession):
    user_in = UserCreate(
        username="authuser",
        email="auth@test.com",
        full_name="Auth User",
        password="correctpass",
        role=UserRole.MANAGER,
    )
    await user_service.create_user(db, user_in)

    user = await user_service.authenticate_user(db, "authuser", "correctpass")
    assert user is not None
    assert user.username == "authuser"

    bad_pass = await user_service.authenticate_user(db, "authuser", "wrongpass")
    assert bad_pass is None

    bad_user = await user_service.authenticate_user(db, "nobody", "pass")
    assert bad_user is None


async def test_deactivate_activate_user(db: AsyncSession, manager_user):
    await user_service.deactivate_user(db, manager_user.id)
    user = await user_service.get_user_by_id(db, manager_user.id)
    assert user.is_active is False

    await user_service.activate_user(db, manager_user.id)
    user = await user_service.get_user_by_id(db, manager_user.id)
    assert user.is_active is True


async def test_deactivate_twice_no_error(db: AsyncSession, manager_user):
    await user_service.deactivate_user(db, manager_user.id)
    await user_service.deactivate_user(db, manager_user.id)  # should not raise
