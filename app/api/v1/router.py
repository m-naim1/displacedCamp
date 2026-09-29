from fastapi import APIRouter

from app.api.v1.endpoints import (
    audit,
    auth,
    dashboard,
    export,
    families,
    lookups,
    reports,
    users,
)

api_router = APIRouter()

# Register the families endpoint
# This means the URL will be: /api/v1/families
api_router.include_router(families.router, prefix="/families", tags=["families"])

# Register the auth endpoint
# This means the URL will be: /api/v1/auth
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])

api_router.include_router(lookups.router, prefix="/lookups", tags=["lookups"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
