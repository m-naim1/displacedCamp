from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.audit import AuditLog


class AuditRepository:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def log(
        self,
        *,
        user_id: int | None,
        actor_username: str,
        actor_role: str,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        details: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            actor_username=actor_username,
            actor_role=actor_role,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details,
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def get_all(
        self,
        *,
        action: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        user_id: int | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[AuditLog]:
        query = select(AuditLog).options(joinedload(AuditLog.user))

        if action:
            query = query.where(AuditLog.action == action)
        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)
        if entity_id:
            query = query.where(AuditLog.entity_id == str(entity_id))
        if user_id:
            query = query.where(AuditLog.user_id == user_id)

        result = await self.db.execute(
            query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().unique().all())
