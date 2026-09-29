from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.enums import UserRole
from app.models.lookups import (
    City,
    Governor,
    RelationshipToHead,
    ShelterBlock,
    ShelterCenter,
    ShelterQuality,
)
from app.models.user import User
from app.repositories.lookupRepository import LookupRepository
from app.schemas.lookups import (
    CityCreate,
    CityResponse,
    LookupCreate,
    LookupResponse,
    LookupUpdate,
    ShelterBlockCreate,
    ShelterBlockResponse,
    ShelterCenterCreate,
    ShelterCenterResponse,
)
from app.services.lookup_service import LookupService

router = APIRouter()


def register_lookup_routes(
    router: APIRouter,
    prefix: str,
    model,
    create_schema,
    response_schema,
    create_roles: tuple[UserRole, ...] = (UserRole.SUPERADMIN,),
):
    @router.get(
        f"/{prefix}",
        response_model=list[response_schema],
    )
    async def list_items(
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
        db: AsyncSession = Depends(get_db),
        # Read access for all authenticated users (needed for UI dropdowns)
        _=Depends(
            require_role(
                UserRole.SUPERADMIN,
                UserRole.MANAGER,
                UserRole.BLOCK_HEAD,
                UserRole.FAMILY,
            )
        ),
    ):
        service = LookupService(model, LookupRepository(model, db))
        return await service.get_all(skip, limit, is_active)

    @router.post(
        f"/{prefix}",
        response_model=response_schema,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_item(
        data: create_schema,  # type: ignore[valid-type]
        db: AsyncSession = Depends(get_db),
        current_user=Depends(require_role(*create_roles)),
    ):
        service = LookupService(model, LookupRepository(model, db))
        if (
            prefix == "shelter-blocks"
            and isinstance(current_user, User)
            and current_user.role == UserRole.MANAGER
            and data.shelter_center_id != current_user.shelter_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Blocks can only be created within the manager's shelter center",
            )
        return await service.create(data)

    @router.put(
        f"/{prefix}/{{item_id}}",
        response_model=response_schema,
    )
    async def update_item(
        item_id: int,
        data: LookupUpdate,
        db: AsyncSession = Depends(get_db),
        _=Depends(require_role(UserRole.SUPERADMIN)),
    ):
        service = LookupService(model, LookupRepository(model, db))
        return await service.update(item_id, data)

    @router.delete(
        f"/{prefix}/{{item_id}}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    async def delete_item(
        item_id: int,
        db: AsyncSession = Depends(get_db),
        _=Depends(require_role(UserRole.SUPERADMIN)),
    ):
        service = LookupService(model, LookupRepository(model, db))
        await service.delete(item_id)


# --- Register all Lookup Routes ---
register_lookup_routes(router, "governors", Governor, LookupCreate, LookupResponse)
register_lookup_routes(router, "cities", City, CityCreate, CityResponse)
register_lookup_routes(
    router,
    "shelter-centers",
    ShelterCenter,
    ShelterCenterCreate,
    ShelterCenterResponse,
)
register_lookup_routes(
    router,
    "shelter-blocks",
    ShelterBlock,
    ShelterBlockCreate,
    ShelterBlockResponse,
    create_roles=(UserRole.SUPERADMIN, UserRole.MANAGER),
)
register_lookup_routes(
    router,
    "shelter-qualities",
    ShelterQuality,
    LookupCreate,
    LookupResponse,
)
register_lookup_routes(
    router,
    "relationships",
    RelationshipToHead,
    LookupCreate,
    LookupResponse,
)
