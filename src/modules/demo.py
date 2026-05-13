"""
This is a demo module. It subscribes and logs heartbeat.
"""

import blpapi
import logging

from .protocol import ModuleProtocol


# blpapi names
SLOW_CONSUMER_WARNING         = blpapi.Name("SlowConsumerWarning")
SLOW_CONSUMER_WARNING_CLEARED = blpapi.Name("SlowConsumerWarningCleared")

SESSION_STARTED               = blpapi.Name("SessionStarted")
SESSION_TERMINATED            = blpapi.Name("SessionTerminated")
SESSION_STARTUP_FAILURE       = blpapi.Name("SessionStartupFailure")
SESSION_CONNECTION_UP         = blpapi.Name("SessionConnectionUp")
SESSION_CONNECTION_DOWN       = blpapi.Name("SessionConnectionDown")

SERVICE_OPENED                = blpapi.Name("ServiceOpened")
SERVICE_OPEN_FAILURE          = blpapi.Name("ServiceOpenFailure")

SUBSCRIPTION_FAILURE          = blpapi.Name("SubscriptionFailure")
SUBSCRIPTION_STARTED          = blpapi.Name("SubscriptionStarted")
SUBSCRIPTION_TERMINATED       = blpapi.Name("SubscriptionTerminated")

ORDER_ROUTE_FIELDS            = blpapi.Name("OrderRouteFields")


class DemoModule(ModuleProtocol):
    """
    Logging module
    """
    def __init__(self):
        self._log_prefix = f"[{self.__class__.__name__}]"
        self._order_sub_cid = blpapi.CorrelationId(98)
        self._route_sub_cid = blpapi.CorrelationId(99)


    def process_event(
            self,
            event  : blpapi.Event,
            session: blpapi.Session,
    ):
        et = event.eventType()
        if   et == blpapi.Event.SESSION_STATUS    : self.process_session_status_event(event, session)
        elif et == blpapi.Event.SERVICE_STATUS    : self.process_service_status_event(event, session)
        elif et == blpapi.Event.SUBSCRIPTION_DATA : self.process_subscription_data_event(event, session)
        else: pass


    @staticmethod
    def process_session_status_event(event: blpapi.Event, session: blpapi.Session):
        for msg in event:
            if msg.messageType() == SESSION_STARTED:
                session.openService("//blp/emapisvc")


    def process_service_status_event(self, event: blpapi.Event, session: blpapi.Session):
        for msg in event:
            if msg.messageType() == SERVICE_OPENED:
                self.subscribe_orders(session)
                self.subscribe_routes(session)


    def subscribe_orders(self, session: blpapi.Session):
        emsx_fields = [
            "EMSX_SEQUENCE",
        ]
        topic = "//blp/emapisvc/order?fields=" + ",".join(emsx_fields)
        subscription = blpapi.SubscriptionList()
        subscription.add(topic=topic, correlationId=self._order_sub_cid)
        session.subscribe(subscription)


    def subscribe_routes(self, session: blpapi.Session):
        emsx_fields = [
            "EMSX_SEQUENCE",
        ]
        topic = "//blp/emapisvc/route?fields=" + ",".join(emsx_fields)
        subscription = blpapi.SubscriptionList()
        subscription.add(topic=topic, correlationId=self._route_sub_cid)
        session.subscribe(subscription)


    def process_subscription_data_event(self, event: blpapi.Event, session: blpapi.Session):
        for msg in event:
            try:
                if msg.messageType() != ORDER_ROUTE_FIELDS: continue

                match msg.getElementAsInteger("EVENT_STATUS"):
                    case 1:
                        if msg.correlationIds()[0].value() == self._order_sub_cid.value(): logging.info("O.")
                        elif msg.correlationIds()[0].value() == self._route_sub_cid.value(): logging.info("R.")
                    case 11:
                        if msg.correlationIds()[0].value() == self._order_sub_cid.value(): logging.info("Order - End of initial paint")
                        elif msg.correlationIds()[0].value() == self._route_sub_cid.value(): logging.info("Route - End of initial paint")
                    case _: ...

            except Exception as e:
                logging.exception(f"[{self.__class__.__name__}] Exception: {e}")