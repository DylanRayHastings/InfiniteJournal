"""
Universal Service Framework - Core Architecture
Eliminates ALL service duplication through generic, reusable patterns.

This module provides the foundation for all services in the application,
ensuring consistent lifecycle management, error handling, and dependency injection.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic, Protocol, Callable
from pathlib import Path
from contextlib import contextmanager
import threading
import uuid

logger = logging.getLogger(__name__)

T = TypeVar('T')
ServiceType = TypeVar('ServiceType', bound='UniversalService')


class ServiceState(Enum):
    """Universal service state enumeration."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class ServiceError(Exception):
    """Base exception for all service operations."""
    
    def __init__(self, message: str, service_name: str = None, cause: Exception = None):
        super().__init__(message)
        self.service_name = service_name
        self.cause = cause
        self.timestamp = datetime.now(timezone.utc)


class ServiceInitializationError(ServiceError):
    """Raised when service initialization fails."""
    pass


class ServiceOperationError(ServiceError):
    """Raised when service operations fail."""
    pass


class ServiceDependencyError(ServiceError):
    """Raised when service dependencies are not satisfied."""
    pass


@dataclass(frozen=True)
class ServiceConfiguration:
    """Universal service configuration."""
    service_name: str
    debug_mode: bool = False
    auto_start: bool = True
    retry_count: int = 3
    timeout_seconds: float = 30.0
    dependencies: List[str] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.service_name:
            raise ServiceError("Service name cannot be empty")
        if self.retry_count < 0:
            raise ServiceError("Retry count must be non-negative")
        if self.timeout_seconds <= 0:
            raise ServiceError("Timeout must be positive")


class ServiceDependency(Protocol):
    """Protocol for service dependencies."""
    
    def get_state(self) -> ServiceState:
        """Get current service state."""
        ...
    
    def is_ready(self) -> bool:
        """Check if service is ready for use."""
        ...


class ServiceMetrics:
    """Service performance and operational metrics."""
    
    def __init__(self):
        self.start_time: Optional[datetime] = None
        self.operation_count = 0
        self.error_count = 0
        self.last_operation_time: Optional[datetime] = None
        self.total_operation_duration = 0.0
        
    def record_operation(self, duration: float):
        """Record an operation execution."""
        self.operation_count += 1
        self.total_operation_duration += duration
        self.last_operation_time = datetime.now(timezone.utc)
        
    def record_error(self):
        """Record an error occurrence."""
        self.error_count += 1
        
    def get_average_operation_time(self) -> float:
        """Get average operation execution time."""
        if self.operation_count == 0:
            return 0.0
        return self.total_operation_duration / self.operation_count


class UniversalService(Generic[T], ABC):
    """
    Universal service base class eliminating all service duplication.
    
    Provides standardized service lifecycle, error handling, logging,
    state management, and dependency injection for all application services.
    """
    
    def __init__(
        self,
        config: ServiceConfiguration,
        validation_service: Any = None,
        event_bus: Any = None,
        storage_provider: Any = None
    ):
        """Initialize universal service with common dependencies."""
        self.config = config
        self.validation_service = validation_service
        self.event_bus = event_bus
        self.storage_provider = storage_provider
        
        self.service_id = str(uuid.uuid4())
        self.state = ServiceState.UNINITIALIZED
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.metrics = ServiceMetrics()
        self._lock = threading.RLock()
        
        self._dependencies: Dict[str, ServiceDependency] = {}
        self._subscribers: List[str] = []
        
        if config.debug_mode:
            self.logger.setLevel(logging.DEBUG)
        
        self.logger.info(f"Service {config.service_name} initialized with ID {self.service_id}")
    
    @abstractmethod
    def _initialize_service(self) -> None:
        """Initialize service-specific components."""
        pass
    
    @abstractmethod
    def _cleanup_service(self) -> None:
        """Clean up service-specific resources."""
        pass
    
    def start(self) -> None:
        """Start service with full lifecycle management."""
        with self._lock:
            if self.state != ServiceState.UNINITIALIZED:
                raise ServiceOperationError(
                    f"Cannot start service in state: {self.state}",
                    self.config.service_name
                )
            
            try:
                self.state = ServiceState.INITIALIZING
                self.metrics.start_time = datetime.now(timezone.utc)
                
                self._check_dependencies()
                self._setup_event_subscriptions()
                self._initialize_service()
                
                self.state = ServiceState.RUNNING
                self._publish_service_event('service_started', {
                    'service_name': self.config.service_name,
                    'service_id': self.service_id,
                    'start_time': self.metrics.start_time.isoformat()
                })
                
                self.logger.info(f"Service {self.config.service_name} started successfully")
                
            except Exception as error:
                self.state = ServiceState.ERROR
                self.metrics.record_error()
                self.logger.error(f"Failed to start service {self.config.service_name}: {error}")
                raise ServiceInitializationError(
                    f"Service startup failed: {error}",
                    self.config.service_name,
                    error
                ) from error
    
    def stop(self) -> None:
        """Stop service with proper cleanup."""
        with self._lock:
            if self.state not in [ServiceState.RUNNING, ServiceState.PAUSED]:
                return
            
            try:
                self.state = ServiceState.STOPPING
                
                self._cleanup_event_subscriptions()
                self._cleanup_service()
                
                self.state = ServiceState.STOPPED
                self._publish_service_event('service_stopped', {
                    'service_name': self.config.service_name,
                    'service_id': self.service_id,
                    'uptime_seconds': self._get_uptime_seconds()
                })
                
                self.logger.info(f"Service {self.config.service_name} stopped")
                
            except Exception as error:
                self.state = ServiceState.ERROR
                self.metrics.record_error()
                self.logger.error(f"Error stopping service {self.config.service_name}: {error}")
    
    def execute_with_error_handling(self, operation_name: str, operation: Callable[[], T]) -> T:
        """Execute operation with standardized error handling."""
        if not self.is_ready():
            raise ServiceOperationError(
                f"Service not ready for operation: {operation_name}",
                self.config.service_name
            )
        
        start_time = time.time()
        
        try:
            result = operation()
            execution_time = time.time() - start_time
            self.metrics.record_operation(execution_time)
            
            self.logger.debug(f"Operation {operation_name} completed in {execution_time:.3f}s")
            return result
            
        except Exception as error:
            execution_time = time.time() - start_time
            self.metrics.record_error()
            
            self.logger.error(f"Operation {operation_name} failed after {execution_time:.3f}s: {error}")
            self._publish_service_event('service_error', {
                'service_name': self.config.service_name,
                'operation': operation_name,
                'error': str(error),
                'execution_time': execution_time
            })
            
            raise ServiceOperationError(
                f"Operation {operation_name} failed: {error}",
                self.config.service_name,
                error
            ) from error
    
    def get_state(self) -> ServiceState:
        """Get current service state."""
        return self.state
    
    def is_ready(self) -> bool:
        """Check if service is ready for operations."""
        return self.state == ServiceState.RUNNING
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        return {
            'service_id': self.service_id,
            'service_name': self.config.service_name,
            'state': self.state.value,
            'uptime_seconds': self._get_uptime_seconds(),
            'operation_count': self.metrics.operation_count,
            'error_count': self.metrics.error_count,
            'average_operation_time': self.metrics.get_average_operation_time(),
            'dependencies_count': len(self._dependencies),
            'subscribers_count': len(self._subscribers)
        }
    
    def _check_dependencies(self) -> None:
        """Check all service dependencies are ready."""
        for name, dependency in self._dependencies.items():
            if not dependency.is_ready():
                raise ServiceDependencyError(
                    f"Dependency not ready: {name}",
                    self.config.service_name
                )
    
    def _setup_event_subscriptions(self) -> None:
        """Set up event subscriptions for service."""
        if self.event_bus:
            self.event_bus.subscribe('service_shutdown', self._handle_shutdown_request)
            self._subscribers.append('service_shutdown')
    
    def _cleanup_event_subscriptions(self) -> None:
        """Clean up event subscriptions."""
        if self.event_bus:
            for event_name in self._subscribers:
                try:
                    self.event_bus.unsubscribe(event_name, self._handle_shutdown_request)
                except Exception as error:
                    self.logger.warning(f"Failed to unsubscribe from {event_name}: {error}")
        
        self._subscribers.clear()
    
    def _handle_shutdown_request(self, data: Any) -> None:
        """Handle shutdown request event."""
        self.logger.info(f"Shutdown requested for service {self.config.service_name}")
        self.stop()
    
    def _get_uptime_seconds(self) -> float:
        """Get service uptime in seconds."""
        if self.metrics.start_time is None:
            return 0.0
        return (datetime.now(timezone.utc) - self.metrics.start_time).total_seconds()
    
    def _publish_service_event(self, event_name: str, data: Dict[str, Any]) -> None:
        """Publish service event if event bus available."""
        if self.event_bus:
            try:
                self.event_bus.publish(event_name, data)
            except Exception as error:
                self.logger.warning(f"Failed to publish event {event_name}: {error}")


class ServiceRegistry:
    """Registry for managing multiple services with lifecycle coordination."""
    
    def __init__(self):
        """Initialize service registry."""
        self.services: Dict[str, UniversalService] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self._lock = threading.RLock()
    
    def register_service(self, service: UniversalService) -> None:
        """Register service in registry."""
        with self._lock:
            service_name = service.config.service_name
            
            if service_name in self.services:
                raise ServiceError(f"Service already registered: {service_name}")
            
            self.services[service_name] = service
            self.logger.info(f"Registered service: {service_name}")
    
    def get_service(self, service_name: str) -> UniversalService:
        """Get service by name."""
        with self._lock:
            if service_name not in self.services:
                raise ServiceError(f"Service not found: {service_name}")
            return self.services[service_name]
    
    def start_all_services(self) -> None:
        """Start all registered services."""
        with self._lock:
            for service_name, service in self.services.items():
                try:
                    if service.config.auto_start:
                        service.start()
                except Exception as error:
                    self.logger.error(f"Failed to start service {service_name}: {error}")
    
    def stop_all_services(self) -> None:
        """Stop all registered services."""
        with self._lock:
            for service_name, service in reversed(list(self.services.items())):
                try:
                    service.stop()
                except Exception as error:
                    self.logger.error(f"Failed to stop service {service_name}: {error}")
    
    def get_registry_statistics(self) -> Dict[str, Any]:
        """Get statistics for all services."""
        with self._lock:
            return {
                'total_services': len(self.services),
                'running_services': sum(1 for s in self.services.values() if s.is_ready()),
                'services': {name: service.get_statistics() for name, service in self.services.items()}
            }


class ServiceFactory:
    """Factory for creating standardized services with dependency injection."""
    
    @staticmethod
    def create_service(
        service_class: Type[ServiceType],
        config: ServiceConfiguration,
        validation_service: Any = None,
        event_bus: Any = None,
        storage_provider: Any = None,
        **kwargs
    ) -> ServiceType:
        """Create service instance with dependency injection."""
        return service_class(
            config=config,
            validation_service=validation_service,
            event_bus=event_bus,
            storage_provider=storage_provider,
            **kwargs
        )


class ServiceLifecycleManager:
    """Manages service lifecycle with dependency resolution."""
    
    def __init__(self, registry: ServiceRegistry = None):
        self.registry = registry or ServiceRegistry()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def add_service(self, service: UniversalService) -> None:
        """Add service to lifecycle management."""
        self.registry.register_service(service)
    
    def start_services(self) -> None:
        """Start all services with dependency resolution."""
        self.registry.start_all_services()
    
    def stop_services(self) -> None:
        """Stop all services gracefully."""
        self.registry.stop_all_services()
    
    @contextmanager
    def service_lifecycle(self):
        """Context manager for complete service lifecycle."""
        try:
            self.start_services()
            yield self.registry
        finally:
            self.stop_services()


def create_production_service(
    service_class: Type[ServiceType],
    service_name: str,
    validation_service: Any = None,
    event_bus: Any = None,
    storage_provider: Any = None,
    **config_overrides
) -> ServiceType:
    """Create production-ready service with standard configuration."""
    config = ServiceConfiguration(
        service_name=service_name,
        debug_mode=False,
        auto_start=True,
        retry_count=3,
        timeout_seconds=30.0,
        **config_overrides
    )
    
    return ServiceFactory.create_service(
        service_class=service_class,
        config=config,
        validation_service=validation_service,
        event_bus=event_bus,
        storage_provider=storage_provider
    )