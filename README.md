# ⚡ FITerminal | Advanced Financial Intelligence Agent

## Overview
A production-grade, multi-asset algorithmic financial terminal mirroring the layout and robust workflows of tools like Bloomberg/TradingView, built purely in Python (FastAPI + Streamlit).

This project satisfies all **Track A** and **Advanced Track B** execution goals, prioritizing real-time analytics, mathematical portfolio execution, multi-agent frameworks, and resilience.

## Features Implemented ✅
1. **Multi-Asset Terminal Engine**: Real-time Websocket syncing of Equities, Bonds, Treasury Yields (FRED API), and Options Math (Native Black-Scholes).
2. **PyPortfolioOpt (MPT)**: Mathematical portfolio optimization calculating maximum Sharpe ratios based on historical variance/covariance.
3. **Advanced Async Architecture**: True `asyncio` execution of LLM LangGraph pipelines, concurrent fetches, and persistent heartbeat background tasks tracking market thresholds.
4. **Professional UI/UX Overhaul**: Stripped default Streamlit styling. Adopted exact 70/30 split pane, JetBrains Mono ticker aesthetics, `aggrid` interactive tables, and `streamlit-option-menu` native desktop sidebar simulations.
5. **PDF Reporting Tooling (fpdf2)**: 1-click automated translations of massive complex dashboards directly to printable Executive PDFs.

## Architecture & Technology Stack
- **Backend API**: FastAPI (with BackgroundTasks, SlowAPI rate-limiters, Global error traps).
- **Core Orchestration**: LangGraph (Multi-agent loops) + LangChain.
- **Data Layers**: SQLite (ACID portfolio tracking) + `yfinance` / `pandas-datareader`.
- **Frontend App**: Streamlit (Heavy custom CSS + Plotly declarative charting).
- **Vector DB**: ChromaDB.

## Running the Application
### 1. Boot the Backend (FastAPI)
```cmd
cd financial_ai/backend
uvicorn app.main:app --port 8000 --reload
```
Navigate to `http://localhost:8000/docs` to view the finalized OpenAPI Specification interface.

### 2. Boot the Frontend (Streamlit)
```cmd
cd financial_ai
python -m streamlit run frontend/streamlit_app.py
```
Open `http://localhost:8501`.

## Development Roadmap Passed
- Phase 1: Prototype LLM Chat & Data Pipeline.
- Phase 2: Vector RAG & SQLite Portfolios.
- Phase 3: Track B Heavy Lifting (MPT Math, Background Pollers, Macro).
- Phase 4: UI/UX Final Polish & Layout Rigidity.

*Developed by AI pair programmers bridging sophisticated quantitative analysis with highly reactive UI execution.*
