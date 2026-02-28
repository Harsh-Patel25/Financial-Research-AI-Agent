"""
Schemas – Analyze Module (app/schemas/analyze.py)

This module defines the data contract layer of the application.
It strictly controls what the client can send (Request schema)
and what the server must return (Response schema).

By using Pydantic models, the API remains structured,
validated, and production-safe.

────────────────────────────────────────────

1) Imports

- BaseModel:
  Used to define structured data models.
- Field:
  Used to add validation constraints (e.g., min/max length).

Pydantic integrates tightly with FastAPI and automatically
validates incoming requests.

────────────────────────────────────────────

2) AnalyzeRequest

class AnalyzeRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)

Purpose:
- Ensures the client must send a "question" field.
- Enforces validation rules:
    • Required field (cannot be omitted)
    • Minimum length: 3 characters
    • Maximum length: 1000 characters

Benefits:
- Prevents empty input
- Blocks extremely short or spam-like input
- Protects against oversized payloads
- Removes need for manual validation logic

────────────────────────────────────────────

3) AnalyzeResponse

class AnalyzeResponse(BaseModel):
    category: str
    summary: str

Purpose:
- Enforces a consistent response structure.
- Guarantees the API always returns:
    • category
    • summary

If the returned data does not match this structure,
FastAPI will raise an error automatically.

────────────────────────────────────────────

Why This File Is Important

✔ Blocks invalid or garbage input
✔ Prevents empty or oversized requests
✔ Guarantees predictable API responses
✔ Enforces strict request/response contracts
✔ Keeps API behavior consistent

────────────────────────────────────────────

Future Benefit (LLM Integration)

When integrating an LLM, you can instruct it to:
"Return output strictly in this JSON format."

The response can then be validated against AnalyzeResponse,
making the system more reliable and future-proof.

────────────────────────────────────────────

Architecture Flow

Client
   ↓
AnalyzeRequest (automatic validation)
   ↓
Business Logic / LLM
   ↓
AnalyzeResponse (enforced structure)
   ↓
Client

This schema layer acts as both:
- A security gate (input validation)
- A contract enforcer (output structure)
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal


# ── Request ──────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The user's financial question or query.",
        examples=["What is the current price of AAPL?"],
    )


# ── Response ─────────────────────────────────────────────────────────────────

class AnalyzeResponse(BaseModel):
    category: Literal["stock", "news", "portfolio", "general"]
    summary: str = Field(..., description="LLM-generated analysis summary.")
    data: Optional[dict] = Field(
        default=None,
        description="Structured data from external sources (stock, news, etc.)",
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Model confidence score (0-1).",
    )


# ── Health ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    app: str = "Financial Research AI"
