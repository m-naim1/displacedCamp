from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.enums import UserRole, Gender, MaritalStatus, HousingType, ResidencyStatus
from app.models.user import User
from app.portals.common import templates, require_portal_role, load_lookups, logger
from app.schemas.family import FamilyCreate, FamilyUpdate, MemberCreate
from app.services import family_service, block_head_service, update_request_service
from app.services.family_service import get_families

router = APIRouter()


@router.get("/manager")
async def manager_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_portal_role(UserRole.MANAGER)),
):
    stats = await family_service.get_dashboard_stats(db)
    families = await get_families(db, limit=100)
    return templates.TemplateResponse(
        request=request,
        name="portals/manager_dashboard.html",
        context={"stats": stats, "families": families},
    )


@router.get("/manager/families/create")
async def manager_family_create_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_portal_role(UserRole.MANAGER)),
):
    lookups = await load_lookups(db)
    return templates.TemplateResponse(
        request=request,
        name="portals/manager_family_form.html",
        context={"lookups": lookups, "family": None, "mode": "create"},
    )


@router.post("/manager/families/create")
async def manager_family_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_portal_role(UserRole.MANAGER)),
):
    form = await request.form()
    try:
        head_id = int(form["head_id"])
        members = [
            MemberCreate(
                id=head_id,
                full_name=form["head_full_name"],
                gender=Gender(form["head_gender"]),
                marital_status=MaritalStatus(form["head_marital_status"]),
                date_of_birth=date.fromisoformat(form["head_dob"]),
                relationship_to_head_id=1,
                disabled=form.get("head_disabled") == "on",
                injured=form.get("head_injured") == "on",
                has_chronic_disease=form.get("head_chronic") == "on",
                pregnant=form.get("head_pregnant") == "on",
                breastfeeding=form.get("head_breastfeeding") == "on",
            )
        ]
        spouse_id = form.get("spouse_id")
        if spouse_id and spouse_id.strip():
            spouse_id_val = int(spouse_id)
            members.append(
                MemberCreate(
                    id=spouse_id_val,
                    full_name=form["spouse_full_name"],
                    gender=Gender.FEMALE,
                    marital_status=MaritalStatus.MARRIED,
                    date_of_birth=date.fromisoformat(form["spouse_dob"]),
                    relationship_to_head_id=2,
                    disabled=form.get("spouse_disabled") == "on",
                    injured=form.get("spouse_injured") == "on",
                    has_chronic_disease=form.get("spouse_chronic") == "on",
                    pregnant=form.get("spouse_pregnant") == "on" if form.get("spouse_pregnant") else False,
                    breastfeeding=form.get("spouse_breastfeeding") == "on" if form.get("spouse_breastfeeding") else False,
                )
            )
        else:
            spouse_id_val = None

        family_in = FamilyCreate(
            head_id=head_id,
            spouse_id=spouse_id_val,
            female_headed=form.get("female_headed") == "on",
            child_headed=form.get("child_headed") == "on",
            primary_phone_number=form["primary_phone"],
            secondary_phone_number=form.get("secondary_phone") or None,
            residency_status=ResidencyStatus(form["residency_status"]),
            housing_type=HousingType(form["housing_type"]),
            original_governor_id=int(form["original_governor_id"]),
            original_city_id=int(form["original_city_id"]),
            current_governor_id=int(form["current_governor_id"]),
            current_city_id=int(form["current_city_id"]),
            current_shelter_center_id=int(form["shelter_center_id"]),
            shelter_block_id=int(form["shelter_block_id"]),
            shelter_quality_id=int(form["shelter_quality_id"]) if form.get("shelter_quality_id") else None,
            members=members,
        )
        family = await family_service.create_family(db, family_in)
        logger.info(f"Manager created family #{family.id}")
        return RedirectResponse(url=f"/portal/manager/families/{family.id}", status_code=303)
    except Exception as e:
        lookups = await load_lookups(db)
        return templates.TemplateResponse(
            request=request,
            name="portals/manager_family_form.html",
            context={"lookups": lookups, "family": None, "mode": "create", "error": str(e)},
        )


@router.get("/manager/families/{family_id}")
async def manager_family_detail(
    request: Request,
    family_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_portal_role(UserRole.MANAGER)),
):
    family = await family_service.get_family(db, family_id)
    lookups = await load_lookups(db)
    return templates.TemplateResponse(
        request=request,
        name="portals/manager_family_detail.html",
        context={"family": family, "lookups": lookups},
    )


@router.get("/manager/families/{family_id}/edit")
async def manager_family_edit_form(
    request: Request,
    family_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_portal_role(UserRole.MANAGER)),
):
    family = await family_service.get_family(db, family_id)
    lookups = await load_lookups(db)
    return templates.TemplateResponse(
        request=request,
        name="portals/manager_family_form.html",
        context={"lookups": lookups, "family": family, "mode": "edit"},
    )


@router.post("/manager/families/{family_id}/edit")
async def manager_family_edit(
    request: Request,
    family_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_portal_role(UserRole.MANAGER)),
):
    form = await request.form()
    try:
        update = FamilyUpdate(
            primary_phone_number=form.get("primary_phone") or None,
            secondary_phone_number=form.get("secondary_phone") or None,
            residency_status=ResidencyStatus(form["residency_status"]) if form.get("residency_status") else None,
            housing_type=HousingType(form["housing_type"]) if form.get("housing_type") else None,
            female_headed=form.get("female_headed") == "on",
            child_headed=form.get("child_headed") == "on",
            original_governor_id=int(form["original_governor_id"]) if form.get("original_governor_id") else None,
            original_city_id=int(form["original_city_id"]) if form.get("original_city_id") else None,
            current_governor_id=int(form["current_governor_id"]) if form.get("current_governor_id") else None,
            current_city_id=int(form["current_city_id"]) if form.get("current_city_id") else None,
            current_shelter_center_id=int(form["shelter_center_id"]) if form.get("shelter_center_id") else None,
            shelter_block_id=int(form["shelter_block_id"]) if form.get("shelter_block_id") else None,
            shelter_quality_id=int(form["shelter_quality_id"]) if form.get("shelter_quality_id") else None,
        )
        await family_service.update_family(db, family_id, update)
        logger.info(f"Manager updated family #{family_id}")
        return RedirectResponse(url=f"/portal/manager/families/{family_id}", status_code=303)
    except Exception as e:
        family = await family_service.get_family(db, family_id)
        lookups = await load_lookups(db)
        return templates.TemplateResponse(
            request=request,
            name="portals/manager_family_form.html",
            context={"lookups": lookups, "family": family, "mode": "edit", "error": str(e)},
        )


@router.post("/manager/families/{family_id}/archive")
async def manager_family_archive(
    request: Request,
    family_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_portal_role(UserRole.MANAGER)),
):
    await family_service.deactivate_family(db, family_id)
    logger.info(f"Manager archived family #{family_id}")
    return RedirectResponse(url="/portal/manager", status_code=303)


@router.post("/manager/families/{family_id}/restore")
async def manager_family_restore(
    request: Request,
    family_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_portal_role(UserRole.MANAGER)),
):
    await family_service.activate_family(db, family_id)
    logger.info(f"Manager restored family #{family_id}")
    return RedirectResponse(url="/portal/manager", status_code=303)


@router.get("/manager/families/{family_id}/members/add")
async def manager_add_member_form(
    request: Request,
    family_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_portal_role(UserRole.MANAGER)),
):
    family = await family_service.get_family(db, family_id)
    lookups = await load_lookups(db)
    return templates.TemplateResponse(
        request=request,
        name="portals/manager_member_form.html",
        context={"lookups": lookups, "family": family},
    )


@router.post("/manager/families/{family_id}/members/add")
async def manager_add_member(
    request: Request,
    family_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_portal_role(UserRole.MANAGER)),
):
    form = await request.form()
    try:
        member_in = MemberCreate(
            id=int(form["member_id"]),
            full_name=form["full_name"],
            gender=Gender(form["gender"]),
            marital_status=MaritalStatus(form["marital_status"]),
            date_of_birth=date.fromisoformat(form["date_of_birth"]),
            relationship_to_head_id=int(form["relationship_to_head_id"]),
            disabled=form.get("disabled") == "on",
            injured=form.get("injured") == "on",
            has_chronic_disease=form.get("chronic") == "on",
            pregnant=form.get("pregnant") == "on",
            breastfeeding=form.get("breastfeeding") == "on",
        )
        await family_service.add_member(db, family_id, member_in)
    except Exception as e:
        return RedirectResponse(url=f"/portal/manager/families/{family_id}?error={str(e)}", status_code=303)
    return RedirectResponse(url=f"/portal/manager/families/{family_id}", status_code=303)


@router.post("/manager/families/{family_id}/members/{member_id}/remove")
async def manager_remove_member(
    request: Request,
    family_id: int,
    member_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_portal_role(UserRole.MANAGER)),
):
    await family_service.delete_member(db, member_id)
    return RedirectResponse(url=f"/portal/manager/families/{family_id}", status_code=303)


@router.get("/manager/block-heads")
async def manager_block_heads(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_portal_role(UserRole.MANAGER)),
):
    result = await db.execute(
        select(User).where(User.role == UserRole.BLOCK_HEAD, User.is_active == True)
    )
    block_heads = result.scalars().all()
    perms = {}
    for bh in block_heads:
        p = await block_head_service.get_permission(db, bh.id)
        perms[bh.id] = p
    return templates.TemplateResponse(
        request=request,
        name="portals/manager_block_heads.html",
        context={"block_heads": block_heads, "perms": perms},
    )


@router.post("/manager/block-heads/{user_id}/permissions")
async def update_block_head_permission(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_portal_role(UserRole.MANAGER)),
):
    form = await request.form()
    can_edit = form.get("can_edit") == "on"
    can_add = form.get("can_add") == "on"
    can_delete = form.get("can_delete") == "on"
    await block_head_service.upsert_permission(db, user_id, can_edit, can_add, can_delete)
    logger.info(f"Manager updated permissions for block head #{user_id}")
    return RedirectResponse(url="/portal/manager/block-heads", status_code=303)


@router.get("/manager/requests")
async def manager_requests(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_portal_role(UserRole.MANAGER)),
):
    reqs = await update_request_service.get_all_requests(db)
    return templates.TemplateResponse(
        request=request,
        name="portals/manager_requests.html",
        context={"requests": reqs},
    )


@router.post("/manager/requests/{request_id}/review")
async def review_update_request(
    request: Request,
    request_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_portal_role(UserRole.MANAGER)),
):
    form = await request.form()
    status = form.get("status", "rejected")
    user = request.session.get("portal_user")
    await update_request_service.review_request(db, request_id, status, user["id"])
    logger.info(f"Manager reviewed update request #{request_id} as {status}")
    return RedirectResponse(url="/portal/manager/requests", status_code=303)
