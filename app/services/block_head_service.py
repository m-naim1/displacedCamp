from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.logging import logger
from app.models.user import BlockHeadPermission


async def get_permission(db: AsyncSession, user_id: int) -> BlockHeadPermission | None:
    result = await db.execute(
        select(BlockHeadPermission).where(BlockHeadPermission.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def upsert_permission(
    db: AsyncSession, user_id: int, can_edit: bool, can_add: bool, can_delete: bool
) -> BlockHeadPermission:
    result = await db.execute(
        select(BlockHeadPermission).where(BlockHeadPermission.user_id == user_id)
    )
    perm = result.scalar_one_or_none()
    if perm:
        perm.can_edit = can_edit
        perm.can_add = can_add
        perm.can_delete = can_delete
    else:
        perm = BlockHeadPermission(
            user_id=user_id,
            can_edit=can_edit,
            can_add=can_add,
            can_delete=can_delete,
        )
        db.add(perm)
    await db.commit()
    await db.refresh(perm)
    logger.info(f"Upserted permissions for block head #{user_id}: edit={can_edit} add={can_add} delete={can_delete}")
    return perm
