from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_report_service, require_role
from app.models.enums import UserRole
from app.services.report_service import ReportService

router = APIRouter()


@router.get("/families")
async def get_families_report(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    block_ids: list[int] | None = Query(None),
    service: ReportService = Depends(get_report_service),
    current_user=Depends(
        require_role(UserRole.MANAGER, UserRole.BLOCK_HEAD, UserRole.SUPERADMIN)
    ),
):
    skip = (page - 1) * limit
    return await service.get_families_report(
        current_user, block_ids, selected_ids=None, skip=skip, limit=limit
    )


@router.get("/families/export")
async def export_families_report(
    block_ids: list[int] | None = Query(None),
    selected_ids: list[int] | None = Query(None),
    columns: list[str] | None = Query(None),
    format: Literal["csv", "json"] = Query("csv"),
    service: ReportService = Depends(get_report_service),
    current_user=Depends(
        require_role(UserRole.MANAGER, UserRole.BLOCK_HEAD, UserRole.SUPERADMIN)
    ),
):
    data = await service.get_families_report(current_user, block_ids, selected_ids)
    if format == "csv":
        return service.generate_csv(data, columns)
    return data


@router.get("/members")
async def get_members_report(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    block_ids: list[int] | None = Query(None),
    special_only: bool = Query(False),
    service: ReportService = Depends(get_report_service),
    current_user=Depends(
        require_role(UserRole.MANAGER, UserRole.BLOCK_HEAD, UserRole.SUPERADMIN)
    ),
  ):
  skip = (page - 1) * limit
  return await service.get_members_report(
      current_user, block_ids, special_only, selected_ids=None, skip=skip, limit=limit
  )


@router.get("/members/export")
async def export_members_report(
    block_ids: list[int] | None = Query(None),
    special_only: bool = Query(False),
    selected_ids: list[int] | None = Query(None),
    columns: list[str] | None = Query(None),
    format: Literal["csv", "json"] = Query("csv"),
    service: ReportService = Depends(get_report_service),
    current_user=Depends(
        require_role(UserRole.MANAGER, UserRole.BLOCK_HEAD, UserRole.SUPERADMIN)
    ),
):
    data = await service.get_members_report(
        current_user, block_ids, special_only, selected_ids
    )
    if format == "csv":
        return service.generate_csv(data, columns)
    return data
