"""
Fixed bootstrap/factory.py for Universal Services Framework Compatibility
========================================================================

This replaces your existing bootstrap/factory.py to work with the new
Universal Services Framework while maintaining backward compatibility.
"""

import logging
from pathlib import Path
from .errors import StartupError

logger = logging.getLogger(__name__)


# Try to import EventBus from the best available source
try:
    from services import create_event_bus
    EventBus = lambda: create_event_bus()
except ImportError:
    try:
        from core.event_bus import EventBus
    except ImportError:
        # Fallback minimal EventBus
        class EventBus:
            def __init__(self):
                self.subscribers = {}
            def publish(self, event, data=None):
                pass
            def subscribe(self, event, handler):
                pass

logger = logging.getLogger(__name__)


def create_simple_app(settings):
    """
    Create a simple, working application with Universal Services Framework support.
    
    This function has been updated to work with both the new Universal Services
    Framework and legacy compatibility mode.
    """
    
    # Create event bus
    try:
        bus = EventBus() if callable(EventBus) else EventBus
    except:
        # Fallback if EventBus creation fails
        bus = None
    
    # Ensure data directory exists
    Path(settings.DATA_PATH).mkdir(parents=True, exist_ok=True)
    
    try:
        # Try to use Universal Services Framework first
        try:
            return _create_universal_services_app(settings, bus)
        except ImportError as import_error:
            logger.warning(f"Universal Services not available: {import_error}")
            logger.info("Falling back to legacy compatibility mode")
            return _create_legacy_compatible_app(settings, bus)
            
    except Exception as e:
        logger.error("Failed to create application: %s", e)
        raise StartupError(f"App creation failed: {e}") from e


def _create_universal_services_app(settings, bus):
    """Create application using Universal Services Framework."""
    from services import (
        create_complete_application,
        ApplicationSettings,
        integrate_with_existing_backend
    )
    
    # Load adapters
    engine, clock, input_adapter = _load_adapters()
    
    # Integrate existing backend with Universal Services
    adapted_backend = integrate_with_existing_backend(engine)
    
    # Convert settings to new format
    app_settings = ApplicationSettings(
        window_width=getattr(settings, 'WIDTH', 1280),
        window_height=getattr(settings, 'HEIGHT', 720),
        window_title=getattr(settings, 'TITLE', 'InfiniteJournal'),
        target_fps=getattr(settings, 'FPS', 60),
        debug_mode=getattr(settings, 'DEBUG', False),
        data_directory=Path(getattr(settings, 'DATA_PATH', './data'))
    )
    
    # Create Universal Services application
    app = create_complete_application(
        backend=adapted_backend,
        window_width=app_settings.window_width,
        window_height=app_settings.window_height,
        window_title=app_settings.window_title,
        target_fps=app_settings.target_fps,
        debug_mode=app_settings.debug_mode
    )
    
    logger.info("Created application with Universal Services Framework")
    return app


def _create_legacy_compatible_app(settings, bus):
    """Create application using legacy compatibility mode."""
    
    # Load adapters
    engine, clock, input_adapter = _load_adapters()
    
    # Create legacy SimpleApp (now available from services.app)
    from services.app import SimpleApp
    
    app = SimpleApp(
        settings=settings,
        engine=engine,
        clock=clock,
        input_adapter=input_adapter,
        bus=bus
    )
    
    logger.info("Created application with legacy compatibility")
    return app


def _load_adapters():
    """Load simplified pygame adapters."""
    try:
        from adapters.pygame_adapter import (
            PygameEngineAdapter, 
            PygameClockAdapter, 
            PygameInputAdapter
        )
        
        engine = PygameEngineAdapter()
        clock = PygameClockAdapter()
        input_adapter = PygameInputAdapter()
        
        # Validate adapters have required methods
        required_engine_methods = ['poll_events', 'clear', 'present']
        for method in required_engine_methods:
            if not hasattr(engine, method):
                logger.warning(f"Engine adapter missing '{method}' method")
        
        # Add compatibility methods if missing
        if not hasattr(engine, 'init_window') and not hasattr(engine, 'open_window'):
            raise StartupError("Engine adapter missing window initialization method")
        
        logger.info("Adapters loaded successfully")
        return engine, clock, input_adapter
        
    except ImportError as e:
        raise StartupError(f"Failed to import pygame adapters: {e}") from e
    except Exception as e:
        raise StartupError(f"Failed to initialize adapters: {e}") from e


# Legacy function for backward compatibility
def compose_app(settings, bus=None):
    """
    Legacy compose_app function for backward compatibility.
    
    This maintains the old interface while using the new implementation.
    """
    logger.warning("compose_app() is deprecated. Use create_simple_app() instead.")
    return create_simple_app(settings)