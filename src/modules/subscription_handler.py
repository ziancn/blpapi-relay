"""
This module handles subscription requests and responses for real-time data from Bloomberg API
and manages connections with frontend clients via WebSockets.

STRUCTURE OF SUBSCRIPTION STRING

 "//blp/mktdata/ticker/IBM US Equity?fields=BID,ASK&interval=2"
  |-----------||------||-----------||------------------------|
        |          |         |                  |
     Service    Prefix   Instrument           Suffix

"""

import blpapi
import logging
import asyncio
import json
import datetime

from typing import Dict, Set
from fastapi import WebSocket

from .protocol import ModuleProtocol


logger = logging.getLogger(__name__)


# Utility parse method
def parse_mktdata_event_msg(msg):
    cid = msg.correlationIds()[0].value()
    
    msg_dict = {
        "MESSAGE_TYPE": str(msg.messageType()),
        "CORRELATION_ID": str(cid),
        "TOPIC": str(msg.topicName())
    }

    # (Element)
    for i in range(msg.numElements()):
        element = msg.getElement(i)
        name = str(element.name())
        
        # 1. Python: None (JSON: null)
        if element.isNull():
            msg_dict[name] = None
            continue
            
        # 2. This is also AI generated, I am not very clear with BLPAPI DataTypes
        if element.datatype() in [blpapi.DataType.CHOICE, blpapi.DataType.SEQUENCE]:
            try:
                msg_dict[name] = str(element.getValue())
            except:
                pass
            continue

        value = element.getValue()
        
        # 3. Cross Platform datatype alignment
        if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
            msg_dict[name] = value.isoformat()
        elif isinstance(value, blpapi.Name):
            msg_dict[name] = str(value)
        elif isinstance(value, (int, float, bool, str)):
            msg_dict[name] = value
        else:
            msg_dict[name] = str(value)  # stringfy unknown types
            
    return msg_dict



class SubscriptionHandler(ModuleProtocol):
    def __init__(self, loop = None):
        self.session: blpapi.Session = None
        self.loop = loop or asyncio.get_event_loop()
        self.topics: Dict[str, Set[WebSocket]] = {}
        self.cids: Dict[str, str] = {}

    
    def process_event(
            self,
            event  : blpapi.Event,
            session: blpapi.Session,
    ):
        match event.eventType():
            case blpapi.Event.SUBSCRIPTION_DATA: self.process_subscription_data(event, session)
            case _: pass


    def process_subscription_data(self, event: blpapi.Event, session: blpapi.Session):
        for msg in event:
            if not msg.correlationIds(): continue

            topic = msg.correlationIds()[0].value()

            if topic in self.topics:
                data = parse_mktdata_event_msg(msg)
                self.broadcast(topic, data)


    # ==================== #
    # WebSocket management
    # Async jobs

    def broadcast(self, topic: str, data: dict):
        if self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.send_update(topic, data), self.loop)
        else:
            logger.warning("Asyncio event loop is not running. Cannot broadcast update.")


    async def send_update(self, topic: str, data: dict):
        """Send update to all WebSockets that subscribed to a topic"""
        json_payload = json.dumps(data)
        if topic in self.topics:
            sockets = self.topics[topic]
            if sockets:
                await asyncio.gather(
                    *[ws.send_json(json_payload) for ws in sockets],
                    return_exceptions=True
                )


    async def connect(self, websocket: WebSocket, topic: str):
        """
        `topic` we expect here is the full subscription string like:
        "//blp/mktdata/ticker/IBM US Equity?fields=BID,ASK"
        """
        if topic not in self.topics:
            self.topics[topic] = {websocket}

            cid = blpapi.CorrelationId(topic)
            self.cids[topic] = cid

            subscription = blpapi.SubscriptionList()
            subscription.add(topic, correlationId=cid)
            self.session.subscribe(subscription)
        else:
            self.topics[topic].add(websocket)

    
    async def disconnect(self, websocket: WebSocket, topic: str):
        if topic in self.topics:
            self.topics[topic].discard(websocket)
            if not self.topics[topic]:  # No more subscribers for this topic
                cid = self.cids.pop(topic, None)
                if cid:
                    unsub = blpapi.SubscriptionList()
                    unsub.add(topic=topic, correlationId=cid)
                    self.session.unsubscribe(unsub)
                    logger.info(f"Unsubscribed from Bloomberg topic: {topic}")
                del self.topics[topic]


    
