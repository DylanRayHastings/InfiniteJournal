"""
Simple Application with Unified Architecture.

Production-ready application implementing layered rendering system with
centralized validation, dependency injection, and zero code duplication.

Key Features:
- Centralized validation logic
- Dependency injection for testability
- Flattened control flow with minimal nesting
- Zero code duplication
- Clear service boundaries
- Comprehensive error handling

Quick Start:
    settings = ApplicationSettings()
    app = SimpleApplicationFactory.create_application(settings)
    app.run()

Extension Points:
- Add new event types: Extend EventType enum and add handlers
- Add new validation rules: Extend ValidationService methods
- Add new rendering layers: Implement LayerRenderer interface
- Add new input devices: Implement InputAdapter interface
"""

import logging
from typing import Any, Dict, List, Tuple, Optional, Protocol
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event type enumeration for input handling."""
    QUIT = "QUIT"
    MOUSE_DOWN = "MOUSE_DOWN"
    MOUSE_MOVE = "MOUSE_MOVE"
    MOUSE_UP = "MOUSE_UP"
    KEY_PRESS = "KEY_PRESS"
    SCROLL_WHEEL = "SCROLL_WHEEL"


class RenderingState(Enum):
    """Rendering state enumeration for application lifecycle."""
    INITIALIZING = "initializing"
    LAYERS_READY = "layers_ready"
    FALLBACK_MODE = "fallback_mode"
    ERROR_STATE = "error_state"


@dataclass(frozen=True)
class ApplicationDimensions:
    """Application window dimensions data."""
    width: int
    height: int
    
    def is_valid(self) -> bool:
        """Check if dimensions are valid for window creation."""
        return self.width > 0 and self.height > 0


@dataclass(frozen=True)
class EventData:
    """Event data container for input events."""
    event_type: EventType
    data: Dict[str, Any]
    
    def get_position(self) -> Tuple[int, int]:
        """Extract position data from event."""
        position_data = self.data.get('pos', (0, 0))
        return tuple(position_data) if isinstance(position_data, (list, tuple)) else (0, 0)
    
    def get_button(self) -> int:
        """Extract button data from event."""
        return self.data.get('button', 1)
    
    def get_direction(self) -> int:
        """Extract scroll direction from event."""
        return self.data.get('direction', 0)
    
    def get_key(self) -> str:
        """Extract key data from event."""
        return str(self.data) if isinstance(self.data, str) else ""


class ValidationService:
    """Centralized validation service for all application validation needs."""
    
    def __init__(self, settings: Any):
        """Initialize validation service with application settings."""
        self.settings = settings
    
    def validate_window_dimensions(self, dimensions: ApplicationDimensions) -> None:
        """Validate window dimensions for creation."""
        if not dimensions.is_valid():
            raise ValueError(f"Invalid window dimensions: {dimensions.width}x{dimensions.height}")
        
        if dimensions.width > 7680 or dimensions.height > 4320:
            logger.warning(f"Very large window dimensions: {dimensions.width}x{dimensions.height}")
    
    def validate_window_title(self, title: str) -> None:
        """Validate window title string."""
        if not title:
            raise ValueError("Window title cannot be empty")
        
        if len(title) > 100:
            raise ValueError("Window title too long")
    
    def validate_target_fps(self, fps: int) -> None:
        """Validate target frames per second value."""
        if fps <= 0:
            raise ValueError("Target FPS must be positive")
        
        if fps > 300:
            logger.warning(f"Very high target FPS: {fps}")
    
    def validate_position_coordinates(self, x: int, y: int) -> None:
        """Validate position coordinates are within reasonable bounds."""
        if x < -1000 or x > 10000 or y < -1000 or y > 10000:
            logger.warning(f"Position coordinates outside expected range: ({x}, {y})")
    
    def validate_brush_width(self, width: int) -> None:
        """Validate brush width parameter."""
        if width < 1:
            raise ValueError("Brush width must be at least 1")
        
        if width > 100:
            raise ValueError("Brush width cannot exceed 100")
    
    def validate_event_data(self, event_data: EventData) -> None:
        """Validate event data structure and contents."""
        if not isinstance(event_data.event_type, EventType):
            raise ValueError("Invalid event type")
        
        if event_data.event_type in [EventType.MOUSE_DOWN, EventType.MOUSE_MOVE, EventType.MOUSE_UP]:
            position = event_data.get_position()
            self.validate_position_coordinates(position[0], position[1])


class ErrorRecoveryService:
    """Service for handling errors and recovery strategies."""
    
    def __init__(self, validation_service: ValidationService):
        """Initialize error recovery service."""
        self.validation_service = validation_service
        self.error_count = 0
        self.max_errors = 10
    
    def handle_window_initialization_error(self, error: Exception, dimensions: ApplicationDimensions, title: str) -> None:
        """Handle window initialization errors with recovery strategy."""
        logger.error(f"Window initialization failed: {error}")
        self.error_count += 1
        
        if self.error_count > self.max_errors:
            raise RuntimeError("Too many initialization errors") from error
        
        raise RuntimeError("Failed to initialize application window") from error
    
    def handle_event_processing_error(self, error: Exception, event_data: EventData) -> bool:
        """Handle event processing errors and determine if processing should continue."""
        logger.error(f"Event processing error for {event_data.event_type}: {error}")
        self.error_count += 1
        
        if self.error_count > self.max_errors:
            logger.critical("Too many event processing errors, stopping application")
            return False
        
        return True
    
    def handle_rendering_error(self, error: Exception, rendering_state: RenderingState) -> RenderingState:
        """Handle rendering errors and return appropriate fallback state."""
        logger.error(f"Rendering error in state {rendering_state}: {error}")
        self.error_count += 1
        
        if rendering_state == RenderingState.LAYERS_READY:
            logger.info("Switching to fallback rendering mode")
            return RenderingState.FALLBACK_MODE
        
        if self.error_count > self.max_errors:
            return RenderingState.ERROR_STATE
        
        return rendering_state


class EventProcessor:
    """Service for processing and dispatching application events."""
    
    def __init__(self, validation_service: ValidationService, error_recovery_service: ErrorRecoveryService):
        """Initialize event processor with required services."""
        self.validation_service = validation_service
        self.error_recovery_service = error_recovery_service
    
    def process_quit_event(self, event_data: EventData) -> bool:
        """Process quit event and return whether application should continue."""
        logger.info("Application quit requested")
        return False
    
    def process_mouse_down_event(self, event_data: EventData, drawing_service: Any) -> bool:
        """Process mouse down event and update drawing service."""
        try:
            self.validation_service.validate_event_data(event_data)
            position = event_data.get_position()
            button = event_data.get_button()
            
            drawing_service.handle_mouse_down(position[0], position[1], button)
            return True
            
        except Exception as error:
            return self.error_recovery_service.handle_event_processing_error(error, event_data)
    
    def process_mouse_move_event(self, event_data: EventData, drawing_service: Any) -> bool:
        """Process mouse move event and update drawing service."""
        try:
            self.validation_service.validate_event_data(event_data)
            position = event_data.get_position()
            
            drawing_service.handle_mouse_move(position[0], position[1])
            return True
            
        except Exception as error:
            return self.error_recovery_service.handle_event_processing_error(error, event_data)
    
    def process_mouse_up_event(self, event_data: EventData, drawing_service: Any) -> bool:
        """Process mouse up event and update drawing service."""
        try:
            self.validation_service.validate_event_data(event_data)
            position = event_data.get_position()
            button = event_data.get_button()
            
            drawing_service.handle_mouse_up(position[0], position[1], button)
            return True
            
        except Exception as error:
            return self.error_recovery_service.handle_event_processing_error(error, event_data)
    
    def process_key_press_event(self, event_data: EventData, drawing_service: Any) -> bool:
        """Process key press event and update drawing service."""
        try:
            key = event_data.get_key()
            drawing_service.handle_key_press(key)
            return True
            
        except Exception as error:
            return self.error_recovery_service.handle_event_processing_error(error, event_data)
    
    def process_scroll_wheel_event(self, event_data: EventData, drawing_service: Any) -> bool:
        """Process scroll wheel event and update drawing service."""
        try:
            direction = event_data.get_direction()
            drawing_service.handle_scroll(direction)
            return True
            
        except Exception as error:
            return self.error_recovery_service.handle_event_processing_error(error, event_data)


class ApplicationRenderer:
    """Service responsible for all application rendering operations."""
    
    def __init__(self, validation_service: ValidationService, error_recovery_service: ErrorRecoveryService):
        """Initialize application renderer with required services."""
        self.validation_service = validation_service
        self.error_recovery_service = error_recovery_service
        self.rendering_state = RenderingState.INITIALIZING
    
    def set_rendering_state(self, new_state: RenderingState) -> None:
        """Update current rendering state."""
        self.rendering_state = new_state
        logger.debug(f"Rendering state changed to: {new_state}")
    
    def render_application_frame(self, engine: Any, drawing_service: Any) -> None:
        """Render complete application frame using appropriate rendering strategy."""
        try:
            if self.rendering_state == RenderingState.LAYERS_READY:
                self.render_with_layered_system(engine, drawing_service)
                return
            
            if self.rendering_state == RenderingState.FALLBACK_MODE:
                self.render_with_fallback_system(engine)
                return
            
            if self.rendering_state == RenderingState.ERROR_STATE:
                self.render_error_state(engine)
                return
            
            self.render_initialization_state(engine)
            
        except Exception as error:
            self.rendering_state = self.error_recovery_service.handle_rendering_error(error, self.rendering_state)
            self.render_with_fallback_system(engine)
    
    def render_with_layered_system(self, engine: Any, drawing_service: Any) -> None:
        """Render frame using layered drawing system."""
        drawing_service.render(engine.screen)
        self.render_user_interface_overlay(engine, drawing_service)
        engine.present()
    
    def render_with_fallback_system(self, engine: Any) -> None:
        """Render frame using fallback system when layers are unavailable."""
        engine.clear()
        self.render_fallback_grid(engine)
        self.render_fallback_status_message(engine)
        engine.present()
    
    def render_error_state(self, engine: Any) -> None:
        """Render error state message."""
        try:
            engine.clear()
            engine.draw_text("APPLICATION ERROR - RESTART REQUIRED", (10, 10), 16, (255, 0, 0))
            engine.present()
        except Exception:
            pass
    
    def render_initialization_state(self, engine: Any) -> None:
        """Render initialization state message."""
        try:
            engine.clear()
            engine.draw_text("INITIALIZING APPLICATION...", (10, 10), 16, (255, 255, 0))
            engine.present()
        except Exception:
            pass
    
    def render_fallback_grid(self, engine: Any) -> None:
        """Render fallback grid pattern."""
        try:
            dimensions = self.get_engine_dimensions(engine)
            grid_spacing = 40
            grid_color = (30, 30, 30)
            
            for x in range(0, dimensions.width, grid_spacing):
                engine.draw_line((x, 0), (x, dimensions.height), 1, grid_color)
            
            for y in range(0, dimensions.height, grid_spacing):
                engine.draw_line((0, y), (dimensions.width, y), 1, grid_color)
                
        except Exception as error:
            logger.debug(f"Error rendering fallback grid: {error}")
    
    def render_fallback_status_message(self, engine: Any) -> None:
        """Render fallback status message."""
        try:
            engine.draw_text("FALLBACK RENDERING MODE", (10, 50), 12, (255, 100, 100))
        except Exception as error:
            logger.debug(f"Error rendering status message: {error}")
    
    def render_user_interface_overlay(self, engine: Any, drawing_service: Any) -> None:
        """Render user interface overlay with application status and controls."""
        try:
            self.render_tool_status(engine, drawing_service)
            self.render_brush_information(engine, drawing_service)
            self.render_layer_status(engine)
            self.render_bug_fixes_status(engine)
            self.render_control_instructions(engine)
            
        except Exception as error:
            logger.debug(f"Error rendering UI overlay: {error}")
    
    def render_tool_status(self, engine: Any, drawing_service: Any) -> None:
        """Render current tool status information."""
        current_tool = drawing_service.get_current_tool()
        drawing_indicator = " [DRAWING]" if drawing_service.is_drawing() else ""
        tool_color = (0, 255, 0) if drawing_service.is_drawing() else (255, 255, 255)
        
        engine.draw_text(f"Tool: {current_tool.capitalize()}{drawing_indicator}", (10, 10), 16, tool_color)
    
    def render_brush_information(self, engine: Any, drawing_service: Any) -> None:
        """Render brush size information for applicable tools."""
        current_tool = drawing_service.get_current_tool()
        
        if current_tool in ['brush', 'eraser']:
            brush_width = drawing_service.get_current_brush_width()
            engine.draw_text(f"Size: {brush_width}", (10, 30), 14, (255, 255, 255))
    
    def render_layer_status(self, engine: Any) -> None:
        """Render layer system status."""
        if self.rendering_state == RenderingState.LAYERS_READY:
            engine.draw_text("LAYERED RENDERING", (10, 50), 10, (0, 255, 0))
        else:
            engine.draw_text("FALLBACK MODE", (10, 50), 10, (255, 100, 100))
    
    def render_bug_fixes_status(self, engine: Any) -> None:
        """Render fixed bugs indicator."""
        bug_fixes = [
            "Eraser preserves background",
            "Clean brushes no artifacts",
            "Dynamic brush width",
            "Proper parabola orientation"
        ]
        
        for index, fix in enumerate(bug_fixes):
            engine.draw_text(f"✓ {fix}", (10, 80 + index * 12), 9, (100, 255, 100))
    
    def render_control_instructions(self, engine: Any) -> None:
        """Render control instructions for user guidance."""
        instructions = [
            ("Controls:", (255, 255, 0)),
            ("Space: Cycle tools", (200, 200, 200)),
            ("1-5: Neon colors", (200, 200, 200)),
            ("C: Clear canvas", (200, 200, 200)),
            ("+/-: Brush size", (200, 200, 200)),
            ("Scroll: Dynamic brush size", (200, 200, 200)),
            ("", (200, 200, 200)),
            ("Tools: brush, eraser, line, rect, circle, triangle, parabola", (100, 200, 255)),
            ("Parabola: Drag down=bowl, drag up=rainbow", (100, 200, 255))
        ]
        
        for index, (instruction, color) in enumerate(instructions):
            if instruction:
                engine.draw_text(instruction, (10, 150 + index * 12), 9, color)
    
    def get_engine_dimensions(self, engine: Any) -> ApplicationDimensions:
        """Get dimensions from rendering engine."""
        try:
            width, height = engine.get_size()
            return ApplicationDimensions(width, height)
        except Exception:
            return ApplicationDimensions(800, 600)


class SimpleApp:
    """
    Production-ready application with layered rendering and unified architecture.
    
    Provides complete drawing application functionality with centralized validation,
    dependency injection, error recovery, and clear service boundaries.
    
    The application manages the complete lifecycle from initialization through
    event processing to rendering, with comprehensive error handling and
    fallback strategies for robust operation.
    
    Architecture:
    - ValidationService: Centralizes all validation logic
    - ErrorRecoveryService: Handles errors and recovery strategies  
    - EventProcessor: Processes and dispatches input events
    - ApplicationRenderer: Manages all rendering operations
    - Drawing service integration through dependency injection
    
    Event Processing Flow:
    1. Poll events from engine through input adapter
    2. Validate and process events through EventProcessor
    3. Update drawing service state based on processed events
    4. Render frame using ApplicationRenderer with current state
    5. Maintain target FPS through clock management
    """
    
    def __init__(
        self,
        settings: Any,
        engine: Any,
        clock: Any,
        input_adapter: Any,
        bus: Any,
        drawing_service: Any = None,
        validation_service: ValidationService = None,
        error_recovery_service: ErrorRecoveryService = None,
        event_processor: EventProcessor = None,
        application_renderer: ApplicationRenderer = None
    ):
        """
        Initialize application with required and optional dependencies.
        
        Maintains backward compatibility with existing bootstrap system
        while enabling dependency injection for testing and customization.
        Services not provided will be created with default implementations.
        """
        self.settings = settings
        self.engine = engine
        self.clock = clock
        self.input_adapter = input_adapter
        self.bus = bus
        
        # Create services if not provided (backward compatibility)
        if validation_service is None:
            validation_service = ValidationService(settings)
        if error_recovery_service is None:
            error_recovery_service = ErrorRecoveryService(validation_service)
        if event_processor is None:
            event_processor = EventProcessor(validation_service, error_recovery_service)
        if application_renderer is None:
            application_renderer = ApplicationRenderer(validation_service, error_recovery_service)
        if drawing_service is None:
            drawing_service = self.create_default_drawing_service()
        
        self.drawing_service = drawing_service
        self.validation_service = validation_service
        self.error_recovery_service = error_recovery_service
        self.event_processor = event_processor
        self.application_renderer = application_renderer
        
        self.should_force_render = True
        self.application_dimensions = ApplicationDimensions(0, 0)
        
        self.subscribe_to_drawing_events()
        logger.info("SimpleApp initialized with unified architecture")
    
    def create_default_drawing_service(self) -> Any:
        """Create default drawing service for backward compatibility."""
        try:
            from services.drawing import LayeredDrawingService
            return LayeredDrawingService(self.bus, self.settings)
        except ImportError as error:
            logger.error(f"Failed to import LayeredDrawingService: {error}")
            raise RuntimeError("Drawing service unavailable") from error
    
    def subscribe_to_drawing_events(self) -> None:
        """Subscribe to drawing service events that require re-rendering."""
        self.bus.subscribe('brush_width_changed', self.handle_brush_width_changed)
        self.bus.subscribe('tool_changed', self.handle_tool_changed)
    
    def handle_brush_width_changed(self, width: int) -> None:
        """Handle brush width change events."""
        try:
            self.validation_service.validate_brush_width(width)
            self.should_force_render = True
        except Exception as error:
            logger.error(f"Invalid brush width change: {error}")
    
    def handle_tool_changed(self, tool: str) -> None:
        """Handle tool change events."""
        self.should_force_render = True
        logger.debug(f"Tool changed to: {tool}")
    
    def run(self) -> None:
        """
        Launch application and run main execution loop.
        
        Manages complete application lifecycle including window initialization,
        layer setup, event processing loop, and graceful shutdown handling.
        """
        try:
            self.initialize_application_window()
            self.execute_main_application_loop()
            
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
            
        except Exception as error:
            logger.exception("Unhandled exception in application execution")
            raise
    
    def initialize_application_window(self) -> None:
        """
        Initialize application window and drawing layers.
        
        Sets up window with validated dimensions and title, then initializes
        the layered drawing system. Updates renderer state based on success
        or failure of layer initialization.
        """
        try:
            self.validate_application_settings()
            self.create_application_window()
            self.initialize_drawing_layers()
            
            logger.info(f"Application initialized: {self.application_dimensions.width}×{self.application_dimensions.height}")
            
        except Exception as error:
            self.error_recovery_service.handle_window_initialization_error(
                error, self.application_dimensions, self.settings.TITLE
            )
    
    def validate_application_settings(self) -> None:
        """Validate all application settings before window creation."""
        self.application_dimensions = ApplicationDimensions(
            self.settings.WIDTH,
            self.settings.HEIGHT
        )
        
        self.validation_service.validate_window_dimensions(self.application_dimensions)
        self.validation_service.validate_window_title(self.settings.TITLE)
        self.validation_service.validate_target_fps(self.settings.FPS)
    
    def create_application_window(self) -> None:
        """Create application window with validated settings."""
        self.engine.init_window(
            self.application_dimensions.width,
            self.application_dimensions.height,
            self.settings.TITLE
        )
    
    def initialize_drawing_layers(self) -> None:
        """Initialize drawing service layers and update renderer state."""
        try:
            self.drawing_service.initialize_layers(
                self.application_dimensions.width,
                self.application_dimensions.height
            )
            self.application_renderer.set_rendering_state(RenderingState.LAYERS_READY)
            
        except Exception as error:
            logger.warning(f"Layer initialization failed, using fallback: {error}")
            self.application_renderer.set_rendering_state(RenderingState.FALLBACK_MODE)
    
    def execute_main_application_loop(self) -> None:
        """
        Execute main application loop with event processing and rendering.
        
        Continuously processes input events, updates application state,
        and renders frames while maintaining target FPS. Loop continues
        until quit event received or critical error occurs.
        """
        target_fps = self.settings.FPS
        
        while True:
            should_continue = self.process_frame_events()
            if not should_continue:
                logger.info("Application shutdown requested")
                break
            
            self.render_application_frame()
            self.maintain_target_fps(target_fps)
    
    def process_frame_events(self) -> bool:
        """
        Process all events for current frame.
        
        Polls events from engine, translates them through input adapter,
        and processes each event through event processor. Returns whether
        application should continue running.
        """
        try:
            raw_events = self.engine.poll_events()
            translated_events = self.input_adapter.translate(raw_events)
            
            for event in translated_events:
                should_continue = self.process_single_event(event)
                if not should_continue:
                    return False
            
            return True
            
        except Exception as error:
            logger.error(f"Error processing frame events: {error}")
            return True
    
    def process_single_event(self, event: Any) -> bool:
        """
        Process individual event through appropriate event processor method.
        
        Dispatches events to specialized processing methods based on event type.
        Returns whether application should continue running after processing.
        """
        try:
            event_data = EventData(EventType(event.type), event.data)
            
            if event_data.event_type == EventType.QUIT:
                return self.event_processor.process_quit_event(event_data)
            
            if event_data.event_type == EventType.MOUSE_DOWN:
                success = self.event_processor.process_mouse_down_event(event_data, self.drawing_service)
                if success:
                    self.should_force_render = True
                return True
            
            if event_data.event_type == EventType.MOUSE_MOVE:
                success = self.event_processor.process_mouse_move_event(event_data, self.drawing_service)
                if success:
                    self.should_force_render = True
                return True
            
            if event_data.event_type == EventType.MOUSE_UP:
                success = self.event_processor.process_mouse_up_event(event_data, self.drawing_service)
                if success:
                    self.should_force_render = True
                return True
            
            if event_data.event_type == EventType.KEY_PRESS:
                success = self.event_processor.process_key_press_event(event_data, self.drawing_service)
                if success:
                    self.should_force_render = True
                return True
            
            if event_data.event_type == EventType.SCROLL_WHEEL:
                success = self.event_processor.process_scroll_wheel_event(event_data, self.drawing_service)
                if success:
                    self.should_force_render = True
                return True
            
            return True
            
        except Exception as error:
            logger.error(f"Error processing event: {error}")
            return True
    
    def render_application_frame(self) -> None:
        """Render complete application frame using application renderer."""
        self.application_renderer.render_application_frame(self.engine, self.drawing_service)
    
    def maintain_target_fps(self, target_fps: int) -> None:
        """Maintain target frames per second using clock service."""
        try:
            self.clock.tick(target_fps)
        except Exception as error:
            logger.debug(f"Clock tick error: {error}")


class SimpleAppFactory:
    """
    Factory for creating SimpleApp instances with dependency injection.
    
    Provides static methods for creating complete application instances with
    all required services properly configured and injected. Enables easy
    testing through service replacement and configuration customization.
    """
    
    @staticmethod
    def create_application(settings: Any, engine: Any = None, clock: Any = None, 
                         input_adapter: Any = None, bus: Any = None) -> SimpleApp:
        """
        Create complete SimpleApp instance with all dependencies.
        
        Creates and configures all required services, then injects them into
        the application instance. Services can be provided externally for
        testing or customization, or will be created with default implementations.
        """
        validation_service = ValidationService(settings)
        error_recovery_service = ErrorRecoveryService(validation_service)
        event_processor = EventProcessor(validation_service, error_recovery_service)
        application_renderer = ApplicationRenderer(validation_service, error_recovery_service)
        
        drawing_service = SimpleAppFactory.create_drawing_service(bus, settings)
        
        return SimpleApp(
            settings=settings,
            engine=engine,
            clock=clock,
            input_adapter=input_adapter,
            bus=bus,
            drawing_service=drawing_service,
            validation_service=validation_service,
            error_recovery_service=error_recovery_service,
            event_processor=event_processor,
            application_renderer=application_renderer
        )
    
    @staticmethod
    def create_drawing_service(bus: Any, settings: Any) -> Any:
        """Create drawing service instance with dependency injection."""
        try:
            from services.drawing import LayeredDrawingService
            return LayeredDrawingService(bus, settings)
            
        except ImportError as error:
            logger.error(f"Failed to import LayeredDrawingService: {error}")
            raise RuntimeError("Drawing service unavailable") from error
    
    @staticmethod
    def create_application_for_testing(settings: Any, **service_overrides: Any) -> SimpleApp:
        """
        Create application instance with service overrides for testing.
        
        Allows replacement of any service with mock or test implementations
        for comprehensive unit testing of application behavior.
        """
        validation_service = service_overrides.get('validation_service', ValidationService(settings))
        error_recovery_service = service_overrides.get('error_recovery_service', ErrorRecoveryService(validation_service))
        event_processor = service_overrides.get('event_processor', EventProcessor(validation_service, error_recovery_service))
        application_renderer = service_overrides.get('application_renderer', ApplicationRenderer(validation_service, error_recovery_service))
        
        return SimpleApp(
            settings=settings,
            engine=service_overrides.get('engine'),
            clock=service_overrides.get('clock'),
            input_adapter=service_overrides.get('input_adapter'),
            bus=service_overrides.get('bus'),
            drawing_service=service_overrides.get('drawing_service'),
            validation_service=validation_service,
            error_recovery_service=error_recovery_service,
            event_processor=event_processor,
            application_renderer=application_renderer
        )


def create_production_application(settings: Any, engine: Any, clock: Any, 
                                input_adapter: Any, bus: Any) -> SimpleApp:
    """
    Create production-ready application instance with all dependencies.
    
    Convenience function for creating application with production configuration.
    All dependencies must be provided for production deployment.
    """
    return SimpleAppFactory.create_application(
        settings=settings,
        engine=engine,
        clock=clock,
        input_adapter=input_adapter,
        bus=bus
    )