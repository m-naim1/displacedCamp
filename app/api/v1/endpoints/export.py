from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import get_export_service, require_role
from app.models.enums import UserRole
from app.services.export_service import (
    XLSX_FILENAMES,
    XLSX_MEDIA_TYPE,
    ExportService,
)

router = APIRouter()


def _xlsx_response(data: bytes, filename: str) -> Response:
    return Response(
        content=data,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/families")
async def export_families(
    block_ids: list[int] | None = Query(None),
    selected_ids: list[int] | None = Query(None),
    columns: list[str] | None = Query(None),
    service: ExportService = Depends(get_export_service),
    current_user=Depends(
        require_role(UserRole.MANAGER, UserRole.BLOCK_HEAD, UserRole.SUPERADMIN)
    ),
):
    data = await service.export_families_xlsx(
        current_user,
        block_ids=block_ids,
        selected_ids=selected_ids,
        columns=columns,
    )
    return _xlsx_response(data, XLSX_FILENAMES["families"])


@router.get("/members")
async def export_members(
    block_ids: list[int] | None = Query(None),
    selected_ids: list[int] | None = Query(None),
    special_only: bool = Query(False),
    columns: list[str] | None = Query(None),
    service: ExportService = Depends(get_export_service),
    current_user=Depends(
        require_role(UserRole.MANAGER, UserRole.BLOCK_HEAD, UserRole.SUPERADMIN)
    ),
):
    data = await service.export_members_xlsx(
        current_user,
        block_ids=block_ids,
        special_only=special_only,
        selected_ids=selected_ids,
        columns=columns,
    )
    return _xlsx_response(data, XLSX_FILENAMES["members"])