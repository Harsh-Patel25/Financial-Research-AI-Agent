"""
Stream API Router (app/api/stream.py)

Real-time data streaming architecture using WebSockets.
Pushes live stock prices to the connected client at a regular interval.
"""
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.stock_service import stock_service

router = APIRouter(prefix="/api/v1/stream", tags=["stream"])
logger = logging.getLogger(__name__)

@router.websocket("/price/{symbol}")
async def websocket_price_endpoint(websocket: WebSocket, symbol: str):
    """
    WebSocket endpoint that streams the current price of a symbol continuously.
    Client connects, and we push JSON indefinitely until they disconnect.
    """
    await websocket.accept()
    logger.info(f"WebSocket Client connected for stream: {symbol}")
    
    symbol = symbol.upper().strip()
    
    try:
        while True:
            try:
                # Fetch fresh price
                price_data = stock_service.get_current_price(symbol)
                
                # Push safely to client
                await websocket.send_json({
                    "symbol": price_data["symbol"],
                    "price": price_data["price"],
                    "market_state": price_data["market_state"]
                })
                
                # Sleep between ticks to prevent yFinance rate limits
                # Polling every 5 seconds is a safe live-ticker cadence
                await asyncio.sleep(5)
                
            except ValueError as ve:
                # E.g. Bad symbol
                await websocket.send_json({"error": str(ve)})
                break
            except RuntimeError as re:
                # Network downstream error
                await websocket.send_json({"error": "Price service temporarily unavailable."})
                await asyncio.sleep(10) # Wait longer before retrying
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket Client disconnected from stream: {symbol}")
    except Exception as e:
        logger.error(f"WebSocket stream error for {symbol}: {e}")
        try:
            await websocket.close()
        except Exception:
            pass
