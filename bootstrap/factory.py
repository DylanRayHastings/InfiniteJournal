"""
Simple factory for creating the working application.

Uses the simplified components that focus on core functionality.
"""

import logging
from pathlib import Path
from core.event_bus import EventBus
from .errors import StartupError

logger = logging.getLogger(__name__)


def create_simple_app(settings):
    """Create a simple, working application."""
    
    # Create event bus
    bus = EventBus()
    
    # Ensure data directory exists
    Path(settings.DATA_PATH).mkdir(parents=True, exist_ok=True)
    
    try:
        # Load simplified adapters
        engine, clock, input_adapter = _load_simple_adapters()
        
        # Create simple app
        from services.app import SimpleApp
        app = SimpleApp(
            settings=settings,
            engine=engine,
            clock=clock,
            input_adapter=input_adapter,
            bus=bus
        )
        
        logger.info("Simple application created successfully")
        return app
        
    except Exception as e:
        logger.error("Failed to create simple app: %s", e)
        raise StartupError(f"Simple app creation failed: {e}") from e


def _load_simple_adapters():
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
        required_engine_methods = ['init_window', 'poll_events', 'clear', 'present', 'draw_line']
        for method in required_engine_methods:
            if not hasattr(engine, method):
                raise StartupError(f"Engine adapter missing '{method}' method")
        
        logger.info("Simple adapters loaded successfully")
        return engine, clock, input_adapter
        
    except ImportError as e:
        raise StartupError(f"Failed to import pygame adapters: {e}") from e
    except Exception as e:
        raise StartupError(f"Failed to initialize adapters: {e}") from e