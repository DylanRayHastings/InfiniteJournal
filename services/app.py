"""
services/app.py - Compatibility Bridge
=====================================

This module provides backward compatibility for existing code that imports
from 'services.app'. It bridges the old App class to the new Universal Services Framework.

This allows gradual migration without breaking existing bootstrap code.
"""

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class App:
    """
    Legacy App class compatibility bridge.
    
    This wraps the new Universal Services Framework to provide the same
    interface as the old App class, allowing existing bootstrap code to work.
    """
    
    def __init__(
        self,
        settings,
        engine,
        clock,
        input_adapter,
        journal_service=None,
        tool_service=None,
        undo_service=None,
        repository=None,
        exporter=None,
        widgets=None,
        bus=None,
        **kwargs
    ):
        """Initialize legacy App with compatibility for old constructor."""
        self.settings = settings
        self.engine = engine
        self.clock = clock
        self.input_adapter = input_adapter
        self.journal_service = journal_service
        self.tool_service = tool_service
        self.undo_service = undo_service
        self.repository = repository
        self.exporter = exporter
        self.widgets = widgets or []
        self.bus = bus
        
        # Legacy state
        self.running = False
        self.frame_count = 0
        self.start_time = None
        
        # Try to create Universal Services application as backend
        self._unified_app = None
        try:
            from services import (
                create_complete_application,
                ApplicationSettings,
                integrate_with_existing_backend
            )
            
            # Convert settings to new format
            app_settings = ApplicationSettings(
                window_width=getattr(settings, 'WIDTH', 1280),
                window_height=getattr(settings, 'HEIGHT', 720),
                window_title=getattr(settings, 'TITLE', 'InfiniteJournal'),
                target_fps=getattr(settings, 'FPS', 60),
                debug_mode=getattr(settings, 'DEBUG', False)
            )
            
            # Integrate with existing backend
            adapted_backend = integrate_with_existing_backend(engine)
            
            # Create unified app as backend
            self._unified_app = create_complete_application(
                backend=adapted_backend,
                window_width=app_settings.window_width,
                window_height=app_settings.window_height,
                window_title=app_settings.window_title,
                target_fps=app_settings.target_fps,
                debug_mode=app_settings.debug_mode
            )
            
            logger.info("Created Universal Services backend for legacy app")
            
        except Exception as error:
            logger.warning(f"Could not create Universal Services backend: {error}")
            logger.info("Running in pure legacy compatibility mode")
        
        logger.info("Legacy App initialized with compatibility bridge")
    
    def run(self):
        """Run the application with legacy interface."""
        if self._unified_app:
            return self._run_with_universal_services()
        else:
            return self._run_legacy_mode()
    
    def _run_with_universal_services(self):
        """Run using Universal Services Framework backend."""
        try:
            logger.info("Running with Universal Services Framework backend")
            
            # Initialize and run unified app
            self._unified_app.initialize()
            self._unified_app.run()
            
        except Exception as error:
            logger.error(f"Universal Services execution failed: {error}")
            # Fallback to legacy mode
            logger.info("Falling back to legacy mode")
            return self._run_legacy_mode()
    
    def _run_legacy_mode(self):
        """Run in pure legacy compatibility mode."""
        logger.info("Running in legacy compatibility mode")
        
        self.running = True
        self.start_time = time.time()
        target_frame_time = 1.0 / getattr(self.settings, 'FPS', 60)
        
        try:
            # Initialize window
            if hasattr(self.engine, 'init_window'):
                self.engine.init_window(
                    getattr(self.settings, 'WIDTH', 1280),
                    getattr(self.settings, 'HEIGHT', 720),
                    getattr(self.settings, 'TITLE', 'InfiniteJournal')
                )
            elif hasattr(self.engine, 'open_window'):
                self.engine.open_window(
                    getattr(self.settings, 'WIDTH', 1280),
                    getattr(self.settings, 'HEIGHT', 720),
                    getattr(self.settings, 'TITLE', 'InfiniteJournal')
                )
            
            # Main loop
            while self.running:
                frame_start = time.time()
                
                # Process frame
                if not self._process_legacy_frame():
                    break
                
                # Frame rate limiting
                frame_time = time.time() - frame_start
                if frame_time < target_frame_time:
                    time.sleep(target_frame_time - frame_time)
                
                self.frame_count += 1
            
            logger.info(f"Legacy app completed after {self.frame_count} frames")
            
        except KeyboardInterrupt:
            logger.info("Legacy app interrupted by user")
        except Exception as error:
            logger.error(f"Legacy app error: {error}")
            raise
    
    def _process_legacy_frame(self) -> bool:
        """Process single frame in legacy mode."""
        try:
            # Poll events
            events = []
            if hasattr(self.engine, 'poll_events'):
                events = self.engine.poll_events()
            
            # Process events
            for event in events:
                if hasattr(event, 'type'):
                    if event.type == 'QUIT':
                        self.running = False
                        return False
                    
                    # Handle other events through services if available
                    if self.tool_service and event.type in ['MOUSE_DOWN', 'MOUSE_UP', 'MOUSE_MOVE']:
                        self._handle_tool_event(event)
            
            # Clear screen
            if hasattr(self.engine, 'clear'):
                self.engine.clear()
            
            # Render widgets
            for widget in self.widgets:
                try:
                    if hasattr(widget, 'render'):
                        widget.render()
                except Exception as error:
                    logger.warning(f"Widget rendering error: {error}")
            
            # Present frame
            if hasattr(self.engine, 'present'):
                self.engine.present()
            
            return True
            
        except Exception as error:
            logger.error(f"Frame processing error: {error}")
            return False
    
    def _handle_tool_event(self, event):
        """Handle tool-related events."""
        try:
            if not self.tool_service:
                return
            
            event_data = getattr(event, 'data', {})
            
            if event.type == 'MOUSE_DOWN':
                position = event_data.get('pos', (0, 0))
                if hasattr(self.tool_service, 'start_tool_operation'):
                    # New interface
                    self.tool_service.start_tool_operation(position)
                elif self.journal_service and hasattr(self.journal_service, 'start_stroke'):
                    # Legacy interface
                    color = getattr(self.tool_service, 'current_color', (255, 255, 255))
                    width = getattr(self.tool_service, 'brush_width', 5)
                    self.journal_service.start_stroke(position, color, width)
            
            elif event.type == 'MOUSE_UP':
                position = event_data.get('pos', (0, 0))
                if hasattr(self.tool_service, 'finish_tool_operation'):
                    # New interface
                    self.tool_service.finish_tool_operation(position)
                elif self.journal_service and hasattr(self.journal_service, 'finish_stroke'):
                    # Legacy interface
                    self.journal_service.finish_stroke()
            
            elif event.type == 'MOUSE_MOVE':
                position = event_data.get('pos', (0, 0))
                if hasattr(self.tool_service, 'update_tool_operation'):
                    # New interface
                    self.tool_service.update_tool_operation(position)
                elif self.journal_service and hasattr(self.journal_service, 'add_stroke_point'):
                    # Legacy interface
                    self.journal_service.add_stroke_point(position)
                    
        except Exception as error:
            logger.warning(f"Tool event handling error: {error}")


class SimpleApp:
    """
    Simple app compatibility for bootstrap/factory.py create_simple_app().
    
    This provides the SimpleApp interface expected by the factory.
    """
    
    def __init__(self, settings, engine, clock, input_adapter, bus):
        """Initialize simple app."""
        self.settings = settings
        self.engine = engine
        self.clock = clock
        self.input_adapter = input_adapter
        self.bus = bus
        
        # Create legacy App wrapper
        self.app = App(
            settings=settings,
            engine=engine,
            clock=clock,
            input_adapter=input_adapter,
            bus=bus
        )
        
        logger.info("SimpleApp initialized with legacy compatibility")
    
    def run(self):
        """Run simple app."""
        return self.app.run()


# Provide the imports that bootstrap/factory.py expects
__all__ = ['App', 'SimpleApp']