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

from app.core.config import settings
from app.api.analyze import router as analyze_router
from app.schemas.analyze import HealthResponse

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    description="Production-grade Financial Research AI API.",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,  # disable Swagger in prod
    redoc_url=None,
)

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
@app.on_event("startup")
async def on_startup() -> None:
    logger.info("🚀 %s starting up", settings.app_name)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("🛑 %s shutting down", settings.app_name)


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(analyze_router)


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check() -> HealthResponse:
    """Liveness probe — returns 200 if the service is up."""
    return HealthResponse(status="ok", app=settings.app_name)


