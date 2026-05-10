from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.enums import UserRole
from app.services import user_service, family_service
from app.portals.common import templates, get_portal_user, logger
from app.portals.manager_portal import router as manager_router
from app.portals.blockhead_portal import router as blockhead_router
from app.portals.family_portal import router as family_router

router = APIRouter()
router.include_router(manager_router)
router.include_router(blockhead_router)
router.include_router(family_router)


@router.get("/login")
async def login_page(request: Request):
    user = get_portal_user(request)
    if user:
        role = request.session.get("portal_role")
        redirect_map = {
            UserRole.SUPERADMIN: "/admin",
            UserRole.MANAGER: "/portal/manager",
            UserRole.BLOCK_HEAD: "/portal/block",
            UserRole.FAMILY: "/portal/family",
        }
        dest = redirect_map.get(role, "/portal/login")
        return RedirectResponse(url=dest)
    return templates.TemplateResponse(request=request, name="portals/login.html")


@router.post("/login")
async def login_submit(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    username = form.get("username", "")
    password = form.get("password", "")

    user = await user_service.authenticate_user(db, username, password)
    if not user:
        logger.warning(f"Failed login attempt for username: {username}")
        return templates.TemplateResponse(
            request=request,
            name="portals/login.html",
            context={"error": "Invalid username or password"},
        )

    logger.info(f"User {user.username} ({user.role}) logged in successfully")
    request.session.update({
        "portal_user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
        },
        "portal_role": user.role,
        "portal_block_id": user.block_id,
    })
    redirect_map = {
        UserRole.SUPERADMIN: "/admin",
        UserRole.MANAGER: "/portal/manager",
        UserRole.BLOCK_HEAD: "/portal/block",
    }
    dest = redirect_map.get(user.role, "/portal/login")
    return RedirectResponse(url=dest, status_code=303)


@router.post("/family-login")
async def family_login_submit(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    national_id = form.get("national_id", "")
    date_of_birth = form.get("date_of_birth", "")

    from datetime import date
    from app.services import family_service

    try:
        mid = int(national_id)
        dob = date.fromisoformat(date_of_birth)
    except (ValueError, TypeError):
        return templates.TemplateResponse(
            request=request,
            name="portals/login.html",
            context={"error": "Invalid national ID or date format"},
        )

    head = await family_service.get_member(db, mid)
    if not head or head.date_of_birth != dob:
        return templates.TemplateResponse(
            request=request,
            name="portals/login.html",
            context={"error": "Invalid credentials"},
        )

    from app.models.family import Family
    from sqlalchemy import select
    result = await db.execute(
        select(Family).where(Family.head_id == head.id, Family.is_active == True)
    )
    family = result.scalar_one_or_none()
    if not family:
        return templates.TemplateResponse(
            request=request,
            name="portals/login.html",
            context={"error": "Family not found or inactive"},
        )

    request.session.update({
        "portal_user": {
            "family_id": family.id,
            "head_name": head.full_name,
        },
        "portal_role": UserRole.FAMILY,
    })
    logger.info(f"Family #{family.id} logged in (head: {head.full_name})")
    return RedirectResponse(url="/portal/family", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    request.session.pop("portal_user", None)
    request.session.pop("portal_role", None)
    request.session.pop("portal_block_id", None)
    return RedirectResponse(url="/portal/login")


@router.get("")
async def portal_root(request: Request):
    user = get_portal_user(request)
    if not user:
        return RedirectResponse(url="/portal/login")
    role = request.session.get("portal_role")
    redirect_map = {
        UserRole.SUPERADMIN: "/admin",
        UserRole.MANAGER: "/portal/manager",
        UserRole.BLOCK_HEAD: "/portal/block",
        UserRole.FAMILY: "/portal/family",
    }
    dest = redirect_map.get(role, "/portal/login")
    return RedirectResponse(url=dest)


@router.get("/admin")
async def portal_admin_redirect(request: Request):
    return RedirectResponse(url="/admin", status_code=301)
