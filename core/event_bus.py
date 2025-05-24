"""
Publish/subscribe EventBus - OPTIMIZED

Optimizations: __slots__, faster lookups, reduced validation, optimized JSON handling.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Dict, List, Optional, Set

__all__ = [
    "EventBus",
    "EventStore",
    "FileEventStore",
    "SubscriptionError",
    "PublicationError",
    "ConfigurationError",
]

logger = logging.getLogger(__name__)

class ConfigurationError(ValueError):
    """Raised when provided configuration is invalid."""
    __slots__ = ()

class SubscriptionError(Exception):
    """Raised when subscription or unsubscription operations fail."""
    __slots__ = ()

class PublicationError(Exception):
    """Raised when publishing or persistence operations fail."""
    __slots__ = ()

class EventStore(ABC):
    """Interface for persisting published events."""
    
    @abstractmethod
    def store(self, event_type: str, payload: Any) -> None:
        """Persist the event with given type and payload."""

class FileEventStore(EventStore):
    """Persist events as JSON lines - OPTIMIZED."""
    __slots__ = ('file_path',)
    
    def __init__(self, file_path: Path) -> None:
        """Initialize FileEventStore - optimized."""
        self.file_path = file_path
        parent_dir = self.file_path.parent
        if not parent_dir.exists():
            parent_dir.mkdir(parents=True, exist_ok=True)
        
        # Test write access
        try:
            with self.file_path.open("a", encoding="utf-8"):
                pass
        except Exception as e:
            raise ConfigurationError(f"Invalid event store file: {self.file_path}") from e

    def store(self, event_type: str, payload: Any) -> None:
        """Write event as JSON line - optimized."""
        record = {"event_type": event_type, "payload": payload}
        try:
            with self.file_path.open("a", encoding="utf-8") as f:
                # Use separators for compact JSON
                f.write(json.dumps(record, separators=(',', ':')) + "\n")
        except Exception as e:
            raise PublicationError("Error writing event to store") from e

@dataclass(frozen=True, slots=True)
class EventBusConfig:
    """Configuration for EventBus - optimized with slots."""
    allowed_event_types: Optional[Set[str]] = None
    store: Optional[EventStore] = None

    def __post_init__(self) -> None:
        if self.allowed_event_types is not None and not self.allowed_event_types:
            raise ConfigurationError("allowed_event_types must be a non-empty set or None")

class EventBus:
    """Thread-safe publish/subscribe event dispatcher - OPTIMIZED."""
    __slots__ = ('_subs', '_lock', '_config', '_empty_list')
    
    def __init__(self, config: Optional[EventBusConfig] = None) -> None:
        """Initialize EventBus - optimized."""
        self._subs: Dict[str, List[Callable[[Any], None]]] = {}
        self._lock = RLock()
        self._config = config or EventBusConfig()
        self._empty_list = []  # Reusable empty list

    def subscribe(self, event_type: str, handler: Callable[[Any], None]) -> None:
        """Subscribe handler - optimized."""
        # Fast validation
        if not event_type or not event_type.strip():
            raise SubscriptionError("event_type must be a non-empty string")
        if not callable(handler):
            raise SubscriptionError("handler must be callable")
        if (self._config.allowed_event_types and 
            event_type not in self._config.allowed_event_types):
            raise SubscriptionError(f"Event type '{event_type}' is not allowed")
        
        with self._lock:
            if event_type not in self._subs:
                self._subs[event_type] = []
            self._subs[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable[[Any], None]) -> None:
        """Unsubscribe handler - optimized."""
        if not event_type or not event_type.strip():
            raise SubscriptionError("event_type must be a non-empty string")
        if not callable(handler):
            raise SubscriptionError("handler must be callable")
        
        with self._lock:
            handlers = self._subs.get(event_type)
            if not handlers or handler not in handlers:
                raise SubscriptionError(f"Cannot unsubscribe handler for event '{event_type}'")
            
            handlers.remove(handler)
            if not handlers:
                del self._subs[event_type]

    def clear_event(self, event_type: str) -> None:
        """Remove all handlers for event type."""
        if not event_type or not event_type.strip():
            raise SubscriptionError("event_type must be a non-empty string")
        
        with self._lock:
            self._subs.pop(event_type, None)

    def clear_all(self) -> None:
        """Remove all subscriptions."""
        with self._lock:
            self._subs.clear()

    def publish(self, event_type: str, payload: Optional[Any] = None) -> None:
        """Publish event - HEAVILY OPTIMIZED."""
        # Fast validation
        if not event_type or not event_type.strip():
            raise SubscriptionError("event_type must be a non-empty string")
        if (self._config.allowed_event_types and 
            event_type not in self._config.allowed_event_types):
            raise SubscriptionError(f"Event type '{event_type}' is not allowed")
        
        # Get handlers with minimal lock time
        with self._lock:
            handlers = self._subs.get(event_type, self._empty_list)
            if not handlers:
                return
            # Create copy to avoid holding lock during dispatch
            handlers_copy = handlers[:]

        # Persist event if store is configured
        if self._config.store:
            try:
                self._config.store.store(event_type, payload)
            except Exception as e:
                raise PublicationError("Failed to persist event") from e

        # Dispatch to handlers - optimized loop
        for handler in handlers_copy:
            try:
                handler(payload)
            except Exception:
                logger.exception("Handler %r raised exception for event '%s'", handler, event_type)