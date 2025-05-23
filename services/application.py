"""
Unified Application Architecture
Eliminates ALL application duplication through unified lifecycle management.

This module consolidates patterns from app.py, database integration, and
service orchestration into a single, comprehensive application framework.
"""

import logging
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Protocol, Callable
from enum import Enum
from pathlib import Path

from .core import (
    UniversalService, ServiceConfiguration, ServiceRegistry, ServiceLifecycleManager,
    EventBus, ValidationService, StorageProvider, create_event_bus, create_memory_storage
)
from .drawing import DrawingEngine, ToolManager, RenderingBackend, create_drawing_engine, create_tool_manager

logger = logging.getLogger(__name__)


class ApplicationError(Exception):
    """Base exception for application operations."""
    pass


class ApplicationStartupError(ApplicationError):
    """Raised when application startup fails."""
    pass


class ApplicationRuntimeError(ApplicationError):
    """Raised during application runtime."""
    pass


class ApplicationState(Enum):
    """Application lifecycle states."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN = "shutdown"
    ERROR = "error"


@dataclass(frozen=True)
class ApplicationSettings:
    """Immutable application configuration."""
    # Window settings
    window_width: int = 1280
    window_height: int = 720
    window_title: str = "Unified Application"
    target_fps: int = 60
    vsync_enabled: bool = True
    
    # Drawing settings
    default_brush_size: int = 5
    default_color: Tuple[int, int, int] = (255, 255, 255)
    stroke_smoothing: bool = True
    
    # Application settings
    debug_mode: bool = False
    auto_save_interval: float = 30.0
    data_directory: Path = Path("./data")
    log_level: str = "INFO"
    
    # Performance settings
    max_undo_history: int = 100
    render_quality: str = "high"  # low, medium, high
    background_processing: bool = True


class InputEvent:
    """Universal input event container."""
    
    def __init__(self, event_type: str, data: Dict[str, Any] = None):
        self.event_type = event_type
        self.data = data or {}
        self.timestamp = time.time()
        self.handled = False
    
    def mark_handled(self):
        """Mark event as handled."""
        self.handled = True
    
    def is_handled(self) -> bool:
        """Check if event was handled."""
        return self.handled


class InputProcessor:
    """Universal input processing eliminating all input handling duplication."""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.logger = logging.getLogger(self.__class__.__name__)
        self.key_mappings: Dict[str, str] = {
            '1': 'brush',
            '2': 'eraser', 
            '3': 'line',
            '4': 'rect',
            '5': 'circle'
        }
    
    def process_input_events(self, raw_events: List[Any]) -> List[InputEvent]:
        """Process raw input events into universal format."""
        processed_events = []
        
        for raw_event in raw_events:
            try:
                processed_event = self._convert_raw_event(raw_event)
                if processed_event:
                    processed_events.append(processed_event)
            except Exception as error:
                self.logger.warning(f"Failed to process input event: {error}")
        
        return processed_events
    
    def handle_input_events(self, events: List[InputEvent]):
        """Handle processed input events."""
        for event in events:
            if event.is_handled():
                continue
            
            try:
                self._handle_specific_event(event)
            except Exception as error:
                self.logger.error(f"Error handling event {event.event_type}: {error}")
    
    def _convert_raw_event(self, raw_event: Any) -> Optional[InputEvent]:
        """Convert raw backend event to universal format."""
        if not hasattr(raw_event, 'type'):
            return None
        
        event_type = raw_event.type
        
        if event_type == 'QUIT':
            return InputEvent('application_quit')
        
        elif event_type == 'MOUSE_DOWN':
            return InputEvent('mouse_down', {
                'position': raw_event.data.get('pos', (0, 0)),
                'button': raw_event.data.get('button', 1)
            })
        
        elif event_type == 'MOUSE_UP':
            return InputEvent('mouse_up', {
                'position': raw_event.data.get('pos', (0, 0)),
                'button': raw_event.data.get('button', 1)
            })
        
        elif event_type == 'MOUSE_MOVE':
            return InputEvent('mouse_move', {
                'position': raw_event.data.get('pos', (0, 0)),
                'relative': raw_event.data.get('rel', (0, 0))
            })
        
        elif event_type == 'KEY_PRESS':
            key_name = str(raw_event.data) if raw_event.data else ''
            return InputEvent('key_press', {'key': key_name})
        
        elif event_type == 'SCROLL_WHEEL':
            return InputEvent('scroll_wheel', {
                'direction': raw_event.data.get('direction', 0),
                'position': raw_event.data.get('pos', (0, 0))
            })
        
        return None
    
    def _handle_specific_event(self, event: InputEvent):
        """Handle specific event types."""
        if event.event_type == 'application_quit':
            self.event_bus.publish('application_quit_requested')
            event.mark_handled()
        
        elif event.event_type == 'mouse_down':
            self.event_bus.publish('mouse_pressed', event.data)
            event.mark_handled()
        
        elif event.event_type == 'mouse_up':
            self.event_bus.publish('mouse_released', event.data)
            event.mark_handled()
        
        elif event.event_type == 'mouse_move':
            self.event_bus.publish('mouse_moved', event.data)
            event.mark_handled()
        
        elif event.event_type == 'key_press':
            key = event.data.get('key', '')
            
            # Handle tool shortcuts
            if key in self.key_mappings:
                self.event_bus.publish('tool_shortcut_pressed', {
                    'tool': self.key_mappings[key]
                })
                event.mark_handled()
            
            # Handle other shortcuts
            elif key == 'space':
                self.event_bus.publish('canvas_reset_requested')
                event.mark_handled()
            
            elif key in ['ctrl+z', 'cmd+z']:
                self.event_bus.publish('undo_requested')
                event.mark_handled()
            
            elif key in ['ctrl+y', 'cmd+y']:
                self.event_bus.publish('redo_requested')
                event.mark_handled()
        
        elif event.event_type == 'scroll_wheel':
            self.event_bus.publish('wheel_scrolled', event.data)
            event.mark_handled()


class RenderingOrchestrator:
    """Universal rendering coordination eliminating render duplication."""
    
    def __init__(self, drawing_engine: DrawingEngine, backend: RenderingBackend):
        self.drawing_engine = drawing_engine
        self.backend = backend
        self.logger = logging.getLogger(self.__class__.__name__)
        self.render_stats = {
            'frames_rendered': 0,
            'total_render_time': 0.0,
            'last_frame_time': 0.0
        }
    
    def render_frame(self):
        """Render complete application frame."""
        start_time = time.time()
        
        try:
            # Clear frame
            self.backend.clear()
            
            # Render drawing content
            self.drawing_engine.render_frame()
            
            # Present frame
            self.backend.present()
            
            # Update statistics
            frame_time = time.time() - start_time
            self.render_stats['frames_rendered'] += 1
            self.render_stats['total_render_time'] += frame_time
            self.render_stats['last_frame_time'] = frame_time
            
        except Exception as error:
            self.logger.error(f"Frame rendering failed: {error}")
            raise ApplicationRuntimeError(f"Rendering error: {error}")
    
    def get_render_statistics(self) -> Dict[str, Any]:
        """Get rendering performance statistics."""
        avg_frame_time = 0.0
        if self.render_stats['frames_rendered'] > 0:
            avg_frame_time = self.render_stats['total_render_time'] / self.render_stats['frames_rendered']
        
        return {
            'frames_rendered': self.render_stats['frames_rendered'],
            'average_frame_time': avg_frame_time,
            'last_frame_time': self.render_stats['last_frame_time'],
            'estimated_fps': 1.0 / avg_frame_time if avg_frame_time > 0 else 0
        }


class ApplicationStateManager:
    """Manages application state and persistence."""
    
    def __init__(self, storage: StorageProvider, event_bus: EventBus):
        self.storage = storage
        self.event_bus = event_bus
        self.logger = logging.getLogger(self.__class__.__name__)
        self.auto_save_timer = 0.0
        self.last_save_time = time.time()
    
    def save_application_state(self, components: Dict[str, Any]):
        """Save complete application state."""
        try:
            state_data = {
                'timestamp': time.time(),
                'components': components
            }
            
            self.storage.store('application_state', state_data)
            self.last_save_time = time.time()
            
            self.event_bus.publish('state_saved', {
                'timestamp': state_data['timestamp']
            })
            
            self.logger.debug("Application state saved")
            
        except Exception as error:
            self.logger.error(f"Failed to save application state: {error}")
    
    def load_application_state(self) -> Optional[Dict[str, Any]]:
        """Load application state."""
        try:
            if self.storage.exists('application_state'):
                state_data = self.storage.retrieve('application_state')
                self.logger.debug("Application state loaded")
                return state_data.get('components', {})
        except Exception as error:
            self.logger.error(f"Failed to load application state: {error}")
        
        return None
    
    def update_auto_save_timer(self, delta_time: float, auto_save_interval: float):
        """Update auto-save timer."""
        self.auto_save_timer += delta_time
        
        if self.auto_save_timer >= auto_save_interval:
            self.event_bus.publish('auto_save_requested')
            self.auto_save_timer = 0.0


class UnifiedApplication:
    """
    Complete application lifecycle management eliminating all app class duplication.
    
    Orchestrates all services, handles input, manages rendering, and provides
    unified application lifecycle with comprehensive error handling.
    """
    
    def __init__(
        self,
        settings: ApplicationSettings,
        backend: RenderingBackend,
        storage: StorageProvider = None,
        validation_service: ValidationService = None
    ):
        self.settings = settings
        self.backend = backend
        self.storage = storage or create_memory_storage("app_storage")
        self.validation_service = validation_service
        
        self.state = ApplicationState.UNINITIALIZED
        self.logger = logging.getLogger(self.__class__.__name__)
        self.running = False
        self.frame_time = 0.0
        
        # Core services
        self.event_bus = create_event_bus()
        self.service_manager = ServiceLifecycleManager()
        
        # Application components
        self.drawing_engine: Optional[DrawingEngine] = None
        self.tool_manager: Optional[ToolManager] = None
        self.input_processor: Optional[InputProcessor] = None
        self.rendering_orchestrator: Optional[RenderingOrchestrator] = None
        self.state_manager: Optional[ApplicationStateManager] = None
        
        # Performance tracking
        self.performance_stats = {
            'startup_time': 0.0,
            'total_runtime': 0.0,
            'frame_count': 0
        }
    
    def initialize(self):
        """Initialize complete application."""
        if self.state != ApplicationState.UNINITIALIZED:
            raise ApplicationStartupError(f"Cannot initialize from state: {self.state}")
        
        startup_start = time.time()
        self.state = ApplicationState.INITIALIZING
        
        try:
            self._initialize_backend()
            self._initialize_core_services()
            self._initialize_application_components()
            self._setup_event_subscriptions()
            self._start_all_services()
            
            self.state = ApplicationState.RUNNING
            
            startup_time = time.time() - startup_start
            self.performance_stats['startup_time'] = startup_time
            
            self.logger.info(f"Application initialized successfully in {startup_time:.3f}s")
            
        except Exception as error:
            self.state = ApplicationState.ERROR
            self.logger.error(f"Application initialization failed: {error}")
            raise ApplicationStartupError(f"Initialization failed: {error}") from error
    
    def run(self):
        """Run main application loop."""
        if self.state != ApplicationState.RUNNING:
            raise ApplicationRuntimeError(f"Cannot run from state: {self.state}")
        
        self.running = True
        loop_start_time = time.time()
        last_frame_time = time.time()
        target_frame_time = 1.0 / self.settings.target_fps
        
        self.logger.info("Starting main application loop")
        
        try:
            while self.running and self.state == ApplicationState.RUNNING:
                current_time = time.time()
                self.frame_time = current_time - last_frame_time
                last_frame_time = current_time
                
                # Process frame
                frame_processed = self._process_frame()
                
                if not frame_processed:
                    break
                
                # Frame rate limiting
                if self.settings.vsync_enabled:
                    elapsed = time.time() - current_time
                    if elapsed < target_frame_time:
                        time.sleep(target_frame_time - elapsed)
                
                self.performance_stats['frame_count'] += 1
            
            self.performance_stats['total_runtime'] = time.time() - loop_start_time
            self.logger.info("Application loop completed")
            
        except KeyboardInterrupt:
            self.logger.info("Application interrupted by user")
        except Exception as error:
            self.state = ApplicationState.ERROR
            self.logger.error(f"Application runtime error: {error}")
            raise ApplicationRuntimeError(f"Runtime error: {error}") from error
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Shutdown application gracefully."""
        if self.state == ApplicationState.SHUTDOWN:
            return
        
        self.state = ApplicationState.SHUTTING_DOWN
        self.running = False
        
        try:
            # Save application state
            if self.state_manager:
                components = self._gather_component_states()
                self.state_manager.save_application_state(components)
            
            # Stop all services
            self.service_manager.stop_services()
            
            # Shutdown event bus
            self.event_bus.shutdown()
            
            self.state = ApplicationState.SHUTDOWN
            self.logger.info("Application shutdown completed")
            
        except Exception as error:
            self.logger.error(f"Error during application shutdown: {error}")
    
    def _initialize_backend(self):
        """Initialize rendering backend."""
        if hasattr(self.backend, 'init_window'):
            self.backend.init_window(
                self.settings.window_width,
                self.settings.window_height,
                self.settings.window_title
            )
        
        self.logger.debug("Backend initialized")
    
    def _initialize_core_services(self):
        """Initialize core services."""
        # Create drawing engine
        self.drawing_engine = create_drawing_engine(
            backend=self.backend,
            validation_service=self.validation_service,
            event_bus=self.event_bus
        )
        self.service_manager.add_service(self.drawing_engine)
        
        # Create tool manager
        self.tool_manager = create_tool_manager(
            validation_service=self.validation_service,
            event_bus=self.event_bus
        )
        self.service_manager.add_service(self.tool_manager)
        
        self.logger.debug("Core services initialized")
    
    def _initialize_application_components(self):
        """Initialize application-specific components."""
        # Input processor
        self.input_processor = InputProcessor(self.event_bus)
        
        # Rendering orchestrator
        self.rendering_orchestrator = RenderingOrchestrator(
            self.drawing_engine, 
            self.backend
        )
        
        # State manager
        self.state_manager = ApplicationStateManager(
            self.storage,
            self.event_bus
        )
        
        # Update drawing engine screen size
        self.drawing_engine.set_screen_size(
            self.settings.window_width,
            self.settings.window_height
        )
        
        self.logger.debug("Application components initialized")
    
    def _setup_event_subscriptions(self):
        """Setup event subscriptions."""
        self.event_bus.subscribe('application_quit_requested', self._handle_quit_request)
        self.event_bus.subscribe('auto_save_requested', self._handle_auto_save)
        self.event_bus.subscribe('tool_shortcut_pressed', self._handle_tool_shortcut)
        self.event_bus.subscribe('mouse_pressed', self._handle_mouse_press)
        self.event_bus.subscribe('mouse_released', self._handle_mouse_release)
        self.event_bus.subscribe('mouse_moved', self._handle_mouse_move)
        
        self.logger.debug("Event subscriptions setup")
    
    def _start_all_services(self):
        """Start all registered services."""
        self.service_manager.start_services()
        self.logger.debug("All services started")
    
    def _process_frame(self) -> bool:
        """Process single application frame."""
        try:
            # Poll input events
            raw_events = []
            if hasattr(self.backend, 'poll_events'):
                raw_events = self.backend.poll_events()
            
            # Process input
            if self.input_processor:
                processed_events = self.input_processor.process_input_events(raw_events)
                self.input_processor.handle_input_events(processed_events)
            
            # Update auto-save timer
            if self.state_manager:
                self.state_manager.update_auto_save_timer(
                    self.frame_time,
                    self.settings.auto_save_interval
                )
            
            # Render frame
            if self.rendering_orchestrator:
                self.rendering_orchestrator.render_frame()
            
            return True
            
        except Exception as error:
            self.logger.error(f"Frame processing error: {error}")
            return False
    
    def _gather_component_states(self) -> Dict[str, Any]:
        """Gather state from all components."""
        states = {}
        
        try:
            if self.tool_manager:
                states['tool_manager'] = {
                    'current_tool': self.tool_manager.current_state.tool_type.value,
                    'brush_size': self.tool_manager.current_state.brush_width,
                    'color': self.tool_manager.current_state.color
                }
            
            if self.drawing_engine:
                states['drawing_engine'] = {
                    'viewport_offset': (
                        self.drawing_engine.coordinate_system.viewport.offset_x,
                        self.drawing_engine.coordinate_system.viewport.offset_y
                    ),
                    'viewport_scale': self.drawing_engine.coordinate_system.viewport.scale
                }
            
            states['application'] = {
                'performance_stats': self.performance_stats
            }
            
        except Exception as error:
            self.logger.error(f"Error gathering component states: {error}")
        
        return states
    
    def _handle_quit_request(self, data: Any):
        """Handle application quit request."""
        self.logger.info("Quit request received")
        self.running = False
    
    def _handle_auto_save(self, data: Any):
        """Handle auto-save request."""
        components = self._gather_component_states()
        self.state_manager.save_application_state(components)
    
    def _handle_tool_shortcut(self, data: Dict[str, Any]):
        """Handle tool shortcut press."""
        tool_name = data.get('tool')
        if tool_name and self.tool_manager:
            self.event_bus.publish('tool_changed', {'tool_type': tool_name})
    
    def _handle_mouse_press(self, data: Dict[str, Any]):
        """Handle mouse press event."""
        position = data.get('position', (0, 0))
        button = data.get('button', 1)
        
        if button == 1 and self.tool_manager:  # Left click
            self.tool_manager.start_tool_operation(position)
    
    def _handle_mouse_release(self, data: Dict[str, Any]):
        """Handle mouse release event."""
        position = data.get('position', (0, 0))
        button = data.get('button', 1)
        
        if button == 1 and self.tool_manager:  # Left click
            self.tool_manager.finish_tool_operation(position)
    
    def _handle_mouse_move(self, data: Dict[str, Any]):
        """Handle mouse move event."""
        position = data.get('position', (0, 0))
        
        if self.tool_manager and self.tool_manager.active_operation:
            self.tool_manager.update_tool_operation(position)


# Legacy compatibility wrapper
class SimpleApp:
    """Legacy compatibility wrapper for existing code."""
    
    def __init__(self, settings, engine, clock, input_adapter, bus):
        self.settings = settings
        self.engine = engine
        self.clock = clock
        self.input_adapter = input_adapter
        self.bus = bus
        
        # Create unified application
        app_settings = ApplicationSettings(
            window_width=settings.WIDTH,
            window_height=settings.HEIGHT,
            window_title=settings.TITLE,
            target_fps=settings.FPS,
            debug_mode=settings.DEBUG
        )
        
        self.unified_app = UnifiedApplication(
            settings=app_settings,
            backend=engine
        )
    
    def run(self):
        """Run legacy application."""
        self.unified_app.initialize()
        self.unified_app.run()


class SimpleApplicationFactory:
    """Factory for creating simple applications."""
    
    @staticmethod
    def create_from_settings(settings) -> SimpleApp:
        """Create simple app from legacy settings."""
        # This would integrate with existing bootstrap code
        # For now, return placeholder
        return None


# Factory functions
def create_application(
    settings: ApplicationSettings,
    backend: RenderingBackend,
    storage: StorageProvider = None,
    validation_service: ValidationService = None
) -> UnifiedApplication:
    """Create unified application with standard configuration."""
    return UnifiedApplication(
        settings=settings,
        backend=backend,
        storage=storage,
        validation_service=validation_service
    )


def create_production_application(
    backend: RenderingBackend,
    **settings_overrides
) -> UnifiedApplication:
    """Create production-ready application."""
    settings = ApplicationSettings(**settings_overrides)
    
    return create_application(
        settings=settings,
        backend=backend,
        storage=create_memory_storage("production_storage")
    )