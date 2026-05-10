import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.enums import UserRole
from app.portals.common import templates, require_portal_role, logger
from app.services import family_service, update_request_service
from app.schemas.update_request import UpdateRequestCreate

router = APIRouter()


@router.get("/family")
async def family_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_portal_role(UserRole.FAMILY)),
):
    user = request.session.get("portal_user")
    family_id = user["family_id"]
    family = await family_service.get_family(db, family_id)
    reqs = await update_request_service.get_pending_requests(db, family_id)
    return templates.TemplateResponse(
        request=request,
        name="portals/family_dashboard.html",
        context={"family": family, "requests": reqs},
    )


@router.post("/family/request-update")
async def request_update(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_portal_role(UserRole.FAMILY)),
):
    user = request.session.get("portal_user")
    form = await request.form()

    changes = {}
    for field in ("primary_phone", "secondary_phone", "housing_type", "residency_status", "notes"):
        val = form.get(field)
        if val and val.strip():
            changes[field] = val.strip()

    if not changes:
        return RedirectResponse(url="/portal/family?error=no_changes", status_code=303)

    req_in = UpdateRequestCreate(
        family_id=user["family_id"],
        requested_changes=json.dumps(changes, ensure_ascii=False),
    )
    await update_request_service.create_update_request(db, req_in)
    logger.info(f"Family #{user['family_id']} submitted update request")
    return RedirectResponse(url="/portal/family", status_code=303)
