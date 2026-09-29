from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import AsyncSessionLocal
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.auditRepository import AuditRepository
from app.repositories.familyRepository import FamilyRepository
from app.repositories.MemberRepository import MemberRepository
from app.repositories.updateRequestRepository import FamilyUpdateRequestRepository
from app.repositories.userrepository import UserRepository
from app.services.audit_service import AuditService
from app.services.export_service import ExportService
from app.services.family_service import FamilyService, MemberService
from app.services.report_service import ReportService
from app.services.update_request_service import UpdateRequestService
from app.services.user_service import UserService

oauth2_schema = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as db:
        yield db


async def get_audit_service(db: AsyncSession = Depends(get_db)):
    return AuditService(AuditRepository(db))


async def get_family_service(db: AsyncSession = Depends(get_db)):
    return FamilyService(
        FamilyRepository(db),
        MemberRepository(db),
        audit_service=AuditService(AuditRepository(db)),
    )


async def get_member_service(db: AsyncSession = Depends(get_db)):
    return MemberService(
        MemberRepository(db),
        FamilyRepository(db),
        audit_service=AuditService(AuditRepository(db)),
    )


async def get_user_service(db: AsyncSession = Depends(get_db)):
    return UserService(
        UserRepository(db), audit_service=AuditService(AuditRepository(db))
    )


async def get_update_request_service(db: AsyncSession = Depends(get_db)):
    return UpdateRequestService(
        update_request_repo=FamilyUpdateRequestRepository(db),
        family_repo=FamilyRepository(db),
        member_repo=MemberRepository(db),
        audit_service=AuditService(AuditRepository(db)),
    )


async def get_report_service(db: AsyncSession = Depends(get_db)):
    return ReportService(
        family_repo=FamilyRepository(db), member_repo=MemberRepository(db)
    )


async def get_export_service(db: AsyncSession = Depends(get_db)):
    return ExportService(
        report_service=ReportService(
            family_repo=FamilyRepository(db), member_repo=MemberRepository(db)
        )
    )


async def get_current_user(
    token: str = Depends(oauth2_schema), db: AsyncSession = Depends(get_db)
) -> User | dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    role = payload.get("role")

    # Family token — no User row exists
    if role == UserRole.FAMILY:
        family_id = payload.get("family_id")
        if not family_id:
            raise credentials_exception
        return {"role": UserRole.FAMILY, "family_id": family_id}

    # System user token
    username: str = payload.get("sub")  # type: ignore
    if not username:
        raise credentials_exception
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise credentials_exception
    return user


def require_role(*allowed_roles: UserRole):
    def checker(current_user=Depends(get_current_user)) -> User | dict:
        user_role = (
            current_user.role
            if isinstance(current_user, User)
            else current_user.get("role")
        )
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return current_user

    return checker
