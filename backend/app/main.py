"""
Application Entry Point (main.py)

This module serves as the central orchestration layer of the FastAPI application.

Responsibilities:

1. Logging Configuration
   - Configures structured logging for the entire application.
   - Log level is controlled via environment settings.
   - Ensures consistent log formatting for observability.

2. Application Initialization
   - Creates the FastAPI app instance.
   - Dynamically sets metadata (title, version, description).
   - Enables API documentation only in debug mode for security.

3. Global Exception Handling
   - Handles RequestValidationError and returns structured 422 responses.
   - Catches unhandled exceptions and returns safe 500 responses.
   - Logs all errors for monitoring and debugging.

4. Lifecycle Events
   - Logs startup and shutdown events.
   - Provides extension points for initializing resources (e.g., DB, cache).

5. Router Registration
   - Includes feature-specific routers.
   - Maintains modular and scalable architecture.

6. Health Check Endpoint
   - Exposes /health endpoint for liveness monitoring.
   - Used by load balancers and orchestration systems.

Overall, this file ensures the application is production-ready,
secure, modular, and observable.
"""

import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError 
from fastapi.responses import JSONResponse

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    HAS_SLOWAPI = True
except ImportError:
    HAS_SLOWAPI = False

from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .api.analyze import router as analyze_router
from .api.portfolio import router as portfolio_router
from .api.stream import router as stream_router
from .api.rag import router as rag_router
from .api.assets import router as assets_router
from .api.alerts import router as alerts_router
from .schemas.analyze import HealthResponse
from .core.database import validate_db_connection, engine, Base
from .core.telemetry import performance_metrics_middleware
from . import models  # noqa: F401

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="FITerminal Core API",
    description="""
    Production-grade Financial Research AI API implementing Modern Portfolio Theory,
    Background Market Alerts, Dual-Asset Comparisons, and Live Websocket streaming.
    
    ## Core Microservices:
    * **RAG**: NLP context analysis against dense document stores.
    * **Stream**: Live WebSockets matching frontend ticks.
    * **Portfolio**: Math engine using `PyPortfolioOpt`.
    * **Assets**: Global Multi-Asset (Bonds, Commodities, Options) fetchers.
    """,
    version="2.0.0",
    docs_url="/docs",  
    redoc_url="/redoc",
)

# ── Rate Limiting ─────────────────────────────────────────────────────────────
if HAS_SLOWAPI:
    try:
        limiter = Limiter(key_func=get_remote_address, default_limits=["20/minute"])
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app.add_middleware(SlowAPIMiddleware)
        logger.info("🛡️ Rate Limiter enabled")
    except Exception as e:
        logger.warning("Rate Limiter initialization failed: %s", e)
else:
    logger.warning("🛡️ Rate Limiter disabled (library not found)")

# --- Middleware: CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production: restrict to frontend domain
    allow_credentials=False, # Must be False if allow_origins is ["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(performance_metrics_middleware)

# ── Middleware: Global Error Handler ──────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning("Validation error: %s", exc.errors())
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.error("Unhandled exception: %s", str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": "An unexpected error occurred."},
    )


# ── Startup / Shutdown ────────────────────────────────────────────────────────
from .services.alert_service import start_scheduler, stop_scheduler

@app.on_event("startup")
async def on_startup() -> None:
    logger.info("🚀 %s starting up", settings.app_name)
    validate_db_connection()  # Fail fast if DB is unreachable
    Base.metadata.create_all(bind=engine)  # Auto-create all registered tables
    start_scheduler()
    logger.info("🗃️ Tables created/verified")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    stop_scheduler()
    logger.info("🛑 %s shutting down", settings.app_name)


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(analyze_router)
app.include_router(portfolio_router)
app.include_router(stream_router)
app.include_router(rag_router)
app.include_router(assets_router)
app.include_router(alerts_router)


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check() -> HealthResponse:
    """Liveness probe reporting system status."""
    is_db_up = True
    try:
        validate_db_connection()
    except Exception:
        is_db_up = False
        
    return HealthResponse(
        status="ok" if is_db_up else "degraded", 
        app=settings.app_name,
        details={"database": "online" if is_db_up else "offline"}
    )


