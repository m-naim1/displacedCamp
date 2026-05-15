import uvicorn
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette_admin.contrib.sqla import Admin, ModelView
from app.admin import UserAdminView, DashboardView, AdminAuthProvider
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import NotFoundError, ConflictError, DomainError
from app.db.session import Base, engine
from sqlalchemy import select
from app.models.family import Family, Member
from app.models.user import User
from app.models.lookups import (
    City,
    Governor,
    RelationshipToHead,
    ShelterQuality,
    ShelterBlock,
    ShelterCenter,
)

from app.db.session import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.enums import UserRole
from app.seed import seed_all

# ── Startup validation ────────────────────────────────────────────────────────
if settings.SECRET_KEY == "change-me":
    import warnings

    warnings.warn(
        "⚠️  SECRET_KEY is set to the default 'change-me'. "
        "Set a strong random key in your .env file before deploying.",
        stacklevel=1,
    )


async def seed_superadmin():
    db = AsyncSessionLocal()
    try:
        result = await db.execute(select(User).where(User.role == UserRole.SUPERADMIN))
        if not result.scalar_one_or_none():
            admin = User(
                username="admin",
                email="admin@camp.local",
                full_name="System Admin",
                hashed_password=get_password_hash("admin1234"),
                role=UserRole.SUPERADMIN,
            )
            db.add(admin)
            await db.commit()
            print("✓ Superadmin created — username: admin / password: admin1234")
    finally:
        await db.close()


# Table creation must also be async:
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    await seed_superadmin()
    async with AsyncSessionLocal() as db:
        await seed_all(db)
    yield


app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    description="REST API for managing displaced families across humanitarian shelter centers.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)


# ── Global error handlers ─────────────────────────────────────────────────────
@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": exc.message})


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(status_code=400, content={"detail": exc.message})


admin = Admin(
    engine=engine,
    title="Displaced Camp Admin",
    templates_dir="templates",  # ← tells admin where your templates folder is
    auth_provider=AdminAuthProvider(),
    index_view=DashboardView(
        label="Dashboard",
        icon="fa fa-home",
        path="/",
        add_to_menu=False,  # already the home page, no need to show in sidebar
    ),
)
admin.add_view(UserAdminView(User, label="Users"))
admin.add_view(ModelView(Family))
admin.add_view(ModelView(Member))
admin.add_view(ModelView(Governor))
admin.add_view(ModelView(City))
admin.add_view(ModelView(RelationshipToHead))
admin.add_view(ModelView(ShelterQuality))
admin.add_view(ModelView(ShelterCenter))
admin.add_view(ModelView(ShelterBlock))

admin.mount_to(app)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {"name": settings.PROJECT_NAME}


@app.get("/health")
def health_check():
    return {"status": "ok"}


# 3. Main execution block to run the app using Uvicorn
if __name__ == "__main__":
    # The uvicorn.run() function starts the server.
    # The first argument specifies the application: "main:app"
    # means look for the 'app' object inside the 'main' module (main.py).
    # 'host' is the IP address to listen on (0.0.0.0 listens on all interfaces).
    # 'port' is the port number.
    # 'reload=True' enables auto-reloading during development.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
