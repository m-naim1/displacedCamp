import structlog

from app.models.enums import AuditAction, UserRole
from app.models.user import User
from app.repositories.auditRepository import AuditRepository

logger = structlog.getLogger()


class AuditService:
    """Writes and queries the append-only audit trail.

    Kept separate from business repositories so services can accept it as an
    optional collaborator (`audit_service=None` keeps existing tests wiring).
    """

    def __init__(self, audit_repository: AuditRepository):
        self.audit_repo = audit_repository

    async def log(
        self,
        actor: User | dict | None,
        action: str,
        entity_type: str,
        entity_id: int | str | None = None,
        details: dict | None = None,
    ) -> None:
        match actor:
            case User():
                user_id = actor.id
                username = actor.username
                role = actor.role.value if isinstance(actor.role, UserRole) else str(actor.role)
            case {"role": UserRole.FAMILY, "family_id": family_id}:
                # Family self-service token — no User row exists
                user_id = None
                username = f"family:{family_id}"
                role = UserRole.FAMILY.value
            case _:
                user_id = None
                username = "system"
                role = "SYSTEM"

        await self.audit_repo.log(
            user_id=user_id,
            actor_username=username,
            actor_role=role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
        logger.info(
            "audit_logged",
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=username,
        )

    async def get_logs(
        self,
        *,
        action: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        user_id: int | None = None,
        skip: int = 0,
        limit: int = 50,
    ):
        return await self.audit_repo.get_all(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            skip=skip,
            limit=limit,
        )
