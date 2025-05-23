"""Optimized Services Framework - Core exports."""

from .core import (
    UniversalService, Service, ServiceConfiguration, ServiceRegistry, ServiceFactory,
    ServiceLifecycleManager, ValidationService, ValidationError, EventBus, EventHandler, 
    StorageProvider, create_memory_storage, create_event_bus, create_production_service,
    validate_coordinate, validate_color, validate_brush_width, validate_tool_key
)
from .drawing import (
    DrawingEngine, ToolManager, ToolType, ToolState, create_drawing_engine, create_tool_manager
)
from .application import (
    UnifiedApplication, ApplicationSettings, SimpleApp, create_application
)

def create_complete_application(backend, **settings):
    """Create complete application with all services."""
    app_settings = ApplicationSettings(**settings)
    return UnifiedApplication(backend, app_settings)

def create_working_application(backend, **settings):
    """Create working application."""
    return create_complete_application(backend, **settings)

def integrate_with_existing_backend(backend):
    """Integrate with existing backend."""
    return backend

class WorkingApplication:
    """Working application wrapper for easy use."""
    
    def __init__(self, backend, **settings):
        self.app = create_complete_application(backend, **settings)
        
    def initialize(self):
        return self.app.initialize()
        
    def run(self):
        return self.app.run()
        
    def shutdown(self):
        return self.app.shutdown()

__all__ = [
    'UniversalService', 'Service', 'ServiceConfiguration', 'ServiceRegistry', 'ServiceFactory',
    'ServiceLifecycleManager', 'ValidationService', 'ValidationError', 'EventBus', 'EventHandler',
    'StorageProvider', 'create_memory_storage', 'create_event_bus', 'create_production_service',
    'DrawingEngine', 'ToolManager', 'ToolType', 'ToolState', 'create_drawing_engine', 'create_tool_manager',
    'UnifiedApplication', 'ApplicationSettings', 'SimpleApp', 'create_application',
    'create_complete_application', 'create_working_application', 'WorkingApplication',
    'integrate_with_existing_backend', 'validate_coordinate', 'validate_color', 'validate_brush_width'
]