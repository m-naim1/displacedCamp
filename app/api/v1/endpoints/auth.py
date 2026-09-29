from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import (
    get_current_user,
    get_family_service,
    get_member_service,
    get_user_service,
    require_role,
)
from app.core.config import settings
from app.core.security import create_access_token
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import FamilyLoginSchema, Token, UserCreate, UserResponse
from app.services.family_service import FamilyService, MemberService
from app.services.user_service import UserService

router = APIRouter()

limiter = Limiter(key_func=get_remote_address)
auth_limit = limiter.limit(settings.AUTH_RATE_LIMIT)


@router.post("/login", response_model=Token)
@auth_limit
async def login(
    request: Request,
    credentials: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service),
):
    user = await user_service.authenticate_user(
        credentials.username, credentials.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        data={"sub": user.username, "role": user.role, "shelter_id": user.shelter_id}
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/family-login", response_model=Token)
@auth_limit
async def family_login(
    request: Request,
    credentials: FamilyLoginSchema,
    family_service: FamilyService = Depends(get_family_service),
    member_service: MemberService = Depends(get_member_service),
):
    head = await member_service.get_member(credentials.national_id)
    if not head or head.date_of_birth != credentials.date_of_birth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    family = await family_service.get_family(head.family_id, current_user=None)
    if family.head_id != head.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = create_access_token(
        data={
            "sub": str(credentials.national_id),
            "role": UserRole.FAMILY,
            "family_id": family.id,
        }
    )
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    if isinstance(current_user, dict):
        raise HTTPException(
            status_code=403, detail="Family users do not have a profile endpoint"
        )
    return current_user


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_in: UserCreate,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Create a new system user (Manager, Block_Head, etc).
    Superadmins can create any user; MANAGERs can only create BLOCK_HEADS
    within their own shelter center/block.
    """
    if current_user.role == UserRole.MANAGER:
        if user_in.role != UserRole.BLOCK_HEAD:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Managers can only create BLOCK_HEAD accounts",
            )
        if user_in.shelter_id != current_user.shelter_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Block head must belong to the manager's shelter center",
            )
        if not user_in.shelter_id:
            user_in.shelter_id = current_user.shelter_id

    return await user_service.create_user(user_in, actor=current_user)
