"""Simplified event system."""

import logging
import threading
from collections import defaultdict
from typing import Any, Callable

logger = logging.getLogger(__name__)

class EventHandler:
    """Simple event handler wrapper."""
    
    def __init__(self, handler_func):
        self.handler_func = handler_func
        
    def handle_event(self, data):
        return self.handler_func(data)

class EventSubscription:
    """Event subscription info."""
    
    def __init__(self, event_name, handler):
        self.event_name = event_name
        self.handler = handler

class EventBus:
    """Simple event bus."""
    
    def __init__(self):
        self._handlers = defaultdict(list)
        self._lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
    def subscribe(self, event_name, handler):
        """Subscribe to event."""
        with self._lock:
            if callable(handler):
                self._handlers[event_name].append(handler)
            else:
                self._handlers[event_name].append(handler.handle_event)
        return EventSubscription(event_name, handler)
        
    def publish(self, event_name, data=None):
        """Publish event."""
        with self._lock:
            for handler in self._handlers[event_name]:
                try:
                    handler(data)
                except Exception as e:
                    self.logger.error(f"Event handler error: {e}")
                    
    def unsubscribe(self, event_name, handler):
        """Unsubscribe from event."""
        with self._lock:
            if event_name in self._handlers:
                try:
                    self._handlers[event_name].remove(handler)
                except ValueError:
                    pass
                    
    def shutdown(self):
        """Shutdown event bus."""
        with self._lock:
            self._handlers.clear()

def create_event_bus():
    """Create event bus."""
    return EventBus()

def create_event_handler(func):
    """Create event handler."""
    return EventHandler(func)