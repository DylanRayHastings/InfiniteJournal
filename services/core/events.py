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


# services/core/storage.py - Simplified storage
"""Simplified storage system."""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class StorageProvider:
    """Simple storage provider interface."""
    
    def store(self, key, value):
        raise NotImplementedError
        
    def retrieve(self, key):
        raise NotImplementedError
        
    def exists(self, key):
        raise NotImplementedError


class MemoryStorageProvider(StorageProvider):
    """Memory storage provider."""
    
    def __init__(self, name="memory"):
        self.name = name
        self._data = {}
        
    def store(self, key, value):
        self._data[key] = value
        return True
        
    def retrieve(self, key):
        return self._data.get(key)
        
    def exists(self, key):
        return key in self._data
        
    def delete(self, key):
        if key in self._data:
            del self._data[key]
            return True
        return False


def create_memory_storage(name="memory"):
    """Create memory storage."""
    return MemoryStorageProvider(name)


def create_file_storage(path):
    """Create file storage."""
    return MemoryStorageProvider("file")  # Simplified to memory
