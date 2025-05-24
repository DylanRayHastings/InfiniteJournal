"""Base backend interface."""

from abc import ABC, abstractmethod
from infinitejournal.config import Config


class Backend(ABC):
    """Abstract base class for rendering backends."""
    
    def __init__(self, config: Config):
        """Initialize backend with configuration."""
        self.config = config
        
    @abstractmethod
    def initialize(self):
        """Initialize the backend."""
        pass
        
    @abstractmethod
    def clear(self):
        """Clear the screen."""
        pass
        
    @abstractmethod
    def present(self):
        """Present the rendered frame."""
        pass
        
    @abstractmethod
    def handle_events(self):
        """Handle window and input events."""
        pass
        
    @abstractmethod
    def get_delta_time(self):
        """Get time since last frame."""
        pass
        
    @abstractmethod
    def shutdown(self):
        """Shutdown the backend."""
        pass
        
    @abstractmethod
    def is_running(self):
        """Check if the backend is still running."""
        pass
        
    @abstractmethod
    def start(self):
        """Start the backend."""
        pass
