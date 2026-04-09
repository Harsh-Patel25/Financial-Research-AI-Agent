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
- [x] Track A Milestone: Deploy basic version on Streamlit Cloud
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

### Track B Checklist:
- [x] All Track A requirements plus:
- [x] Set up advanced environment (LangGraph, Redis for caching, PostgreSQL)
- [x] Implement real-time data streaming architecture
- [x] Add comprehensive error handling for API failures
- [x] Set up monitoring for API rate limits and costs
- [x] Create CI/CD pipeline with financial data testing

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
- [x] Implement PDF loader (PyPDF/LangChain)
- [x] Implement Text extraction
- [x] Apply `RecursiveCharacterTextSplitter`
- [x] Configure chunk size and overlap
- [x] Store metadata (source, page, date)

### TASK 7.5: Vector DB Persistence
- [x] Setup Chroma with persistent storage (disk-based)
- [x] Ensure data survives app restart
- [x] Implement collection versioning
- [x] Add metadata indexing for faster filtering
    > **Deliverable:** ✔ Persistent vector storage layer

### TASK 8: Embeddings Pipeline
- [x] Generate embeddings (OpenAI `text-embedding-3-small` or HuggingFace)
- [x] Store embeddings with metadata in Chroma
- [x] Implement embedding version control

### TASK 9: Semantic Retrieval
- [x] Convert user query to embedding
- [x] Perform similarity search
- [x] Apply score threshold filtering (Exclude irrelevant chunks)
- [x] Inject retrieved context into LLM prompt
- [x] Add retrieval logging (Inspect what chunks are being retrieved)
    > **Deliverable:** ✔ Stable RAG pipeline integrated with main workflow

---

## 🔴 PHASE 3 – PRODUCTION READINESS

### TASK 10: Evaluation & Observability
- [x] Create gold-standard evaluation dataset (Questions + Ideal Answers)
- [x] Expand test query dataset
- [x] Implement evaluation scoring script (LLM-as-a-Judge)
- [x] Integrate LLM tracing:
    - [x] LangSmith OR
    - [x] Local structured logging
- [x] Add performance metrics tracking (Latency, Token Usage, Cost)
    > **Deliverable:** ✔ Measurable system quality & observability

### TASK 11: Caching & Rate Limiting
- [x] Integrate Redis caching
- [x] Cache strategies:
    - [x] Stock responses (TTL: 1-5 mins)
    - [x] News responses (TTL: 30-60 mins)
    - [x] Embedding lookups (Optional)
- [x] Implement API rate limiting (e.g., `slowapi`)
- [x] Add per-user rate limits
    > **Deliverable:** ✔ Performance-optimized backend

### ⚠ TASK 12: Deployment & CI/CD
- [x] Finalize `Dockerfile` (Multi-stage build)
- [x] Finalize `docker-compose.yml` (App + DB + Redis)
- [x] Setup GitHub Actions:
    - [x] Lint check
    - [x] Test execution
    - [x] Build validation
- [x] Environment-based configuration (Dev/Staging/Prod)
- [x] Prepare production-ready `.env.example`
    > **Deliverable:** ✔ CI-enabled, containerized deployment-ready system

---

## 🟣 PHASE 4 – TRACK B FINALIZATION & POLISH (SENIOR ARCHITECT PLAN)

### 📈 Module 1: Multi-Asset APIs & Resilience
- [ ] Fetch macroeconomic metrics (Bonds/Inflation) via FRED API (`pandas-datareader`)
- [ ] Acquire Options/Commodities data via `yfinance` multi-ticker fetches
- [ ] Hardcode fallback graceful degradation when limits are hit (`pybreaker`)
- [ ] Support Multi-asset class analysis (equities, fixed income, commodities)

### 🧮 Module 2: Advanced Financial Math
- [ ] Integrate `PyPortfolioOpt` for Modern Portfolio Theory calculations
- [ ] Optimize portfolio based on Max Sharpe Ratio / Efficient Frontier
- [ ] Basic Options pricing logic (Black-Scholes)

### ⚖️ Module 3: Stock Comparison & Market Alerts
- [ ] Build Comparison Tab: 2 tickers, normalized percentage Plotly lines, AI dual-analysis
- [ ] Build Background Polling: Task runner (`apscheduler`/`Celery`) for market events
- [ ] Build UI Notifications: Use `st.toast` to feed background alerts into Streamlit

### 🎨 Module 4: UI Overhaul & Deployment
- [ ] Layout Architecture: Integrate `streamlit-option-menu` for sidebar tab routing
- [ ] Advanced Grids: Integrate `streamlit-aggrid` for professional portfolio tracking
- [ ] PDF Generation: Integrate `fpdf2` or `WeasyPrint` for 1-click Executive Reports
- [ ] Industry Standard: Ensure FastAPI `/docs` is heavily documented
- [ ] Deploy Application: Push to robust cloud hosting environment
- [ ] Deliverable Record: 10 Minute professional demo recording
