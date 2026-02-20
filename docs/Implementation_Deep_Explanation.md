# Infrastructure & Core Architecture Setup

## 1. What Was Built
We established the **foundational skeleton** for a production-grade FastAPI application. This is not just "Hello World"; it is a structured architecture designed for scalability, testability, and maintainability.

Specific components implemented:
1.  **Modular Project Structure**: Separated concerns into `api` (routers), `core` (config), `schemas` (data models), `services` (business logic), and `utils`.
2.  **Typed Configuration Management**: Used `pydantic-settings` to load and validate environment variables.
3.  **Structured Logging**: Configured a centralized logging format in `main.py`.
4.  **Global Error Handling**: Implemented middleware to catch and standardize `RequestValidationError` and unhandled `Exception`s.
5.  **Strict Data Contracts**: Defined Pydantic models (`AnalyzeRequest`, `AnalyzeResponse`) to enforce input/output schemas.
6.  **Testing Infrastructure**: Set up `pytest` with a session-scoped `TestClient` fixture and smoke tests.

## 2. Why This Approach Was Chosen
In a "Financial Research AI Agent," reliability and determinism are paramount. 

1.  **Reliability**: The strict Pydantic schemas prevent "garbage in, garbage out" scenarios, which is critical when dealing with financial data and LLM outputs.
2.  **Observability**: Centralized logging and global exception handling ensure that when (not if) things go wrong in production, we have structured logs and standard error responses (JSON) instead of unstructured stack traces crashing the server.
3.  **Security & Config**: Hardcoding API keys is a security risk. `pydantic-settings` strictly validates that required keys exist at startup.
4.  **Scalability**: Putting everything in one `main.py` works for 100 lines of code. For a system with Stocks, News, Portfolios, and RAG, a modular structure prevents circular imports and spaghetti code.

## 3. How It Works (Step-by-Step Flow)
1.  **Startup**:
    *   `app.main` imports `settings` from `app.core.config`.
    *   `Settings` loads variables from `.env`. If a required variable is missing, the app crashes immediately (fail-fast).
    *   `logging` is configured based on `settings.log_level`.
    *   `FastAPI` app is initialized.
    *   Routers (currently `analyze_router`) are registered.
2.  **Request Lifecycle (`POST /api/v1/analyze`)**:
    *   **Validation**: FastAPI uses `AnalyzeRequest` schema to validate the JSON body. If invalid, `validation_exception_handler` intercepts and returns a 422 JSON.
    *   **Routing**: Valid request is passed to `app.api.analyze.analyze`.
    *   **Processing**: The handler (currently a stub) would normally call `services`.
    *   **Response**: The handler returns a dictionary or object. FastAPI validates it against `AnalyzeResponse` schema.
    *   **Output**: JSON response is sent to the client.
3.  **Error Handling**:
    *   If any code raises an unhandled exception, `global_exception_handler` catches it, logs the stack trace, and returns a sanitized 500 Internal Server Error to the user.

## 4. Internal Code Breakdown

### `app/core/config.py`
```python
class Settings(BaseSettings):
    app_name: str = "Financial Research AI"
    # ...
    class Config:
        env_file = ".env"
```
*   **Why**: Logic-less configuration. It separates *code* from *environment*.
*   **Detail**: `BaseSettings` automatically reads from environment variables (case-insensitive). The inputs are typed (`bool`, `str`), performing implicit coercion (e.g., "true" string becomes `True` bool).

### `app/main.py` - Global Exception Handler
```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", str(exc), exc_info=True)
    return JSONResponse(status_code=500, content={"error": "internal_server_error", ...})
```
*   **Why**: Security and User Experience. Exposing raw stack traces to users is a security vulnerability (info leakage). This wrapper ensures the user sees a polite error while the developer gets the full trace in the logs.

### `app/schemas/analyze.py`
```python
class AnalyzeRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
```
*   **Why**: Defensive programming. We reject empty queries or massive payloads *before* they even reach our business logic or LLM.

## 5. Alternative Approaches

### A. Monolithic `main.py`
*   **Description**: Putting all logic, models, and routes in a single file.
*   **Why Rejected**: Unmaintainable for a multi-module system (Stock, News, RAG).

### B. Flask / Django
*   **Description**: Using older synchronous frameworks.
*   **Why Rejected**:
    *   **Async**: Financial data fetching and LLM calls are I/O bound. FastAPI's native `async` support handles concurrency much better than Flask.
    *   **Pydantic Integration**: FastAPI's deep integration with Pydantic makes validation declarative and automatic, saving boilerplate.

## 6. Trade-Off Analysis
| Feature | Chosen Approach (Modular FastAPI) | Alternative (Simple Script) |
| :--- | :--- | :--- |
| **Setup Time** | High (Files, folders, configs) | Low (One file) |
| **Refactoring Cost** | Low (Components are isolated) | High (Tangled logic) |
| **Type Safety** | High (Pydantic + Hints) | Low (dict passing) |
| **Performance** | High (Async/Uvicorn) | Medium/Low |

**Decision**: We paid the "Setup Time" cost now to avoid the "Refactoring Cost" later.

## 7. Risks & Limitations
1.  **Complexity Overhead**: For a new developer, navigating 6+ directories for a single endpoint can feel overwhelming compared to a single file.
2.  **Stub implementation**: currently `analyze.py` does nothing. The risk is that the implementation logic might become bloated inside the controller if we don't strictly move it to `services/`.

## 8. Future Improvements
1.  **Dependency Injection**: Use FastAPI's `Depends` to inject services (e.g., `StockService`) into routes. This improves testability by allowing easy mocking.
2.  **Structured Logging Middleware**: Replace the basic logger with structlog middleware that adds `request_id` to every log line for tracing.
3.  **Config Validation**: Add stricter validators to `Settings` (e.g., regex for API keys) to fail even faster if keys are malformed.

## Summary for Future Me
We built a **fortress, not a shack**.
*   **Config** is typed and declarative (`core/config.py`).
*   **Inputs/Outputs** are strictly contracted (`schemas/`).
*   **Errors** are caught and sanitized globally (`main.py`).
*   **Tests** are ready to run (`tests/`).

When you add the Stock Service, **do not** write logic in the router. Create `app/services/stock.py`, inject it into `app/api/analyze.py`, and let the router simply coordinate. Keep the architecture clean.

---

# Query Categorization Layer (Task 2)

## 1. What Was Built
A dedicated **Query Categorization Service** (`app/services/categorizer.py`) that classifies user input into one of four distinct intents:
*   `stock`: Direct questions about price, charts, or indicators.
*   `news`: Requests for headlines or recent events.
*   `portfolio`: Queries regarding personal holdings or transactions.
*   `general`: Everything else.

Features:
*   **Strict Typing**: Uses `Literal["stock", ...]` to enforce compile-time and runtime type safety.
*   **Mock Implementation**: Currently uses a robust keyword-based heuristic (logic branching) to simulate LLM decision-making for testing purposes.
*   **Comprehensive Testing**: Verified with 20+ test cases covering all categories and edge cases.

## 2. Why This Approach Was Chosen
Categorization is the **router** of our AI agent. If this fails, the whole downstream process fails (e.g., fetching stock data for a "hello" message).

1.  **Separation of Concerns**: By isolating this logic in `services/categorizer.py`, the API router (`analyze.py`) remains clean and doesn't care *how* categorization happens (LLM vs Rule-based).
2.  **Mockability**: We implemented a deterministic keyword-based mock first. This allows us to build and test the *rest* of the system (API, Frontend, Data Fetching) without blocked on API keys or incurring LLM costs during dev.
3.  **Strict Contracts**: Returning a string is dangerous. Returning a `Literal` ensures we catch typos like "Stock" (uppercase) vs "stock" (lowercase) immediately.

## 3. How It Works (Step-by-Step Flow)
1.  **Input**: `categorize_query(query: str)` receives the raw user question.
2.  **Normalization**: The query is lowercased to ensure case-insensitive matching.
3.  **Heuristic Matching** (Current Mock):
    *   Checks for **Stock** keywords (`price`, `pe ratio`, `chart`, etc.).
    *   Checks for **News** keywords (`news`, `headline`, `event`).
    *   Checks for **Portfolio** keywords (`holding`, `bought`, `sell`).
4.  **Fallback**: If no specific keywords match, it defaults to `general`. This is a "fail-safe" mechanism to prevent the agent from hallucinating financial actions on non-financial queries.
5.  **Output**: Returns a `Category` typed string.

## 4. Internal Code Breakdown

### `app/services/categorizer.py`
```python
Category = Literal["stock", "news", "portfolio", "general"]

async def categorize_query(query: str) -> Category:
    # ...
    if any(x in q for x in ["price", "pe ratio", ...]):
        return "stock"
    return "general"
```
*   **Design Decision**: Why `async`? Even though the mock is synchronous, the *interface* is defined as `async`. This is forward-looking. When we replace the keywords with an actual LLM network call, we won't need to refactor the function signature or the callers.

### `tests/test_categorization.py`
```python
@pytest.mark.asyncio
async def test_categorize_stock():
    queries = ["What is the price of AAPL?", ...]
    for q in queries:
        assert await categorize_query(q) == "stock"
```
*   **Why**: We test behavior, not implementation. We feed raw strings and expect specific enums. This test will remain valid even when we swap the keyword logic for OpenAI.

## 5. Alternative Approaches

### A. All-in-One LLM Call
*   **Description**: Sending the query to the LLM and asking it to "Answer this question" directly without categorization.
*   **Why Rejected**:
    *   **Cost**: "Hello" doesn't need a GPT-4 call.
    *   **Reliability**: An unconstrained LLM might try to invent stock prices. Categorizing first allows us to call the *correct* tool (yFinance) or route (RAG).

### B. Regex Matching
*   **Description**: Using complex Regex patterns.
*   **Why Rejected**: Too brittle. `any(x in q)` contains the same logic but is more readable Python. Eventually, both will be replaced by an LLM, so investing in complex Regex is waste.

## 6. Risks & Limitations
1.  **Keyword Fragility**: The current mock is easily fooled. "What is the *price* of a shoe?" will be categorized as `stock` because of the word "price".
    *   *Mitigation*: This is acceptable for Phase 1 dev. Phase 2 (LLM) fixes this context awareness.
2.  **Overlap**: "News about Apple stock price" contains keywords for both `news` and `stock`. The current precedence rules (Stock > News) might hide intent.

## 7. Future Improvements
1.  **LLM Integration**: Replace the `if/else` block with a structured LLM prompt (using `instructor` or strict JSON mode) to get the category.
2.  **Confidence Score**: Return `(Category, float)` so the system can ask for clarification if confidence is low (e.g., < 0.7).
