"""Simplified service framework."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class ServiceConfiguration:
    """Service configuration."""
    service_name: str
    debug_mode: bool = False
    auto_start: bool = True

class UniversalService(ABC):
    """Base service class."""
    
    def __init__(self, config: ServiceConfiguration, validation_service=None, 
                 event_bus=None, storage_provider=None):
        self.config = config
        self.validation_service = validation_service
        self.event_bus = event_bus
        self.storage_provider = storage_provider
        self.logger = logging.getLogger(config.service_name)
        self.running = False
        
    def start(self):
        """Start the service."""
        self.running = True
        self._initialize_service()
        self.logger.info(f"Service {self.config.service_name} started")
        
    def stop(self):
        """Stop the service."""
        self.running = False
        self._cleanup_service()
        self.logger.info(f"Service {self.config.service_name} stopped")
        
    def is_ready(self):
        """Check if service is ready."""
        return self.running
        
    @abstractmethod
    def _initialize_service(self):
        """Initialize service implementation."""
        pass
        
    @abstractmethod
    def _cleanup_service(self):
        """Clean up service implementation."""
        pass

class ServiceRegistry:
    """Simple service registry."""
    
    def __init__(self):
        self.services = {}
        
    def register_service(self, service):
        self.services[service.config.service_name] = service
        
    def get_service(self, name):
        return self.services.get(name)

class ServiceFactory:
    """Simple service factory."""
    
    @staticmethod
    def create_service(service_class, config, **kwargs):
        return service_class(config, **kwargs)

class ServiceLifecycleManager:
    """Service lifecycle manager."""
    
    def __init__(self):
        self.services = []
        
    def add_service(self, service):
        self.services.append(service)
        
    def start_services(self):
        for service in self.services:
            try:
                service.start()
            except Exception as e:
                logger.error(f"Failed to start service: {e}")
                
    def stop_services(self):
        for service in reversed(self.services):
            try:
                service.stop()
            except Exception as e:
                logger.error(f"Failed to stop service: {e}")

def create_production_service(service_class, service_name, **kwargs):
    """Create production service."""
    config = ServiceConfiguration(service_name)
    return ServiceFactory.create_service(service_class, config, **kwargs)