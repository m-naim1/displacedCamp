from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.logging import logger
from app.models.update_request import UpdateRequest
from app.schemas.update_request import UpdateRequestCreate


async def create_update_request(
    db: AsyncSession, req_in: UpdateRequestCreate
) -> UpdateRequest:
    req = UpdateRequest(
        family_id=req_in.family_id,
        requested_changes=req_in.requested_changes,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    logger.info(f"Created update request #{req.id} for family #{req.family_id}")
    return req


async def get_pending_requests(
    db: AsyncSession, family_id: int | None = None
) -> Sequence[UpdateRequest]:
    query = select(UpdateRequest).where(UpdateRequest.status == "pending")
    if family_id:
        query = query.where(UpdateRequest.family_id == family_id)
    query = query.order_by(UpdateRequest.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


async def get_all_requests(db: AsyncSession) -> Sequence[UpdateRequest]:
    result = await db.execute(
        select(UpdateRequest).order_by(UpdateRequest.created_at.desc())
    )
    return result.scalars().all()


async def review_request(
    db: AsyncSession, request_id: int, status: str, reviewed_by: int
) -> UpdateRequest:
    result = await db.execute(
        select(UpdateRequest).where(UpdateRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise NotFoundError(
            code="request_not_found",
            message=f"Update request {request_id} not found",
        )
    req.status = status
    req.reviewed_at = datetime.now(timezone.utc)
    req.reviewed_by = reviewed_by
    await db.commit()
    await db.refresh(req)
    logger.info(
        f"Update request #{request_id} reviewed as {status} by user #{reviewed_by}"
    )
    return req
