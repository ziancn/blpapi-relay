"""
This module houses the SessionManager class, which controls session lifecycle and event handling.
"""

import asyncio
import uuid
import blpapi
import logging

from typing import List, Set

from .modules.protocol import ModuleProtocol


# Configure logger for this module
logger = logging.getLogger(__name__)


# Common services to open during startup
COMMON_SERVICES = [
    "//blp/refdata",
    # "//blp/mktdata",
    # "//blp/apiflds",
]


# Event name
EVENT_NAME = {
    blpapi.Event.UNKNOWN:              "UNKNOWN",
    blpapi.Event.ADMIN:                "ADMIN",
    blpapi.Event.SESSION_STATUS:       "SESSION_STATUS",
    blpapi.Event.SUBSCRIPTION_STATUS:  "SUBSCRIPTION_STATUS",
    blpapi.Event.REQUEST_STATUS:       "REQUEST_STATUS",
    blpapi.Event.RESPONSE:             "RESPONSE",
    blpapi.Event.PARTIAL_RESPONSE:     "PARTIAL_RESPONSE",
    blpapi.Event.SUBSCRIPTION_DATA:    "SUBSCRIPTION_DATA",
    blpapi.Event.SERVICE_STATUS:       "SERVICE_STATUS",
    blpapi.Event.TIMEOUT:              "TIMEOUT",
    blpapi.Event.AUTHORIZATION_STATUS: "AUTHORIZATION_STATUS",
    blpapi.Event.RESOLUTION_STATUS:    "RESOLUTION_STATUS",
    blpapi.Event.TOPIC_STATUS:         "TOPIC_STATUS",
    blpapi.Event.TOKEN_STATUS:         "TOKEN_STATUS",
    blpapi.Event.REQUEST:              "REQUEST",
}


class SessionManager:
    """
    SessionManager controls session connection, request/response handling and event distribution
    to registered modules which you can customize and extend.
    """
    def __init__(self, host: str = "localhost", port: int = 8194):
        session_options = blpapi.SessionOptions()
        session_options.setServerHost(host)
        session_options.setServerPort(port)

        self._session = blpapi.Session(session_options, self._process_event)
        self._modules: List[ModuleProtocol] = []
        self._pending_requests = {}
        self._opened_services: Set[str] = set()


    # PRIVATE
    def _process_event(self, event: blpapi.Event, session: blpapi.Session):
        et = event.eventType()
        logger.debug(f"{EVENT_NAME.get(et)} event received")

        # 1. Dispatch responses
        if et in (blpapi.Event.RESPONSE, blpapi.Event.PARTIAL_RESPONSE):
            self._dispatch_response(event, session)

        # 2. Broadcast to all registered modules
        for module in self._modules:
            try:
               module.process_event(event, session)
            except Exception as e:
               logger.exception(f"Module '{module}' error: {e}")


    def _dispatch_response(self, event: blpapi.Event, session: blpapi.Session):
        for msg in event:
            if not msg.correlationIds(): continue
            
            cid_value = msg.correlationIds()[0].value()
            logger.debug(f"Dispatching response for CID: {cid_value}")
            
            # 1. If it's a response from request triggered by API call (async)
            if cid_value in self._pending_requests:
                try:
                    data = str(msg)
                    loop = self._pending_requests[cid_value]['loop']
                    future = self._pending_requests[cid_value]['future']
                    if not future.done():  # Check if future is already completed
                        logger.debug(f"Setting result for future, CID: {cid_value}")
                        loop.call_soon_threadsafe(future.set_result, data)
                except Exception as e:
                    logger.exception(f"Error setting future result: {e}")
                    loop.call_soon_threadsafe(future.set_exception, e)
                finally:
                    if cid_value in self._pending_requests:
                        del self._pending_requests[cid_value]  # Clean up


    # PUBLIC
    @property
    def session(self) -> blpapi.Session:
        return self._session


    def start(self):
        if not self._session.start():
            raise RuntimeError("Failed to start EMSX session")
        
        for service in COMMON_SERVICES:
            try:
                self._session.openService(service)
                self._opened_services.add(service)
                logger.info(f"Opened service: {service}")
            except Exception as e:
                logger.warning(f"Failed to open service {service}: {e}")


    def start_async(self):
        if not self._session.startAsync():
            raise RuntimeError("Failed to start(async) EMSX session")


    def stop(self):
        self._session.stop()


    def register_module(self, module: ModuleProtocol):
        if module not in self._modules:
            self._modules.append(module)


    # Async APIs
    async def get_refdata(self, tickers: list[str], fields: list[str]) -> str:
        service = self._session.getService("//blp/refdata")
        request = service.createRequest("ReferenceDataRequest")

        for t in tickers:
            request.append("securities", t)
    
        for f in fields:
            request.append("fields", f)

        cid = blpapi.CorrelationId(str(uuid.uuid4()))
        self._session.sendRequest(request, correlationId=cid)
        
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        self._pending_requests[cid.value()] = {
            "future" : future,
            "loop"   : loop
        }

        try:
            result = await asyncio.wait_for(future, timeout=10.0)
            logger.debug(f"Response: {result}")
            return result
        except asyncio.TimeoutError:
            logger.error(f"Request timed out for CID: {cid.value()}")
            logger.debug(request.toString())
            raise
        finally:
            if cid.value() in self._pending_requests:
                del self._pending_requests[cid.value()]