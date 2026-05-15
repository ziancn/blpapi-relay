"""
FastAPI application factory and routes.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Response

from .session_manager import SessionManager
from .modules.status_monitor import StatusMonitor
from .modules.refdata_handler import RefDataHandler


# Configure logging
logger = logging.getLogger(__name__)


sm = SessionManager()
status_monitor = StatusMonitor()
refdata_handler = RefDataHandler()

sm.register_module(status_monitor)
sm.register_module(refdata_handler)


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
def create_app() -> FastAPI:
    app = FastAPI(
        title="Bloomberg API Relay",
        description="A relay layer for Bloomberg BLPAPI via RESTful API endpoints implemented with FastAPI",
        version="0.1.0",
        lifespan=lifespan
    )

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

    return app


# Create app instance for ASGI servers
app = create_app()