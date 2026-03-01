# Infrastructure & Core Architecture Setup

## 1. What Was Built
We established the **foundational skeleton** for a production-grade FastAPI application. This is not just "Hello World"; it is a structured architecture designed for scalability, testability, and maintainability.

Specific components implemented:
1.  **Modular Project Structure**: Separated concerns into `api` (routers), `core` (config), `schemas` (data models), `services` (business logic), and `utils`.
2.  **Typed Configuration Management**: Used `pydantic-settings`-> `Environment variables ko typed Python objects mein convert aur validate karti hai.`
without it :
❌ Sab strings return hote hain
❌ Type conversion manual karna padta hai
❌ Missing variable detect nahi hota
❌ Silent failure hota hai
❌ No validation
`pydantic-settings`-> to load and validate environment variables.
with using this : 
✅ Sab strings ko correct types mein convert karta hai
✅ Missing variables ko detect karta hai
✅ Startup pe hi error deta hai (fail-fast)
✅ Automatic validation
✅ Type hints + IDE support
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

# Resilient Database Integration (Task 2.5 Part 1)

## 1. What Was Built
We expanded the core data layer to support **production-ready database configurations**. This includes multi-provider support (SQLite/PostgreSQL) and a "fail-fast" validation system.

Specific components implemented:
1.  **Multi-Provider Engine**: The engine logic in `database.py` now dynamically handles connection arguments based on the database driver (e.g., safe threading for SQLite).
2.  **Startup Connection Validation**: A `validate_db_connection()` utility that runs a lightweight `SELECT 1` query to verify the database is alive before the API starts accepting requests.
3.  **Production Driver Support**: Integrated `psycopg2-binary` as the default PostgreSQL driver.
4.  **Graceful Fail-Fast**: Wired the validation into FastAPI's `on_startup` event so the server crashes immediately with a `CRITICAL` log if the DB is unreachable, preventing misleading "Ghost" service availability.

## 2. Why This Approach Was Chosen
In production, database connection issues (wrong password, network timeout, RDS downtime) are common causes of failure.

1.  **Environment Parity**: Using SQLite for local dev and PostgreSQL for production is the "Twelve-Factor App" standard. We made this switch as easy as changing one line in `.env`.
2.  **Fail-Fast Principle**: It is better for a service to fail to start than to start up and return 500 errors to every user request because of a hidden connection issue.
3.  **Heimdall (Watchman) Pattern**: The `validate_db_connection()` acts as a gatekeeper. It ensures that if the server is "Green" (running), the data layer is guaranteed to be functional.

## 3. How It Works (Step-by-Step Flow)
1.  **Init**: `main.py` triggers the `@app.on_event("startup")` hook.
2.  **Handshake**: `validate_db_connection()` is called.
3.  **Verification**:
    *   The engine creates a temporary connection.
    *   It executes `SELECT 1` (a hardware-agnostic "ping").
    *   If the DB responds, the connection is closed and execution continues.
4.  **Lifecycle**: If the handshake fails, it raises an exception, logs a `CRITICAL` error, and the Uvicorn process terminates.

## 4. Internal Code Breakdown

### `app/core/database.py` - Validation Logic
```python
def validate_db_connection() -> None:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection validated")
    except Exception as exc:
        logger.critical("❌ Database connection FAILED | %s", str(exc))
        raise
```
*   **Why**: By using `engine.connect()` in a context manager (`with`), we ensure the validator doesn't leak connections or leave idle sessions on the database server.

### `requirements.txt`
*   **psycopg2-binary**: This is the "glue" between Python and PostgreSQL. Without this library, SQLAlchemy wouldn't know how to speak the Postgres protocol.

## 5. Risks & Limitations
1.  **Mocking during tests**: Tests currently expect a working DB. If `validate_db_connection()` is called in the test setup and no DB exists, tests will fail immediately.
2.  **Driver Compatibility**: While `psycopg2-binary` is great for dev/prod simplicity, some high-performance production environments prefer the source-compiled `psycopg2`.

## 6. Future Improvements
1.  **Connection Pooling**: Configure `pool_size` and `max_overflow` settings in `database.py` for high-concurrency production environments.
2.  **Health Check Integration**: Expose the DB status in the `/health` endpoint so external monitors (like Kubernetes Liveness probes) can see if the DB goes down *after* startup.

---

# Holdings Model (Task 2.5 – Table Design)

## 1. What Was Built
`app/models/holding.py` — A SQLAlchemy ORM model representing a single stock position inside a portfolio.

Fields:
- `id` — Primary key
- `portfolio_id` — Foreign key to `portfolios.id`, indexed
- `symbol` — Stock ticker (e.g., "AAPL"), indexed
- `quantity` — Float (supports fractional shares)
- `average_price` — Float (average cost per share)

## 2. Key Design Decisions

### Two-Layer Cascade (Critical)
| Layer | What | When it fires |
| :--- | :--- | :--- |
| `ondelete="CASCADE"` on FK | DB-level delete | When a row is deleted directly in SQL |
| `cascade="all, delete-orphan"` on relationship | ORM-level delete | When a Python object is deleted via SQLAlchemy session |

Both are needed because you might delete a portfolio either via raw SQL (migrations, admin scripts) or via the ORM. Having only one layer leaves a gap.

### Circular Import Prevention — `TYPE_CHECKING`
`Portfolio` references `Holding` and `Holding` references `Portfolio`. At runtime, Python resolves imports linearly, which would cause a circular import error.
```python
# Only resolved by mypy/IDE — invisible to Python at runtime
if TYPE_CHECKING:
    from app.models.holding import Holding
```

## 3. How It Integrates
```
portfolio.holdings         → list of Holding objects (ORM navigates FK)
holding.portfolio          → parent Portfolio object (back-reference)
db.delete(portfolio)       → SQLAlchemy auto-deletes all Holdings (ORM cascade)
```

## 4. Potential Errors & Debugging
| Error | Cause | Fix |
| :--- | :--- | :--- |
| `NoForeignKeysError` | Typo in `ForeignKey("portfolios.id")` | Confirm `__tablename__ = "portfolios"` in Portfolio |
| `CircularImportError` | Removed `TYPE_CHECKING` guard | Restore the guard |
| Orphaned rows after delete | `ondelete="CASCADE"` missing | Add it to the ForeignKey definition |

---

# Transactions Model (Task 2.5 – Table Design)

## 1. What Was Built
`app/models/transaction.py` — An immutable audit-trail model recording every buy/sell event for a stock.

Fields:
- `id` — Primary key
- `portfolio_id` — FK to `portfolios.id`, indexed
- `symbol` — Stock ticker, indexed
- `transaction_type` — Enum: `buy` or `sell` (enforced at DB + Python level)
- `quantity` — Shares involved in this transaction
- `price` — Per-share price at transaction time
- `timestamp` — Auto-set by DB server at INSERT time

## 2. Key Design Decisions

### Python Enum + SQLAlchemy Enum (Double Enforcement)
```python
class TransactionType(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"

transaction_type: Mapped[TransactionType] = mapped_column(
    SAEnum(TransactionType, name="transaction_type_enum", create_type=True)
)
```

| Layer | Role |
| :--- | :--- |
| Python `enum.Enum` | Prevents invalid strings in Python code (`TransactionType.BUY` not `"BUY"`) |
| `SAEnum` in SQLAlchemy | Creates a DB-level ENUM type — database rejects any value outside `('buy', 'sell')` |
| `(str, enum.Enum)` inheritance | Value serializes as plain `"buy"` / `"sell"` in JSON without extra conversion |

### `server_default=func.now()` vs `default=datetime.utcnow`
We use `server_default=func.now()` (DB sets the time) rather than Python's `datetime.now()` because:
- DB time is consistent even across **multiple app server instances** or **different time zones**.
- Python time depends on the machine running the app — unreliable in distributed systems.

### Transactions Are Immutable
A `Transaction` record should **never be updated**. It is a financial ledger entry. If you reverse a sell, you record a new BUY transaction. This is a critical financial integrity principle.

## 3. Execution Flow
```
Client calls POST /portfolio/transaction
  → Service creates Transaction(type=BUY, qty=10, price=175.0)
  → db.add(transaction) → db.commit()
  → DB auto-sets timestamp via server_default
  → Service also updates the related Holding's quantity/average_price
```

## 4. Potential Errors & Debugging
| Error | Cause | Fix |
| :--- | :--- | :--- |
| `LookupError: 'BUY' is not a valid TransactionType` | Sending `"BUY"` (uppercase) instead of `"buy"` | Always send lowercase; Enum values are `"buy"` / `"sell"` |
| `DataError: invalid input for enum` | DB received an unlisted value | Use `TransactionType.BUY` — never raw strings |
| Missing `timestamp` column | `create_type=True` missing on Postgres | Add `create_type=True` to `SAEnum(...)` |

---

# ORM Session Layer (Task 2.5 – Session Management)

## 1. What Was Built
`app/core/dependencies.py` — upgraded `get_db()` with full safe transaction management.

## 2. The Transaction Lifecycle (Step-by-Step)
```
Request arrives
    → get_db() opens a new Session
    → yields db to the route handler
        → Route does: db.add(), db.query(), etc.
    → Route returns normally?
        ✅ YES → db.commit()  (writes are permanent)
        ❌ NO  → db.rollback() (all writes are undone)
    → ALWAYS → db.close() (connection returned to pool)
```

## 3. Why This Pattern (try / except / finally)

```python
try:
    yield db          # give session to route
    db.commit()       # success → persist
except Exception as exc:
    db.rollback()     # failure → undo
    raise             # re-raise so FastAPI still returns correct HTTP error
finally:
    db.close()        # always release connection
```

| Block | When | Purpose |
| :--- | :--- | :--- |
| `try` → `yield` | Every request | Opens session and hands it to route |
| `db.commit()` | Route succeeds | Makes all DB changes permanent |
| `except` → `db.rollback()` | Any exception | Reverts all changes — prevents corrupt state |
| `raise` | Any exception | Re-raises so FastAPI returns the correct 404/422/500 |
| `finally` → `db.close()` | Always | Releases DB connection back to the pool |

## 4. Critical Design Decision — Why Commit Inside the Dependency?
The alternative is to call `db.commit()` inside every route handler. The problem:
- Inconsistent — a developer might forget to call `commit()`.
- Noisy — commit/rollback logic inside business routes breaks separation of concerns.

By centralizing it in `get_db()`, every route automatically gets **atomic transaction behavior** without writing a single line of transaction management code.

## 5. Potential Errors & Debugging
| Error | Cause | Fix |
|---|---|---|
| Changes not persisted | Using `db.flush()` thinking it commits | `flush()` writes to DB memory but only `commit()` persists permanently |
| `InvalidRequestError` after exception | Calling `db.commit()` after an exception without rollback | The `except` block handles this automatically |
| Connection pool exhaustion | Session not closed | The `finally` block guarantees `db.close()` always runs |

---

# Portfolio CRUD Endpoints (Task 2.5 – API Layer)

## 1. What Was Built
Three files implementing the full CRUD layer for portfolios following the **thin-controller pattern**:

| File | Role |
| :--- | :--- |
| `app/schemas/portfolio.py` | Pydantic request/response contracts |
| `app/services/portfolio_service.py` | All business logic |
| `app/api/portfolio.py` | Thin HTTP router — delegates everything to service |

## 2. Endpoints Created

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `POST` | `/portfolios/` | Create a new portfolio |
| `POST` | `/portfolios/{id}/holdings` | Add or upsert a stock holding |
| `POST` | `/portfolios/{id}/transactions` | Record a buy/sell transaction |

## 3. Key Design Decisions

### Thin Controller Rule
```
Router → receives HTTP request → validates with schema → calls service
Service → contains all logic → queries/writes DB → returns ORM object
Router → converts ORM object to Pydantic response → returns JSON
```
Routers have zero `if/else` business logic. Every decision is in the service.

### Weighted Average Price (for holdings)
When a holding already exists and more shares are bought:
```
new_avg = (old_qty * old_avg_price + new_qty * new_price) / total_qty
```
This correctly reflects the true average cost basis, matching how brokerage apps calculate it.

### Oversell Guard
A `SELL` transaction is rejected with HTTP 422 if the quantity to sell exceeds shares held:
```python
if existing_holding.quantity < quantity:
    raise HTTPException(422, "Cannot sell more than you hold")
```
This prevents negative holdings, which would corrupt portfolio state.

### Duplicate Portfolio Name
Attempting to create two portfolios with the same name returns HTTP 409 Conflict — not a 500 crash.

### `db.flush()` Before Log
After `db.add(portfolio)`, we call `db.flush()` to get the auto-generated `id` from the DB before commit. Without this, `portfolio.id` would be `None` at log time.

## 4. Full Execution Flow (Create Portfolio)
```
POST /portfolios/ { "name": "My NIFTY50" }
  → CreatePortfolioRequest validates (min_length=1, max_length=255)
  → create_portfolio() queries for duplicate name
  → Not found → Portfolio(...) created → db.add() → db.flush()
  → get_db() commits transaction
  → _build_portfolio_response() maps ORM → Pydantic
  → HTTP 201 { "id": 1, "name": "My NIFTY50", "holdings": [] }
```

## 5. Potential Errors & Debugging
| Error | Cause | Fix |
| :--- | :--- | :--- |
| `409 Conflict` on create | Same portfolio name used twice | Use a unique name |
| `404 Not Found` on holdings/txn | Wrong portfolio_id | Verify the portfolio exists first |
| `422 Unprocessable` on sell | Selling more shares than held | Check current holding quantity |
| `None` for timestamp in response | Transaction not yet committed | `flush()` before returning ensures ID exists; timestamp set by DB on commit |

---

# Fetch Portfolio Summary (Task 2.5 – Summary Endpoint)

## 1. What Was Built
`GET /portfolios/{id}/summary` — Returns an aggregated, read-only view of a portfolio.

### New Files/Changes
| File | Change |
| :--- | :--- |
| `app/schemas/portfolio.py` | Added `PortfolioSummaryResponse` schema |
| `app/services/portfolio_service.py` | Added `get_portfolio_summary()` function |
| `app/api/portfolio.py` | Added `GET /{portfolio_id}/summary` endpoint |

## 2. Response Shape
```json
{
  "id": 1,
  "name": "My Portfolio",
  "created_at": "2026-02-22T00:00:00",
  "total_holdings": 3,
  "total_invested": 15250.00,
  "market_value": null,
  "holdings": [
    { "symbol": "AAPL", "quantity": 10, "average_price": 175.0, "total_invested": 1750.0 }
  ]
}
```

## 3. Key Design Decisions

### `market_value = None` (Placeholder)
Market value = current live price × quantity. We don't have live prices yet (that's Task 3 — Stock Service). Setting it to `None` now with a `Optional[float]` type is intentional:
- Response is structurally correct today.
- Task 3 can plug in `h.quantity * stock_service.get_price(h.symbol)` with zero schema changes.

### `total_invested` Calculation
```python
total_invested = sum(h.quantity * h.average_price for h in holdings)
```
This uses the stored `average_price` (weighted average cost basis), not the live price. This is the "how much did I pay" metric, not "how much is it worth now".

## 4. Execution Flow
```
GET /portfolios/1/summary
  → _get_portfolio_or_404() verifies portfolio exists
  → portfolio.holdings loaded via ORM relationship
  → total_holdings = len(holdings)
  → total_invested = sum(qty × avg_price)
  → market_value = None (placeholder)
  → PortfolioSummaryResponse(**data) returned as JSON
```

## 5. Potential Errors & Debugging
| Error | Cause | Fix |
| :--- | :--- | :--- |
| `404 Not Found` | Wrong portfolio_id in URL | Verify portfolio was created first |
| `total_invested = 0.0` | No holdings exist yet | Add holdings via `POST /{id}/holdings` first |
| `market_value always null` | Expected — placeholder | Will be populated in Task 3 (Stock Service) |

---

# yFinance Stock Service (Task 3)

## 1. What Was Built
`app/services/stock_service.py` — A stateless class that wraps yFinance for clean, structured market data retrieval.

| Method | Purpose |
| :--- | :--- |
| `get_current_price(symbol)` | Fetch latest price + day high/low/prev close |
| `get_historical_data(symbol, period, interval)` | Fetch OHLC + Volume candles as a list of dicts |

A module-level singleton `stock_service` is exported for app-wide use.

## 2. Key Design Decisions

### Class-Based (Not Function-Based)
Using a class allows easy unit testing — tests can mock `StockService` with a fake that returns controlled data, without hitting the real yFinance API.

### `fast_info` with `.info` Fallback
```python
price = getattr(info, "last_price", None)           # fast path (no scraping)
if not price:
    price = ticker.info.get("currentPrice")           # fallback (slower, reliable)
```
`fast_info` is ~10x faster than `.info` (no HTML scraping), but occasionally returns `None` for some exchanges. The fallback catches this silently.

### Clean Dict Output (No DataFrames Leaked)
yFinance returns `pd.DataFrame` and `pd.Timestamp`. These cannot be JSON-serialized directly.
```python
# BAD:  return df                     (DataFrame — JSON fails)
# GOOD: return {"data": [{"date": ts.strftime(...), ...} for ts, row in df.iterrows()]}
```
All pandas types are normalized to `str`, `float`, and `int` before leaving the service.

### Two-Tier Error Handling
| Exception | Meaning | When |
| :--- | :--- | :--- |
| `ValueError` | Bad input (unknown symbol, no data found) | API returned empty response |
| `RuntimeError` | Infrastructure failure (network, timeout) | yFinance internal error |

Routers convert these to HTTP 404 / 503 as needed.  The service never imports FastAPI.

## 3. Execution Flow

```
caller → stock_service.get_current_price("AAPL")
  → yf.Ticker("AAPL")
  → ticker.fast_info.last_price
    → price is None? → fallback to ticker.info["currentPrice"]
    → still None? → raise ValueError("No price data for 'AAPL'")
  → build & return clean dict
```

## 4. Potential Errors & Debugging
| Error | Cause | Fix |
| :--- | :--- | :--- |
| `ValueError: No price data for 'XYZ'` | Bad/delisted symbol | Check symbol spelling; add `.NS` suffix for NSE stocks (e.g., `RELIANCE.NS`) |
| `RuntimeError: Failed to fetch price` | Network timeout or yFinance outage | Retry mechanism handles this automatically (see below) |
| `df.empty = True` for historical | Period/interval mismatch | Use `1d` interval with `1mo` period for reasonable results |

---

# Retry Mechanism — Tenacity (Task 3)

## 1. What Was Built
Both `StockService` methods are now wrapped with a shared **tenacity retry policy** defined once as `_stock_retry` and applied as a decorator.

## 2. Retry Policy Configuration
```python
_stock_retry = retry(
    retry=retry_if_exception_type(RuntimeError),      # Only retry network failures
    stop=stop_after_attempt(3),                        # Max 3 total attempts
    wait=wait_exponential(multiplier=1, min=2, max=8), # 2s → 4s → 8s backoff
    before_sleep=before_sleep_log(logger, logging.WARNING),  # Log every retry
    reraise=True,                                      # Re-raise after exhaustion
)
```

Applied as:
```python
@_stock_retry
def get_current_price(self, symbol): ...

@_stock_retry
def get_historical_data(self, symbol, period, interval): ...
```

## 3. Key Design Decisions

### Why Only Retry `RuntimeError`?
`ValueError` means the symbol is invalid — retrying will always fail. `RuntimeError` means a network/server problem — it may succeed next attempt.

### Why Exponential Backoff?
Linear backoff (wait 2s each time) hits the API at a constant rate during an outage. Exponential backoff gives the external service more time to recover between attempts.

### Shared Policy Object (Not Inline Decorator Args)
Defining `_stock_retry` once and reusing it across methods ensures:
- Both methods have **identical** retry behavior — no copy-paste divergence.
- Changing the retry config requires editing **one place**.

## 4. Retry Timeline
```
Attempt 1 → FAIL (RuntimeError)  → wait 2s  → log WARNING
Attempt 2 → FAIL (RuntimeError)  → wait 4s  → log WARNING
Attempt 3 → FAIL (RuntimeError)  → reraise RuntimeError to caller
```

## 5. Potential Issues
| Issue | Cause | Fix |
| :--- | :--- | :--- |
| Retries fire for `ValueError` | Wrong exception type in `retry_if_exception_type` | Keep it as `RuntimeError` only |
| Retries too slow | `min` backoff too high | Reduce `min=2` if needed for low-latency contexts |
| `RetryError` not caught | Caller expects `RuntimeError` | `reraise=True` ensures original `RuntimeError` is raised, not `RetryError` |


# Circuit Breaker Pattern (Task 3 – Resilience Layer)

## 1. Overview

Implemented: `app/core/circuit_breaker.py`

A thread-safe, 3-state circuit breaker protecting `StockService` from cascading failures when yFinance is unavailable.

Purpose:
> Prevent repeated network hits to a failing external dependency and maintain backend stability.

---

## 2. Problem Solved

Without Circuit Breaker:
- Repeated failing network calls
- Increased latency
- Thread pool exhaustion risk
- Cascading service degradation

With Circuit Breaker:
- Stops calls after failure threshold
- Protects system resources
- Enables controlled recovery

---

## 3. Three-State Model

```

CLOSED ──(≥3 failures)──► OPEN ──(timeout)──► HALF_OPEN
▲                                           │
└──────────────(probe success)──────────────┘

```

| State      | Behavior |
|------------|----------|
| CLOSED     | Normal operation; calls pass through |
| OPEN       | Calls blocked immediately |
| HALF_OPEN  | One probe call allowed |

---

## 4. State Transitions

- **CLOSED → OPEN**  
  After 3 consecutive `RuntimeError` failures.

- **OPEN → HALF_OPEN**  
  After `recovery_timeout` (default: 30s).

- **HALF_OPEN → CLOSED**  
  Probe succeeds → reset failure count.

- **HALF_OPEN → OPEN**  
  Probe fails → reopen circuit.

---

## 5. Integration Flow

```

Route
↓
StockService
↓
CircuitBreaker.call()
↓
@_stock_retry (Tenacity)
↓
yFinance API

```

- Retry handles transient errors (per request).
- Circuit breaker handles systemic failures (across requests).

---

## 6. Thread Safety

Uses `threading.Lock` to:
- Protect `_failure_count`
- Ensure atomic state transitions
- Prevent race conditions under concurrency

---

## 7. Singleton Design

`stock_service` is module-level singleton → circuit breaker state is shared globally.

Correct behavior:
- Failure accumulation across all requests
- System-wide protection

---

## 8. Retry + Circuit Breaker Interaction

Example timeline:

```

Request 1 → retry exhausted → failure_count = 1
Request 2 → retry exhausted → failure_count = 2
Request 3 → retry exhausted → failure_count = 3 → OPEN
Next requests → blocked instantly

```

---

## 9. Configuration

| Parameter | Default | Purpose |
|------------|----------|----------|
| failure_threshold | 3 | Failures before OPEN |
| recovery_timeout | 30s | Wait before HALF_OPEN |
| exception_type | RuntimeError | Count only infra failures |

---

## 10. Benefits

- Fault isolation
- Controlled recovery
- Resource protection
- Reduced cascading failures
- Production-grade resilience

---

## 11. Current Resilience Level

| Feature | Status |
|----------|--------|
| Retry with backoff | ✅ |
| Circuit breaker | ✅ |
| Thread safety | ✅ |
| Shared failure state | ✅ |

StockService is now production-grade in terms of fault tolerance.
```

---

# DataProvider Interface (Task 3)

## What Was Built
`app/services/data_provider.py` — An abstract interface (Strategy pattern) that decouples all business logic from any specific stock data source.

| Class | Role |
| :--- | :--- |
| `DataProvider` (ABC) | Defines the contract — `get_stock_data()` and `get_historical_data()` |
| `YFinanceProvider` | Concrete implementation — delegates to the existing `StockService` |
| `default_provider` | Module-level singleton used by routers and services |

## What Changed and Why
Previously, business logic would import `stock_service` (yFinance) directly — tightly coupling every caller to one provider. Adding AlphaVantage or a test mock would require touching multiple files.

With this pattern, all callers import `default_provider`. Switching providers = changing **one line** in `data_provider.py`. Everything else stays the same.

`YFinanceProvider` inherits all existing resilience (retry + circuit breaker) automatically, since it delegates to `StockService`.

## How to Plug In a New Provider
```python
class AlphaVantageProvider(DataProvider):
    def get_stock_data(self, symbol: str) -> dict: ...
    def get_historical_data(self, symbol, period, interval) -> dict: ...

# One-line swap — no other file changes needed:
default_provider = AlphaVantageProvider()
```

## Potential Errors & Debugging
| Error | Cause | Fix |
| :--- | :--- | :--- |
| `TypeError: Can't instantiate abstract class` | New provider missing a required method | Implement all `@abstractmethod` methods |
| Circular import at startup | `stock_service` imported at module top | Import is deferred inside `__init__` — resolves lazily |

---

# Technical Indicators & StockDataResponse (Task 3 – Analytics Layer)

## 1. Overview

Implemented: `app/services/indicators.py`, `app/schemas/stock.py`, and `get_full_stock_data()` in `StockService`.

A pure-function technical analysis module coupled with a strict Pydantic response schema to enrich raw price data with standard market indicators.

Purpose:
> Transform basic market quotes into actionable financial datasets suitable for LLM analysis, ensuring all calculations are mathematically sound, isolated from external I/O, and structured deterministically.

---

## 2. Problem Solved

Without this layer:
- LLM receives only raw prices, forcing it to guess market momentum
- Indicator logic gets tangled with API fetch logic, making testing impossible
- Null or missing data from APIs causes silent downstream math errors or schema validation crashes

With this layer:
- LLM receives pre-calculated, deterministic technical signals (RSI, SMA, EMA)
- Pure functions allow 100% unit test coverage without network calls
- Strict schema enforces safe fallback (null) for missing historical data without breaking the live price feed

---

## 3. What Was Built

### A. Pure Indicator Functions (`indicators.py`)
- **`calculate_rsi(prices, period=14)`**: Uses Wilder's Exponential Smoothing (industry standard, matching TradingView/Bloomberg). Identifies overbought (>70) and oversold (<30) conditions.
- **`calculate_sma(prices, period=20)`**: Simple Moving Average. Arithmetic mean of the window.
- **`calculate_ema(prices, period=20)`**: Exponential Moving Average. Weights recent prices more heavily using pandas `ewm(span=20, adjust=False)`.
- **`calculate_all(prices)`**: Composite wrapper that safely computes all 3 indicators and traps `ValueError` (insufficient data) to return `None` silently.

### B. Output Contract (`schemas/stock.py`)
`StockDataResponse` acts as the final gatekeeper before data is returned to the router or injected into an LLM prompt.
- **Mandatory fields**: `symbol`, `current_price` (must be > 0), `timestamp`
- **Optional/Context fields**: `currency`, `exchange`, `market_state`, `previous_close`, `day_high/low`, `volume`
- **Nullable Indicator fields**: `rsi`, `sma`, `ema`

---

## 4. State & Data Flow Pipeline

```
Route / Agent
↓
StockService.get_full_stock_data("AAPL")
│
├── 1. Live Price Fetch
│      └─► CircuitBreaker.call(get_current_price) → dict
│
├── 2. Historical Fetch (Isolated Try/Except)
│      └─► CircuitBreaker.call(get_historical) → pandas.Series
│
├── 3. Pure Calculation Phase
│      └─► calculate_all(series) → {"rsi": 57.1, "sma": 145.2, ...}
│
└── 4. Schema Assembly
       └─► Merge dicts → Return flattened output
↓
StockDataResponse.model_validate(output)
```

---

## 5. Key Design Decisions

### Pure Functions for Math
Indicators accept `pd.Series` or `list` and return `float`. They do absolutely zero network calling. This cleanly separates the "how to get data" (yFinance) from the "how to analyze data" (pandas).

### Soft Failure on Historical Data
If `get_current_price` fails, the request aborts (raises RuntimeError). Live price is critical.
However, if `get_historical_data` fails (or returns < 20 days of data for a newly listed IPO), the indicators silently fall back to `None`. The client still receives the live stock quote.

### Wilder's Smoothing for RSI
Naïve RSI implementations use standard rolling averages. Professional trading desks use J. Welles Wilder's original exponential smoothing. The implementation `ewm(alpha=1/period, adjust=False)` guarantees that our RSI exactly matches charting platforms.

---

## 6. Schema Structure

| Field | Type | Validation | Missing State |
|---|---|---|---|
| `current_price` | `float` | `gt=0` | Triggers 404/503 (mandatory) |
| `rsi` | `float` | `ge=0, le=100` | `null` |
| `sma` / `ema` | `float` | None | `null` |
| `market_state` | `str` | None | `"UNKNOWN"` |

---

## 7. Potential Errors & Fixes

| Issue | Cause | Resolution |
|---|---|---|
| Validation Error on `current_price` | API returned 0 or null | Upstream (StockService) already blocks this, but Schema explicitly enforces `>0` just in case. |
| All indicators return `null` | Newly listed stock (IPO) or halted | Expected behavior. `calculate_all` traps the Pandas `ValueError` when `len(series) < 20`. |
| "NaN" outputs in JSON | Pandas leaked NaNs | Fixed using `.dropna()` before converting to native Python `round(float(), 4)`. Schema only serializes native types. |


---

# News Data Service (Task 4 – Context Layer)

## 1. Overview

Implemented: `app/services/news_service.py` and `app/schemas/news.py`

A dedicated service to fetch, standardize, and cache recent financial news articles for a given stock symbol.

Purpose:
> Provide normalized textual context (headlines, sources, dates) for the final LLM prompt, while heavily caching the data to avoid spamming external providers during repeated queries.

---

## 2. Problem Solved

Without this layer:
- Agent makes an external API call for news *every single time* a user asks a question, causing rate limits
- Different news providers (NewsAPI, Yahoo, AlphaVantage) return wildly different JSON structures
- A failed news API call crashes the entire LLM analysis request

With this layer:
- In-memory LRU caching guarantees we only fetch news once every 15 minutes per stock
- All responses are forced into a strict `NewsArticle` Pydantic schema
- Complete network failures return an empty list `[]` instead of 500 Internel Server Error — the LLM simply states "no recent news available".

---

## 3. What Was Built

### A. Core Service (`NewsService`)
- Uses **Yahoo Finance RSS feeds** instead of NewsAPI.
  - *Why?* RSS is free, requires no API keys, has no rate limits, and is incredibly reliable for top headlines.
- Implements an **In-memory cache dict** mapping symbols to their payload and timestamp.

### B. Output Contracts (`schemas/news.py`)
- **`NewsArticle`**: Title, Source (e.g., "Bloomberg"), Published Date (parsed to native datetime), URL, and an optional 500-char summary snippet.
- **`NewsResponse`**: Wraps the article array and injects metadata (`count`, `cached=True/False`, `provider`).

---

## 4. State & Data Flow Pipeline

```
Route / Agent
↓
NewsService.get_news_for_symbol("AAPL", limit=5)
│
├── 1. Cache Check
│      ├─► (HIT under 15 min) → Return immediate NewsResponse
│      └─► (MISS) → Proceed to network
│
├── 2. RSS Fetch
│      └─► feedparser.parse("https://feeds.finance.yahoo...")
│
├── 3. Parsing & Normalization
│      └─► Iterate entries → Extract RFC822 dates → Map to NewsArticle
│
└── 4. Cache Update & Return
       └─► Store in self._cache_store → Return NewsResponse
```

---

## 5. Key Design Decisions

### In-Memory Dict over Redis (For Now)
Since this is a lightweight agent, a local Python dict `self._cache_store` achieves 0ms cache hits without requiring the developer to spin up a sidecar Redis container. (Can be trivially swapped to a Redis backend later via the same interface).

### Graceful Degradation is Priority 1
Financial systems must be resilient. If the user searches for a junk symbol like `BADSTRING123`, the RSS feed returns a `bozo=1` parse error. Instead of crashing, the parser catches the error, logs a clean warning, and returns `[]`.

### Capping the Summary
RSS descriptions can sometimes contain megabytes of HTML data or tracking pixels. The parser strips excessive data and hard-caps the `summary` field at 500 characters `[:500]` to prevent blowing up the LLM context window later in Task 5.

---

## 6. Schema Structure

| Field | Type | Behavior |
|---|---|---|
| `cached` | `bool` | True if served from memory, False if a network call occurred. |
| `published_at` | `datetime` | Safely parsed from the feed. Defaults to `datetime.now()` if the feed lacks a timestamp. |
| `url` | `HttpUrl` | Strongly typed Pydantic url — guarantees it's clickable. |

---

## 7. Configuration & Performance

| Parameter | Default | Impact |
|---|---|---|
| Timeout/TTL | 15 minutes | Balances fresh news vs API load. |
| Limit | 5 articles | Prevents context window exhaustion in the LLM. |
| Speed | ~0.9s | Initial fetch time (XML parsing overhead). |
| Cached Speed | **0.0000s** | Subsequent fetches (Instant). |


---

# LLM Analysis Layer (Task 5 – Intelligence Layer)

## 1. Overview

Implemented: `app/ai/analyst.py` and `app/schemas/analysis.py`

The core intelligence node of the agent. It takes deterministic data from `StockService` and `NewsService`, injects it into a strict system prompt, and forces the LLM to return a validated JSON payload containing sentiment and key findings.

Purpose:
> Convert raw arrays of prices and headlines into a structured, professional financial summary without risking LLM hallucinations or broken formatting.

---

## 2. Problem Solved

Without this layer:
- LLMs naturally write chatty, markdown-heavy prose ("Here is the analysis you requested...").
- LLMs format bullet points inconsistently.
- Frontends break when trying to parse unpredictable string outputs into UI cards.

With this layer:
- The LLM is forced into a highly restricted, temperature=0.2 persona.
- Langchain's `PydanticOutputParser` injects the exact JSON schema required directly into the system prompt.
- The output is validated against `FinancialAnalysisResult` before being released to the client.

---

## 3. What Was Built

### A. Strict Response Schema (`schemas/analysis.py`)
`FinancialAnalysisResult` enforces exactly 5 fields:
1. `summary`: 2-3 sentence overview.
2. `sentiment`: Restricted to Literal `BULLISH`, `BEARISH`, `NEUTRAL`.
3. `technical_posture`: Interpretation of RSI/SMA.
4. `key_findings`: Array of 3-5 structured bullet points (`topic`, `detail`).
5. `risk_factors`: Array of 1-3 strings.

### B. The Analyst Agent (`analyst.py`)
- **Dual Support**: Supports both `gemini-2.5-flash` and `gpt-4o-mini` seamlessly depending on which key is in `.env`.
- **Low Temperature**: Set at `0.2` to ensure the model focuses purely on data synthesis rather than creative writing.
- **Data Formatting**: Dumps Pydantic objects into clean JSON blocks so the LLM explicitly understands the properties (e.g., `current_price: 150`, `rsi: 74`).
- **Resilient Parsing**: Attempts to strip rogue ` ```json ` markdown wrappers if the LLM accidentally leaks them (a common issue even with strict instructions).

---

## 4. State & Data Flow Pipeline

```
Route
↓
AnalystAgent.analyze_stock(StockDataResponse, NewsResponse)
│
├── 1. Context Formatting
│      ├─► JSON.dumps(stock_data)
│      └─► JSON.dumps(news_data)
│
├── 2. Prompt Assembly
│      └─► Inject System Prompt + Langchain Format Instructions + Human Context
│
├── 3. LLM Invocation (gemini/openai)
│      └─► model.invoke(messages, temperature=0.2)
│
└── 4. Parsing & Validation
       ├─► Strip raw markdown wrappers
       ├─► parser.parse(raw_content)
       └─► Return FinancialAnalysisResult
```

---

## 5. Potential Errors & Fixes

| Issue | Cause | Resolution |
|---|---|---|
| `ValueError: No LLM API key configured` | Missing `.env` variables | Ensure `GEMINI_API_KEY` or `OPENAI_API_KEY` is set in the environment. |
| `ValidationError` (Output Parsing) | LLM hallucinated a schema | The agent raises a `RuntimeError` which will cleanly translate to a 500 in the API rather than returning malformed data to the frontend. |
| Missing News | RSS feed failed | Agent falls back to `"No recent news available."` text block in the prompt. |


---

# Interactive Streamlit Dashboard (Task 7 – UI Layer)

## 1. Overview

Implemented: `frontend/streamlit_app.py`

A track A interactive analytical dashboard built purely in Python using Streamlit to interact directly with our backend Python services without needing a separate API layer or Node.js server.

Purpose:
> Provide a sleek, dark-themed, "Bloomberg Terminal" style visual interface for the user to query stocks, view interactive historical charts, read recent news, and consume the deterministic LLM analysis seamlessly.

---

## 2. Problem Solved

Without this layer:
- The system exists purely as a set of disconnected Python services and REST API endpoints.
- Visualizing moving averages (SMA/EMA) alongside candlestick data requires manual Jupyter Notebooks.
- Reading the JSON output of the LLM is difficult for non-technical users.

With this layer:
- One input box orchestrates `StockService`, `NewsService`, and `AnalystAgent` sequentially.
- Complex JSON structures are mapped into visual metric cards (delta values, colored sentiments).
- Plotly renders a highly interactive, zoomable Candlestick chart overlaid with the 20-day SMA.

---

## 3. What Was Built

### A. Core UI Layout
- **Sidebar**: Input controls and an interactive checklist of tracked features.
- **Header**: Progress bars rendering the exact state of the pipeline (Fetching prices → Fetching news → Generating LLM analysis).
- **Metric Row**: 4-column layout mapping out `Current Price`, `RSI`, `SMA`, and dynamic `<span style="...">` HTML for `AI Sentiment` (Bullish/Bearish/Neutral).

### B. Visualization
- **Plotly Candlesticks**: Automatically fetches an overlapping 30-day historical window (to ensure 20-day SMA calculations are accurate) and maps it to a `plotly_dark` themed interactive chart.

### C. Graceful Degradation & Error Trapping
- If any service in the pipeline throws an exception (e.g., yFinance goes down, or the Gemini API key is exhausted), a `try/except` block catches it at the top layer, destroys the loading bar via `.empty()`, and prints a clean, red `st.error()` message instead of crashing the Streamlit server.

---

## 4. Run Instructions

To test the application locally:
```bash
streamlit run frontend/streamlit_app.py
```

---

# Guardrails & Validation (Task 6 – Self-Healing AI)

## 1. Overview

Implemented in `app/ai/analyst.py`

The Analyst agent cannot crash the UI if the LLM hallucinates a bad JSON structure. We implemented a **Single-Attempt Retry Loop** (a self-healing mechanism) that catches parsing errors, explains the mistake to the AI, and asks it to try again before gracefully failing.

Purpose:
> Handle non-deterministic AI outputs safely by providing a mechanical feedback loop to correct malformed JSON schemas.

---

## 2. Problem Solved

Without this layer:
- The `PydanticOutputParser` raises a `ValidationError` if the AI forgets a required field (e.g., `technical_posture`) or returns a string instead of an array for `key_findings`.
- This exception crashes the backend `analyze_stock()` method, resulting in an HTTP 500 error and a broken UI.

With this layer:
- The system catches the `ValidationError`.
- It dynamically generates a new prompt: *"Your previous response failed validation... Please correct your JSON."*
- It gives the LLM exactly one chance to fix the syntax.
- If it fails again, it returns a **Safe Fallback Object** rather than crashing.

---

## 3. How It Works (Execution Flow)

```
LLM Call 1
   ├─► Success → Returns Parsed `FinancialAnalysisResult`
   │
   └─► Failure (ValidationError)
         │
         ├── 1. Catch Exception `ve`
         ├── 2. Log Warning (Attempt failed)
         ├── 3. Append Bad Response & Correction Prompt to Message History
         │        └─► "Your output failed with error: {ve}"
         │
         └── LLM Call 2 (Retry)
               ├─► Success → Returns Parsed Object
               │
               └─► Failure (ValidationError)
                     └─► Log Error → Return Safe Fallback Result (Neutral sentiment, Error summary)
```

## 4. Key Design Decisions

### A. Why Only One Retry? (`max_retries = 1`)
LLMs are expensive and slow. If `gpt-4o-mini` or `gemini-2.5-flash` fails to write valid JSON twice in a row when given the exact validation error, it is likely stuck in an unrecoverable hallucination loop. Failing fast after one retry provides a better user experience than waiting 45 seconds for 5 retries that all fail.

### B. Appending the Assistant's Bad Output
In the retry loop, we append both the LLM's bad output and the system's correction prompt:
```python
messages.append(response) # Add the bad response to context
messages.append(correction_message)
```
This is a critical prompt engineering technique. Without seeing *what* it just generated, the LLM won't understand the context of the `ValidationError` we are showing it.

### C. Safe Fallback Object
If the retry fails, preventing an application crash is paramount. We return a statically defined `FinancialAnalysisResult` where:
- `sentiment` = `NEUTRAL`
- `summary` = *"Analysis failed due to repetitive validation errors..."*
This ensures the Streamlit UI still receives the expected data types and renders gracefully, informing the user of the system failure without a chaotic Python stack trace taking over the screen.

---

# Toxicity & Content Safety Filter (Task 6 – Guardrails Part 2)

## 1. Overview

Implemented in `app/ai/moderation.py` — Called from `app/ai/analyst.py`

A dedicated, single-responsibility safety module that scans every field of the LLM's `FinancialAnalysisResult` for toxic, harmful, or manipulative language before it is released to the caller or rendered in the Streamlit UI.

Purpose:
> Ensure the AI will never surface profanity, threats, hate speech, or illegal financial advice to the user, regardless of what the LLM hallucinates.

---

## 2. Problem Solved

Without this filter:
- A low-temperature LLM can still occasionally hallucinate wildly off-topic or harmful content (especially with poorly formatted context inputs).
- Phrases like "guaranteed profit" or "get rich quick" inside a summary constitute illegal financial advice.
- Threatening or profane language has no place in a professional tool.

With this filter:
- **Every single text field** in the AI output is screened against a registered keyword blocklist.
- If *any* field contains a flagged term, the entire result is replaced with a safe, neutral fallback.
- The exact field and triggering keyword are logged as a `WARNING` for audit purposes.

---

## 3. Architecture — Separation of Concerns

The filter lives in its own file (`moderation.py`) completely separate from `analyst.py`. This is intentional:

| File | Responsibility |
|---|---|
| `analyst.py` | LLM invocation, prompt building, retry logic |
| `moderation.py` | Content safety — keyword detection, fallback generation |

This makes the moderation rules easy to update (just edit `moderation.py`) without ever touching the core AI logic.

---

## 4. Implementation Details

### Keyword Blocklist (`_TOXIC_KEYWORDS`)
Three categories of prohibited terms:
1. **Profanity / Abuse** — Unacceptable in any professional context.
2. **Violent / Threatening Language** — Phrases like "bomb" or "attack".
3. **Manipulative Financial Language** — Phrases like `"guaranteed profit"`, `"risk-free"`, or `"get rich quick"` which would constitute illegal financial advice if surfaced to users.

### Fields Checked
The scanner does NOT just check the `summary` field. It checks **every text field**:
- `summary`
- `technical_posture`
- Every `topic` and `detail` within `key_findings[]`
- Every string within `risk_factors[]`

This is critical — the LLM may slip through in a less-visible field like a single `risk_factors` entry.

### Execution Flow
```
analyze_stock() call succeeds
    ↓
result = parser.parse(raw_content)     ← Pydantic validation
    ↓
result = run_toxicity_check(result)    ← Content safety filter
    ↓
return result                          ← Guaranteed clean to client
```

### Safe Fallback Response
When toxicity is detected:
```json
{
  "summary": "The AI-generated analysis was flagged by the content safety filter...",
  "sentiment": "NEUTRAL",
  "technical_posture": "Technical analysis data is currently unavailable.",
  "key_findings": [],
  "risk_factors": [
    "The analysis output was quarantined due to a content policy violation."
  ]
}
```
This is structurally valid — the Streamlit UI can still render it gracefully and show the user a polite error card.

---

## 5. Logging & Auditability

Every interception is logged at the `WARNING` level:
```
🚨 Toxicity filter triggered | field=risk_factors[1] | reason=Blocked keyword detected: 'guaranteed profit'
```
This creates a built-in audit trail — you can grep your logs for `Toxicity filter triggered` to discover unexpected LLM behavior patterns over time.

---

## 6. Future Improvements
1. **OpenAI Moderation API**: Replace or augment the keyword list with OpenAI's `/v1/moderations` endpoint for semantic (context-aware) toxicity detection.
2. **Configurable Blocklist**: Load keywords from a YAML/JSON file so the list can be expanded without code deployments.
3. **Severity Levels**: Instead of blocking all flagged results, apply a two-tier response — `WARN` for borderline terms, `BLOCK` for hard violations.

---

# Hallucination Check (Task 6 – Guardrails Part 3)

## 1. Overview

Implemented in `app/ai/hallucination_check.py` — Called from `app/ai/analyst.py`

A numeric fact-checker that extracts any price-like numbers mentioned in the LLM's free-text output and cross-validates them against the **ground-truth stock data fetched from yFinance milliseconds earlier**. Mismatches beyond a 10% tolerance are flagged, logged, and annotated inline on the result.

Purpose:
> Detects stale or fabricated price data in LLM text (e.g., AI says $180 when the actual price is $145) and alerts the user without suppressing the rest of the analysis.

---

## 2. Problem Solved

LLMs are trained on data with a knowledge cutoff — they can confidently state a stock price that was accurate 6 months ago but is wildly wrong today. Even though we inject current prices into the prompt, the model can occasionally "remember" an old value or confuse two tickers.

Without this check:
- The LLM confidently writes: *"AAPL is currently trading at $220"* — but yFinance says $175. The user sees a $45 discrepancy and loses trust in the entire system.

With this check:
- The system extracts `220` from the text, compares it to `175`, sees a 25.7% deviation (> 10% threshold), logs a `WARNING`, and appends a correction notice to the summary automatically.

---

## 3. How It Works (Step-by-Step)

```
LLM Output Text (e.g. summary field)
    ↓
_extract_numbers(text)          → [220.0, 14.3, 72.5]   ← All numbers found
    ↓
_is_price_like(num, actual_price) → [True, False, False] ← 220 looks like a price
    ↓
_pct_diff(220, 175)             → 25.7%                  ← Exceeds 10% threshold
    ↓
Log WARNING: "LLM stated $220.00, actual price is $175.00 (25.7% deviation)"
    ↓
Annotate summary: append "[⚠️ Note: AI cited inaccurate price data...]"
    ↓
Return corrected result
```

---

## 4. Key Design Decisions

### A. Regex Extraction — Not LLM Parsing
Using a lightweight `re.compile` pattern to extract numbers is orders of magnitude faster and more reliable than asking a second LLM to find the numbers. Regex doesn't hallucinate.

```python
_NUM_PATTERN = re.compile(r"\$?([\d,]+\.?\d*)")
```

### B. `_is_price_like()` — Filtering Out Non-Price Numbers
Not every number in the text is a price. The LLM might mention `72.3` (RSI) or `5.2%` (percentage). The filter eliminates these:
```python
def _is_price_like(value, actual_price):
    ratio = value / actual_price
    return 0.02 < ratio < 50.0 and value > 100.0
```
- `value > 100.0` → Excludes RSI, percentages (0–100 range).
- `ratio between 0.02x and 50x` → Number must be "in the ballpark" of the stock price.

### C. Annotation, Not Suppression
Unlike the toxicity filter (which replaces the entire result), this filter **annotates** the summary with a correction notice. This is the right trade-off:
- The analysis is still mostly useful — only one or two numbers were wrong.
- The user is visibly warned, so they know to check the live metric cards above.
- Suppressing the entire analysis for a single stale price would be overly aggressive.

### D. 10% Tolerance (`_PRICE_TOLERANCE = 0.10`)
A 10% deviation is very generous — legitimate rounding or citing a recent intraday low/high might cause small differences. The threshold is set high enough to avoid false positives while still catching clear hallucinations.

---

## 5. Full Guardrail Pipeline in `analyst.py`

After this implementation, the complete guardrail chain looks like:

```
LLM Output
    ↓ 1. Pydantic ValidationError Retry  → Fix or safe fallback
    ↓ 2. run_toxicity_check()            → Block harmful content
    ↓ 3. run_hallucination_check()       → Annotate bad numbers
    ↓
✅ Clean, validated, safe result returned to client
```

---

## 6. Potential Errors & Debugging

| Issue | Cause | Fix |
|---|---|---|
| False positive on RSI | RSI value > 100 (not possible) | The `_RSI_MAX_VALUE = 100` guard prevents this |
| Annotation missing | `model_copy()` not applied | Ensure `result = result.model_copy(update=...)` captures the return |
| Warning not appearing in logs | Log level too high | Set `LOG_LEVEL=DEBUG` in `.env` to see all check passes |

---

## 7. Future Improvements
1. **Extend to RSI / SMA Cross-Validation**: Extract RSI values from the `technical_posture` field and compare against the actual `rsi` field from `StockDataResponse`.
2. **Configurable Threshold**: Expose `_PRICE_TOLERANCE` via `Settings` in `config.py` so different deployments (e.g., crypto with higher volatility) can tune the sensitivity.
3. **Per-Finding Correction**: Instead of only annotating the summary, find and replace the specific sentence containing the hallucinated value with a corrected one.

---

# Response Length Limits (Task 6 – Guardrails Part 4)

## 1. Overview

Implemented in `app/ai/response_limits.py` — Called from `app/ai/analyst.py`

Enforces hard character-level caps on every free-text field of the LLM output. If any field exceeds its configured limit, it is silently truncated and an ellipsis `…` is appended so the UI still renders cleanly.

Purpose:
> Prevent the LLM from generating bloated, essay-style summaries or individual risk factors that overflow their UI cards and increase token costs unnecessarily.

---

## 2. Field Limits Configured

| Field | Limit (chars) | Rationale |
|---|---|---|
| `summary` | 600 | ~4-5 compact readable sentences |
| `technical_posture` | 300 | 2-3 sentences is sufficient |
| `key_findings[].topic` | 60 | Should be a header label, not a paragraph |
| `key_findings[].detail` | 250 | 1-2 crisp sentences per finding |
| `risk_factors[]` | 200 | One tight sentence per risk |

---

## 3. Key Design Decisions

### Ellipsis Truncation (Not Silent Cut)
```python
truncated = text[:limit - len("…")].rstrip() + "…"
```
A visible `…` is appended so the user knows the content was trimmed — not silently dropped. This maintains transparency.

### `model_copy(update=...)` — Immutable Records
Rather than mutating the Pydantic model in place (which would fail since Pydantic models are frozen by default), the function uses `.model_copy(update={...})` to create a new record with only the changed fields replaced.

### Field-Level Granularity (Not Token-Level)
Unlike truncating at the LLM's `max_tokens` parameter (which cuts mid-sentence), this operates *after* the LLM has finished, field-by-field. This is more precise — only oversized fields are trimmed, not the entire output.

---

## 4. Full Guardrail Pipeline — Final State

After this implementation, the complete 4-layer guardrail chain in `analyst.py` is:

```
LLM Raw Output
    ↓ 1. Markdown Wrapper Strip       → Remove ```json leakage
    ↓ 2. Defensive JSON Pre-parse     → Catch completely malformed JSON
    ↓ 3. Pydantic ValidationError Retry → Fix schema or safe fallback
    ↓ 4. run_toxicity_check()         → Block harmful / manipulative text
    ↓ 5. run_hallucination_check()    → Annotate fabricated price data
    ↓ 6. run_length_check()           → Trim oversized fields
    ↓
✅ Clean, validated, safe, compact result → Streamlit UI
```

---

# Defensive JSON Parsing (Task 6 – Guardrails Part 5)

## 1. Overview

Implemented inline in `app/ai/analyst.py` (step 2 of the pipeline above)

A lightweight `json.loads()` dry-run is applied to the raw LLM response string *before* it reaches the `PydanticOutputParser`. This catches completely broken output (e.g., the LLM returned plain English, or an apology message instead of JSON) before Pydantic even sees it.

Purpose:
> Catch `"I cannot provide financial advice."` or `"Here is your analysis:"` style responses that are not JSON at all — before they cause obscure Pydantic errors.

---

## 2. Problem Solved

The `PydanticOutputParser` can raise cryptic error messages when completely non-JSON content is passed to it. Examples:
- `"JSONDecodeError: Expecting value: line 1 column 1"` — unhelpful.
- `"ValidationError: 5 validation errors for FinancialAnalysisResult"` — misleading.

The defensive pre-parse step produces a clear, logged warning:
```
Attempt 1: Raw LLM response is not valid JSON for AAPL: Expecting value: line 1 column 1
```
...and then re-uses the existing retry loop to ask the LLM to fix it.

---

## 3. Implementation

```python
try:
    json.loads(raw_content)  # dry-run — raises JSONDecodeError if totally broken
except json.JSONDecodeError as jde:
    logger.warning("Attempt %d: Raw LLM response is not valid JSON for %s: %s", ...)
    raise ValidationError.from_exception_data(...)  # triggers retry loop
```

### Why `json.loads()` and not `try/except` on `parser.parse()`?
`parser.parse()` produces generic `OutputParserException` messages. A `json.loads()` pre-check gives us:
1. A precise error location (`line X column Y`) for logging.
2. A clean path to re-use the retry loop via a deliberate `ValidationError` re-raise.
3. Separation between *"invalid JSON structure"* and *"valid JSON but wrong schema"*.

---

# Track B: Advanced Environment (LangGraph & Redis)

## 1. Overview

Implemented a state-driven analysis workflow replacing the static while-loop LLM call, and introduced a robust distributed caching layer to optimize API limits and latency.

Purpose:
> Elevate the system architecture to support complex graph-based agents (Track B requirement) and defend external vendor APIs (yFinance, News) against rate-limits.

---

## 2. In-Memory / Redis Hybrid Caching (`app/core/cache.py`)

A centralized resilient cache utility was introduced.
- **Dependency:** Added `redis:7-alpine` to `docker-compose.yml` and the Python `redis` client to `requirements.txt`.
- **Hybrid Strategy:** The `CacheService` attempts a ping on the `redis_url`. If Redis is offline (e.g., local development without docker), it silently logs a warning and falls back to an internal Python dictionary cache.
- **Time-to-Live (TTL):**
    - `get_full_stock_data()` is cached for 120 seconds (2 minutes).
    - `get_news_for_symbol()` is cached for 900 seconds (15 minutes).

---

## 3. LangGraph Orchestration (`app/ai/analyst.py`)

Migrated `AnalystAgent` from a linear procedural execution to a `langgraph.graph.StateGraph`.

### State Management (`AgentState`)
Instead of losing data between retries, state is preserved:
```python
class AgentState(TypedDict):
    stock_data: StockDataResponse
    news_data: Optional[NewsResponse]
    messages: Annotated[list[BaseMessage], add_messages]
    parsed_result: Optional[FinancialAnalysisResult]
    retry_count: int
```

### Graph Nodes
1. **`generate_analysis`**: Exclusively handles invoking Gemini/OpenAI and returning the `AIMessage`.
2. **`validate_and_guard`**: Applies the 4-layer validation pipeline (Pre-parse, Pydantic, Toxicity, Hallucination, Length). If it fails, it appends a correction `HumanMessage` to the state and increments `retry_count`.
3. **`fallback_analysis`**: Hardcoded safe response if all retries are exhausted.

### Conditional Routing
An `_edge_should_retry` function inspects `parsed_result` yielding `end`, `retry`, or `fallback` dynamically.

This graph structure ensures extreme reliability while keeping the public `analyze_stock()` interface perfectly identical for the Streamlit frontend.

---

## 4. Real-Time Data Streaming Architecture (WebSockets)

Fulfilled the requirement to add real-time streaming capabilities without breaking the Streamlit synchronous execution model.

1. **FastAPI Backend (`app/api/stream.py`)** 
   - Created an asynchronous `WebSocket` endpoint mapping to `/api/v1/stream/price/{symbol}`.
   - Runs an infinite loop fetching `stock_service.get_current_price()` and pushing JSON down the socket every 5 seconds.
2. **Streamlit Frontend Injection (`frontend/streamlit_app.py`)**
   - Streamlit naturally struggles with asynchronous real-time event listening because every state change triggers a full top-down Python script re-execution.
   - To bypass this, we utilize `st.components.v1.html` to inject a raw Vanilla JavaScript payload.
   - The JS client connects to the WebSocket URL, listens for events, and dynamically mutates the DOM elements mapping to the UI (ignoring the Streamlit Python rerun cycle entirely).
   - This provides a flawless, flicker-free live ticker experience.

---

## 5. API Rate Limiting & Cost Monitoring (LangSmith & SlowAPI)

Fulfilled the requirement: `Set up monitoring for API rate limits and costs`

1. **Cost & Trajectory Monitoring (LangSmith)**
   - Because we utilized `langgraph`, LangSmith observability is natively supported without requiring invasive code changes.
   - We exposed `LANGCHAIN_TRACING_V2` and `LANGCHAIN_API_KEY` through the `.env` template.
   - Activating this streams token usage, total dollar cost per generation, and step-by-step agent traces to the LangSmith cloud console for complete LLM observability.
2. **Endpoint Rate Limiting (SlowAPI)**
   - To defend the application against abuse or misconfigured scripts spamming the backend, we integrated `slowapi` globally across the FastAPI `app` configuration.
   - We applied a strict `@limiter.limit("5/minute")` to the heavy `/api/v1/analyze` endpoint.
   - This prevents our LLM or external financial APIs from being exhausted rapidly by malicious or overactive IP addresses.

---

## 6. Continuous Integration (CI/CD)

Fulfilled the requirement: `Create CI/CD pipeline with financial data testing`

To guarantee stable long-term development during Track B:
1. **GitHub Actions Workflow**
   - We created `.github/workflows/ci.yml`.
   - On every `push` and `pull_request` to `main`, a runner spawns a Python 3.11 environment.
   - It automatically installs all dependencies from `requirements.txt`.
2. **Quality Gates**
   - **Formatting & Linting**: It executes `black` (for standard formatting) and `ruff` (for high-speed static analysis).
   - **Automated Testing**: It executes `pytest backend/tests/ -v`.
3. **Financial Data Unit Tests**
   - Added robust tests in `test_financial_data.py` specifically targeting the `StockService` and `NewsService`.
   - The test suite uses Python `unittest.mock.patch` to simulate and intercept Vendor API responses.
   - This ensures our data normalization schemas are correct and that error boundaries hold up without actually hitting rate limits on `yfinance` or external RSS feeds during the CI build process.
