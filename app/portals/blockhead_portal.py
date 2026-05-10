from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.enums import UserRole
from app.models.family import Family
from app.portals.common import templates, require_portal_role, logger
from app.services import block_head_service

router = APIRouter()


@router.get("/block")
async def block_head_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_portal_role(UserRole.BLOCK_HEAD)),
):
    block_id = request.session.get("portal_block_id")
    if not block_id:
        raise HTTPException(status_code=400, detail="No block assigned")

    user = request.session.get("portal_user")
    perm = await block_head_service.get_permission(db, user["id"])

    result = await db.execute(
        select(Family).where(
            Family.shelter_block_id == block_id,
            Family.is_active == True,
        )
    )
    families = result.scalars().all()

    logger.info(f"Block head #{user['id']} viewed block #{block_id} ({len(families)} families)")
    return templates.TemplateResponse(
        request=request,
        name="portals/blockhead_dashboard.html",
        context={
            "families": families,
            "permission": perm,
            "block_id": block_id,
        },
    )
