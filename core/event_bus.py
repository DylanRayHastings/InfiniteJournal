"""
Publish/subscribe EventBus with optional persistence and configuration.

This module provides:
- EventBus: thread-safe event dispatcher.
- EventStore: interface for persisting published events.
- FileEventStore: JSON Lines file-based event store.
- Custom exceptions for clear error handling.
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


class SubscriptionError(Exception):
    """Raised when subscription or unsubscription operations fail."""


class PublicationError(Exception):
    """Raised when publishing or persistence operations fail."""


class EventStore(ABC):
    """Interface for persisting published events."""

    @abstractmethod
    def store(self, event_type: str, payload: Any) -> None:
        """Persist the event with given type and payload."""


class FileEventStore(EventStore):
    """Persist events as JSON lines in a file."""

    def __init__(self, file_path: Path) -> None:
        """Initialize FileEventStore.

        Args:
            file_path: Path to the JSONL file to write events to.

        Raises:
            ConfigurationError: If the file cannot be created or written.
        """
        self.file_path = file_path
        parent_dir = self.file_path.parent
        if not parent_dir.exists():
            parent_dir.mkdir(parents=True, exist_ok=True)
        try:
            # Test write access
            with self.file_path.open("a", encoding="utf-8"):
                pass
        except Exception as e:
            logger.error("Cannot open event store file '%s': %s", self.file_path, e)
            raise ConfigurationError(f"Invalid event store file: {self.file_path}") from e

    def store(self, event_type: str, payload: Any) -> None:
        """Write the event as a JSON line to the persistence file.

        Args:
            event_type: Identifier for the event.
            payload: Data to persist.

        Raises:
            PublicationError: If writing to disk fails.
        """
        record = {"event_type": event_type, "payload": payload}
        try:
            with self.file_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.exception("Failed to persist event '%s'", event_type)
            raise PublicationError("Error writing event to store") from e


@dataclass(frozen=True)
class EventBusConfig:
    """Configuration for EventBus behavior.

    Attributes:
        allowed_event_types: If set, only these event types may be used.
        store: Optional EventStore to persist published events.
    """
    allowed_event_types: Optional[Set[str]] = None
    store: Optional[EventStore] = None

    def __post_init__(self) -> None:
        if self.allowed_event_types is not None and not self.allowed_event_types:
            raise ConfigurationError("allowed_event_types must be a non-empty set or None")


class EventBus:
    """Thread-safe publish/subscribe event dispatcher."""

    def __init__(self, config: Optional[EventBusConfig] = None) -> None:
        """Initialize EventBus.

        Args:
            config: Optional EventBusConfig. If provided,
                enforces allowed_event_types and persists events via config.store.
        """
        self._subs: Dict[str, List[Callable[[Any], None]]] = {}
        self._lock = RLock()
        self._config = config or EventBusConfig()
        logger.info("EventBus initialized with config: %s", self._config)

    def subscribe(self, event_type: str, handler: Callable[[Any], None]) -> None:
        """Subscribe a handler to an event type.

        Args:
            event_type: Identifier for the event.
            handler: Callable accepting a single `payload` argument.

        Raises:
            SubscriptionError: If validation fails or subscription cannot be added.
        """
        try:
            self._validate_event_type(event_type)
            self._validate_handler(handler)
            with self._lock:
                self._subs.setdefault(event_type, []).append(handler)
            logger.debug("Subscribed handler %r to event '%s'", handler, event_type)
        except Exception as e:
            logger.error("subscribe failed for event '%s': %s", event_type, e)
            raise SubscriptionError(f"Cannot subscribe to event '{event_type}'") from e

    def unsubscribe(self, event_type: str, handler: Callable[[Any], None]) -> None:
        """Unsubscribe a handler from an event type.

        Args:
            event_type: Identifier for the event.
            handler: The handler to remove.

        Raises:
            SubscriptionError: If event or handler is not found.
        """
        try:
            self._validate_event_type(event_type)
            self._validate_handler(handler)
            with self._lock:
                handlers = self._subs.get(event_type)
                if not handlers or handler not in handlers:
                    raise KeyError
                handlers.remove(handler)
                if not handlers:
                    self._subs.pop(event_type, None)
            logger.debug("Unsubscribed handler %r from event '%s'", handler, event_type)
        except Exception as e:
            logger.error("unsubscribe failed for event '%s': %s", event_type, e)
            raise SubscriptionError(f"Cannot unsubscribe handler for event '{event_type}'") from e

    def clear_event(self, event_type: str) -> None:
        """Remove all handlers for a given event type.

        Args:
            event_type: Identifier for the event.
        """
        self._validate_event_type(event_type)
        with self._lock:
            self._subs.pop(event_type, None)
        logger.info("Cleared handlers for event '%s'", event_type)

    def clear_all(self) -> None:
        """Remove all subscriptions for all events."""
        with self._lock:
            self._subs.clear()
        logger.info("Cleared all event subscriptions")

    def publish(self, event_type: str, payload: Optional[Any] = None) -> None:
        """Publish an event to all subscribed handlers.

        Args:
            event_type: Identifier for the event.
            payload: Data to pass to each handler.

        Raises:
            PublicationError: If event persistence fails.
        """
        self._validate_event_type(event_type)
        # Minimize lock hold time by copying handlers
        with self._lock:
            handlers = list(self._subs.get(event_type, []))

        if not handlers:
            logger.warning("No handlers for published event '%s'", event_type)
            return

        logger.debug("Publishing event '%s' to %d handler(s)", event_type, len(handlers))

        # Persist event if an EventStore is configured
        if self._config.store:
            try:
                self._config.store.store(event_type, payload)
            except Exception as e:
                logger.error("Event persistence failed for '%s': %s", event_type, e)
                raise PublicationError("Failed to persist event") from e

        # Dispatch to handlers
        for handler in handlers:
            try:
                handler(payload)
            except Exception:
                logger.exception("Handler %r raised exception for event '%s'", handler, event_type)

    def _validate_event_type(self, event_type: str) -> None:
        """Confirm that event_type is a non-empty string (and allowed, if configured)."""
        if not isinstance(event_type, str) or not event_type.strip():
            raise SubscriptionError("event_type must be a non-empty string")
        if self._config.allowed_event_types and event_type not in self._config.allowed_event_types:
            raise SubscriptionError(f"Event type '{event_type}' is not allowed")

    def _validate_handler(self, handler: Callable[[Any], None]) -> None:
        """Confirm that handler is callable."""
        if not callable(handler):
            raise SubscriptionError("handler must be callable")
