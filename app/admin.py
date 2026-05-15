from starlette.requests import Request
from starlette.responses import Response
from starlette_admin import CustomView
from starlette_admin.auth import AdminUser, AuthProvider
from starlette_admin.contrib.sqla import ModelView
from starlette_admin.exceptions import LoginFailed

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.logging import logger
from app.models.enums import UserRole
from app.services import user_service, family_service


class AdminAuthProvider(AuthProvider):
    async def login(
        self,
        username: str,
        password: str,
        remember_me: bool,
        request: Request,
        response: Response,
    ) -> Response:
        db: AsyncSession = request.state.session
        user = await user_service.get_user_by_username(db, username)

        if not user or not user.is_active:
            logger.warning(f"Failed admin login attempt for username: {username}")
            raise LoginFailed("Invalid username or password")
        if not verify_password(password, user.hashed_password):
            logger.warning(f"Failed admin login attempt for username: {username}")
            raise LoginFailed("Invalid username or password")
        if user.role not in (UserRole.SUPERADMIN, UserRole.MANAGER):
            logger.warning(
                f"Unauthorized admin login attempt by {username} (role: {user.role})"
            )
            raise LoginFailed("You do not have permission to access the admin panel")

        logger.info(f"Admin login: {username} ({user.role})")
        request.session.update(
            {
                "admin_username": username,
                "admin_full_name": user.full_name or username,
            }
        )
        return response

    async def is_authenticated(self, request: Request) -> bool:
        username = request.session.get("admin_username")
        if not username:
            return False
        db: AsyncSession = request.state.session
        user = await user_service.get_active_user_by_username(db, username)
        return user is not None

    def get_admin_user(self, request: Request) -> AdminUser | None:
        username = request.session.get("admin_username")
        if not username:
            return None
        # Full name may have been stored at login; fall back to username
        full_name = request.session.get("admin_full_name") or username
        return AdminUser(username=full_name)

    async def logout(self, request: Request, response: Response) -> Response:
        request.session.clear()
        return response


class DashboardView(CustomView):
    async def render(self, request: Request, templates) -> Response:
        db: AsyncSession = request.state.session
        stats = await family_service.get_dashboard_stats(db)

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"stats": stats},
        )


class UserAdminView(ModelView):
    exclude_fields_from_list = ["hashed_password"]
    exclude_fields_from_detail = ["hashed_password"]
    form_include_pk = False

    async def before_create(self, request, data, obj):
        plain = data.pop("hashed_password", None)
        if plain:
            obj.hashed_password = get_password_hash(plain)

    async def before_edit(self, request, data, obj):
        plain = data.pop("hashed_password", None)
        if plain and plain.strip():
            obj.hashed_password = get_password_hash(plain)
