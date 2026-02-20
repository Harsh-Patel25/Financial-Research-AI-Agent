# 🚀 IMPLEMENTATION PLAN (Execution Roadmap)

Use this roadmap to track weekly goals. Mark items as complete `[x]` as you finish them.

---

## 🗓 WEEK 1 – Backend Foundation & Essential Reliability
**Goal:** A working, tested, single-stock analysis pipeline that doesn't break.

### Day 1: Infrastructure & API Skeleton
- [ ] Initialize Git & `.gitignore`
- [ ] Setup `pytest` environment
- [ ] Create `Dockerfile` & `docker-compose.yml` (Basic App + DB)
- [ ] Setup FastAPI project structure
- [ ] Implement `POST /analyze` (Dummy response)
- [ ] Setup Logging (Structlog)

### Day 2: Categorization & Testing
- [ ] Implement Categorization Logic (LLM Prompt)
- [ ] Write Unit Tests for Categorizer (20+ samples)
- [ ] Implement `Validator` class for output enforcement
- [ ] **Milestone Check:** Run `pytest` - All Green?

### Day 3: Data Services (Stock + Portfolio)
- [ ] Setup SQLite/PostgreSQL Database (SQLAlchemy models)
- [ ] Implement Portfolio CRUD (Create, Add Stock, List)
- [ ] Implement Stock Service (yFinance Wrapper + Retry Logic)
- [ ] Manual Test: Fetch Stock Data & Store in DB

### Day 4: Core Analysis Engine
- [ ] Connect LLM (OpenAI/Gemini)
- [ ] Build "Financial Analyst" System Prompt
- [ ] Inject Real Data (Stock Service) -> LLM
- [ ] Parse Output -> JSON (Pydantic Validation)

### Day 5: Integration & Guardrails
- [ ] Add Basic Guardrails (Valid JSON, No Hallucinations)
- [ ] Integration Test: End-to-End Flow (User -> API -> Data -> LLM -> JSON)
- [ ] Review Logs & Optimize Prompts
- [ ] **Deliverable:** Working v0.1 API

---

## 🗓 WEEK 2 – Data Expansion & RAG Foundations
**Goal:** User personalization and broader market intelligence.

### Day 1-2: News & External Data
- [ ] Integrate News API
- [ ] Implement Caching for News (Redis/Memory)
- [ ] Normalize News Data structure
- [ ] Update Analyst Prompt to use News Context

### Day 3: Vector DB Setup
- [ ] Setup ChromaDB (Persistent Mode)
- [ ] Create "Document Ingestion" Script (PDF/Text)
- [ ] Test Embedding Generation (OpenAI/HF)

### Day 4: Document Pipeline
- [ ] Implement PDF Loader & Chunker
- [ ] Run Ingestion on Sample Financial Reports
- [ ] Verify Data Storage in Chroma

### Day 5: Semantic Retrieval
- [ ] Implement `retrieve_context(query)` function
- [ ] Connect Retrieval to Main `/analyze` flow
- [ ] **Deliverable:** RAG-enabled Financial Assistant

---

## 🗓 WEEK 3 – Production Hardening & Scale
**Goal:** Make it fast, secure, and observable.

### Day 1: Advanced Retrieval
- [ ] Tune Chunk Size & Overlap for better context
- [ ] Implement "Hybrid Search" (Keyword + Semantic) if needed
- [ ] Add Source Citations in LLM Response

### Day 2: Caching & Rate Limiting
- [ ] Implement Redis Caching for Stock Data (TTL 5 mins)
- [ ] Implement API Rate Limiting (`slowapi`)
- [ ] Stress Test: Simulate 50 concurrent requests

### Day 3: Evaluation & Refinement
- [ ] Run "Golden Dataset" Evaluation
- [ ] Score Responses (Accuracy, Format, Latency)
- [ ] Fix Prompt issues based on eval results

### Day 4: Monitoring & Tracing
- [ ] Integrate Tracing (LangSmith or Local Log Analysis)
- [ ] Add Performance Metrics Middleware
- [ ] Create basic Dashboard (Streamlit Admin Panel)

### Day 5: Final Polish & Deploy Prep
- [ ] Final Code Cleanup (Linting/Typing)
- [ ] Update `README.md` with setup instructions
- [ ] Final Docker Build & Test
- [ ] **Deliverable:** Production-Ready v1.0

---

## 🎯 IMPORTANT RULES
1. **Vertical Slices:** Don't build all "Data" then all "LLM". Build One Feature (e.g., Stock Price) End-to-End.
2. **Test First:** Don't write logic without a test case in mind.
3. **Fail Fast:** If yFinance breaks, handle it gracefully. Don't let the API crash.
4. **Deterministic > Smart:** A reliable dumb agent is better than a smart crashing one.

---

### Legend
- `[ ]` To Do
- `[x]` Done
- `[/]` In Progress (Notion style)
