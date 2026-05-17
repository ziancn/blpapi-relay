"""
FastAPI application factory and routes.
"""

import asyncio
import logging
import math
import xlwings as xw

from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from .session_manager import SessionManager
from .modules.status_monitor import StatusMonitor
from .modules.refdata_handler import RefDataHandler
from .modules.mktdata_handler import MktDataHandler
from .modules.bql_handler import BqlHandler


# Configure logging
logger = logging.getLogger(__name__)


# Session setup
sm = SessionManager()

status_monitor = StatusMonitor()
sm.register_module(status_monitor)

refdata_handler = RefDataHandler()
sm.register_module(refdata_handler)

mktdata_handler = MktDataHandler()
sm.register_module(mktdata_handler)

bql_handler = BqlHandler()
sm.register_module(bql_handler)


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
            const wsUrl = `ws://localhost:8000/mktdata?tickers=${encodeURIComponent(ticker)}&fields=BID&fields=ASK&fields=LAST_PRICE`;
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
    tickers: list[str] = Query(["IBM US Equity"]),
    fields: list[str] = Query(["LAST_PRICE"]),
    # Pass below control first, for most usecases we don't need this and it's more complex to manage
    # options: str | None =  Query(None, description="Examples: interval=1, interval=0.5&delayed"),
):
    # WebSocket connection handshake
    await websocket.accept()
    logger.info(f"New WebSocket established for {tickers} with fields: {fields}")

    # Bind running asyncio loop to subscription_handler
    mktdata_handler.loop = asyncio.get_running_loop()

    await mktdata_handler.connect(websocket, tickers, fields)

    try:
        while True:
            await websocket.receive_text() 
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected")
    finally:
        await mktdata_handler.disconnect(websocket, tickers)


@app.get("/bql")
async def bql(
    query: str,
    excel_relay: bool = True,
):
    logger.debug(f"BQL Query received: {query}")
    
    if not excel_relay:
        raise HTTPException(status_code=400, detail="Direct BQL API is disabled.")
    
    try:
        wb = xw.Book(Path(__file__).parent / "bql.xlsx")
        ws = wb.sheets[0]
        ws.clear_contents()
        ws.range("A1").formula = f'=BQL.Query("{query}")'
        
        # Loop to check if data arrived
        timeout_seconds, retry_interval = 20, 0.2
        max_retries = int(math.ceil(timeout_seconds/retry_interval))
        
        for i in range(max_retries):
            await asyncio.sleep(retry_interval)
            
            a1_val = ws.range("A1").value
            if a1_val is None: continue
                
            a1_str = str(a1_val).strip()
            if "Requesting" in a1_str or a1_str == "nan" or a1_str == "#N/A": continue
            if "ERR" in a1_str: raise HTTPException(status_code=422, detail=f"Bloomberg Error: {a1_str}")
            
            break
        
        # Parse result
        current_table = ws.range("A1").expand()
        table_value = current_table.value

        if not isinstance(table_value, list):
            # Only one cell (single underlying and single field)
            formatted_json = [{"value": table_value}]
        elif not isinstance(table_value[0], list):
            if len(table_value) == 1:
                # Safety check, if still only one cell
                formatted_json = [{"value": table_value[0]}]
            else:
                # Only one column of data
                header = str(table_value[0])
                formatted_json = [{header: row} for row in table_value[1:]]
        else:
            # Clear all-empty rows
            clean_table = [row for row in table_value if any(cell is not None for cell in row)]
            if len(clean_table) == 1:
                # Only one row
                formatted_json = [{"value": cell} for cell in clean_table[0]]
            else:
                # Standard 2-dimensional table
                headers = [str(h) if h is not None else f"col_{idx}" for idx, h in enumerate(clean_table[0])]
                rows = clean_table[1:]
                formatted_json = [dict(zip(headers, row)) for row in rows]

        # Return the parsed result
        return {
            "status": "success",
            "total_rows": len(formatted_json),
            "data": formatted_json
        }
            
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Excel Relay internal error: {str(e)}")
