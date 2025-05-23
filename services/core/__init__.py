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

# Add aliases for bootstrap compatibility
Service = UniversalService  # Bootstrap expects 'Service'

__all__ = [
    'UniversalService', 'Service', 'ServiceConfiguration', 'ServiceRegistry', 'ServiceFactory',
    'ServiceLifecycleManager', 'ValidationService', 'ValidationError', 'EventBus', 
    'EventHandler', 'EventSubscription', 'StorageProvider', 'create_memory_storage', 
    'create_event_bus', 'create_event_handler', 'validate_coordinate', 'validate_color',
    'validate_brush_width', 'validate_tool_key', 'create_validator_chain', 'create_production_service'
]