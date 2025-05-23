"""
Universal Event System
Eliminates ALL event handling duplication through unified pub/sub architecture.

This module consolidates event patterns from across the application into a
single, type-safe, high-performance event bus with comprehensive monitoring.
"""

import logging
import threading
import weakref
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar, Generic, Protocol
from collections import defaultdict, deque
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

T = TypeVar('T')
EventData = TypeVar('EventData')


class EventPriority(Enum):
    """Event priority levels for processing order."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass(frozen=True)
class Event:
    """Universal event container with metadata."""
    name: str
    data: Any
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: Optional[str] = None
    priority: EventPriority = EventPriority.NORMAL
    
    def __post_init__(self):
        if not self.name:
            raise ValueError("Event name cannot be empty")


class EventHandler(Protocol):
    """Protocol for event handlers."""
    
    def handle_event(self, event_data: Any) -> None:
        """Handle event data."""
        ...


class EventFilter(Protocol):
    """Protocol for event filters."""
    
    def should_process(self, event: Event) -> bool:
        """Determine if event should be processed."""
        ...


@dataclass
class EventSubscription:
    """Event subscription with metadata and control."""
    handler: EventHandler
    event_name: str
    subscription_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    is_weak: bool = False
    filter_func: Optional[EventFilter] = None
    priority: EventPriority = EventPriority.NORMAL
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        if self.is_weak:
            self.handler = weakref.ref(self.handler)


class EventMetrics:
    """Event system performance metrics."""
    
    def __init__(self):
        self.events_published = 0
        self.events_processed = 0
        self.events_failed = 0
        self.handler_errors = 0
        self.processing_times: deque = deque(maxlen=1000)
        self.recent_events: deque = deque(maxlen=100)
        
    def record_event_published(self, event: Event):
        """Record event publication."""
        self.events_published += 1
        self.recent_events.append(event)
        
    def record_event_processed(self, processing_time: float):
        """Record event processing."""
        self.events_processed += 1
        self.processing_times.append(processing_time)
        
    def record_event_failed(self):
        """Record event processing failure."""
        self.events_failed += 1
        
    def record_handler_error(self):
        """Record handler execution error."""
        self.handler_errors += 1
        
    def get_average_processing_time(self) -> float:
        """Get average event processing time."""
        if not self.processing_times:
            return 0.0
        return sum(self.processing_times) / len(self.processing_times)


class EventPublisher:
    """Mixin for classes that publish events."""
    
    def __init__(self, event_bus: 'EventBus' = None):
        self._event_bus = event_bus
        
    def set_event_bus(self, event_bus: 'EventBus'):
        """Set the event bus for publishing."""
        self._event_bus = event_bus
        
    def publish(self, event_name: str, data: Any = None, **kwargs):
        """Publish event through the bus."""
        if self._event_bus:
            self._event_bus.publish(event_name, data, **kwargs)


class EventBus:
    """
    Universal event bus eliminating all pub/sub duplication.
    
    Provides thread-safe, high-performance event distribution with priorities,
    filters, metrics, and comprehensive error handling.
    """
    
    def __init__(self, max_queue_size: int = 10000):
        self._subscriptions: Dict[str, List[EventSubscription]] = defaultdict(list)
        self._global_handlers: List[EventSubscription] = []
        self._event_queue: deque = deque(maxlen=max_queue_size)
        self._metrics = EventMetrics()
        self._lock = threading.RLock()
        self._shutdown = False
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def publish(
        self, 
        event_name: str, 
        data: Any = None, 
        source: str = None,
        priority: EventPriority = EventPriority.NORMAL
    ) -> str:
        """Publish event to all subscribers."""
        if self._shutdown:
            self.logger.warning(f"Attempted to publish to shutdown bus: {event_name}")
            return None
            
        event = Event(
            name=event_name,
            data=data,
            source=source,
            priority=priority
        )
        
        with self._lock:
            self._metrics.record_event_published(event)
            self._process_event_immediately(event)
            
        return event.event_id
    
    def subscribe(
        self,
        event_name: str,
        handler: EventHandler,
        priority: EventPriority = EventPriority.NORMAL,
        filter_func: Optional[EventFilter] = None,
        weak_ref: bool = False
    ) -> EventSubscription:
        """Subscribe to specific event."""
        subscription = EventSubscription(
            handler=handler,
            event_name=event_name,
            priority=priority,
            filter_func=filter_func,
            is_weak=weak_ref
        )
        
        with self._lock:
            self._subscriptions[event_name].append(subscription)
            # Sort by priority (higher priority first)
            self._subscriptions[event_name].sort(
                key=lambda s: s.priority.value, 
                reverse=True
            )
            
        self.logger.debug(f"Subscribed to {event_name}: {handler}")
        return subscription
    
    def subscribe_global(
        self,
        handler: EventHandler,
        priority: EventPriority = EventPriority.NORMAL,
        filter_func: Optional[EventFilter] = None
    ) -> EventSubscription:
        """Subscribe to all events globally."""
        subscription = EventSubscription(
            handler=handler,
            event_name="*",
            priority=priority,
            filter_func=filter_func
        )
        
        with self._lock:
            self._global_handlers.append(subscription)
            self._global_handlers.sort(
                key=lambda s: s.priority.value,
                reverse=True
            )
            
        self.logger.debug(f"Global subscription added: {handler}")
        return subscription
    
    def unsubscribe(self, event_name: str, handler: EventHandler) -> bool:
        """Unsubscribe from specific event."""
        with self._lock:
            if event_name in self._subscriptions:
                initial_count = len(self._subscriptions[event_name])
                self._subscriptions[event_name] = [
                    sub for sub in self._subscriptions[event_name]
                    if sub.handler != handler
                ]
                removed = initial_count - len(self._subscriptions[event_name])
                if removed > 0:
                    self.logger.debug(f"Unsubscribed from {event_name}: {handler}")
                    return True
        return False
    
    def unsubscribe_by_id(self, subscription_id: str) -> bool:
        """Unsubscribe using subscription ID."""
        with self._lock:
            # Check specific subscriptions
            for event_name, subscriptions in self._subscriptions.items():
                for i, sub in enumerate(subscriptions):
                    if sub.subscription_id == subscription_id:
                        del subscriptions[i]
                        self.logger.debug(f"Unsubscribed by ID {subscription_id}")
                        return True
            
            # Check global handlers
            for i, sub in enumerate(self._global_handlers):
                if sub.subscription_id == subscription_id:
                    del self._global_handlers[i]
                    self.logger.debug(f"Unsubscribed global by ID {subscription_id}")
                    return True
                    
        return False
    
    def clear_subscriptions(self, event_name: str = None):
        """Clear subscriptions for event or all events."""
        with self._lock:
            if event_name:
                if event_name in self._subscriptions:
                    del self._subscriptions[event_name]
                    self.logger.debug(f"Cleared subscriptions for {event_name}")
            else:
                self._subscriptions.clear()
                self._global_handlers.clear()
                self.logger.debug("Cleared all subscriptions")
    
    def get_subscription_count(self, event_name: str = None) -> int:
        """Get subscription count for event or total."""
        with self._lock:
            if event_name:
                return len(self._subscriptions.get(event_name, []))
            else:
                total = sum(len(subs) for subs in self._subscriptions.values())
                total += len(self._global_handlers)
                return total
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive event bus metrics."""
        return {
            'events_published': self._metrics.events_published,
            'events_processed': self._metrics.events_processed,
            'events_failed': self._metrics.events_failed,
            'handler_errors': self._metrics.handler_errors,
            'average_processing_time': self._metrics.get_average_processing_time(),
            'total_subscriptions': self.get_subscription_count(),
            'event_types': len(self._subscriptions),
            'global_handlers': len(self._global_handlers)
        }
    
    def shutdown(self):
        """Shutdown event bus gracefully."""
        with self._lock:
            self._shutdown = True
            self.clear_subscriptions()
            self.logger.info("Event bus shutdown completed")
    
    def _process_event_immediately(self, event: Event):
        """Process event immediately on current thread."""
        import time
        start_time = time.time()
        
        try:
            # Process specific event subscribers
            if event.name in self._subscriptions:
                self._notify_subscribers(self._subscriptions[event.name], event)
            
            # Process global handlers
            self._notify_subscribers(self._global_handlers, event)
            
            processing_time = time.time() - start_time
            self._metrics.record_event_processed(processing_time)
            
        except Exception as error:
            self._metrics.record_event_failed()
            self.logger.error(f"Failed to process event {event.name}: {error}")
    
    def _notify_subscribers(self, subscriptions: List[EventSubscription], event: Event):
        """Notify list of subscribers about event."""
        for subscription in subscriptions:
            try:
                # Apply filter if present
                if subscription.filter_func and not subscription.filter_func.should_process(event):
                    continue
                
                # Get handler (handle weak references)
                handler = subscription.handler
                if subscription.is_weak:
                    handler = handler()  # Dereference weak reference
                    if handler is None:
                        continue  # Handler was garbage collected
                
                # Call handler
                if hasattr(handler, 'handle_event'):
                    handler.handle_event(event.data)
                elif callable(handler):
                    handler(event.data)
                else:
                    self.logger.warning(f"Invalid handler for {event.name}: {handler}")
                    
            except Exception as error:
                self._metrics.record_handler_error()
                self.logger.error(f"Handler error for {event.name}: {error}")


class EventChannelManager:
    """Manages event channels for different application domains."""
    
    def __init__(self):
        self._channels: Dict[str, EventBus] = {}
        self._default_channel = "default"
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Create default channel
        self._channels[self._default_channel] = EventBus()
    
    def create_channel(self, name: str) -> EventBus:
        """Create new event channel."""
        if name in self._channels:
            raise ValueError(f"Channel already exists: {name}")
        
        self._channels[name] = EventBus()
        self.logger.info(f"Created event channel: {name}")
        return self._channels[name]
    
    def get_channel(self, name: str = None) -> EventBus:
        """Get event channel by name."""
        channel_name = name or self._default_channel
        
        if channel_name not in self._channels:
            raise ValueError(f"Channel not found: {channel_name}")
        
        return self._channels[channel_name]
    
    def shutdown_all(self):
        """Shutdown all channels."""
        for name, channel in self._channels.items():
            channel.shutdown()
            self.logger.info(f"Shutdown channel: {name}")


# Convenience functions for common patterns
def create_event_bus() -> EventBus:
    """Create standard event bus."""
    return EventBus()


def create_event_handler(func: Callable[[Any], None]) -> EventHandler:
    """Create event handler from function."""
    class FunctionHandler:
        def handle_event(self, event_data: Any) -> None:
            func(event_data)
    
    return FunctionHandler()


def create_priority_filter(min_priority: EventPriority) -> EventFilter:
    """Create filter for minimum priority events."""
    class PriorityFilter:
        def should_process(self, event: Event) -> bool:
            return event.priority.value >= min_priority.value
    
    return PriorityFilter()


def create_source_filter(allowed_sources: Set[str]) -> EventFilter:
    """Create filter for specific event sources."""
    class SourceFilter:
        def should_process(self, event: Event) -> bool:
            return event.source in allowed_sources
    
    return SourceFilter()