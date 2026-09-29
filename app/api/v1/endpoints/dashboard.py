from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.enums import UserRole
from app.schemas.dashboard import BlockCount, CenterCount, DashboardStats
from app.services.family_service import get_dashboard_stats

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(
        require_role(UserRole.SUPERADMIN, UserRole.MANAGER, UserRole.BLOCK_HEAD)
    ),
):
    """Live statistics for the dashboard: family/member totals and occupancy."""
    stats = await get_dashboard_stats(db, current_user)
    stats["block_counts"] = [
        BlockCount(name=name, count=count) for name, count in stats["block_counts"]
    ]
    stats["center_counts"] = [
        CenterCount(name=name, count=count) for name, count in stats["center_counts"]
    ]
    return stats