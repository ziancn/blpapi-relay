"""
FastAPI application factory and routes.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from .session_manager import SessionManager
from .modules.status_monitor import StatusMonitor
from .modules.refdata_handler import RefDataHandler
from .modules.subscription_handler import SubscriptionHandler


# Configure logging
logger = logging.getLogger(__name__)


# Session setup
sm = SessionManager()

status_monitor = StatusMonitor()
sm.register_module(status_monitor)

refdata_handler = RefDataHandler()
sm.register_module(refdata_handler)

subscription_handler = SubscriptionHandler()
sm.register_module(subscription_handler)


# This is Gemini+Grok generated frontend demo
# Able to query live data successfully
html = """
<!DOCTYPE html>
<html>
<head>
    <title>Bloomberg Minimal Feed</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #121212; color: #ffffff; padding: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { font-size: 24px; border-bottom: 2px solid #333; padding-bottom: 10px; color: #4facfe; }
        
        .dashboard { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 30px; }
        
        .card { background: #1e1e1e; padding: 25px; border-radius: 12px; border: 1px solid #333; }
        .card-title { font-size: 14px; color: #888; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 15px; }
        
        .price-display { font-size: 42px; font-weight: bold; margin-bottom: 10px; font-variant-numeric: tabular-nums; }
        .trade-price { color: #00e676; }
        .quote-price { color: #2196f3; }
        
        .meta-info { font-size: 14px; color: #aaa; line-height: 1.6; }
        .timestamp { color: #ff9800; font-family: monospace; }
        .status { margin-top: 20px; padding: 10px; background: #333; border-radius: 6px; font-size: 12px; text-align: center;}
    </style>
</head>
<body>
    <div class="container">
        <h1 id="tickerTitle">Loading Ticker...</h1>
        
        <div class="dashboard">
            <div class="card">
                <div class="card-title">Latest Trade (LAST_PRICE)</div>
                <div class="price-display trade-price" id="lastPrice">--</div>
                <div class="meta-info">
                    Update Time: <span class="timestamp" id="tradeTime">--</span><br>
                    Change 1D: <span id="tradeChange">--</span>
                </div>
            </div>

            <div class="card">
                <div class="card-title">Current Market (BID / ASK)</div>
                <div class="price-display quote-price">
                    <span id="bidPrice">--</span> / <span id="askPrice">--</span>
                </div>
                <div class="meta-info">
                    Update Time: <span class="timestamp" id="quoteTime">--</span><br>
                    Spread: <span id="quoteSpread">--</span>
                </div>
            </div>
        </div>

        <div class="status" id="statusBox">WebSocket Connecting...</div>
    </div>

    <script>
        const ticker = new URLSearchParams(window.location.search).get('ticker') || "XBTUSD Curncy";
        document.getElementById('tickerTitle').innerText = `📊 ${ticker} Live Feed`;

        function connectWebSocket() {
            const wsUrl = `ws://localhost:8000/mktdata?ticker=${encodeURIComponent(ticker)}&fields=BID&fields=ASK&fields=LAST_PRICE`;
            const ws = new WebSocket(wsUrl);
            const statusBox = document.getElementById('statusBox');

            ws.onopen = () => {
                statusBox.innerText = "🟢 Connected to Bloomberg Server";
                statusBox.style.color = "#00e676";
            };

            ws.onmessage = (event) => {
                try {
                    let data = event.data;
                    
                    while (typeof data === 'string') {
                        data = JSON.parse(data);
                    }
                    
                    //console.log(data);

                    const eventType = data.MKTDATA_EVENT_TYPE;

                    if (eventType === "TRADE") {
                        if (data.LAST_PRICE !== undefined) {
                            document.getElementById('lastPrice').innerText = Number(data.LAST_PRICE).toFixed(2);
                        }
                        if (data.EVT_TRADE_TIME_RT) {
                            document.getElementById('tradeTime').innerText = data.EVT_TRADE_TIME_RT;
                        }
                        if (data.RT_PX_CHG_NET_1D !== undefined) {
                            document.getElementById('tradeChange').innerText = Number(data.RT_PX_CHG_NET_1D).toFixed(2);
                        }
                    } 
                    else if (eventType === "QUOTE") {
                        if (data.BID !== undefined) {
                            document.getElementById('bidPrice').innerText = Number(data.BID).toFixed(2);
                        }
                        if (data.ASK !== undefined) {
                            document.getElementById('askPrice').innerText = Number(data.ASK).toFixed(2);
                        }
                        if (data.TIME) {
                            document.getElementById('quoteTime').innerText = data.TIME;
                        }
                        if (data.SPREAD_BA !== undefined) {
                            document.getElementById('quoteSpread').innerText = Number(data.SPREAD_BA).toFixed(2);
                        }
                    } 
                    else if (eventType === "SUMMARY") {
                        if (data.LAST_PRICE !== undefined) {
                            document.getElementById('lastPrice').innerText = Number(data.LAST_PRICE).toFixed(2);
                        }
                        if (data.BID !== undefined) {
                            document.getElementById('bidPrice').innerText = Number(data.BID).toFixed(2);
                        }
                        if (data.ASK !== undefined) {
                            document.getElementById('askPrice').innerText = Number(data.ASK).toFixed(2);
                        }
                    }

                } catch (e) {
                    console.error("Parse or Update Error:", e, event.data);
                }
            };

            ws.onclose = () => {
                statusBox.innerText = "🔴 Disconnected. Reconnecting...";
                statusBox.style.color = "#ff3d00";
                setTimeout(connectWebSocket, 3000);
            };
        }

        window.addEventListener('load', connectWebSocket);
    </script>
</body>
</html>
"""


# This is the new way to handle startup and shutdown in FastAPI
# Replacing @startup and @shutdown event handlers
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown."""
    try:
        sm.start()
    except Exception as e:
        raise

    yield
    
    try:
        sm.stop()
    except Exception as e:
        raise


# FastAPI app instance creation method
# I don't really understand this part, just use AI generated code for now
app = FastAPI(
    title="Bloomberg API Relay",
    description="A relay layer for Bloomberg BLPAPI via RESTful API endpoints implemented with FastAPI",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@app.get("/helloworld")
async def helloworld():
    return {"message": "Hello, World!"}


@app.get("/refdata")
async def get_refdata(
    tickers: list[str] = Query(["AAPL US Equity"]), 
    fields: list[str] = Query(["PX_LAST"])
):
    try:
        data = await refdata_handler.get_refdata(tickers, fields)
        return {"status": "success", "data": data}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Bloomberg Timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")


@app.websocket("/mktdata")
async def mktdata(
    websocket: WebSocket,
    ticker: str = Query("IBM US Equity"),
    fields: list[str] = Query(["BID", "ASK"])
):
    # WebSocket connection handshake
    await websocket.accept()

    fields_str = ",".join(fields)
    topic = f"//blp/mktdata/ticker/{ticker}?fields={fields_str}"

    logger.info(f"New client connected. Topic: {topic}")

    # Bind running asyncio loop to subscription_handler
    subscription_handler.loop = asyncio.get_running_loop()

    await subscription_handler.connect(websocket, topic)

    try:
        while True:
            await websocket.receive_text() 
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from topic: {topic}")
    finally:
        await subscription_handler.disconnect(websocket, topic)