import time
import logging
from fastapi import Request

# Use standard logging to avoid "Missing Module" yellow lines
logger = logging.getLogger("telemetry")

async def performance_metrics_middleware(request: Request, call_next):
    """
    Middleware to log execution time for all endpoints.
    Helps track performance bottlenecks and LLM latency.
    """
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Do not log standard health checks heavily to prevent spam
    if "/health" not in str(request.url):
        duration_ms = round(process_time * 1000, 2)
        logger.info(
            "API Request processed | %s %s | Status: %d | Duration: %0.2fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms
        )
    return response
