from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import (
    get_audit_service,
    get_family_service,
    get_member_service,
    get_update_request_service,
    require_role,
)
from app.core.errors import ConflictError, DomainError, ValidationError
from app.models.enums import AuditAction, UserRole
from app.models.user import User
from app.schemas.family import (
    FamilyCreate,
    FamilyListResponse,
    FamilyResponse,
    FamilyUpdate,
    MemberCreate,
    MemberResponse,
    MemberUpdate,
    UpdateRequestCreate,
    UpdateRequestResponse,
)
from app.schemas.filters import FamilyFilterParams, MemberFilterParams
from app.services.audit_service import AuditService
from app.services.family_service import FamilyService, MemberService
from app.services.import_service import parse_families_csv
from app.services.update_request_service import UpdateRequestService

router = APIRouter()


@router.post("/", response_model=FamilyResponse, status_code=status.HTTP_201_CREATED)
async def create_new_family(
    family_in: FamilyCreate,
    family_service: FamilyService = Depends(get_family_service),
    current_user: User = Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Create a new family with all its members.
    - Validates IDs using Luhn algorithm.
    - Prevents duplicate members.
    """
    return await family_service.create_family(
        family_in=family_in, current_user=current_user
    )


@router.post("/import", status_code=status.HTTP_200_OK)
async def import_families_csv(
    file: UploadFile = File(...),
    family_service: FamilyService = Depends(get_family_service),
    audit_service: AuditService = Depends(get_audit_service),
    current_user: User = Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Bulk-register families from a CSV file (one row per member; rows grouped
    by `family_code`; the `is_head=true` row carries family-level fields).
    Valid families are created; invalid ones are reported, not fatal.
    """
    if (file.content_type or "") not in {"text/csv", "application/csv", ""} and not (
        file.filename or ""
    ).lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    content = (await file.read()).decode("utf-8-sig")
    parsed = parse_families_csv(content)

    created: list[int] = []
    # Re-check families that are duplicates of already-imported codes
    seen_errors = [
        {"row": e.row, "family_code": e.family_code, "message": e.message}
        for e in parsed.errors
    ]
    for family_in in parsed.families:
        try:
            family = await family_service.create_family(
                family_in=family_in, current_user=current_user
            )
            created.append(family.id)
        except (ConflictError, DomainError, ValidationError) as e:
            seen_errors.append(
                {"row": 0, "family_code": f"#{family_in.head_id}", "message": e.message}
            )

    if created:
        await audit_service.log(
            current_user,
            AuditAction.BULK_IMPORT,
            "family",
            details={"created_count": len(created), "failed_count": len(seen_errors)},
        )

    return {
        "created_count": len(created),
        "created_family_ids": created,
        "failed_count": len(seen_errors),
        "errors": seen_errors,
    }


@router.get("/{family_id:int}", response_model=FamilyResponse)
async def read_family(
    family_id: int,
    family_service: FamilyService = Depends(get_family_service),
    current_user: User = Depends(
        require_role(
            UserRole.SUPERADMIN,
            UserRole.MANAGER,
            UserRole.BLOCK_HEAD,
        )
    ),
):
    """
    Get a specific family by ID to see the calculated stats and members.
    """
    return await family_service.get_family(
        family_id=family_id, current_user=current_user
    )


@router.get("/", response_model=list[FamilyListResponse])
async def read_families(
    page: int = 1,
    limit: int = 100,
    filters: FamilyFilterParams = Depends(),
    family_service: FamilyService = Depends(get_family_service),
    current_user: User = Depends(
        require_role(UserRole.SUPERADMIN, UserRole.MANAGER, UserRole.BLOCK_HEAD)
    ),
):
    """
    Get Sequence of families with advanced filtering and sorting.
    """
    skip = (page - 1) * limit
    return await family_service.get_families(
        filters=filters, current_user=current_user, skip=skip, limit=limit
    )


@router.put("/{family_id:int}", response_model=FamilyResponse)
async def update_family_details(
    family_id: int,
    family_update: FamilyUpdate,
    family_service: FamilyService = Depends(get_family_service),
    current_user: User = Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Update family-level details (Housing, Phone, Status).
    """
    return await family_service.update_family(
        family_id=family_id, family_data=family_update, current_user=current_user
    )


@router.patch("/{family_id}/archive", response_model=FamilyResponse)
async def archive_family(
    family_id: int,
    family_service: FamilyService = Depends(get_family_service),
    current_user: User = Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Soft delete (archive) a family.
    Sets is_active = False and records the archived_at timestamp.
    """
    return await family_service.deactivate_family(
        family_id=family_id, current_user=current_user
    )


@router.patch("/{family_id}/restore", response_model=FamilyResponse)
async def restore_family(
    family_id: int,
    family_service: FamilyService = Depends(get_family_service),
    current_user: User = Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Restore an archived family back to active status.
    """
    return await family_service.activate_family(
        family_id=family_id, current_user=current_user
    )


@router.post("/{family_id}/members", response_model=MemberResponse)
async def add_member_to_family(
    family_id: int,
    member_in: MemberCreate,
    member_service: MemberService = Depends(get_member_service),
    current_user: User = Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Add a new member to an existing family.
    Automatically recalculates family statistics.
    """
    return await member_service.add_member(
        family_id=family_id, member_in=member_in, current_user=current_user
    )


@router.get("/members", response_model=list[MemberResponse])
async def read_members(
    page: int = 1,
    limit: int = 100,
    filters: MemberFilterParams = Depends(),
    member_service: MemberService = Depends(get_member_service),
    current_user: User = Depends(
        require_role(UserRole.SUPERADMIN, UserRole.MANAGER, UserRole.BLOCK_HEAD)
    ),
):
    """
    Get Sequence of members with advanced filtering and sorting.
    """
    skip = (page - 1) * limit
    return await member_service.get_members(
        filters=filters, current_user=current_user, skip=skip, limit=limit
    )


@router.put("/members/{member_id}", response_model=MemberResponse)
async def update_member(
    member_id: int,
    member_update: MemberUpdate,
    member_service: MemberService = Depends(get_member_service),
    current_user: User = Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Update a specific member's details (e.g., pregnancy status, injury).
    Automatically recalculates family statistics.
    """
    return await member_service.update_member(
        member_id=member_id, member_in=member_update, current_user=current_user
    )


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    member_id: int,
    member_service: MemberService = Depends(get_member_service),
    current_user: User = Depends(require_role(UserRole.SUPERADMIN, UserRole.MANAGER)),
):
    """
    Permanently remove a member from the family.
    Automatically recalculates family statistics.
    """
    await member_service.delete_member(member_id=member_id, current_user=current_user)


@router.get("/me", response_model=FamilyResponse)
async def get_my_family(
    family_service: FamilyService = Depends(get_family_service),
    current_user=Depends(require_role(UserRole.FAMILY)),
):
    """Families can only view their own data."""
    if isinstance(current_user, dict) and current_user.get("role") == UserRole.FAMILY:
        family_id = current_user.get("family_id", -1)
        return await family_service.get_family(family_id=family_id, current_user=None)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only family users can access this endpoint",
    )


@router.post(
    "/me/update-requests", status_code=status.HTTP_201_CREATED, tags=["update-request"]
)
async def request_family_update(
    req_in: UpdateRequestCreate,
    current_user=Depends(require_role(UserRole.FAMILY)),
    update_req_service: UpdateRequestService = Depends(get_update_request_service),
):
    """Family proposes a change (e.g., new baby, changed phone number)."""
    if (
        not isinstance(current_user, dict)
        or current_user.get("role") != UserRole.FAMILY
    ):
        raise HTTPException(status_code=403, detail="Only families can request updates")
    new_req = await update_req_service.create_request(
        current_user.get("family_id", -1), req_in, actor=current_user
    )

    return {"message": "Update request submitted for manager review", "id": new_req.id}


@router.get(
    "/me/update-requests",
    response_model=list[UpdateRequestResponse],
    status_code=status.HTTP_200_OK,
    tags=["update-request"],
)
async def get_my_update_requests(
    current_user=Depends(require_role(UserRole.FAMILY)),
    update_req_service: UpdateRequestService = Depends(get_update_request_service),
):
    """Families can view all their own update requests (any status)."""
    if (
        not isinstance(current_user, dict)
        or current_user.get("role") != UserRole.FAMILY
    ):
        raise HTTPException(
            status_code=403, detail="Only family users can access this endpoint"
        )
    return await update_req_service.get_family_requests(
        current_user.get("family_id", -1)
    )


@router.get(
    "/update-requests",
    response_model=list[dict],
    status_code=status.HTTP_200_OK,
    tags=["update-request"],
)
async def get_families_update_requests(
    current_user=Depends(
        require_role(UserRole.SUPERADMIN, UserRole.MANAGER, UserRole.BLOCK_HEAD)
    ),
    update_req_service: UpdateRequestService = Depends(get_update_request_service),
):
    """get families update requests (e.g., new baby, changed phone number)."""
    return await update_req_service.get_scoped_pending_requests(current_user)


@router.patch("/{request_id}/approve", tags=["update-request"])
async def approve_request(
    request_id: int,
    current_user=Depends(
        require_role(UserRole.SUPERADMIN, UserRole.MANAGER, UserRole.BLOCK_HEAD)
    ),
    service: UpdateRequestService = Depends(get_update_request_service),
):
    return await service.approve_request(request_id, current_user)


@router.patch("/{request_id}/reject", tags=["update-request"])
async def reject_request(
    request_id: int,
    current_user=Depends(
        require_role(UserRole.SUPERADMIN, UserRole.MANAGER, UserRole.BLOCK_HEAD)
    ),
    service: UpdateRequestService = Depends(get_update_request_service),
):
    return await service.reject_request(request_id, current_user)
