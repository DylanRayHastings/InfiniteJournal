"""Core services package exports."""

from .framework import (
    UniversalService, ServiceConfiguration, ServiceRegistry, ServiceFactory,
    ServiceLifecycleManager, create_production_service
)
from .validation import (
    ValidationService, ValidationError, validate_coordinate, validate_color,
    validate_brush_width, validate_tool_key, create_validator_chain
)
from .events import (
    EventBus, EventHandler, EventSubscription, create_event_bus, create_event_handler
)
from .storage import (
    StorageProvider, create_memory_storage, create_file_storage
)

__all__ = [
    'UniversalService', 'ServiceConfiguration', 'ServiceRegistry', 'ServiceFactory',
    'ValidationService', 'ValidationError', 'EventBus', 'StorageProvider',
    'create_memory_storage', 'create_event_bus'
]
