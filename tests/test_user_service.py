import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.core.security import verify_password
from app.models.enums import UserRole
from app.repositories.userrepository import UserRepository
from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService

pytestmark = pytest.mark.asyncio


def _service(db: AsyncSession) -> UserService:
    return UserService(UserRepository(db))


def _user_create(
    username: str = "newuser",
    email: str = "new@example.com",
    role: UserRole = UserRole.MANAGER,
    block_id: int | None = None,
    shelter_id: int | None = None,
) -> UserCreate:
    return UserCreate(
        username=username,
        email=email,
        full_name="New User",
        password="testpass123",
        role=role,
        block_id=block_id,
        shelter_id=shelter_id,
    )


async def test_create_manager(db: AsyncSession, manager_user):
    user = await _service(db).create_user(
        _user_create(username="manager2", shelter_id=1)
    )
    assert user.id is not None
    assert user.role == UserRole.MANAGER
    assert user.shelter_id == 1
    assert user.is_active is True
    assert await verify_password("testpass123", user.hashed_password)


async def test_create_block_head(db: AsyncSession, block_head_user):
    user = await _service(db).create_user(
        _user_create(
            username="blockhead2",
            email="bh2@example.com",
            role=UserRole.BLOCK_HEAD,
            block_id=1,
        )
    )
    assert user.role == UserRole.BLOCK_HEAD
    assert user.block_id == 1


async def test_create_superadmin(db: AsyncSession, admin_user):
    user = await _service(db).create_user(
        _user_create(
            username="admin2",
            email="admin2@example.com",
            role=UserRole.SUPERADMIN,
        )
    )
    assert user.role == UserRole.SUPERADMIN


async def test_create_manager_without_shelter_raises(db: AsyncSession):
    from sqlalchemy.exc import InvalidRequestError

    with pytest.raises((ValueError, InvalidRequestError)):
        await _service(db).create_user(_user_create(username="badmanager"))


async def test_create_user_duplicate(db: AsyncSession):
    service = _service(db)
    await service.create_user(
        _user_create(username="dupuser", email="dup@example.com", shelter_id=1)
    )
    with pytest.raises(ConflictError):
        await service.create_user(
            _user_create(username="dupuser", email="dup@example.com", shelter_id=1)
        )


async def test_get_user_by_username(db: AsyncSession, manager_user):
    user = await _service(db).get_by_username("manager")
    assert user is not None
    assert user.username == "manager"

    with pytest.raises(NotFoundError):
        await _service(db).get_by_username("nonexistent")


async def test_get_active_user_by_username(db: AsyncSession, manager_user):
    service = _service(db)
    user = await service.get_active_user_by_username("manager")
    assert user is not None

    user.is_active = False
    await db.commit()

    user = await service.get_active_user_by_username("manager")
    assert user is None


async def test_get_user_by_id(db: AsyncSession, manager_user):
    user = await _service(db).get_user_by_id(manager_user.id)
    assert user.id == manager_user.id

    with pytest.raises(NotFoundError):
        await _service(db).get_user_by_id(9999)


async def test_get_users(db: AsyncSession, admin_user, manager_user):
    users = await _service(db).get_users()
    assert len(users) >= 2


async def test_update_user(db: AsyncSession, manager_user):
    service = _service(db)
    update = UserUpdate(full_name="Updated Name")
    user = await service.update_user(manager_user.id, update)
    assert user.full_name == "Updated Name"


async def test_update_user_password(db: AsyncSession, manager_user):
    user = await _service(db).update_user(
        manager_user.id, UserUpdate(password="newpass1")
    )
    assert await verify_password("newpass1", user.hashed_password)


async def test_authenticate_user(db: AsyncSession):
    service = _service(db)
    user_in = _user_create(username="authuser", email="auth@test.com", shelter_id=1)
    await service.create_user(user_in)

    user = await service.authenticate_user("authuser", "testpass123")
    assert user is not None
    assert user.username == "authuser"

    bad_pass = await service.authenticate_user("authuser", "wrongpass")
    assert bad_pass is None

    bad_user = await service.authenticate_user("nobody", "pass")
    assert bad_user is None


async def test_deactivate_user(db: AsyncSession, manager_user):
    service = _service(db)
    await service.deactivate_user(manager_user.id)
    user = await service.get_user_by_id(manager_user.id)
    assert user.is_active is False


async def test_deactivate_twice_no_error(db: AsyncSession, manager_user):
    service = _service(db)
    await service.deactivate_user(manager_user.id)
    await service.deactivate_user(manager_user.id)  # should not raise

    with pytest.raises(NotFoundError):
        await service.deactivate_user(9999)