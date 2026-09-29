import logging
import time
from contextlib import asynccontextmanager

import structlog
import uvicorn
from asgi_correlation_id import CorrelationIdMiddleware, correlation_id
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware
from starlette_admin.contrib.sqla import Admin, ModelView

from app.admin import AdminAuthProvider, DashboardView, UserAdminView
from app.api.v1.endpoints.auth import limiter as auth_limiter
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import ConflictError, DomainError, NotFoundError, ValidationError
from app.db.session import AsyncSessionLocal, engine
from app.models.family import Family, Member
from app.models.lookups import (
    City,
    Governor,
    RelationshipToHead,
    ShelterBlock,
    ShelterCenter,
    ShelterQuality,
)
from app.models.user import User

# ── Startup validation ────────────────────────────────────────────────────────
if settings.SECRET_KEY == "change-me":
    import warnings

    warnings.warn(
        "SECRET_KEY is set to the default 'change-me'. "
        "Set a strong random key in your .env file before deploying.",
        stacklevel=1,
    )


# Configure Structured Logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,  # Injects the Correlation ID
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),  # Colors for your terminal. Use JSONRenderer() in prod!
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
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
# Add Correlation ID middleware (Generates X-Request-ID header)


# ── Middleware ────────────────────────────────────────────────────────────────

# 1. Add SessionMiddleware FIRST (Innermost layer)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# CORS for the SPA frontend (Vite dev server; adjust origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 2. Define your custom access logger (Middle layer)
@app.middleware("http")
async def custom_access_log(request: Request, call_next):
    # 🛑 Ignore Prometheus and Health check noise
    if request.url.path in [
        "/metrics",
        "/health",
        "/health/liveness",
        "/health/readiness",
    ]:
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    start_time = time.time()

    try:
        response = await call_next(request)
    except Exception as e:
        logger.error("request_crashed", error=str(e))
        raise e

    process_time = (time.time() - start_time) * 1000
    req_id = correlation_id.get()
    logger.info(
        "api_request",
        request_id=req_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(process_time, 2),
        client_ip=client_ip,
    )

    # 🧹 Clean up context so the request_id doesn't leak to the next async request
    structlog.contextvars.clear_contextvars()

    return response


# 3. Add CorrelationIdMiddleware LAST (Outermost layer - Runs FIRST on incoming requests!)
app.add_middleware(CorrelationIdMiddleware)

# ── Rate limiting (public auth endpoints; see endpoints/auth.py) ─────────────
app.state.limiter = auth_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 4. Instrument Prometheus (Usually added after Correlation ID)
Instrumentator().instrument(app).expose(
    app, endpoint="/metrics", include_in_schema=False
)


# ── Global error handlers ─────────────────────────────────────────────────────
@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    logger.error(
        exc.code,
        method=request.method,
        url=str(request.url),
        error_type="NotFoundError",
        error_message=exc.message,
        exc_info=True,  # This prints the full Python traceback to your console
    )
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": exc.message}
    )


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError):
    logger.error(
        exc.code,
        method=request.method,
        url=str(request.url),
        error_type="ConfflictError",
        error_message=exc.message,
        exc_info=True,  # This prints the full Python traceback to your console
    )
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT, content={"detail": exc.message}
    )


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    logger.error(
        exc.code,
        method=request.method,
        url=str(request.url),
        error_type="DomainError",
        error_message=exc.message,
        exc_info=True,  # This prints the full Python traceback to your console
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST, content={"detail": exc.message}
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    logger.error(
        exc.code,
        method=request.method,
        url=str(request.url),
        error_type="ValidationError",
        error_message=exc.message,
        exc_info=True,  # This prints the full Python traceback to your console
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST, content={"detail": exc.message}
    )


@app.exception_handler(Exception)
async def global_unhandled_exception_handler(request: Request, exc: Exception):
    # Log the exact line of code that crashed with the Request ID attached
    logger.error(
        "unhandled_exception",
        method=request.method,
        url=str(request.url),
        error_type=type(exc).__name__,
        error_message=str(exc),
        exc_info=True,  # This prints the full Python traceback to your console
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected internal server error occurred."},
    )


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

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {"name": settings.PROJECT_NAME}


@app.get("/health")
async def health_check():
    try:
        async with AsyncSessionLocal() as db:
            # Actually ping the database
            await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        # If DB is down, return 503 so load balancers pull this instance out
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "disconnected", "detail": str(e)},
        )


# 3. Main execution block to run the app using Uvicorn
if __name__ == "__main__":
    # The uvicorn.run() function starts the server.
    # The first argument specifies the application: "main:app"
    # means look for the 'app' object inside the 'main' module (main.py).
    # 'host' is the IP address to listen on (0.0.0.0 listens on all interfaces).
    # 'port' is the port number.
    # 'reload=True' enables auto-reloading during development.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
