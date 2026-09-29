from fastapi import APIRouter, Depends, status

from app.api.deps import get_user_service, require_role
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter()


@router.get("/", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_role(UserRole.SUPERADMIN)),
):
    return await user_service.get_users(skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_role(UserRole.SUPERADMIN)),
):
    return await user_service.get_user_by_id(user_id)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_role(UserRole.SUPERADMIN)),
):
    return await user_service.update_user(user_id, user_in, actor=current_user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: int,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_role(UserRole.SUPERADMIN)),
):
    await user_service.deactivate_user(user_id, actor=current_user)
