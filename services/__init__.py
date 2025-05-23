"""
ARCHITECTURE:
    services/
    ├── core/                    # Universal framework (685 lines)
    │   ├── __init__.py         # Framework exports
    │   ├── framework.py        # Universal service architecture  
    │   ├── validation.py       # Universal validation system
    │   ├── events.py           # Universal event system
    │   └── storage.py          # Universal storage system
    │
    ├── drawing/                 # Drawing module (520 lines)
    │   ├── __init__.py         # Drawing exports
    │   ├── engine.py           # Unified drawing engine
    │   └── tools.py            # Unified tool management
    │
    ├── application.py          # Unified application (890 lines)
    ├── utilities.py            # Consolidated utilities (385 lines)
    └── __init__.py             # This file (exports)

"""

# Core Framework - Universal patterns eliminating all duplication
import pygame
from .core import (
    # Universal Service Framework
    UniversalService,
    ServiceConfiguration,
    ServiceFactory,
    ServiceRegistry,
    ServiceLifecycleManager,
    create_production_service,
    
    # Universal Validation - eliminates 8+ validation classes
    ValidationService,
    ValidationRule,
    ValidationError,
    validate_coordinate,
    validate_color,
    validate_brush_width,
    validate_file_path,
    validate_tool_key,
    create_validator_chain,
    
    # Universal Event System - eliminates 6+ event interfaces
    EventBus,
    EventSubscription,
    EventPublisher,
    EventHandler,
    create_event_bus,
    create_event_handler,
    
    # Universal Storage - eliminates 4+ storage providers  
    StorageProvider,
    ConfigurationProvider,
    StateProvider,
    create_file_storage,
    create_memory_storage,
    create_json_storage
)

# Drawing System - Consolidated drawing functionality
from .drawing import (
    # Unified Drawing Engine - replaces 3+ drawing services
    DrawingEngine,
    RenderingBackend,
    CoordinateSystem,
    ViewportState,
    WorldCoordinate,
    ScreenCoordinate,
    DrawingConfiguration,
    create_drawing_engine,
    create_pygame_backend,
    
    # Unified Tool Management - replaces tools.py + undo.py + journal.py patterns
    ToolManager,
    DrawingTool,
    ToolState,
    ShapeGenerator,
    BrushController,
    create_tool_manager,
    create_shape_generator
)

# Unified Application - Replaces app.py + database integration
from .application import (
    UnifiedApplication,
    ApplicationSettings,
    ApplicationState,
    InputProcessor,
    RenderingOrchestrator,
    create_application,
    create_production_application,
    
    # Legacy compatibility for existing code
    SimpleApp,
    SimpleApplicationFactory
)

# Consolidated Utilities - Replaces grid.py + calculator.py + scattered utilities
from .utilities import (
    # Grid System - replaces entire grid.py
    GridRenderer,
    GridConfiguration,
    GridStyle,
    create_grid_renderer,
    
    # Math Engine - replaces calculator.py mathematical operations
    MathEngine,
    MathResult,
    MathOperationType,
    GeometryCalculator,
    create_math_engine,
    
    # Utility Service - unified access to all utilities
    UtilityService,
    ConfigurationManager,
    create_utility_service,
    
    # Convenience functions
    calculate_distance,
    interpolate_line,
    solve_equation,
    plot_function
)

# MISSING FUNCTIONS - Add the functions that main.py and services/app.py are trying to import

def create_complete_application(
    backend,
    window_width=1280,
    window_height=720,
    window_title="InfiniteJournal",
    target_fps=60,
    debug_mode=False,
    **kwargs
):
    """
    Create complete application with all services integrated.
    
    This function was missing and causing the import error.
    It creates a UnifiedApplication with all necessary services.
    """
    # Create application settings
    settings = ApplicationSettings(
        window_width=window_width,
        window_height=window_height,
        window_title=window_title,
        target_fps=target_fps,
        debug_mode=debug_mode,
        **kwargs
    )
    
    # Create storage and validation
    storage = create_memory_storage("main_app")
    validation_service = ValidationService()
    event_bus = create_event_bus()
    
    # Create unified application
    app = UnifiedApplication(
        settings=settings,
        backend=backend,
        storage=storage,
        validation_service=validation_service
    )
    
    return app


def create_working_application(
    backend,
    window_width=1280,
    window_height=720,
    window_title="InfiniteJournal",
    target_fps=60,
    debug_mode=False
):
    """
    Create a working application with proper service initialization.
    
    This function ensures all services start correctly and provides drawing functionality.
    """
    from services.drawing.tools import ToolManager, ToolType, ToolState
    from services.drawing.engine import DrawingEngine, DrawingConfiguration
    from services.core.events import create_event_bus
    from services.core.storage import create_memory_storage
    from services.core.validation import ValidationService
    from services.core.framework import ServiceConfiguration
    
    # Create core services
    event_bus = create_event_bus()
    storage = create_memory_storage("working_app")
    validation_service = ValidationService()
    
    # Create drawing engine
    drawing_config = ServiceConfiguration(
        service_name="drawing_engine",
        debug_mode=debug_mode,
        auto_start=False  # Start manually
    )
    
    drawing_engine = DrawingEngine(
        config=drawing_config,
        backend=backend,
        validation_service=validation_service,
        event_bus=event_bus,
        drawing_config=DrawingConfiguration()
    )
    
    # Create tool manager
    tool_config = ServiceConfiguration(
        service_name="tool_manager", 
        debug_mode=debug_mode,
        auto_start=False  # Start manually
    )
    
    tool_manager = ToolManager(
        config=tool_config,
        validation_service=validation_service,
        event_bus=event_bus
    )
    
    # Create working application wrapper
    app = WorkingApplication(
        backend=backend,
        drawing_engine=drawing_engine,
        tool_manager=tool_manager,
        event_bus=event_bus,
        window_width=window_width,
        window_height=window_height,
        window_title=window_title,
        target_fps=target_fps,
        debug_mode=debug_mode
    )
    
    return app


class WorkingApplication:
    """
    Working application wrapper that ensures proper initialization and functionality.
    
    This provides a simplified but functional drawing application.
    """
    
    def __init__(
        self,
        backend,
        drawing_engine,
        tool_manager,
        event_bus,
        window_width=1280,
        window_height=720,
        window_title="InfiniteJournal",
        target_fps=60,
        debug_mode=False
    ):
        self.backend = backend
        self.drawing_engine = drawing_engine
        self.tool_manager = tool_manager
        self.event_bus = event_bus
        
        self.window_width = window_width
        self.window_height = window_height
        self.window_title = window_title
        self.target_fps = target_fps
        self.debug_mode = debug_mode
        
        self.running = False
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Drawing state
        self.is_drawing = False
        self.current_color = (255, 255, 255)  # White
        self.brush_size = 5
        self.last_pos = None
        self.strokes = []  # Store drawn strokes
        
    def initialize(self):
        """Initialize the working application."""
        try:
            # Initialize backend window
            self.backend.init_window(
                self.window_width,
                self.window_height,
                self.window_title
            )
            
            # Start services manually
            self.drawing_engine.start()
            self.tool_manager.start()
            
            # Set up drawing engine
            self.drawing_engine.set_screen_size(self.window_width, self.window_height)
            
            # Set default tool without using service wrapper
            self._set_default_tool()
            
            self.logger.info("Working application initialized successfully")
            
        except Exception as error:
            self.logger.error(f"Failed to initialize working application: {error}")
            raise
    
    def _set_default_tool(self):
        """Set default tool bypassing service state checks."""
        try:
            from services.drawing.tools import ToolType, ToolState
            
            # Set tool state directly
            self.tool_manager.current_state = ToolState(
                tool_type=ToolType.BRUSH,
                brush_width=self.brush_size,
                color=self.current_color,
                is_active=True
            )
            
            # Set current tool directly
            if ToolType.BRUSH in self.tool_manager.tools:
                self.tool_manager.current_tool = self.tool_manager.tools[ToolType.BRUSH]
            
            self.logger.info("Default tool set to BRUSH")
            
        except Exception as error:
            self.logger.warning(f"Failed to set default tool: {error}")
    
    def run(self):
        """Run the working application."""
        self.running = True
        self.logger.info("Starting working application main loop")
        
        try:
            import pygame
            clock = pygame.time.Clock()
            
            while self.running:
                # Process events
                events = pygame.event.get()
                
                for event in events:
                    if event.type == pygame.QUIT:
                        self.running = False
                        break
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        self._handle_mouse_down(event)
                    elif event.type == pygame.MOUSEBUTTONUP:
                        self._handle_mouse_up(event)
                    elif event.type == pygame.MOUSEMOTION:
                        self._handle_mouse_move(event)
                    elif event.type == pygame.KEYDOWN:
                        self._handle_key_press(event)
                
                # Render frame
                self._render_frame()
                
                # Control frame rate
                clock.tick(self.target_fps)
                
        except KeyboardInterrupt:
            self.logger.info("Application interrupted by user")
        except Exception as error:
            self.logger.error(f"Application runtime error: {error}")
        finally:
            self.shutdown()
    
    def _handle_mouse_down(self, event):
        """Handle mouse button press."""
        if event.button == 1:  # Left click
            self.is_drawing = True
            self.last_pos = event.pos
            
            # Start new stroke
            self.drawing_engine.start_stroke(event.pos, self.current_color, self.brush_size)
            
            self.logger.debug(f"Started drawing at {event.pos}")
    
    def _handle_mouse_up(self, event):
        """Handle mouse button release."""
        if event.button == 1:  # Left click
            self.is_drawing = False
            
            # Finish current stroke
            self.drawing_engine.finish_current_stroke()
            
            self.last_pos = None
            self.logger.debug(f"Finished drawing at {event.pos}")
    
    def _handle_mouse_move(self, event):
        """Handle mouse movement."""
        if self.is_drawing and self.last_pos:
            # Add point to current stroke
            self.drawing_engine.add_stroke_point(event.pos)
            self.last_pos = event.pos
    
    def _handle_key_press(self, event):
        """Handle key press events."""
        if event.key == pygame.K_ESCAPE:
            self.running = False
        elif event.key == pygame.K_SPACE:
            # Clear canvas
            self.drawing_engine.clear_canvas()
            self.logger.info("Canvas cleared")
        elif event.key == pygame.K_1:
            self.current_color = (255, 255, 255)  # White
            self.logger.info("Color changed to white")
        elif event.key == pygame.K_2:
            self.current_color = (255, 0, 0)      # Red
            self.logger.info("Color changed to red")
        elif event.key == pygame.K_3:
            self.current_color = (0, 255, 0)      # Green
            self.logger.info("Color changed to green")
        elif event.key == pygame.K_4:
            self.current_color = (0, 0, 255)      # Blue
            self.logger.info("Color changed to blue")
        elif event.key == pygame.K_5:
            self.current_color = (255, 255, 0)    # Yellow
            self.logger.info("Color changed to yellow")
        elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
            # Increase brush size
            self.brush_size = min(self.brush_size + 2, 50)
            self.logger.info(f"Brush size increased to {self.brush_size}")
        elif event.key == pygame.K_MINUS:
            # Decrease brush size
            self.brush_size = max(self.brush_size - 2, 1)
            self.logger.info(f"Brush size decreased to {self.brush_size}")
    
    def _render_frame(self):
        """Render a complete frame."""
        # Clear screen to black
        self.backend.clear((0, 0, 0))
        
        # Render all strokes through drawing engine
        self.drawing_engine.render_frame()
        
        # Draw UI elements
        self._draw_ui()
        
        # Present frame
        self.backend.present()
    
    def _draw_ui(self):
        """Draw user interface elements."""
        # Draw instructions
        instructions = [
            "InfiniteJournal - Click and drag to draw",
            f"Current: Color=RGB{self.current_color}, Brush={self.brush_size}",
            "Keys: 1=White, 2=Red, 3=Green, 4=Blue, 5=Yellow",
            "      +=Bigger, -=Smaller, Space=Clear, Esc=Quit"
        ]
        
        y_offset = 10
        for instruction in instructions:
            self.backend.draw_text(instruction, (10, y_offset), 20, (128, 128, 128))
            y_offset += 25
        
        # Draw color indicator
        color_rect = (self.window_width - 80, 10, 60, 30)
        self.backend.draw_rect(color_rect, self.current_color, 0)
        self.backend.draw_rect(color_rect, (255, 255, 255), 2)  # White border
        
        # Draw brush size indicator
        brush_center = (self.window_width - 50, 60)
        self.backend.draw_circle(brush_center, self.brush_size // 2, self.current_color)
        self.backend.draw_circle(brush_center, self.brush_size // 2, (255, 255, 255), 1)  # White border
    
    def shutdown(self):
        """Shutdown the application gracefully."""
        try:
            self.drawing_engine.stop()
            self.tool_manager.stop()
            self.backend.quit()
            self.logger.info("Working application shutdown completed")
        except Exception as error:
            self.logger.error(f"Error during shutdown: {error}")


import logging


def integrate_with_existing_backend(existing_backend):
    """
    Integrate with existing backend (pygame adapter).
    
    This function was missing and causing import errors.
    It wraps an existing backend to work with the Universal Services Framework.
    """
    class BackendWrapper:
        """Wrapper to make existing backend compatible."""
        
        def __init__(self, backend):
            self.backend = backend
            
        def clear(self, color=None):
            """Clear the rendering surface."""
            if hasattr(self.backend, 'clear'):
                if color:
                    self.backend.clear(color)
                else:
                    self.backend.clear()
                    
        def present(self):
            """Present the rendered frame."""
            if hasattr(self.backend, 'present'):
                self.backend.present()
            elif hasattr(self.backend, 'flip'):
                self.backend.flip()
                
        def draw_line(self, start, end, width, color):
            """Draw line between two points."""
            if hasattr(self.backend, 'draw_line'):
                self.backend.draw_line(start, end, width, color)
                
        def draw_circle(self, center, radius, color, width=0):
            """Draw circle at center with radius."""
            if hasattr(self.backend, 'draw_circle'):
                self.backend.draw_circle(center, radius, color, width)
                
        def draw_rect(self, rect, color, width=0):
            """Draw rectangle."""
            if hasattr(self.backend, 'draw_rect'):
                self.backend.draw_rect(rect, color, width)
                
        def draw_text(self, text, pos, size, color):
            """Draw text at position."""
            if hasattr(self.backend, 'draw_text'):
                self.backend.draw_text(text, pos, size, color)
                
        def poll_events(self):
            """Poll input events."""
            if hasattr(self.backend, 'poll_events'):
                return self.backend.poll_events()
            return []
            
        def init_window(self, width, height, title):
            """Initialize window."""
            if hasattr(self.backend, 'init_window'):
                self.backend.init_window(width, height, title)
            elif hasattr(self.backend, 'open_window'):
                self.backend.open_window(width, height, title)
                
    return BackendWrapper(existing_backend)


# Export all public interfaces - COMPLETE THE MISSING EXPORTS
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
    "create_json_storage",
    
    # Drawing system
    "DrawingEngine",
    "RenderingBackend",
    "CoordinateSystem",
    "ViewportState",
    "WorldCoordinate",
    "ScreenCoordinate",
    "DrawingConfiguration",
    "create_drawing_engine",
    "create_pygame_backend",
    
    # Tool management
    "ToolManager",
    "ToolType",
    "ToolState",
    "DrawingTool",
    "BrushTool",
    "EraserTool",
    "LineTool", 
    "RectangleTool",
    "CircleTool",
    "ShapeGenerator",
    "BrushController",
    "create_tool_manager",
    "create_shape_generator",
    
    # Application system
    "UnifiedApplication",
    "ApplicationSettings",
    "ApplicationState",
    "InputProcessor",
    "RenderingOrchestrator",
    "create_application",
    "create_production_application",
    "SimpleApp",
    "SimpleApplicationFactory",
    
    # Utility system
    "GridRenderer",
    "GridConfiguration",
    "GridStyle",
    "create_grid_renderer",
    "MathEngine",
    "MathResult",
    "MathOperationType",
    "GeometryCalculator",
    "create_math_engine",
    "UtilityService",
    "ConfigurationManager",
    "create_utility_service",
    "calculate_distance",
    "interpolate_line",
    "solve_equation",
    "plot_function",
    
    # MISSING FUNCTIONS - Now properly exported
    "create_complete_application",
    "create_working_application",
    "integrate_with_existing_backend",
    "WorkingApplication"
]