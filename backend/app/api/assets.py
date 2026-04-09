from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import List
from app.services.macro_service import get_macro_dashboard
from app.services.options_service import get_options_chain, black_scholes_call, black_scholes_put
from app.services.mpt_service import optimize_portfolio
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


# ── Macro ──────────────────────────────────────────────────────────────────────
@router.get("/macro", summary="Fetch top macroeconomic indicators (FRED)")
@limiter.limit("10/minute")
async def get_macro_data(request: Request):
    """Returns 10Y Treasury yield, CPI inflation, and unemployment rate from FRED."""
    return get_macro_dashboard()


# ── Options Chain ──────────────────────────────────────────────────────────────
@router.get("/options/{symbol}", summary="Fetch near-term options chain for a ticker")
@limiter.limit("10/minute")
async def get_options_data(request: Request, symbol: str):
    """
    Returns the nearest expiration options chain for a given symbol.
    Includes top 5 calls and puts by volume, plus implied market sentiment.
    """
    return get_options_chain(symbol)


# ── Black-Scholes Pricer ───────────────────────────────────────────────────────
class BlackScholesRequest(BaseModel):
    S: float   # Current stock price
    K: float   # Strike price
    T: float   # Time to maturity in years
    r: float = 0.04  # Risk-free rate (default: 4%)
    sigma: float     # Implied volatility (e.g. 0.25 for 25%)

@router.post("/options/pricer", summary="Black-Scholes theoretical option pricing")
async def price_option(payload: BlackScholesRequest):
    """
    Calculates theoretical Call and Put option prices using the Black-Scholes model.

    - **S**: Current stock price  
    - **K**: Strike price  
    - **T**: Time to maturity in years (e.g. 0.25 = 3 months)  
    - **r**: Annual risk-free rate (default: 0.04)  
    - **sigma**: Annual volatility (e.g. 0.30 = 30%)
    """
    call_price = black_scholes_call(payload.S, payload.K, payload.T, payload.r, payload.sigma)
    put_price  = black_scholes_put(payload.S, payload.K, payload.T, payload.r, payload.sigma)
    return {
        "status": "success",
        "inputs": payload.model_dump(),
        "call_price": round(call_price, 4),
        "put_price":  round(put_price, 4),
        "put_call_parity_check": round(call_price - put_price - payload.S + payload.K * __import__("math").exp(-payload.r * payload.T), 6),
    }


# ── MPT Portfolio Optimization ────────────────────────────────────────────────
class MPTRequest(BaseModel):
    tickers: List[str]

@router.post("/mpt/optimize", summary="Modern Portfolio Theory - Max Sharpe Ratio optimization")
@limiter.limit("5/minute")
async def mpt_optimize(request: Request, payload: MPTRequest):
    """
    Given a list of tickers, fetches 5 years of historical price data and computes
    the portfolio allocation that maximizes the Sharpe Ratio (MPT Efficient Frontier).

    Returns optimal weights, expected annual return, volatility, and Sharpe ratio.
    Requires at least 2 tickers.
    """
    return optimize_portfolio(payload.tickers)
