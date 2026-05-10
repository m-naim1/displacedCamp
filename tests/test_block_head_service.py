import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import BlockHeadPermission
from app.services import block_head_service


pytestmark = pytest.mark.asyncio


async def test_get_permission_none(db: AsyncSession):
    perm = await block_head_service.get_permission(db, 999)
    assert perm is None


async def test_upsert_permission_create(db: AsyncSession):
    perm = await block_head_service.upsert_permission(db, 1, True, False, True)
    assert perm.user_id == 1
    assert perm.can_edit is True
    assert perm.can_add is False
    assert perm.can_delete is True

    fetched = await block_head_service.get_permission(db, 1)
    assert fetched is not None
    assert fetched.can_edit is True


async def test_upsert_permission_update(db: AsyncSession):
    perm = await block_head_service.upsert_permission(db, 1, True, True, True)
    assert perm.can_edit is True

    updated = await block_head_service.upsert_permission(db, 1, False, True, False)
    assert updated.can_edit is False
    assert updated.can_add is True
    assert updated.can_delete is False


async def test_upsert_permission_all_false(db: AsyncSession):
    perm = await block_head_service.upsert_permission(db, 1, False, False, False)
    assert perm.can_edit is False
    assert perm.can_add is False
    assert perm.can_delete is False
