import yfinance as yf
from typing import Dict, Any, List
import logging

def get_options_chain(symbol: str) -> Dict[str, Any]:
    """
    Fetches the nearest expiration options chain for a given ticker.
    """
    try:
        ticker = yf.Ticker(symbol)
        expirations = ticker.options
        if not expirations:
            return {"status": "no_options_available", "symbol": symbol}
            
        near_term = expirations[0]
        opt = ticker.option_chain(near_term)
        
        # Extract at-the-money roughly by looking at high volume calls/puts
        calls = opt.calls.sort_values('volume', ascending=False).head(5).to_dict(orient='records')
        puts = opt.puts.sort_values('volume', ascending=False).head(5).to_dict(orient='records')
        
        return {
            "status": "success",
            "symbol": symbol,
            "nearest_expiration": near_term,
            "active_calls": calls,
            "active_puts": puts,
            "implied_sentiment": "bullish" if len(calls) > len(puts) else "bearish"
        }
    except Exception as e:
        logging.error(f"Error fetching options for {symbol}: {e}")
        return {"status": "error", "message": str(e)}

import math

def norm_cdf(x: float) -> float:
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def black_scholes_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Computes theoretical Call Option price using Black-Scholes.
    S: Current stock price
    K: Strike price
    T: Time to maturity in years
    r: Risk-free rate (e.g., 0.04 for 4%)
    sigma: Volatility (e.g., 0.2 for 20%)
    """
    if T <= 0: return max(0.0, S - K)
    if sigma <= 0: return max(0.0, S - K * math.exp(-r * T))
    
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)

def black_scholes_put(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Computes theoretical Put Option price using Black-Scholes."""
    if T <= 0: return max(0.0, K - S)
    if sigma <= 0: return max(0.0, K * math.exp(-r * T) - S)
    
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)

