"""
Simple publish/subscribe event bus.
"""
from typing import Callable, Dict, List

import logging
from icecream import ic
from debug import DEBUG


if DEBUG:
    ic.configureOutput(prefix='[events] ')
    logging.getLogger().setLevel(logging.DEBUG)

class EventBus:
    def __init__(self):
        self._subs: Dict[str, List[Callable]] = {}
        logging.info("EventBus initialized")

    def subscribe(self, event_type: str, handler: Callable) -> None:
        self._subs.setdefault(event_type, []).append(handler)
        if DEBUG:
            ic(f"Subscribed handler to event: '{event_type}'")
        logging.debug(f"Handler subscribed to event '{event_type}'")

    def publish(self, event_type: str, payload=None) -> None:
        handlers = self._subs.get(event_type, [])
        if DEBUG:
            ic(f"Publishing event: '{event_type}' with payload={payload} to {len(handlers)} handlers")
        logging.debug(f"Event published: '{event_type}', handler count: {len(handlers)}")
        for handler in handlers:
            try:
                handler(payload)
            except Exception as e:
                logging.exception(f"Handler for event '{event_type}' raised an exception")
