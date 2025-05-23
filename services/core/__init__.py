"""
Universal Services Framework - Core Module Exports

This module exports all core framework components that eliminate duplication
across the entire application architecture.
"""

# Universal Service Framework
from .framework import (
    # Core service architecture
    UniversalService,
    ServiceConfiguration,
    ServiceState,
    ServiceError,
    ServiceInitializationError,
    ServiceOperationError,
    ServiceDependencyError,
    ServiceDependency,
    ServiceMetrics,
    
    # Service management
    ServiceRegistry,
    ServiceFactory,
    ServiceLifecycleManager,
    
    # Factory functions
    create_production_service
)

# Universal Validation System
from .validation import (
    # Core validation
    ValidationService,
    ValidationRule,
    ValidationChain,
    ValidationResult,
    ValidationError,
    
    # Standard rules
    RequiredRule,
    RangeRule,
    CoordinateRule,
    ColorRule,
    ToolKeyRule,
    
    # Convenience functions
    validate_coordinate,
    validate_color,
    validate_brush_width,
    validate_file_path,
    validate_tool_key,
    
    # Factory functions
    create_validator_chain,
    create_coordinate_validator,
    create_numeric_validator
)

# Universal Event System
from .events import (
    # Core event system
    EventBus,
    Event,
    EventHandler,
    EventSubscription,
    EventPublisher,
    EventFilter,
    EventPriority,
    EventMetrics,
    EventChannelManager,
    
    # Factory functions
    create_event_bus,
    create_event_handler,
    create_priority_filter,
    create_source_filter
)

# Universal Storage System
from .storage import (
    # Core storage
    StorageProvider,
    BaseStorageProvider,
    StorageError,
    StorageNotFoundError,
    StoragePermissionError,
    StorageMetadata,
    
    # Storage implementations
    MemoryStorageProvider,
    FileStorageProvider,
    
    # Specialized providers
    ConfigurationProvider,
    StateProvider,
    
    # Factory functions
    create_memory_storage,
    create_file_storage,
    create_json_storage,
    create_configuration_provider,
    create_state_provider
)

# Version information
__version__ = "1.0.0"
__author__ = "Universal Services Framework"

# Export groups for convenience
__all__ = [
    # Framework core
    "UniversalService",
    "ServiceConfiguration",
    "ServiceRegistry",
    "ServiceFactory",
    "ServiceLifecycleManager",
    "create_production_service",
    
    # Validation system
    "ValidationService",
    "ValidationRule",
    "ValidationError",
    "validate_coordinate",
    "validate_color", 
    "validate_brush_width",
    "validate_tool_key",
    "create_validator_chain",
    
    # Event system
    "EventBus",
    "EventPublisher",
    "EventHandler",
    "EventSubscription",
    "create_event_bus",
    "create_event_handler",
    
    # Storage system
    "StorageProvider",
    "ConfigurationProvider",
    "StateProvider",
    "create_file_storage",
    "create_memory_storage",
    "create_json_storage"
]