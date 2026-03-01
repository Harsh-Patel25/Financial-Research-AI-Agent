import yfinance as yf

symbol = "TATA MOTORS LTD"
print(f"Testing {symbol}")
try:
    ticker = yf.Ticker(symbol)
    print("Ticker created")
    info = ticker.fast_info
    print("fast_info accessed")
    price = getattr(info, "last_price", None)
    print("last_price accessed")
    print(price)
except Exception as e:
    import traceback
    traceback.print_exc()

import sys
sys.exit(0)
