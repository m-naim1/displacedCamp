from app.core.errors import ConflictError, NotFoundError
from app.core.security import get_password_hash, verify_password
from app.models.enums import AuditAction, UserRole
from app.models.user import User
from app.repositories.userrepository import UserRepository
from app.schemas.user import UserCreate, UserUpdate
from app.services.audit_service import AuditService


class UserService:
    def __init__(
        self,
        user_repository: UserRepository,
        audit_service: AuditService | None = None,
    ):
        self.user_repo = user_repository
        self.audit = audit_service

    async def get_by_username(
        self, username: str, is_active: bool = True
    ) -> User | None:
        user = await self.user_repo.get_by_username(username, is_active)
        if not user:
            raise NotFoundError(
                code="User_Not_Found",
                message=f"User with username {username} not found",
            )
        return user

    async def get_active_user_by_username(self, username: str) -> User | None:
        """Returns the user only if they exist AND are active. Used by admin auth."""
        return await self.user_repo.get_by_username(username=username)

    async def get_user_by_id(self, user_id: int) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(
                code="User_Not_Found", message=f"User with id {user_id} not found"
            )
        return user

    async def get_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        return await self.user_repo.get_all(skip=skip, limit=limit)

    async def create_user(
        self, user_in: UserCreate, actor: User | None = None
    ) -> User:
        if await self.user_repo.check_username_and_email(
            user_in.username, user_in.email
        ):
            raise ConflictError(
                code="User_Already_Exists",
                message=f"User with username {user_in.username} already exists",
            )
        user = await self.user_repo.create(
            user_in, await get_password_hash(user_in.password)
        )
        if self.audit:
            await self.audit.log(
                actor, AuditAction.USER_CREATED, "user", user.id,
                details={"new_role": user.role.value if isinstance(user.role, UserRole) else str(user.role)},
            )
        return user

    async def update_user(
        self,
        user_id: int,
        user_in: UserUpdate,
        actor: User | None = None,
    ) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(
                code="User_Not_Found", message=f"User with id {user_id} not found"
            )
        changed = list(user_in.model_dump(exclude_unset=True).keys())
        user = await self.user_repo.update(
            user_id,
            user_in,
            await get_password_hash(user_in.password) if user_in.password else None,
        )
        if self.audit:
            await self.audit.log(
                actor, AuditAction.USER_UPDATED, "user", user_id,
                details={"changed": changed},
            )
        return user

    async def authenticate_user(self, username: str, password: str) -> User | None:
        user = await self.user_repo.get_by_username(username, True)
        if (
            not user
            or not user.is_active
            or not await verify_password(password, user.hashed_password)
        ):
            return None
        return user

    async def deactivate_user(self, user_id: int, actor: User | None = None):
        user = await self.user_repo.archive(user_id)
        if not user:
            raise NotFoundError(
                code="User_Not_Found", message=f"User with id {user_id} not found"
            )
        if self.audit:
            await self.audit.log(
                actor, AuditAction.USER_DEACTIVATED, "user", user_id
            )
