"""
FastAPI application factory and routes.
"""

import asyncio
import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from .web_grab import get_hkex_ss_turnover
from ..src.bql_via_excel import excel_bql

from ..src.session_manager import SessionManager
from ..src.modules.status_monitor import StatusMonitor
from ..src.modules.refdata_handler import RefDataHandler
from ..src.modules.mktdata_handler import MktDataHandler
# from ..src.modules.bql_handler import BqlHandler


logger = logging.getLogger(__name__)


# Session setup
sm = SessionManager()

status_monitor = StatusMonitor()
sm.register_module(status_monitor)

refdata_handler = RefDataHandler()
sm.register_module(refdata_handler)

mktdata_handler = MktDataHandler()
sm.register_module(mktdata_handler)

# bql_handler = BqlHandler()
# sm.register_module(bql_handler)


# This is the new way to handle startup and shutdown in FastAPI
# Replacing @startup and @shutdown event handlers
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown."""
    try: sm.start()
    except Exception as e: raise

    yield
    
    try: sm.stop()
    except Exception as e: raise


# FastAPI App
# APIs defined below
app = FastAPI(
    title="Bloomberg API Relay",
    description="A relay layer for Bloomberg BLPAPI via RESTful API endpoints implemented with FastAPI",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/demopage")
async def get():
    from .demo_page import demo_page
    return HTMLResponse(demo_page)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@app.get("/refdata")
async def get_refdata(
    tickers: list[str] = Query(["AAPL US Equity"]), 
    fields: list[str] = Query(["PX_LAST"])
):
    try:
        data = await refdata_handler.get_refdata(tickers, fields)
        return {"status": "success", "data": data}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Timeout querying Bloomberg API")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/mktdata")
async def mktdata(
    websocket: WebSocket,
    tickers: list[str] = Query(["IBM US Equity"]),
    fields: list[str] = Query(["LAST_PRICE"]),
    # Pass below control first, for most usecases we don't need this and it's more complex to manage
    # options: str | None =  Query(None, description="Examples: interval=1, interval=0.5&delayed"),
):
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
        data = await excel_bql(query)
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Excel Relay internal error: {str(e)}")


@app.get("/hkexss")
async def hkexss():
    try:
        data = await get_hkex_ss_turnover()
        return {"status": "success", "data": data}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Query method internal error: {str(e)}")
