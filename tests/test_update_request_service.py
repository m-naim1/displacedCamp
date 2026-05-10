import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.update_request import UpdateRequest
from app.schemas.update_request import UpdateRequestCreate
from app.services import update_request_service


pytestmark = pytest.mark.asyncio


async def test_create_update_request(db: AsyncSession):
    req_in = UpdateRequestCreate(
        family_id=1,
        requested_changes='{"phone": "+970599123456"}',
    )
    req = await update_request_service.create_update_request(db, req_in)
    assert req.id is not None
    assert req.family_id == 1
    assert req.status == "pending"
    assert req.requested_changes == '{"phone": "+970599123456"}'


async def test_get_pending_requests_by_family(db: AsyncSession):
    req1 = UpdateRequestCreate(family_id=1, requested_changes='{"a": "1"}')
    req2 = UpdateRequestCreate(family_id=2, requested_changes='{"b": "2"}')
    await update_request_service.create_update_request(db, req1)
    await update_request_service.create_update_request(db, req2)

    pending = await update_request_service.get_pending_requests(db, family_id=1)
    assert len(pending) == 1
    assert pending[0].family_id == 1


async def test_get_all_requests(db: AsyncSession):
    req1 = UpdateRequestCreate(family_id=1, requested_changes='{"a": "1"}')
    req2 = UpdateRequestCreate(family_id=2, requested_changes='{"b": "2"}')
    await update_request_service.create_update_request(db, req1)
    await update_request_service.create_update_request(db, req2)

    all_reqs = await update_request_service.get_all_requests(db)
    assert len(all_reqs) >= 2


async def test_review_request(db: AsyncSession):
    req_in = UpdateRequestCreate(family_id=1, requested_changes='{"x": "y"}')
    created = await update_request_service.create_update_request(db, req_in)

    reviewed = await update_request_service.review_request(db, created.id, "approved", 42)
    assert reviewed.status == "approved"
    assert reviewed.reviewed_by == 42
    assert reviewed.reviewed_at is not None


async def test_review_request_not_found(db: AsyncSession):
    with pytest.raises(NotFoundError):
        await update_request_service.review_request(db, 9999, "approved", 1)
