"""
Simple publish/subscribe event bus.
"""
from typing import Callable, Dict, List

class EventBus:
    def __init__(self):
        self._subs: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable) -> None:
        self._subs.setdefault(event_type, []).append(handler)

    def publish(self, event_type: str, payload=None) -> None:
        for handler in self._subs.get(event_type, []):
            handler(payload)
