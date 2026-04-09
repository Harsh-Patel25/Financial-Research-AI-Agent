import pandas as pd
import yfinance as yf
from pypfopt import expected_returns
from pypfopt import risk_models
from pypfopt.efficient_frontier import EfficientFrontier
import logging
from typing import List, Dict, Any

def optimize_portfolio(tickers: List[str]) -> Dict[str, Any]:
    """
    Given a list of ticker symbols, fetches up to 5 years of historical data,
    calculates expected returns and the covariance matrix, and determines
    the optimal weights for the Max Sharpe Ratio (Modern Portfolio Theory).
    """
    if len(tickers) < 2:
        return {"status": "error", "message": "At least 2 assets are required for portfolio optimization."}
        
    try:
        # Fetch historical adjusted close prices
        df = yf.download(tickers, period="5y", auto_adjust=True)
        if 'Close' in df.columns.levels[0] if isinstance(df.columns, pd.MultiIndex) else False:
            prices = df['Close']
        else:
            prices = df
            
        prices = prices.dropna(how="all")
        if prices.empty:
            return {"status": "error", "message": "No historical data found for optimization."}
            
        # Calculate expected returns and sample covariance
        mu = expected_returns.mean_historical_return(prices)
        S = risk_models.sample_cov(prices)
        
        # Optimize for maximal Sharpe ratio
        ef = EfficientFrontier(mu, S)
        raw_weights = ef.max_sharpe()
        cleaned_weights = ef.clean_weights()  # Truncates tiny weights to zero
        
        # Performance metrics
        perf = ef.portfolio_performance(verbose=False)
        # perf is a tuple: (expected_return, annual_volatility, sharpe_ratio)
        
        return {
            "status": "success",
            "optimal_weights": dict(cleaned_weights),
            "expected_annual_return": float(perf[0]),
            "annual_volatility": float(perf[1]),
            "sharpe_ratio": float(perf[2])
        }
    except Exception as e:
        logging.error(f"Error optimizing portfolio for {tickers}: {e}")
        return {"status": "error", "message": str(e)}
