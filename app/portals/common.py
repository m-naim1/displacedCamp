from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole, Gender, MaritalStatus, HousingType, ResidencyStatus
from app.models.lookups import Governor, City, ShelterCenter, ShelterBlock, ShelterQuality, RelationshipToHead
from app.logging import logger

templates = Jinja2Templates(directory="templates")


def get_portal_user(request: Request) -> dict | None:
    user = request.session.get("portal_user")
    if not user:
        return None
    if not request.session.get("portal_role"):
        return None
    return user


def require_portal_role(*roles: UserRole):
    def checker(request: Request) -> dict:
        user = get_portal_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Login required")
        if request.session.get("portal_role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker


def redirect_to_login():
    return RedirectResponse(url="/portal/login", status_code=303)


async def load_lookups(db: AsyncSession) -> dict:
    return {
        "governors": (await db.execute(select(Governor).order_by(Governor.id))).scalars().all(),
        "cities": (await db.execute(select(City).order_by(City.id))).scalars().all(),
        "centers": (await db.execute(select(ShelterCenter).order_by(ShelterCenter.id))).scalars().all(),
        "blocks": (await db.execute(select(ShelterBlock).order_by(ShelterBlock.id))).scalars().all(),
        "qualities": (await db.execute(select(ShelterQuality).order_by(ShelterQuality.id))).scalars().all(),
        "relationships": (await db.execute(select(RelationshipToHead).order_by(RelationshipToHead.id))).scalars().all(),
        "genders": list(Gender),
        "marital_statuses": list(MaritalStatus),
        "housing_types": list(HousingType),
        "residency_statuses": list(ResidencyStatus),
    }
