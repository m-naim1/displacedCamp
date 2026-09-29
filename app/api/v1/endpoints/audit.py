from fastapi import APIRouter, Depends, Query

from app.api.deps import get_audit_service, require_role
from app.models.enums import UserRole
from app.schemas.audit import AuditLogResponse
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("/", response_model=list[AuditLogResponse])
async def list_audit_logs(
    action: str | None = Query(default=None, description="e.g. FAMILY_ARCHIVED"),
    entity_type: str | None = Query(default=None, description="e.g. family, member, user"),
    entity_id: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    audit_service: AuditService = Depends(get_audit_service),
    _=Depends(require_role(UserRole.SUPERADMIN)),
):
    """Query the audit trail: who changed what and when (newest first)."""
    skip = (page - 1) * limit
    return await audit_service.get_logs(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        skip=skip,
        limit=limit,
    )
