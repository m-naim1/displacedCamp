from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_password_hash, verify_password
from app.logging import logger
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.errors import NotFoundError, ConflictError


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_active_user_by_username(db: AsyncSession, username: str) -> User | None:
    """Returns the user only if they exist AND are active. Used by admin auth."""
    result = await db.execute(
        select(User).where(User.username == username, User.is_active == True)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError(
            code="User_Not_Found", message=f"User with id {user_id} not found"
        )
    return user


async def get_users(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> Sequence[User]:
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()


async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    result = await db.execute(select(User).where(User.username == user_in.username))
    if result.scalar_one_or_none():
        raise ConflictError(
            code="User_Already_Exists",
            message=f"User with username {user_in.username} already exists",
        )
    user = User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        role=user_in.role,
        block_id=user_in.block_id,
        hashed_password=get_password_hash(user_in.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info(f"Created user {user.username} (role: {user.role})")
    return user


async def update_user(db: AsyncSession, user_id: int, user_in: UserUpdate) -> User:
    user = await get_user_by_id(db, user_id)
    if user_in.username and user_in.username != user.username:
        result = await db.execute(select(User).where(User.username == user_in.username))
        if result.scalar_one_or_none():
            raise ConflictError(
                code="User_Already_Exists",
                message=f"User with username {user_in.username} already exists",
            )
    for field, value in user_in.model_dump(
        exclude_unset=True, exclude={"password"}
    ).items():
        setattr(user, field, value)
    if user_in.password:
        user.hashed_password = get_password_hash(user_in.password)
    await db.commit()
    await db.refresh(user)
    logger.info(f"Updated user #{user_id} ({user.username})")
    return user


async def authenticate_user(
    db: AsyncSession, username: str, password: str
) -> User | None:
    user = await get_user_by_username(db, username)
    if (
        not user
        or not user.is_active
        or not verify_password(password, user.hashed_password)
    ):
        return None
    return user


async def deactivate_user(db: AsyncSession, user_id: int) -> None:
    user = await get_user_by_id(db, user_id)
    if not user.is_active:
        return
    user.is_active = False
    await db.commit()
    logger.info(f"Deactivated user #{user_id} ({user.username})")


async def activate_user(db: AsyncSession, user_id: int) -> None:
    user = await get_user_by_id(db, user_id)
    if user.is_active:
        return
    user.is_active = True
    await db.commit()
    logger.info(f"Activated user #{user_id} ({user.username})")
