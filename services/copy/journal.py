"""
Production Drawing Service.

Unified drawing service combining all drawing operations, coordinate management,
shape preview systems, and mathematical curve generation into a single,
production-ready implementation.

Quick start:
    service = ProductionDrawingService(event_bus, tool_service, database)
    service.start_stroke(100, 100, 5, (0, 0, 0))
    service.add_point(200, 200, 5)
    service.end_stroke()

Extension points:
    - Add drawing tools: Extend DrawingTool enum and add tool-specific logic
    - Add shape types: Extend ShapeType enum and implement generation functions
    - Add coordinate systems: Implement CoordinateSystem interface
    - Add preview styles: Extend PreviewStyle configuration
    - Add rendering backends: Implement RenderingBackend interface
"""

from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from abc import ABC, abstractmethod
import logging
import time
import math
import uuid

logger = logging.getLogger(__name__)

class DrawingTool(Enum):
    """Drawing tool enumeration."""
    BRUSH = "brush"
    ERASER = "eraser"
    LINE = "line"
    RECTANGLE = "rect"
    CIRCLE = "circle"
    TRIANGLE = "triangle"
    PARABOLA = "parabola"

class ShapeType(Enum):
    """Shape type enumeration."""
    LINE = "line"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    TRIANGLE = "triangle"
    PARABOLA = "parabola"

class CoordinateType(Enum):
    """Coordinate system type enumeration."""
    SCREEN = "screen"
    WORLD = "world"
    INFINITE = "infinite"

class PreviewState(Enum):
    """Preview state enumeration."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    UPDATING = "updating"

@dataclass(frozen=True)
class Point:
    """Drawing point with coordinate and width information."""
    x: float
    y: float
    timestamp: float
    width: float
    
    @classmethod
    def create_point(cls, x: float, y: float, width: float) -> 'Point':
        """Create point with current timestamp."""
        return cls(x, y, time.time(), width)

@dataclass(frozen=True)
class WorldCoordinate:
    """World coordinate representation for infinite canvas support."""
    world_x: float
    world_y: float
    
    @classmethod
    def from_screen(cls, screen_x: int, screen_y: int, viewport_offset_x: float = 0, viewport_offset_y: float = 0, zoom_factor: float = 1.0) -> 'WorldCoordinate':
        """Convert screen coordinates to world coordinates."""
        world_x = (screen_x / zoom_factor) + viewport_offset_x
        world_y = (screen_y / zoom_factor) + viewport_offset_y
        return cls(world_x, world_y)
    
    def to_screen(self, viewport_offset_x: float = 0, viewport_offset_y: float = 0, zoom_factor: float = 1.0) -> Tuple[int, int]:
        """Convert world coordinates to screen coordinates."""
        screen_x = int((self.world_x - viewport_offset_x) * zoom_factor)
        screen_y = int((self.world_y - viewport_offset_y) * zoom_factor)
        return (screen_x, screen_y)
    
    def to_world_tuple(self) -> Tuple[float, float]:
        """Convert to tuple format."""
        return (self.world_x, self.world_y)

@dataclass(frozen=True)
class PreviewStyle:
    """Preview style configuration."""
    color: Tuple[int, int, int] = (128, 128, 255)
    width: int = 2
    alpha: int = 128
    dash_pattern: Optional[List[int]] = None

@dataclass
class Stroke:
    """Drawing stroke containing points and style information."""
    id: str
    points: List[Point]
    color: Tuple[int, int, int]
    width: int
    tool: DrawingTool
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def create_stroke(cls, color: Tuple[int, int, int], width: int, tool: DrawingTool) -> 'Stroke':
        """Create new stroke with unique identifier."""
        return cls(
            id=str(uuid.uuid4()),
            points=[],
            color=color,
            width=width,
            tool=tool
        )
    
    def add_point(self, point: Point) -> None:
        """Add point to stroke."""
        self.points.append(point)
    
    def get_bounding_box(self) -> Optional[Tuple[float, float, float, float]]:
        """Get stroke bounding box as (min_x, min_y, max_x, max_y)."""
        if not self.points:
            return None
        
        x_coords = [p.x for p in self.points]
        y_coords = [p.y for p in self.points]
        
        return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))

@dataclass
class DrawingPage:
    """Drawing page containing all strokes."""
    id: str
    strokes: List[Stroke] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def create_page(cls) -> 'DrawingPage':
        """Create new drawing page."""
        return cls(id=str(uuid.uuid4()))
    
    def add_stroke(self, stroke: Stroke) -> None:
        """Add stroke to page."""
        self.strokes.append(stroke)
    
    def get_stroke_count(self) -> int:
        """Get number of strokes on page."""
        return len(self.strokes)
    
    def get_bounding_box(self) -> Optional[Tuple[float, float, float, float]]:
        """Get page bounding box containing all strokes."""
        if not self.strokes:
            return None
        
        stroke_boxes = [stroke.get_bounding_box() for stroke in self.strokes]
        valid_boxes = [box for box in stroke_boxes if box is not None]
        
        if not valid_boxes:
            return None
        
        min_x = min(box[0] for box in valid_boxes)
        min_y = min(box[1] for box in valid_boxes)
        max_x = max(box[2] for box in valid_boxes)
        max_y = max(box[3] for box in valid_boxes)
        
        return (min_x, min_y, max_x, max_y)

class CoordinateSystem(ABC):
    """Abstract coordinate system interface."""
    
    @abstractmethod
    def screen_to_world(self, screen_x: int, screen_y: int) -> WorldCoordinate:
        """Convert screen coordinates to world coordinates."""
        pass
    
    @abstractmethod
    def world_to_screen(self, world_coord: WorldCoordinate) -> Tuple[int, int]:
        """Convert world coordinates to screen coordinates."""
        pass
    
    @abstractmethod
    def get_viewport_info(self) -> Dict[str, float]:
        """Get current viewport information."""
        pass

class EventBus(ABC):
    """Abstract event bus interface."""
    
    @abstractmethod
    def subscribe(self, event_name: str, callback: Callable) -> None:
        """Subscribe to event."""
        pass
    
    @abstractmethod
    def publish(self, event_name: str, data: Any = None) -> None:
        """Publish event with optional data."""
        pass

class ToolService(ABC):
    """Abstract tool service interface."""
    
    @abstractmethod
    def get_current_tool(self) -> DrawingTool:
        """Get currently selected drawing tool."""
        pass
    
    @abstractmethod
    def get_tool_settings(self, tool: DrawingTool) -> Dict[str, Any]:
        """Get settings for specific tool."""
        pass

class DatabaseService(ABC):
    """Abstract database service interface."""
    
    @abstractmethod
    def save_page(self, page: DrawingPage) -> None:
        """Save drawing page to database."""
        pass
    
    @abstractmethod
    def load_page(self, page_id: str) -> Optional[DrawingPage]:
        """Load drawing page from database."""
        pass

class RenderingBackend(ABC):
    """Abstract rendering backend interface."""
    
    @abstractmethod
    def draw_stroke(self, points: List[Tuple[float, float]], color: Tuple[int, int, int], width: int) -> None:
        """Draw stroke with given points, color, and width."""
        pass
    
    @abstractmethod
    def draw_preview_shape(self, shape_type: ShapeType, start: Tuple[int, int], end: Tuple[int, int], style: PreviewStyle) -> None:
        """Draw preview shape during drawing."""
        pass

def validate_coordinate_input(x: Union[int, float], y: Union[int, float]) -> Tuple[float, float]:
    """Validate and normalize coordinate input."""
    try:
        normalized_x = float(x)
        normalized_y = float(y)
        return (normalized_x, normalized_y)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid coordinate input: {error}") from error

def validate_color_input(color: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Validate and normalize color input."""
    if not isinstance(color, (tuple, list)) or len(color) != 3:
        raise ValueError("Color must be a tuple/list of 3 integers")
    
    try:
        normalized_color = tuple(max(0, min(255, int(c))) for c in color)
        return normalized_color
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid color values: {error}") from error

def validate_width_input(width: Union[int, float]) -> int:
    """Validate and normalize width input."""
    try:
        normalized_width = int(width)
        return max(1, min(200, normalized_width))
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid width input: {error}") from error

def calculate_distance(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
    """Calculate Euclidean distance between two points."""
    dx = point2[0] - point1[0]
    dy = point2[1] - point1[1]
    return math.sqrt(dx * dx + dy * dy)

def generate_line_points(start: Tuple[float, float], end: Tuple[float, float], point_density: float = 2.0) -> List[Tuple[float, float]]:
    """Generate interpolated points for smooth line drawing."""
    distance = calculate_distance(start, end)
    num_points = max(2, int(distance / point_density))
    
    points = []
    for i in range(num_points + 1):
        t = i / num_points
        x = start[0] + t * (end[0] - start[0])
        y = start[1] + t * (end[1] - start[1])
        points.append((x, y))
    
    return points

def generate_circle_points(center: Tuple[float, float], radius: float, resolution: int = 36) -> List[Tuple[float, float]]:
    """Generate points for circle drawing."""
    points = []
    angle_step = 2 * math.pi / resolution
    
    for i in range(resolution + 1):
        angle = i * angle_step
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        points.append((x, y))
    
    return points

def generate_rectangle_points(start: Tuple[float, float], end: Tuple[float, float]) -> List[Tuple[float, float]]:
    """Generate points for rectangle outline."""
    x1, y1 = start
    x2, y2 = end
    
    min_x, max_x = min(x1, x2), max(x1, x2)
    min_y, max_y = min(y1, y2), max(y1, y2)
    
    points = []
    points.extend(generate_line_points((min_x, min_y), (max_x, min_y)))
    points.extend(generate_line_points((max_x, min_y), (max_x, max_y)))
    points.extend(generate_line_points((max_x, max_y), (min_x, max_y)))
    points.extend(generate_line_points((min_x, max_y), (min_x, min_y)))
    
    return points

def generate_triangle_points(start: Tuple[float, float], end: Tuple[float, float]) -> List[Tuple[float, float]]:
    """Generate points for triangle drawing."""
    x1, y1 = start
    x2, y2 = end
    x3, y3 = x2, y1
    
    points = []
    points.extend(generate_line_points((x1, y1), (x2, y2)))
    points.extend(generate_line_points((x2, y2), (x3, y3)))
    points.extend(generate_line_points((x3, y3), (x1, y1)))
    
    return points

def generate_parabola_points(start: Tuple[float, float], end: Tuple[float, float], curvature: float = 1.0, resolution: int = 50) -> List[Tuple[float, float]]:
    """Generate mathematically accurate parabola points."""
    x1, y1 = start
    x2, y2 = end
    
    if abs(x2 - x1) < 1:
        return generate_line_points(start, end)
    
    vertex_x = (x1 + x2) / 2
    vertex_y = min(y1, y2) - abs(x2 - x1) / 4 * curvature
    
    if abs(x1 - vertex_x) > 0.01:
        parabola_coefficient = (y1 - vertex_y) / ((x1 - vertex_x) ** 2)
    else:
        parabola_coefficient = 1.0
    
    points = []
    for i in range(resolution + 1):
        t = i / resolution
        x = x1 + t * (x2 - x1)
        y = parabola_coefficient * (x - vertex_x) ** 2 + vertex_y
        points.append((x, y))
    
    return points

def get_shape_generator(shape_type: ShapeType) -> Callable:
    """Get shape generation function for given shape type."""
    shape_generators = {
        ShapeType.LINE: generate_line_points,
        ShapeType.RECTANGLE: generate_rectangle_points,
        ShapeType.CIRCLE: lambda start, end: generate_circle_points(
            ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2),
            calculate_distance(start, end) / 2
        ),
        ShapeType.TRIANGLE: generate_triangle_points,
        ShapeType.PARABOLA: generate_parabola_points
    }
    
    return shape_generators.get(shape_type, generate_line_points)

def convert_tool_to_shape_type(tool: DrawingTool) -> Optional[ShapeType]:
    """Convert drawing tool to corresponding shape type."""
    tool_to_shape_map = {
        DrawingTool.LINE: ShapeType.LINE,
        DrawingTool.RECTANGLE: ShapeType.RECTANGLE,
        DrawingTool.CIRCLE: ShapeType.CIRCLE,
        DrawingTool.TRIANGLE: ShapeType.TRIANGLE,
        DrawingTool.PARABOLA: ShapeType.PARABOLA
    }
    
    return tool_to_shape_map.get(tool)

class SimpleCoordinateSystem(CoordinateSystem):
    """Simple coordinate system with viewport support."""
    
    def __init__(self, viewport_offset_x: float = 0, viewport_offset_y: float = 0, zoom_factor: float = 1.0):
        self.viewport_offset_x = viewport_offset_x
        self.viewport_offset_y = viewport_offset_y
        self.zoom_factor = zoom_factor
    
    def screen_to_world(self, screen_x: int, screen_y: int) -> WorldCoordinate:
        """Convert screen coordinates to world coordinates."""
        return WorldCoordinate.from_screen(screen_x, screen_y, self.viewport_offset_x, self.viewport_offset_y, self.zoom_factor)
    
    def world_to_screen(self, world_coord: WorldCoordinate) -> Tuple[int, int]:
        """Convert world coordinates to screen coordinates."""
        return world_coord.to_screen(self.viewport_offset_x, self.viewport_offset_y, self.zoom_factor)
    
    def get_viewport_info(self) -> Dict[str, float]:
        """Get current viewport information."""
        return {
            'offset_x': self.viewport_offset_x,
            'offset_y': self.viewport_offset_y,
            'zoom_factor': self.zoom_factor
        }
    
    def update_viewport(self, offset_x: float, offset_y: float, zoom_factor: float) -> None:
        """Update viewport parameters."""
        self.viewport_offset_x = offset_x
        self.viewport_offset_y = offset_y
        self.zoom_factor = max(0.1, min(10.0, zoom_factor))

class ShapePreviewSystem:
    """Shape preview system for real-time shape drawing feedback."""
    
    def __init__(self):
        self.preview_state = PreviewState.INACTIVE
        self.current_shape_type = None
        self.preview_start_point = None
        self.preview_end_point = None
        self.preview_style = PreviewStyle()
    
    def start_shape_preview(self, shape_type: ShapeType, start_x: int, start_y: int, style: PreviewStyle = None) -> None:
        """Start shape preview at given position."""
        self.preview_state = PreviewState.ACTIVE
        self.current_shape_type = shape_type
        self.preview_start_point = (start_x, start_y)
        self.preview_end_point = (start_x, start_y)
        self.preview_style = style or PreviewStyle()
        
        logger.debug(f"Started shape preview: {shape_type}")
    
    def update_shape_preview(self, end_x: int, end_y: int) -> None:
        """Update shape preview end position."""
        if self.preview_state == PreviewState.ACTIVE:
            self.preview_state = PreviewState.UPDATING
            self.preview_end_point = (end_x, end_y)
    
    def end_shape_preview(self) -> None:
        """End shape preview."""
        self.preview_state = PreviewState.INACTIVE
        self.current_shape_type = None
        self.preview_start_point = None
        self.preview_end_point = None
        
        logger.debug("Ended shape preview")
    
    def render_preview(self, rendering_backend: RenderingBackend) -> None:
        """Render current preview using given backend."""
        if self.preview_state in [PreviewState.ACTIVE, PreviewState.UPDATING]:
            if self.current_shape_type and self.preview_start_point and self.preview_end_point:
                rendering_backend.draw_preview_shape(
                    self.current_shape_type,
                    self.preview_start_point,
                    self.preview_end_point,
                    self.preview_style
                )
    
    def is_previewing(self) -> bool:
        """Check if currently showing preview."""
        return self.preview_state != PreviewState.INACTIVE

class ProductionDrawingService:
    """
    Production-ready drawing service with unified architecture.
    
    Provides comprehensive drawing functionality including:
    - Multi-tool drawing support (brush, eraser, shapes)
    - Coordinate system integration for infinite canvas
    - Real-time shape preview with customizable styles
    - Mathematical curve generation for accurate shapes
    - Event-driven architecture with performance optimization
    - Production-ready error handling and logging
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        tool_service: ToolService,
        database_service: DatabaseService,
        coordinate_system: Optional[CoordinateSystem] = None,
        rendering_backend: Optional[RenderingBackend] = None
    ):
        """
        Initialize production drawing service.
        
        Args:
            event_bus: Event bus for publishing drawing events
            tool_service: Service for tool management and settings
            database_service: Service for persisting drawing data
            coordinate_system: Optional coordinate system for infinite canvas
            rendering_backend: Optional rendering backend for custom drawing
        """
        self.event_bus = event_bus
        self.tool_service = tool_service
        self.database_service = database_service
        self.coordinate_system = coordinate_system or SimpleCoordinateSystem()
        self.rendering_backend = rendering_backend
        
        self.current_page = DrawingPage.create_page()
        self.shape_preview_system = ShapePreviewSystem()
        
        self.current_stroke = None
        self.current_brush_width = 5
        self.is_drawing = False
        self.drawing_start_time = 0
        self.last_event_time = 0
        self.event_throttle_interval = 0.016
        
        self.performance_cache = {}
        self.cache_valid = True
        
        self._subscribe_to_events()
        
        logger.info("Production drawing service initialized")
    
    def _subscribe_to_events(self) -> None:
        """Subscribe to relevant events from event bus."""
        self.event_bus.subscribe('brush_width_changed', self._handle_brush_width_change)
        self.event_bus.subscribe('tool_changed', self._handle_tool_change)
        self.event_bus.subscribe('viewport_changed', self._handle_viewport_change)
    
    def _handle_brush_width_change(self, new_width: int) -> None:
        """Handle dynamic brush width changes during drawing."""
        try:
            validated_width = validate_width_input(new_width)
            old_width = self.current_brush_width
            self.current_brush_width = validated_width
            
            if self.is_drawing and self.current_stroke:
                self.current_stroke.width = validated_width
                logger.debug(f"Dynamic brush width change: {old_width} -> {validated_width}")
            
        except ValueError as error:
            logger.warning(f"Invalid brush width change: {error}")
    
    def _handle_tool_change(self, new_tool: DrawingTool) -> None:
        """Handle tool changes during drawing session."""
        if self.shape_preview_system.is_previewing():
            self.shape_preview_system.end_shape_preview()
        
        logger.debug(f"Tool changed to: {new_tool}")
    
    def _handle_viewport_change(self, viewport_data: Dict[str, float]) -> None:
        """Handle viewport changes for coordinate system updates."""
        if isinstance(self.coordinate_system, SimpleCoordinateSystem):
            self.coordinate_system.update_viewport(
                viewport_data.get('offset_x', 0),
                viewport_data.get('offset_y', 0),
                viewport_data.get('zoom_factor', 1.0)
            )
        
        self._invalidate_cache()
    
    def start_stroke(self, screen_x: int, screen_y: int, width: int, color: Tuple[int, int, int]) -> None:
        """
        Begin new drawing stroke with comprehensive validation and setup.
        
        Args:
            screen_x: Screen X coordinate
            screen_y: Screen Y coordinate  
            width: Stroke width
            color: RGB color tuple
        """
        try:
            validated_coords = validate_coordinate_input(screen_x, screen_y)
            validated_color = validate_color_input(color)
            validated_width = validate_width_input(width)
            
            self.current_brush_width = validated_width
            current_tool = self.tool_service.get_current_tool()
            
            world_coord = self.coordinate_system.screen_to_world(int(validated_coords[0]), int(validated_coords[1]))
            stroke_color = self._determine_stroke_color(current_tool, validated_color)
            
            self.is_drawing = True
            self.drawing_start_time = time.time()
            
            if self._is_shape_tool(current_tool):
                self._start_shape_drawing(current_tool, world_coord, validated_coords)
            else:
                self._start_freehand_drawing(current_tool, world_coord, stroke_color, validated_width)
            
            self._invalidate_cache()
            self.event_bus.publish('stroke_started', {'tool': current_tool, 'position': validated_coords})
            
            logger.debug(f"Started stroke with tool: {current_tool}, width: {validated_width}")
            
        except ValueError as error:
            logger.error(f"Failed to start stroke: {error}")
            self.is_drawing = False
    
    def add_point(self, screen_x: int, screen_y: int, width: int) -> None:
        """
        Add point to current stroke with performance optimization.
        
        Args:
            screen_x: Screen X coordinate
            screen_y: Screen Y coordinate
            width: Point width (for dynamic width changes)
        """
        if not self.is_drawing:
            return
        
        try:
            validated_coords = validate_coordinate_input(screen_x, screen_y)
            validated_width = validate_width_input(width)
            
            current_time = time.time()
            world_coord = self.coordinate_system.screen_to_world(int(validated_coords[0]), int(validated_coords[1]))
            current_tool = self.tool_service.get_current_tool()
            
            if self._is_shape_tool(current_tool):
                self._update_shape_drawing(world_coord, validated_coords)
            else:
                self._add_freehand_point(world_coord, validated_width, current_time)
            
            self._throttled_event_publish(current_time)
            
        except ValueError as error:
            logger.error(f"Failed to add point: {error}")
    
    def end_stroke(self) -> None:
        """
        Complete current stroke with finalization and cleanup.
        """
        if not self.is_drawing:
            return
        
        try:
            current_tool = self.tool_service.get_current_tool()
            
            if self._is_shape_tool(current_tool):
                self._finalize_shape_drawing(current_tool)
            
            self._cleanup_drawing_state()
            self._save_current_page()
            
            drawing_duration = time.time() - self.drawing_start_time
            self.event_bus.publish('stroke_completed', {
                'tool': current_tool,
                'duration': drawing_duration,
                'stroke_id': self.current_stroke.id if self.current_stroke else None
            })
            
            logger.debug(f"Completed stroke in {drawing_duration:.3f} seconds")
            
        except Exception as error:
            logger.error(f"Failed to end stroke: {error}")
        finally:
            self.is_drawing = False
            self.current_stroke = None
    
    def _determine_stroke_color(self, tool: DrawingTool, input_color: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """Determine final stroke color based on tool type."""
        if tool == DrawingTool.ERASER:
            return (255, 255, 255)
        return input_color
    
    def _is_shape_tool(self, tool: DrawingTool) -> bool:
        """Check if tool is used for shape drawing."""
        shape_tools = {DrawingTool.LINE, DrawingTool.RECTANGLE, DrawingTool.CIRCLE, DrawingTool.TRIANGLE, DrawingTool.PARABOLA}
        return tool in shape_tools
    
    def _start_shape_drawing(self, tool: DrawingTool, world_coord: WorldCoordinate, screen_coords: Tuple[float, float]) -> None:
        """Initialize shape drawing with preview system."""
        shape_type = convert_tool_to_shape_type(tool)
        if shape_type:
            preview_style = PreviewStyle(
                color=(100, 150, 255),
                width=max(2, self.current_brush_width),
                alpha=128
            )
            
            self.shape_preview_system.start_shape_preview(
                shape_type,
                int(screen_coords[0]),
                int(screen_coords[1]),
                preview_style
            )
    
    def _start_freehand_drawing(self, tool: DrawingTool, world_coord: WorldCoordinate, color: Tuple[int, int, int], width: int) -> None:
        """Initialize freehand drawing stroke."""
        self.current_stroke = Stroke.create_stroke(color, width, tool)
        
        world_point = Point.create_point(world_coord.world_x, world_coord.world_y, width)
        self.current_stroke.add_point(world_point)
        
        logger.debug(f"Started freehand stroke: {self.current_stroke.id}")
    
    def _update_shape_drawing(self, world_coord: WorldCoordinate, screen_coords: Tuple[float, float]) -> None:
        """Update shape drawing preview."""
        self.shape_preview_system.update_shape_preview(int(screen_coords[0]), int(screen_coords[1]))
    
    def _add_freehand_point(self, world_coord: WorldCoordinate, width: int, current_time: float) -> None:
        """Add point to freehand stroke."""
        if self.current_stroke:
            world_point = Point.create_point(world_coord.world_x, world_coord.world_y, width)
            self.current_stroke.add_point(world_point)
            
            self.current_stroke.width = self.current_brush_width
    
    def _finalize_shape_drawing(self, tool: DrawingTool) -> None:
        """Finalize shape drawing by generating stroke from preview."""
        if not self.shape_preview_system.is_previewing():
            return
        
        start_point = self.shape_preview_system.preview_start_point
        end_point = self.shape_preview_system.preview_end_point
        
        if start_point and end_point:
            start_world = self.coordinate_system.screen_to_world(start_point[0], start_point[1])
            end_world = self.coordinate_system.screen_to_world(end_point[0], end_point[1])
            
            shape_type = convert_tool_to_shape_type(tool)
            if shape_type:
                generated_points = self._generate_shape_points(shape_type, start_world.to_world_tuple(), end_world.to_world_tuple())
                
                stroke_color = (100, 100, 100)
                self.current_stroke = Stroke.create_stroke(stroke_color, self.current_brush_width, tool)
                
                for point_coords in generated_points:
                    point = Point.create_point(point_coords[0], point_coords[1], self.current_brush_width)
                    self.current_stroke.add_point(point)
                
                logger.debug(f"Generated shape stroke with {len(generated_points)} points")
        
        self.shape_preview_system.end_shape_preview()
    
    def _generate_shape_points(self, shape_type: ShapeType, start: Tuple[float, float], end: Tuple[float, float]) -> List[Tuple[float, float]]:
        """Generate points for given shape type."""
        try:
            shape_generator = get_shape_generator(shape_type)
            
            if shape_type == ShapeType.CIRCLE:
                center = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
                radius = calculate_distance(start, end) / 2
                return shape_generator(center, radius)
            else:
                return shape_generator(start, end)
                
        except Exception as error:
            logger.error(f"Failed to generate {shape_type} points: {error}")
            return generate_line_points(start, end)
    
    def _throttled_event_publish(self, current_time: float) -> None:
        """Publish events with throttling for performance."""
        if current_time - self.last_event_time > self.event_throttle_interval:
            self.event_bus.publish('stroke_updated')
            self.last_event_time = current_time
    
    def _cleanup_drawing_state(self) -> None:
        """Clean up drawing state after stroke completion."""
        if self.current_stroke:
            self.current_page.add_stroke(self.current_stroke)
        
        if self.shape_preview_system.is_previewing():
            self.shape_preview_system.end_shape_preview()
    
    def _save_current_page(self) -> None:
        """Save current page to database with error handling."""
        try:
            self.database_service.save_page(self.current_page)
            logger.debug(f"Saved page: {self.current_page.id}")
        except Exception as error:
            logger.error(f"Failed to save page: {error}")
    
    def _invalidate_cache(self) -> None:
        """Invalidate performance cache."""
        self.cache_valid = False
        self.performance_cache.clear()
    
    def render(self, rendering_backend: RenderingBackend) -> None:
        """
        Render current drawing state using provided backend.
        
        Args:
            rendering_backend: Backend for rendering operations
        """
        try:
            self._render_page_strokes(rendering_backend)
            
            if self.shape_preview_system.is_previewing():
                self.shape_preview_system.render_preview(rendering_backend)
                
        except Exception as error:
            logger.error(f"Rendering error: {error}")
    
    def _render_page_strokes(self, rendering_backend: RenderingBackend) -> None:
        """Render all strokes on current page."""
        for stroke in self.current_page.strokes:
            if not stroke.points:
                continue
            
            screen_points = []
            for point in stroke.points:
                world_coord = WorldCoordinate(point.x, point.y)
                screen_pos = self.coordinate_system.world_to_screen(world_coord)
                screen_points.append((float(screen_pos[0]), float(screen_pos[1])))
            
            if screen_points:
                rendering_backend.draw_stroke(screen_points, stroke.color, stroke.width)
    
    def reset_page(self) -> None:
        """Reset current page and clear all drawing state."""
        self.current_page = DrawingPage.create_page()
        self.current_stroke = None
        self.is_drawing = False
        
        if self.shape_preview_system.is_previewing():
            self.shape_preview_system.end_shape_preview()
        
        self._invalidate_cache()
        self.event_bus.publish('page_reset')
        
        logger.info("Drawing page reset")
    
    def get_drawing_statistics(self) -> Dict[str, Any]:
        """Get comprehensive drawing session statistics."""
        try:
            page_bounds = self.current_page.get_bounding_box()
            viewport_info = self.coordinate_system.get_viewport_info()
            
            return {
                'stroke_count': self.current_page.get_stroke_count(),
                'is_drawing': self.is_drawing,
                'current_brush_width': self.current_brush_width,
                'page_bounds': page_bounds,
                'viewport_info': viewport_info,
                'preview_active': self.shape_preview_system.is_previewing(),
                'cache_valid': self.cache_valid,
                'page_id': self.current_page.id
            }
            
        except Exception as error:
            logger.error(f"Failed to get drawing statistics: {error}")
            return {}
    
    def export_page_data(self) -> Dict[str, Any]:
        """Export current page data for serialization."""
        try:
            stroke_data = []
            for stroke in self.current_page.strokes:
                point_data = [
                    {'x': p.x, 'y': p.y, 'width': p.width, 'timestamp': p.timestamp}
                    for p in stroke.points
                ]
                
                stroke_data.append({
                    'id': stroke.id,
                    'points': point_data,
                    'color': stroke.color,
                    'width': stroke.width,
                    'tool': stroke.tool.value,
                    'created_at': stroke.created_at.isoformat()
                })
            
            return {
                'page_id': self.current_page.id,
                'created_at': self.current_page.created_at.isoformat(),
                'strokes': stroke_data,
                'stroke_count': len(stroke_data)
            }
            
        except Exception as error:
            logger.error(f"Failed to export page data: {error}")
            return {}
    
    def import_page_data(self, page_data: Dict[str, Any]) -> bool:
        """Import page data from serialized format."""
        try:
            self.reset_page()
            
            if 'page_id' in page_data:
                self.current_page.id = page_data['page_id']
            
            if 'strokes' in page_data:
                for stroke_data in page_data['strokes']:
                    tool = DrawingTool(stroke_data.get('tool', 'brush'))
                    stroke = Stroke.create_stroke(
                        tuple(stroke_data.get('color', (0, 0, 0))),
                        stroke_data.get('width', 5),
                        tool
                    )
                    
                    stroke.id = stroke_data.get('id', stroke.id)
                    
                    for point_data in stroke_data.get('points', []):
                        point = Point(
                            point_data['x'],
                            point_data['y'], 
                            point_data.get('timestamp', time.time()),
                            point_data.get('width', 5)
                        )
                        stroke.add_point(point)
                    
                    self.current_page.add_stroke(stroke)
            
            self.event_bus.publish('page_imported', {'stroke_count': len(page_data.get('strokes', []))})
            logger.info(f"Imported page with {self.current_page.get_stroke_count()} strokes")
            
            return True
            
        except Exception as error:
            logger.error(f"Failed to import page data: {error}")
            return False