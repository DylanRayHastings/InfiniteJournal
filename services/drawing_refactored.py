"""
Refactored Drawing System Module.

This module contains the complete refactored drawing system with all the improvements
from the file combination analysis. It's imported by the compatibility layer to
provide the new functionality while maintaining backward compatibility.

Save this as: services/drawing_refactored.py
"""

import logging
import math
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union

logger = logging.getLogger(__name__)


class DrawingTool(Enum):
    """Available drawing tools for canvas interaction."""
    BRUSH = "brush"
    ERASER = "eraser"
    LINE = "line"
    RECTANGLE = "rect"
    CIRCLE = "circle"
    TRIANGLE = "triangle"
    PARABOLA = "parabola"


class ShapeType(Enum):
    """Shape classification for geometric drawing tools."""
    FREEFORM = "freeform"
    STRAIGHT_LINE = "straight_line"
    GEOMETRIC_SHAPE = "geometric_shape"
    CURVED_SHAPE = "curved_shape"


class InputAction(Enum):
    """User input action types for drawing interaction."""
    START_DRAWING = "start_drawing"
    CONTINUE_DRAWING = "continue_drawing"
    FINISH_DRAWING = "finish_drawing"
    START_PANNING = "start_panning"
    CONTINUE_PANNING = "continue_panning"
    FINISH_PANNING = "finish_panning"
    ADJUST_BRUSH_SIZE = "adjust_brush_size"
    CHANGE_TOOL = "change_tool"


@dataclass(frozen=True)
class WorldCoordinate:
    """Immutable world coordinate representation."""
    x: float
    y: float
    
    def to_screen_coordinate(self, viewport_x: float, viewport_y: float) -> 'ScreenCoordinate':
        """Convert world coordinate to screen coordinate based on viewport position."""
        return ScreenCoordinate(
            x=int(self.x - viewport_x),
            y=int(self.y - viewport_y)
        )


@dataclass(frozen=True)
class ScreenCoordinate:
    """Immutable screen coordinate representation."""
    x: int
    y: int
    
    def to_world_coordinate(self, viewport_x: float, viewport_y: float) -> WorldCoordinate:
        """Convert screen coordinate to world coordinate based on viewport position."""
        return WorldCoordinate(
            x=float(self.x + viewport_x),
            y=float(self.y + viewport_y)
        )


@dataclass(frozen=True)
class DrawingPoint:
    """Individual point in a drawing stroke with pressure and width information."""
    world_coordinate: WorldCoordinate
    width: float
    pressure: float
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class DrawingStroke:
    """Complete drawing stroke containing multiple points and metadata."""
    stroke_id: str
    points: List[DrawingPoint]
    color: Tuple[int, int, int]
    tool: DrawingTool
    shape_type: ShapeType
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def point_count(self) -> int:
        """Get total number of points in this stroke."""
        return len(self.points)
    
    @property
    def bounding_box(self) -> Tuple[WorldCoordinate, WorldCoordinate]:
        """Calculate bounding box of stroke in world coordinates."""
        if not self.points:
            return WorldCoordinate(0, 0), WorldCoordinate(0, 0)
        
        min_x = min(point.world_coordinate.x for point in self.points)
        max_x = max(point.world_coordinate.x for point in self.points)
        min_y = min(point.world_coordinate.y for point in self.points)
        max_y = max(point.world_coordinate.y for point in self.points)
        
        return WorldCoordinate(min_x, min_y), WorldCoordinate(max_x, max_y)


@dataclass(frozen=True)
class ViewportState:
    """Current viewport position and configuration for infinite canvas."""
    x: float
    y: float
    width: int
    height: int
    pan_sensitivity: float = 1.0
    
    def translate(self, delta_x: float, delta_y: float) -> 'ViewportState':
        """Create new viewport state with translated position."""
        return ViewportState(
            x=self.x + delta_x,
            y=self.y + delta_y,
            width=self.width,
            height=self.height,
            pan_sensitivity=self.pan_sensitivity
        )
    
    def contains_world_coordinate(self, coordinate: WorldCoordinate, margin: float = 100) -> bool:
        """Check if world coordinate is visible in viewport with optional margin."""
        return (
            self.x - margin <= coordinate.x <= self.x + self.width + margin and
            self.y - margin <= coordinate.y <= self.y + self.height + margin
        )


@dataclass(frozen=True)
class DrawingConfiguration:
    """Drawing tool configuration and settings."""
    current_tool: DrawingTool
    brush_width: float
    brush_color: Tuple[int, int, int]
    grid_spacing: int = 40
    grid_color: Tuple[int, int, int] = (30, 30, 30)
    background_color: Tuple[int, int, int] = (0, 0, 0)
    
    def with_tool(self, tool: DrawingTool) -> 'DrawingConfiguration':
        """Create new configuration with different tool."""
        return DrawingConfiguration(
            current_tool=tool,
            brush_width=self.brush_width,
            brush_color=self.brush_color,
            grid_spacing=self.grid_spacing,
            grid_color=self.grid_color,
            background_color=self.background_color
        )
    
    def with_brush_width(self, width: float) -> 'DrawingConfiguration':
        """Create new configuration with different brush width."""
        return DrawingConfiguration(
            current_tool=self.current_tool,
            brush_width=width,
            brush_color=self.brush_color,
            grid_spacing=self.grid_spacing,
            grid_color=self.grid_color,
            background_color=self.background_color
        )
    
    def with_brush_color(self, color: Tuple[int, int, int]) -> 'DrawingConfiguration':
        """Create new configuration with different brush color."""
        return DrawingConfiguration(
            current_tool=self.current_tool,
            brush_width=self.brush_width,
            brush_color=color,
            grid_spacing=self.grid_spacing,
            grid_color=self.grid_color,
            background_color=self.background_color
        )


class DrawingValidationError(Exception):
    """Exception raised when drawing input validation fails."""
    pass


class DrawingInputValidator:
    """Centralized validation service for all drawing input data."""
    
    MIN_BRUSH_WIDTH = 1.0
    MAX_BRUSH_WIDTH = 50.0
    MIN_COORDINATE_VALUE = -1000000.0
    MAX_COORDINATE_VALUE = 1000000.0
    MAX_STROKE_POINTS = 10000
    MIN_VIEWPORT_DIMENSION = 1
    MAX_VIEWPORT_DIMENSION = 10000
    
    @classmethod
    def validate_brush_width(cls, width: float) -> None:
        """Validate brush width is within acceptable range."""
        if not isinstance(width, (int, float)):
            raise DrawingValidationError("Brush width must be numeric")
        
        if width < cls.MIN_BRUSH_WIDTH:
            raise DrawingValidationError(f"Brush width must be at least {cls.MIN_BRUSH_WIDTH}")
        
        if width > cls.MAX_BRUSH_WIDTH:
            raise DrawingValidationError(f"Brush width cannot exceed {cls.MAX_BRUSH_WIDTH}")
    
    @classmethod
    def validate_coordinate(cls, coordinate: Union[WorldCoordinate, ScreenCoordinate]) -> None:
        """Validate coordinate values are within acceptable range."""
        x_value = coordinate.x
        y_value = coordinate.y
        
        if not isinstance(x_value, (int, float)) or not isinstance(y_value, (int, float)):
            raise DrawingValidationError("Coordinate values must be numeric")
        
        if x_value < cls.MIN_COORDINATE_VALUE or x_value > cls.MAX_COORDINATE_VALUE:
            raise DrawingValidationError("Coordinate X value out of range")
        
        if y_value < cls.MIN_COORDINATE_VALUE or y_value > cls.MAX_COORDINATE_VALUE:
            raise DrawingValidationError("Coordinate Y value out of range")
    
    @classmethod
    def validate_color(cls, color: Tuple[int, int, int]) -> None:
        """Validate color tuple contains valid RGB values."""
        if not isinstance(color, tuple) or len(color) != 3:
            raise DrawingValidationError("Color must be a tuple of 3 RGB values")
        
        for component in color:
            if not isinstance(component, int) or component < 0 or component > 255:
                raise DrawingValidationError("Color components must be integers between 0 and 255")
    
    @classmethod
    def validate_stroke_points(cls, points: List[DrawingPoint]) -> None:
        """Validate stroke points list is acceptable."""
        if not isinstance(points, list):
            raise DrawingValidationError("Stroke points must be a list")
        
        if len(points) > cls.MAX_STROKE_POINTS:
            raise DrawingValidationError(f"Stroke cannot exceed {cls.MAX_STROKE_POINTS} points")
        
        for point in points:
            if not isinstance(point, DrawingPoint):
                raise DrawingValidationError("All stroke points must be DrawingPoint instances")
            
            cls.validate_coordinate(point.world_coordinate)
            cls.validate_brush_width(point.width)
    
    @classmethod
    def validate_viewport_dimensions(cls, width: int, height: int) -> None:
        """Validate viewport dimensions are acceptable."""
        if not isinstance(width, int) or not isinstance(height, int):
            raise DrawingValidationError("Viewport dimensions must be integers")
        
        if width < cls.MIN_VIEWPORT_DIMENSION or width > cls.MAX_VIEWPORT_DIMENSION:
            raise DrawingValidationError("Viewport width out of acceptable range")
        
        if height < cls.MIN_VIEWPORT_DIMENSION or height > cls.MAX_VIEWPORT_DIMENSION:
            raise DrawingValidationError("Viewport height out of acceptable range")


class ShapeGenerationService:
    """Service for generating geometric shapes as sequences of drawing points."""
    
    @staticmethod
    def generate_line_points(
        start_coordinate: WorldCoordinate, 
        end_coordinate: WorldCoordinate,
        brush_width: float
    ) -> List[DrawingPoint]:
        """Generate points for straight line between two coordinates."""
        DrawingInputValidator.validate_coordinate(start_coordinate)
        DrawingInputValidator.validate_coordinate(end_coordinate)
        DrawingInputValidator.validate_brush_width(brush_width)
        
        return [
            DrawingPoint(start_coordinate, brush_width, 1.0),
            DrawingPoint(end_coordinate, brush_width, 1.0)
        ]
    
    @staticmethod
    def generate_rectangle_points(
        start_coordinate: WorldCoordinate, 
        end_coordinate: WorldCoordinate,
        brush_width: float
    ) -> List[DrawingPoint]:
        """Generate points for rectangle outline between two coordinates."""
        DrawingInputValidator.validate_coordinate(start_coordinate)
        DrawingInputValidator.validate_coordinate(end_coordinate)
        DrawingInputValidator.validate_brush_width(brush_width)
        
        corner_coordinates = [
            start_coordinate,
            WorldCoordinate(end_coordinate.x, start_coordinate.y),
            end_coordinate,
            WorldCoordinate(start_coordinate.x, end_coordinate.y),
            start_coordinate
        ]
        
        return [
            DrawingPoint(coord, brush_width, 1.0) 
            for coord in corner_coordinates
        ]
    
    @staticmethod
    def generate_circle_points(
        center_coordinate: WorldCoordinate, 
        radius_coordinate: WorldCoordinate,
        brush_width: float,
        point_density: int = 64
    ) -> List[DrawingPoint]:
        """Generate points for circle outline with specified center and radius."""
        DrawingInputValidator.validate_coordinate(center_coordinate)
        DrawingInputValidator.validate_coordinate(radius_coordinate)
        DrawingInputValidator.validate_brush_width(brush_width)
        
        radius = math.sqrt(
            (radius_coordinate.x - center_coordinate.x) ** 2 + 
            (radius_coordinate.y - center_coordinate.y) ** 2
        )
        
        if radius < 1:
            return [DrawingPoint(center_coordinate, brush_width, 1.0)]
        
        circle_points = []
        angle_step = 2 * math.pi / max(point_density, radius * 2)
        
        for i in range(int(2 * math.pi / angle_step) + 1):
            angle = i * angle_step
            point_x = center_coordinate.x + radius * math.cos(angle)
            point_y = center_coordinate.y + radius * math.sin(angle)
            
            circle_points.append(
                DrawingPoint(
                    WorldCoordinate(point_x, point_y), 
                    brush_width, 
                    1.0
                )
            )
        
        return circle_points
    
    @staticmethod
    def generate_triangle_points(
        first_coordinate: WorldCoordinate, 
        second_coordinate: WorldCoordinate,
        brush_width: float
    ) -> List[DrawingPoint]:
        """Generate points for right triangle outline."""
        DrawingInputValidator.validate_coordinate(first_coordinate)
        DrawingInputValidator.validate_coordinate(second_coordinate)
        DrawingInputValidator.validate_brush_width(brush_width)
        
        third_coordinate = WorldCoordinate(second_coordinate.x, first_coordinate.y)
        
        triangle_coordinates = [
            first_coordinate,
            second_coordinate,
            third_coordinate,
            first_coordinate
        ]
        
        return [
            DrawingPoint(coord, brush_width, 1.0) 
            for coord in triangle_coordinates
        ]
    
    @staticmethod
    def generate_parabola_points(
        start_coordinate: WorldCoordinate, 
        end_coordinate: WorldCoordinate,
        brush_width: float,
        point_density: int = 100
    ) -> List[DrawingPoint]:
        """Generate dense point sequence for smooth parabolic curve."""
        DrawingInputValidator.validate_coordinate(start_coordinate)
        DrawingInputValidator.validate_coordinate(end_coordinate)
        DrawingInputValidator.validate_brush_width(brush_width)
        
        delta_x = end_coordinate.x - start_coordinate.x
        delta_y = end_coordinate.y - start_coordinate.y
        
        if abs(delta_x) < 2 and abs(delta_y) < 2:
            return [
                DrawingPoint(start_coordinate, brush_width, 1.0),
                DrawingPoint(end_coordinate, brush_width, 1.0)
            ]
        
        distance = math.sqrt(delta_x * delta_x + delta_y * delta_y)
        vertex_offset = distance * 0.25
        
        mid_x = (start_coordinate.x + end_coordinate.x) / 2.0
        vertex_y = min(start_coordinate.y, end_coordinate.y) - vertex_offset
        
        if delta_y < 0:
            vertex_y = max(start_coordinate.y, end_coordinate.y) + vertex_offset
        
        try:
            parabola_coefficient = (start_coordinate.y - vertex_y) / ((start_coordinate.x - mid_x) ** 2)
        except ZeroDivisionError:
            parabola_coefficient = 1.0 if delta_y >= 0 else -1.0
        
        parabola_points = []
        
        for i in range(point_density + 1):
            parameter = i / point_density
            current_x = start_coordinate.x + parameter * delta_x
            current_y = parabola_coefficient * ((current_x - mid_x) ** 2) + vertex_y
            
            parabola_points.append(
                DrawingPoint(
                    WorldCoordinate(current_x, current_y), 
                    brush_width, 
                    1.0
                )
            )
        
        return parabola_points


class EventBus(Protocol):
    """Event publishing interface for decoupled communication."""
    
    def publish(self, event_name: str, event_data: Any) -> None:
        """Publish event with data to all subscribers."""
        ...
    
    def subscribe(self, event_name: str, callback_function) -> None:
        """Subscribe callback function to specific event."""
        ...


class CanvasRenderer(Protocol):
    """Rendering interface for drawing canvas content to display."""
    
    def render_background_grid(self, viewport: ViewportState, config: DrawingConfiguration) -> None:
        """Render infinite background grid based on viewport position."""
        ...
    
    def render_stroke(self, stroke: DrawingStroke, viewport: ViewportState) -> None:
        """Render complete drawing stroke to display."""
        ...
    
    def render_stroke_preview(self, points: List[DrawingPoint], viewport: ViewportState, config: DrawingConfiguration) -> None:
        """Render preview of stroke being drawn."""
        ...
    
    def clear_display(self) -> None:
        """Clear entire display surface."""
        ...


class InputHandler(Protocol):
    """Input handling interface for processing user interactions."""
    
    def handle_mouse_down(self, screen_coordinate: ScreenCoordinate, button: int) -> Optional[InputAction]:
        """Process mouse button press and return appropriate action."""
        ...
    
    def handle_mouse_move(self, screen_coordinate: ScreenCoordinate) -> Optional[InputAction]:
        """Process mouse movement and return appropriate action."""
        ...
    
    def handle_mouse_up(self, screen_coordinate: ScreenCoordinate, button: int) -> Optional[InputAction]:
        """Process mouse button release and return appropriate action."""
        ...
    
    def handle_scroll(self, direction: int) -> Optional[InputAction]:
        """Process scroll wheel input and return appropriate action."""
        ...
    
    def handle_key_press(self, key: str) -> Optional[InputAction]:
        """Process keyboard input and return appropriate action."""
        ...


class CanvasDataStore(Protocol):
    """Storage interface for canvas drawing data persistence."""
    
    def save_stroke(self, stroke: DrawingStroke) -> None:
        """Save drawing stroke to persistent storage."""
        ...
    
    def load_all_strokes(self) -> List[DrawingStroke]:
        """Load all saved drawing strokes from storage."""
        ...
    
    def clear_all_strokes(self) -> None:
        """Remove all saved drawing strokes from storage."""
        ...
    
    def get_stroke_count(self) -> int:
        """Get total number of saved strokes."""
        ...


class InfiniteCanvasService:
    """Service managing infinite canvas state and drawing stroke storage."""
    
    def __init__(self, data_store: CanvasDataStore):
        """Initialize canvas service with data storage dependency."""
        self.data_store = data_store
        self.active_stroke_points: List[DrawingPoint] = []
        self.shape_start_coordinate: Optional[WorldCoordinate] = None
        self.shape_preview_points: List[DrawingPoint] = []
        self.is_drawing_active = False
    
    def start_new_stroke(self, start_coordinate: WorldCoordinate, config: DrawingConfiguration) -> None:
        """Begin new drawing stroke at specified world coordinate."""
        DrawingInputValidator.validate_coordinate(start_coordinate)
        DrawingInputValidator.validate_brush_width(config.brush_width)
        DrawingInputValidator.validate_color(config.brush_color)
        
        self.is_drawing_active = True
        self.active_stroke_points = [
            DrawingPoint(start_coordinate, config.brush_width, 1.0)
        ]
        
        if self._is_shape_tool(config.current_tool):
            self.shape_start_coordinate = start_coordinate
            self.shape_preview_points = []
        
        logger.debug(f"Started stroke at {start_coordinate} with tool {config.current_tool}")
    
    def add_stroke_point(self, coordinate: WorldCoordinate, config: DrawingConfiguration) -> None:
        """Add point to current active stroke."""
        if not self.is_drawing_active:
            return
        
        DrawingInputValidator.validate_coordinate(coordinate)
        
        if self._is_shape_tool(config.current_tool):
            self._update_shape_preview(coordinate, config)
        else:
            new_point = DrawingPoint(coordinate, config.brush_width, 1.0)
            self.active_stroke_points.append(new_point)
            
            if len(self.active_stroke_points) > DrawingInputValidator.MAX_STROKE_POINTS:
                self.active_stroke_points = self.active_stroke_points[-5000:]
    
    def complete_current_stroke(self, config: DrawingConfiguration) -> Optional[DrawingStroke]:
        """Complete current stroke and save to storage."""
        if not self.is_drawing_active:
            return None
        
        final_points = self.shape_preview_points if self._is_shape_tool(config.current_tool) else self.active_stroke_points
        
        if not final_points:
            self._reset_drawing_state()
            return None
        
        DrawingInputValidator.validate_stroke_points(final_points)
        
        completed_stroke = DrawingStroke(
            stroke_id=str(uuid.uuid4()),
            points=final_points.copy(),
            color=config.brush_color,
            tool=config.current_tool,
            shape_type=self._determine_shape_type(config.current_tool)
        )
        
        self.data_store.save_stroke(completed_stroke)
        self._reset_drawing_state()
        
        logger.info(f"Completed stroke {completed_stroke.stroke_id} with {len(final_points)} points")
        return completed_stroke
    
    def cancel_current_stroke(self) -> None:
        """Cancel current stroke without saving."""
        self._reset_drawing_state()
        logger.debug("Cancelled current stroke")
    
    def get_current_preview_points(self) -> List[DrawingPoint]:
        """Get current stroke preview points for rendering."""
        if self._is_shape_tool_active():
            return self.shape_preview_points
        return self.active_stroke_points
    
    def get_all_strokes(self) -> List[DrawingStroke]:
        """Get all saved drawing strokes."""
        return self.data_store.load_all_strokes()
    
    def clear_all_strokes(self) -> None:
        """Remove all saved drawing strokes."""
        self.data_store.clear_all_strokes()
        self._reset_drawing_state()
        logger.info("Cleared all canvas strokes")
    
    def get_stroke_count(self) -> int:
        """Get total number of saved strokes."""
        return self.data_store.get_stroke_count()
    
    def _update_shape_preview(self, end_coordinate: WorldCoordinate, config: DrawingConfiguration) -> None:
        """Update shape preview points based on current end coordinate."""
        if not self.shape_start_coordinate:
            return
        
        shape_generator_map = {
            DrawingTool.LINE: ShapeGenerationService.generate_line_points,
            DrawingTool.RECTANGLE: ShapeGenerationService.generate_rectangle_points,
            DrawingTool.CIRCLE: ShapeGenerationService.generate_circle_points,
            DrawingTool.TRIANGLE: ShapeGenerationService.generate_triangle_points,
            DrawingTool.PARABOLA: ShapeGenerationService.generate_parabola_points,
        }
        
        generator_function = shape_generator_map.get(config.current_tool)
        if generator_function:
            self.shape_preview_points = generator_function(
                self.shape_start_coordinate, 
                end_coordinate, 
                config.brush_width
            )
    
    def _is_shape_tool(self, tool: DrawingTool) -> bool:
        """Check if tool is a geometric shape tool."""
        return tool in [DrawingTool.LINE, DrawingTool.RECTANGLE, DrawingTool.CIRCLE, DrawingTool.TRIANGLE, DrawingTool.PARABOLA]
    
    def _is_shape_tool_active(self) -> bool:
        """Check if currently using a shape tool."""
        return self.shape_start_coordinate is not None
    
    def _determine_shape_type(self, tool: DrawingTool) -> ShapeType:
        """Determine shape type classification for drawing tool."""
        shape_type_map = {
            DrawingTool.BRUSH: ShapeType.FREEFORM,
            DrawingTool.ERASER: ShapeType.FREEFORM,
            DrawingTool.LINE: ShapeType.STRAIGHT_LINE,
            DrawingTool.RECTANGLE: ShapeType.GEOMETRIC_SHAPE,
            DrawingTool.CIRCLE: ShapeType.GEOMETRIC_SHAPE,
            DrawingTool.TRIANGLE: ShapeType.GEOMETRIC_SHAPE,
            DrawingTool.PARABOLA: ShapeType.CURVED_SHAPE,
        }
        return shape_type_map.get(tool, ShapeType.FREEFORM)
    
    def _reset_drawing_state(self) -> None:
        """Reset all active drawing state variables."""
        self.is_drawing_active = False
        self.active_stroke_points = []
        self.shape_start_coordinate = None
        self.shape_preview_points = []


class ViewportManagementService:
    """Service managing infinite canvas viewport state and panning operations."""
    
    def __init__(self, initial_viewport: ViewportState):
        """Initialize viewport management with initial state."""
        DrawingInputValidator.validate_viewport_dimensions(initial_viewport.width, initial_viewport.height)
        
        self.current_viewport = initial_viewport
        self.is_panning_active = False
        self.pan_start_coordinate: Optional[ScreenCoordinate] = None
        self.pan_last_coordinate: Optional[ScreenCoordinate] = None
    
    def start_panning(self, screen_coordinate: ScreenCoordinate) -> None:
        """Begin panning operation at specified screen coordinate."""
        DrawingInputValidator.validate_coordinate(screen_coordinate)
        
        self.is_panning_active = True
        self.pan_start_coordinate = screen_coordinate
        self.pan_last_coordinate = screen_coordinate
        
        logger.debug(f"Started panning at {screen_coordinate}")
    
    def update_panning(self, screen_coordinate: ScreenCoordinate) -> ViewportState:
        """Update panning operation and return new viewport state."""
        if not self.is_panning_active or not self.pan_last_coordinate:
            return self.current_viewport
        
        DrawingInputValidator.validate_coordinate(screen_coordinate)
        
        delta_x = (screen_coordinate.x - self.pan_last_coordinate.x) * self.current_viewport.pan_sensitivity
        delta_y = (screen_coordinate.y - self.pan_last_coordinate.y) * self.current_viewport.pan_sensitivity
        
        self.current_viewport = self.current_viewport.translate(-delta_x, -delta_y)
        self.pan_last_coordinate = screen_coordinate
        
        logger.debug(f"Updated viewport to ({self.current_viewport.x}, {self.current_viewport.y})")
        return self.current_viewport
    
    def finish_panning(self) -> ViewportState:
        """Complete panning operation and return final viewport state."""
        self.is_panning_active = False
        self.pan_start_coordinate = None
        self.pan_last_coordinate = None
        
        logger.debug(f"Finished panning at viewport ({self.current_viewport.x}, {self.current_viewport.y})")
        return self.current_viewport
    
    def get_current_viewport(self) -> ViewportState:
        """Get current viewport state."""
        return self.current_viewport


class DrawingConfigurationService:
    """Service managing drawing tool configuration and settings."""
    
    def __init__(self, initial_config: DrawingConfiguration):
        """Initialize configuration service with initial settings."""
        DrawingInputValidator.validate_brush_width(initial_config.brush_width)
        DrawingInputValidator.validate_color(initial_config.brush_color)
        
        self.current_config = initial_config
        self.available_tools = list(DrawingTool)
        self.available_colors = [
            (57, 255, 20),   # Neon Green
            (0, 255, 255),   # Neon Blue  
            (255, 20, 147),  # Neon Pink
            (255, 255, 0),   # Neon Yellow
            (255, 97, 3),    # Neon Orange
            (255, 255, 255), # White
        ]
    
    def change_tool(self, new_tool: DrawingTool) -> DrawingConfiguration:
        """Change current drawing tool and return new configuration."""
        if new_tool not in self.available_tools:
            raise DrawingValidationError(f"Unknown drawing tool: {new_tool}")
        
        self.current_config = self.current_config.with_tool(new_tool)
        logger.debug(f"Changed tool to {new_tool}")
        return self.current_config
    
    def cycle_to_next_tool(self) -> DrawingConfiguration:
        """Cycle to next tool in available tools list."""
        current_index = self.available_tools.index(self.current_config.current_tool)
        next_index = (current_index + 1) % len(self.available_tools)
        next_tool = self.available_tools[next_index]
        
        return self.change_tool(next_tool)
    
    def adjust_brush_width(self, delta: float) -> DrawingConfiguration:
        """Adjust brush width by specified delta amount."""
        new_width = max(
            DrawingInputValidator.MIN_BRUSH_WIDTH,
            min(
                self.current_config.brush_width + delta,
                DrawingInputValidator.MAX_BRUSH_WIDTH
            )
        )
        
        self.current_config = self.current_config.with_brush_width(new_width)
        logger.debug(f"Adjusted brush width to {new_width}")
        return self.current_config
    
    def set_brush_color(self, color: Tuple[int, int, int]) -> DrawingConfiguration:
        """Set brush color and return new configuration."""
        DrawingInputValidator.validate_color(color)
        
        self.current_config = self.current_config.with_brush_color(color)
        logger.debug(f"Set brush color to {color}")
        return self.current_config
    
    def cycle_color(self, color_index: int) -> DrawingConfiguration:
        """Set brush color from available colors by index."""
        if 0 <= color_index < len(self.available_colors):
            return self.set_brush_color(self.available_colors[color_index])
        
        raise DrawingValidationError(f"Color index {color_index} out of range")
    
    def get_current_configuration(self) -> DrawingConfiguration:
        """Get current drawing configuration."""
        return self.current_config


class DrawingOrchestrationService:
    """
    Main orchestrating service coordinating all drawing system components.
    
    Manages interactions between canvas, viewport, configuration, input handling,
    and rendering services to provide unified drawing functionality.
    """
    
    def __init__(
        self,
        canvas_service: InfiniteCanvasService,
        viewport_service: ViewportManagementService,
        config_service: DrawingConfigurationService,
        input_handler: InputHandler,
        renderer: CanvasRenderer,
        event_bus: EventBus
    ):
        """Initialize orchestration service with all required dependencies."""
        self.canvas_service = canvas_service
        self.viewport_service = viewport_service
        self.config_service = config_service
        self.input_handler = input_handler
        self.renderer = renderer
        self.event_bus = event_bus
        
        logger.info("Drawing orchestration service initialized")
    
    def handle_mouse_down(self, x: int, y: int, button: int) -> bool:
        """Process mouse button press and coordinate drawing system response."""
        try:
            screen_coord = ScreenCoordinate(x, y)
            DrawingInputValidator.validate_coordinate(screen_coord)
            
            action = self.input_handler.handle_mouse_down(screen_coord, button)
            
            if action == InputAction.START_DRAWING:
                return self._start_drawing_at_coordinate(screen_coord)
            elif action == InputAction.START_PANNING:
                return self._start_panning_at_coordinate(screen_coord)
            
            return False
            
        except DrawingValidationError as error:
            logger.warning(f"Mouse down validation error: {error}")
            return False
    
    def handle_mouse_move(self, x: int, y: int) -> bool:
        """Process mouse movement and update drawing or panning state."""
        try:
            screen_coord = ScreenCoordinate(x, y)
            DrawingInputValidator.validate_coordinate(screen_coord)
            
            action = self.input_handler.handle_mouse_move(screen_coord)
            
            if action == InputAction.CONTINUE_DRAWING:
                return self._continue_drawing_at_coordinate(screen_coord)
            elif action == InputAction.CONTINUE_PANNING:
                return self._continue_panning_at_coordinate(screen_coord)
            
            return False
            
        except DrawingValidationError as error:
            logger.warning(f"Mouse move validation error: {error}")
            return False
    
    def handle_mouse_up(self, x: int, y: int, button: int) -> bool:
        """Process mouse button release and complete drawing or panning action."""
        try:
            screen_coord = ScreenCoordinate(x, y)
            DrawingInputValidator.validate_coordinate(screen_coord)
            
            action = self.input_handler.handle_mouse_up(screen_coord, button)
            
            if action == InputAction.FINISH_DRAWING:
                return self._finish_drawing()
            elif action == InputAction.FINISH_PANNING:
                return self._finish_panning()
            
            return False
            
        except DrawingValidationError as error:
            logger.warning(f"Mouse up validation error: {error}")
            return False
    
    def handle_scroll(self, direction: int) -> bool:
        """Process scroll wheel input to adjust brush width."""
        try:
            action = self.input_handler.handle_scroll(direction)
            
            if action == InputAction.ADJUST_BRUSH_SIZE:
                delta = 2.0 if direction > 0 else -2.0
                new_config = self.config_service.adjust_brush_width(delta)
                self.event_bus.publish('brush_width_changed', new_config.brush_width)
                return True
            
            return False
            
        except DrawingValidationError as error:
            logger.warning(f"Scroll validation error: {error}")
            return False
    
    def handle_key_press(self, key: str) -> bool:
        """Process keyboard input for tool changes and shortcuts."""
        try:
            action = self.input_handler.handle_key_press(key)
            
            if action == InputAction.CHANGE_TOOL:
                return self._handle_tool_change_key(key)
            
            return False
            
        except DrawingValidationError as error:
            logger.warning(f"Key press validation error: {error}")
            return False
    
    def render_complete_canvas(self) -> None:
        """Render complete canvas including background, strokes, and preview."""
        try:
            current_viewport = self.viewport_service.get_current_viewport()
            current_config = self.config_service.get_current_configuration()
            
            self.renderer.clear_display()
            self.renderer.render_background_grid(current_viewport, current_config)
            
            all_strokes = self.canvas_service.get_all_strokes()
            visible_strokes = self._filter_visible_strokes(all_strokes, current_viewport)
            
            for stroke in visible_strokes:
                self.renderer.render_stroke(stroke, current_viewport)
            
            current_preview_points = self.canvas_service.get_current_preview_points()
            if current_preview_points and not self.viewport_service.is_panning_active:
                self.renderer.render_stroke_preview(current_preview_points, current_viewport, current_config)
            
        except Exception as error:
            logger.error(f"Rendering error: {error}")
    
    def clear_canvas(self) -> None:
        """Clear all strokes from canvas."""
        self.canvas_service.clear_all_strokes()
        self.event_bus.publish('canvas_cleared', None)
        logger.info("Canvas cleared")
    
    def get_current_tool(self) -> DrawingTool:
        """Get currently selected drawing tool."""
        return self.config_service.get_current_configuration().current_tool
    
    def get_current_brush_width(self) -> float:
        """Get current brush width setting."""
        return self.config_service.get_current_configuration().brush_width
    
    def get_viewport_position(self) -> Tuple[float, float]:
        """Get current viewport position in world coordinates."""
        viewport = self.viewport_service.get_current_viewport()
        return (viewport.x, viewport.y)
    
    def get_stroke_count(self) -> int:
        """Get total number of strokes on canvas."""
        return self.canvas_service.get_stroke_count()
    
    def is_drawing_active(self) -> bool:
        """Check if drawing operation is currently active."""
        return self.canvas_service.is_drawing_active
    
    def is_panning_active(self) -> bool:
        """Check if panning operation is currently active."""
        return self.viewport_service.is_panning_active
    
    def _start_drawing_at_coordinate(self, screen_coord: ScreenCoordinate) -> bool:
        """Start new drawing stroke at screen coordinate."""
        current_viewport = self.viewport_service.get_current_viewport()
        current_config = self.config_service.get_current_configuration()
        
        world_coord = screen_coord.to_world_coordinate(current_viewport.x, current_viewport.y)
        self.canvas_service.start_new_stroke(world_coord, current_config)
        
        logger.debug(f"Started drawing at world coordinate {world_coord}")
        return True
    
    def _continue_drawing_at_coordinate(self, screen_coord: ScreenCoordinate) -> bool:
        """Continue current drawing stroke at screen coordinate."""
        if not self.canvas_service.is_drawing_active:
            return False
        
        current_viewport = self.viewport_service.get_current_viewport()
        current_config = self.config_service.get_current_configuration()
        
        world_coord = screen_coord.to_world_coordinate(current_viewport.x, current_viewport.y)
        self.canvas_service.add_stroke_point(world_coord, current_config)
        
        return True
    
    def _finish_drawing(self) -> bool:
        """Complete current drawing stroke and save to canvas."""
        if not self.canvas_service.is_drawing_active:
            return False
        
        current_config = self.config_service.get_current_configuration()
        completed_stroke = self.canvas_service.complete_current_stroke(current_config)
        
        if completed_stroke:
            self.event_bus.publish('stroke_completed', completed_stroke)
            logger.debug(f"Completed stroke {completed_stroke.stroke_id}")
        
        return True
    
    def _start_panning_at_coordinate(self, screen_coord: ScreenCoordinate) -> bool:
        """Start panning operation at screen coordinate."""
        self.viewport_service.start_panning(screen_coord)
        logger.debug(f"Started panning at {screen_coord}")
        return True
    
    def _continue_panning_at_coordinate(self, screen_coord: ScreenCoordinate) -> bool:
        """Continue panning operation at screen coordinate."""
        if not self.viewport_service.is_panning_active:
            return False
        
        updated_viewport = self.viewport_service.update_panning(screen_coord)
        self.event_bus.publish('viewport_changed', updated_viewport)
        
        return True
    
    def _finish_panning(self) -> bool:
        """Complete panning operation."""
        if not self.viewport_service.is_panning_active:
            return False
        
        final_viewport = self.viewport_service.finish_panning()
        self.event_bus.publish('panning_completed', final_viewport)
        
        return True
    
    def _handle_tool_change_key(self, key: str) -> bool:
        """Handle keyboard shortcuts for tool changes and actions."""
        if key == 'space':
            new_config = self.config_service.cycle_to_next_tool()
            self.event_bus.publish('tool_changed', new_config.current_tool)
            return True
        elif key == 'c':
            self.clear_canvas()
            return True
        elif key in '12345':
            color_index = int(key) - 1
            new_config = self.config_service.cycle_color(color_index)
            self.event_bus.publish('color_changed', new_config.brush_color)
            return True
        elif key in ['+', '=']:
            new_config = self.config_service.adjust_brush_width(1.0)
            self.event_bus.publish('brush_width_changed', new_config.brush_width)
            return True
        elif key in ['-', '_']:
            new_config = self.config_service.adjust_brush_width(-1.0)
            self.event_bus.publish('brush_width_changed', new_config.brush_width)
            return True
        
        return False
    
    def _filter_visible_strokes(self, strokes: List[DrawingStroke], viewport: ViewportState) -> List[DrawingStroke]:
        """Filter strokes to only those visible in current viewport."""
        visible_strokes = []
        
        for stroke in strokes:
            min_coord, max_coord = stroke.bounding_box
            
            if (viewport.contains_world_coordinate(min_coord) or 
                viewport.contains_world_coordinate(max_coord)):
                visible_strokes.append(stroke)
        
        return visible_strokes


class InMemoryCanvasDataStore:
    """In-memory implementation of canvas data storage for testing and development."""
    
    def __init__(self):
        """Initialize empty in-memory stroke storage."""
        self.stored_strokes: List[DrawingStroke] = []
        logger.debug("Initialized in-memory canvas data store")
    
    def save_stroke(self, stroke: DrawingStroke) -> None:
        """Save stroke to in-memory storage."""
        self.stored_strokes.append(stroke)
        logger.debug(f"Saved stroke {stroke.stroke_id} to memory")
    
    def load_all_strokes(self) -> List[DrawingStroke]:
        """Load all strokes from in-memory storage."""
        return self.stored_strokes.copy()
    
    def clear_all_strokes(self) -> None:
        """Clear all strokes from in-memory storage."""
        self.stored_strokes.clear()
        logger.debug("Cleared all strokes from memory")
    
    def get_stroke_count(self) -> int:
        """Get count of strokes in memory."""
        return len(self.stored_strokes)


class StandardInputHandler:
    """Standard implementation of input handling for drawing interactions."""
    
    def __init__(self):
        """Initialize input handler with default state."""
        self.left_mouse_button = 1
        self.right_mouse_button = 3
        logger.debug("Initialized standard input handler")
    
    def handle_mouse_down(self, screen_coordinate: ScreenCoordinate, button: int) -> Optional[InputAction]:
        """Process mouse button press and determine appropriate action."""
        if button == self.right_mouse_button:
            return InputAction.START_PANNING
        elif button == self.left_mouse_button:
            return InputAction.START_DRAWING
        
        return None
    
    def handle_mouse_move(self, screen_coordinate: ScreenCoordinate) -> Optional[InputAction]:
        """Process mouse movement and determine if drawing or panning should continue."""
        return InputAction.CONTINUE_DRAWING
    
    def handle_mouse_up(self, screen_coordinate: ScreenCoordinate, button: int) -> Optional[InputAction]:
        """Process mouse button release and determine completion action."""
        if button == self.right_mouse_button:
            return InputAction.FINISH_PANNING
        elif button == self.left_mouse_button:
            return InputAction.FINISH_DRAWING
        
        return None
    
    def handle_scroll(self, direction: int) -> Optional[InputAction]:
        """Process scroll wheel input for brush size adjustment."""
        return InputAction.ADJUST_BRUSH_SIZE
    
    def handle_key_press(self, key: str) -> Optional[InputAction]:
        """Process keyboard input for tool changes and shortcuts."""
        if key in ['space', 'c', '1', '2', '3', '4', '5', '+', '=', '-', '_']:
            return InputAction.CHANGE_TOOL
        
        return None