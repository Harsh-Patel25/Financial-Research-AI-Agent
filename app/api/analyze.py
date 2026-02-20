"""
Analyze API Router (app/api/analyze.py)

This module defines the API boundary for the analysis feature.
It is responsible for handling incoming requests, validating input,
and returning structured responses.

Responsibilities:

1. Router Definition
   - Uses FastAPI's APIRouter to create a modular route group.
   - Keeps this feature isolated from the main application file.
   - Promotes clean and scalable architecture.

2. Request & Response Schemas
   - Enforces strict input validation using AnalyzeRequest.
   - Ensures consistent output structure using AnalyzeResponse.
   - Prevents invalid or unstructured data from entering the system.

3. API Contract Enforcement
   - Defines a POST endpoint at "/analyze".
   - Automatically validates request payloads.
   - Guarantees response format consistency.

4. Separation of Concerns
   - Contains no business logic.
   - Acts only as a thin controller layer.
   - Designed to delegate processing to a future service layer.

5. Extensibility
   - Stub response currently returned.
   - Ready for service injection (e.g., LLM processing, analytics engine).
   - Easily testable and maintainable.

Overall, this module serves as the API interface layer,
ensuring modularity, strict validation, and production-ready structure.
"""

from fastapi import APIRouter
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse

router = APIRouter(prefix="/api/v1", tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    """
    Accepts a financial question, categorizes it, fetches relevant data,
    runs LLM analysis, and returns a structured JSON response.

    This is a stub — services will be wired in subsequent tasks.
    """
    # TODO Task 2: plug in categorization service
    # TODO Task 3/4: plug in stock / news service
    # TODO Task 5: plug in LLM analysis service
    return AnalyzeResponse(
        category="general",
        summary="[STUB] Analysis pipeline not yet connected.",
        data={"question": payload.question},
        confidence=None,
    )
