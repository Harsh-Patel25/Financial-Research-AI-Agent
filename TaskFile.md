# 📘 Financial Research AI – Development Checklist

Use this file to track your progress. Mark tasks as completed by changing `[ ]` to `[x]`.

---

## 🟢 PHASE 1 – CORE WORKFLOW & INFRASTRUCTURE

### 🆕 TASK 0: Infrastructure Setup
- [x] Initialize Git repository
- [x] Configure `.gitignore` (Python, VSCode, Environment files)
- [x] Set up `pytest` framework (Create `tests/` directory)
- [x] Create basic `Dockerfile`
- [x] Create `docker-compose.yml` (optional initial version)
- [x] Configure Pre-commit hooks (Black, Ruff/Flake8, isort)
- [x] Setup environment configuration (`.env` + python-dotenv)
- [x] Define base project folder structure
    > **Deliverable:** ✔ Clean project scaffold with version control and testing support

### TASK 1: Backend API Setup (Hardened)
- [x] Create FastAPI project structure (`app/main.py`, `app/api/`)
- [x] Create `POST /analyze` endpoint
- [x] Implement Global Error Handling (Middleware)
- [x] Define Request & Response schemas using Pydantic
- [x] Implement structured JSON response format
- [x] Add structured logging (Structlog or Loguru recommended)
- [x] Add basic health check endpoint (`/health`)
    > **Deliverable:** ✔ Production-ready API skeleton with logging and error handling

### TASK 2: Query Categorization Layer
- [x] Design LLM categorization prompt
- [x] Implement Categories:
    - [x] `stock`
    - [x] `news`
    - [x] `portfolio`
    - [x] `general`
- [x] Enforce strict single-word lowercase output
- [x] Add validation and fallback mechanism (Default to `general` on failure)
- [x] Add timeout control for LLM call
- [x] **Test:** Validate categorization against 20+ sample queries
    > **Deliverable:** ✔ Stable and test-covered categorization module

### 🆕 TASK 2.5: Portfolio Database (SQL Layer)
- [x] Setup SQLite (Development)
- [x] Setup PostgreSQL connection (Production-ready option)
- [x] Design database schema:
    - [x] `Portfolios` table
    - [x] `Holdings` table
    - [x] `Transactions` table
- [x] Implement ORM layer (SQLAlchemy)
- [x] Create CRUD endpoints:
    - [x] Create portfolio
    - [x] Add holding
    - [x] Record transaction
    - [x] Fetch portfolio summary
    > **Deliverable:** ✔ Functional portfolio management system

### TASK 3: Stock Data Service (Hardened)
- [x] Integrate yFinance
- [x] Wrap API calls with:
    - [x] Retry mechanism (tenacity)
    - [x] Circuit breaker pattern
- [x] Create abstract `DataProvider` interface (allows future AlphaVantage/Polygon swap)
- [x] Fetch Data:
    - [x] Current price
    - [x] Historical OHLC
    - [x] Volume
- [x] Calculate Indicators:
    - [x] RSI
    - [x] Moving Averages (SMA/EMA)
- [x] Return strictly structured financial data (Pydantic model)
    > **Deliverable:** ✔ Deterministic, resilient stock data pipeline

### TASK 4: News Data Service
- [x] Integrate News API (or similar provider)
- [x] Extract Data:
    - [x] Title
    - [x] Source
    - [x] Published Date
    - [x] URL
- [x] Normalize response format
- [x] Implement caching layer (Redis or in-memory LRU) - *News is semi-static*
- [x] Add fallback for API failure
    > **Deliverable:** ✔ Cached and normalized news pipeline

### TASK 5: LLM Analysis Layer
- [x] Create Financial Analyst prompt template
- [x] Inject structured financial/news data into prompt
- [x] Force structured JSON output (Pydantic validation)
- [x] Implement output parsing & validation
- [x] Control LLM Parameters:
    - [x] Temperature (Low for facts)
    - [x] Max tokens
- [x] Log raw LLM responses for debugging
    > **Deliverable:** ✔ Structured, controlled LLM analysis module

### TASK 6: Guardrails & Validation
- [x] Implement JSON schema validation (Verify output matches Pydantic model)
- [x] Add retry mechanism for invalid JSON responses
- [x] Implement basic hallucination check (Cross-reference numbers if possible)
- [x] Implement basic toxicity/safety filter
- [x] Add response length limits
- [x] Add defensive parsing (Handle malformed JSON)
    > **Deliverable:** ✔ Safe and validated LLM output system

---

## 🟡 PHASE 2 – RAG & ADVANCED FEATURES

### TASK 7: Document Ingestion
- [ ] Implement PDF loader (PyPDF/LangChain)
- [ ] Implement Text extraction
- [ ] Apply `RecursiveCharacterTextSplitter`
- [ ] Configure chunk size and overlap
- [ ] Store metadata (source, page, date)

### TASK 7.5: Vector DB Persistence
- [ ] Setup Chroma with persistent storage (disk-based)
- [ ] Ensure data survives app restart
- [ ] Implement collection versioning
- [ ] Add metadata indexing for faster filtering
    > **Deliverable:** ✔ Persistent vector storage layer

### TASK 8: Embeddings Pipeline
- [ ] Generate embeddings (OpenAI `text-embedding-3-small` or HuggingFace)
- [ ] Store embeddings with metadata in Chroma
- [ ] Implement embedding version control

### TASK 9: Semantic Retrieval
- [ ] Convert user query to embedding
- [ ] Perform similarity search
- [ ] Apply score threshold filtering (Exclude irrelevant chunks)
- [ ] Inject retrieved context into LLM prompt
- [ ] Add retrieval logging (Inspect what chunks are being retrieved)
    > **Deliverable:** ✔ Stable RAG pipeline integrated with main workflow

---

## 🔴 PHASE 3 – PRODUCTION READINESS

### TASK 10: Evaluation & Observability
- [ ] Create gold-standard evaluation dataset (Questions + Ideal Answers)
- [ ] Expand test query dataset
- [ ] Implement evaluation scoring script (LLM-as-a-Judge)
- [ ] Integrate LLM tracing:
    - [ ] LangSmith OR
    - [ ] Local structured logging
- [ ] Add performance metrics tracking (Latency, Token Usage, Cost)
    > **Deliverable:** ✔ Measurable system quality & observability

### TASK 11: Caching & Rate Limiting
- [ ] Integrate Redis caching
- [ ] Cache strategies:
    - [ ] Stock responses (TTL: 1-5 mins)
    - [ ] News responses (TTL: 30-60 mins)
    - [ ] Embedding lookups (Optional)
- [ ] Implement API rate limiting (e.g., `slowapi`)
- [ ] Add per-user rate limits
    > **Deliverable:** ✔ Performance-optimized backend

### ⚠ TASK 12: Deployment & CI/CD
- [ ] Finalize `Dockerfile` (Multi-stage build)
- [ ] Finalize `docker-compose.yml` (App + DB + Redis)
- [ ] Setup GitHub Actions:
    - [ ] Lint check
    - [ ] Test execution
    - [ ] Build validation
- [ ] Environment-based configuration (Dev/Staging/Prod)
- [ ] Prepare production-ready `.env.example`
    > **Deliverable:** ✔ CI-enabled, containerized deployment-ready system
