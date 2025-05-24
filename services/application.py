"""
Optimized Drawing Application with Infinite Panning.

Clean, modular implementation designed for senior developers.
Eliminates duplication, maximizes reusability, ensures production readiness.
"""

import time
import logging
from typing import Protocol, Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Point:
    """Immutable 2D point."""
    x: float
    y: float


@dataclass(frozen=True)
class Color:
    """Immutable RGB color."""
    r: int
    g: int
    b: int
    
    @classmethod
    def from_tuple(cls, rgb: Tuple[int, int, int]) -> 'Color':
        """Create color from RGB tuple."""
        return cls(rgb[0], rgb[1], rgb[2])
    
    def to_tuple(self) -> Tuple[int, int, int]:
        """Convert to RGB tuple."""
        return (self.r, self.g, self.b)


@dataclass(frozen=True)
class ViewportState:
    """Immutable viewport state."""
    offset_x: float
    offset_y: float
    
    def translate(self, dx: float, dy: float) -> 'ViewportState':
        """Create new viewport state with translation."""
        return ViewportState(self.offset_x + dx, self.offset_y + dy)


@dataclass(frozen=True)
class DrawingStroke:
    """Immutable drawing stroke."""
    points: List[Point]
    color: Color
    width: int


@dataclass(frozen=True)
class ApplicationConfig:
    """Application configuration."""
    window_width: int = 1280
    window_height: int = 720
    window_title: str = "Drawing Application"
    target_fps: int = 60
    pan_sensitivity: float = 1.0
    arrow_key_speed: int = 20
    max_brush_size: int = 100
    min_brush_size: int = 1
    background_color: Color = Color(15, 15, 15)
    grid_color: Color = Color(30, 30, 30)
    grid_spacing: int = 40


class ValidationError(Exception):
    """Input validation error."""
    pass


class CoordinateTransformer:
    """Handles coordinate system transformations."""
    
    def __init__(self, viewport_state: ViewportState):
        self.viewport_state = viewport_state
    
    def screen_to_world(self, screen_point: Point) -> Point:
        """Transform screen coordinates to world coordinates."""
        return Point(
            screen_point.x + self.viewport_state.offset_x,
            screen_point.y + self.viewport_state.offset_y
        )
    
    def world_to_screen(self, world_point: Point) -> Point:
        """Transform world coordinates to screen coordinates."""
        return Point(
            world_point.x - self.viewport_state.offset_x,
            world_point.y - self.viewport_state.offset_y
        )


class InputValidator:
    """Validates user input."""
    
    @staticmethod
    def validate_brush_size(size: int, min_size: int, max_size: int) -> int:
        """Validate and clamp brush size."""
        if size < min_size:
            return min_size
        if size > max_size:
            return max_size
        return size
    
    @staticmethod
    def validate_point(point: Point) -> None:
        """Validate point coordinates."""
        if not isinstance(point.x, (int, float)) or not isinstance(point.y, (int, float)):
            raise ValidationError("Point coordinates must be numeric")
    
    @staticmethod
    def validate_color(color: Color) -> None:
        """Validate color values."""
        for component in [color.r, color.g, color.b]:
            if not 0 <= component <= 255:
                raise ValidationError("Color components must be between 0 and 255")


class BackendProtocol(Protocol):
    """Backend interface for rendering operations."""
    
    def clear(self, color: Tuple[int, int, int]) -> None:
        """Clear screen with background color."""
        ...
    
    def draw_line(self, start: Tuple[int, int], end: Tuple[int, int], width: int, color: Tuple[int, int, int]) -> None:
        """Draw line between two points."""
        ...
    
    def draw_circle(self, center: Tuple[int, int], radius: int, color: Tuple[int, int, int]) -> None:
        """Draw filled circle."""
        ...
    
    def draw_text(self, text: str, position: Tuple[int, int], size: int, color: Tuple[int, int, int]) -> None:
        """Draw text at position."""
        ...
    
    def present(self) -> None:
        """Present rendered frame."""
        ...
    
    def poll_events(self) -> List[Any]:
        """Poll for input events."""
        ...


class EventProcessor:
    """Processes and normalizes input events."""
    
    def process_mouse_event(self, event: Any) -> Optional[Dict[str, Any]]:
        """Process mouse event into normalized format."""
        try:
            event_type = getattr(event, 'type', None)
            event_data = getattr(event, 'data', {})
            
            if event_type in ['MOUSE_DOWN', 'MOUSEBUTTONDOWN']:
                return {
                    'type': 'mouse_press',
                    'position': Point(*event_data.get('pos', (0, 0))),
                    'button': event_data.get('button', 1)
                }
            
            if event_type in ['MOUSE_UP', 'MOUSEBUTTONUP']:
                return {
                    'type': 'mouse_release',
                    'position': Point(*event_data.get('pos', (0, 0))),
                    'button': event_data.get('button', 1)
                }
            
            if event_type in ['MOUSE_MOVE', 'MOUSEMOTION']:
                return {
                    'type': 'mouse_move',
                    'position': Point(*event_data.get('pos', (0, 0)))
                }
                
            return None
            
        except Exception as error:
            logger.warning(f"Failed to process mouse event: {error}")
            return None
    
    def process_keyboard_event(self, event: Any) -> Optional[Dict[str, Any]]:
        """Process keyboard event into normalized format."""
        try:
            event_type = getattr(event, 'type', None)
            event_data = getattr(event, 'data', {})
            
            if event_type in ['KEY_PRESS', 'KEYDOWN']:
                key = str(event_data.get('key', '')).lower()
                return {'type': 'key_press', 'key': key}
            
            if event_type in ['KEY_UP', 'KEYUP']:
                key = str(event_data.get('key', '')).lower()
                return {'type': 'key_release', 'key': key}
                
            return None
            
        except Exception as error:
            logger.warning(f"Failed to process keyboard event: {error}")
            return None


class ViewportController:
    """Controls viewport panning operations."""
    
    def __init__(self, config: ApplicationConfig):
        self.config = config
        self.viewport_state = ViewportState(0, 0)
        self.is_panning = False
        self.last_mouse_position: Optional[Point] = None
        self.active_keys: set = set()
    
    def start_panning(self, mouse_position: Point) -> None:
        """Start mouse panning operation."""
        self.is_panning = True
        self.last_mouse_position = mouse_position
        logger.debug(f"Panning started at {mouse_position}")
    
    def update_panning(self, mouse_position: Point) -> bool:
        """Update mouse panning with current position."""
        if not self.is_panning or not self.last_mouse_position:
            return False
        
        dx = (mouse_position.x - self.last_mouse_position.x) * self.config.pan_sensitivity
        dy = (mouse_position.y - self.last_mouse_position.y) * self.config.pan_sensitivity
        
        self.viewport_state = self.viewport_state.translate(dx, dy)
        self.last_mouse_position = mouse_position
        
        logger.debug(f"Viewport panned by ({dx:.1f}, {dy:.1f})")
        return True
    
    def stop_panning(self) -> None:
        """Stop panning operation."""
        self.is_panning = False
        self.last_mouse_position = None
        logger.debug("Panning stopped")
    
    def handle_key_press(self, key: str) -> bool:
        """Handle arrow key press for panning."""
        if key in ['up', 'down', 'left', 'right']:
            self.active_keys.add(key)
            return True
        return False
    
    def handle_key_release(self, key: str) -> bool:
        """Handle arrow key release."""
        if key in self.active_keys:
            self.active_keys.remove(key)
            return True
        return False
    
    def update_keyboard_panning(self, delta_time: float) -> bool:
        """Update keyboard-based panning."""
        if not self.active_keys:
            return False
        
        speed = self.config.arrow_key_speed * delta_time * 60
        dx = dy = 0
        
        if 'left' in self.active_keys:
            dx -= speed
        if 'right' in self.active_keys:
            dx += speed
        if 'up' in self.active_keys:
            dy -= speed
        if 'down' in self.active_keys:
            dy += speed
        
        if dx != 0 or dy != 0:
            self.viewport_state = self.viewport_state.translate(dx, dy)
            return True
        
        return False
    
    def reset_viewport(self) -> None:
        """Reset viewport to origin."""
        self.viewport_state = ViewportState(0, 0)
        logger.info("Viewport reset to origin")


class DrawingEngine:
    """Manages drawing operations and stroke storage."""
    
    def __init__(self, validator: InputValidator):
        self.validator = validator
        self.strokes: List[DrawingStroke] = []
        self.current_stroke_points: List[Point] = []
        self.current_color = Color(255, 0, 0)
        self.current_width = 5
        self.is_drawing = False
    
    def start_stroke(self, world_position: Point, color: Color, width: int) -> None:
        """Start new drawing stroke."""
        self.validator.validate_point(world_position)
        self.validator.validate_color(color)
        
        self.current_stroke_points = [world_position]
        self.current_color = color
        self.current_width = width
        self.is_drawing = True
        
        logger.debug(f"Stroke started at {world_position}")
    
    def add_stroke_point(self, world_position: Point) -> None:
        """Add point to current stroke."""
        if not self.is_drawing:
            return
        
        self.validator.validate_point(world_position)
        self.current_stroke_points.append(world_position)
    
    def finish_stroke(self) -> None:
        """Finish current stroke and add to collection."""
        if not self.is_drawing or not self.current_stroke_points:
            return
        
        stroke = DrawingStroke(
            points=self.current_stroke_points.copy(),
            color=self.current_color,
            width=self.current_width
        )
        
        self.strokes.append(stroke)
        self.current_stroke_points.clear()
        self.is_drawing = False
        
        logger.debug(f"Stroke finished with {len(stroke.points)} points")
    
    def clear_canvas(self) -> None:
        """Clear all strokes from canvas."""
        self.strokes.clear()
        self.current_stroke_points.clear()
        self.is_drawing = False
        logger.info("Canvas cleared")


class GridRenderer:
    """Renders infinite grid background."""
    
    def __init__(self, config: ApplicationConfig):
        self.config = config
    
    def render_grid(self, backend: BackendProtocol, viewport_state: ViewportState) -> None:
        """Render infinite grid with viewport offset."""
        try:
            spacing = self.config.grid_spacing
            color = self.config.grid_color.to_tuple()
            
            start_x = (-viewport_state.offset_x % spacing) - spacing
            start_y = (-viewport_state.offset_y % spacing) - spacing
            
            self._render_vertical_lines(backend, start_x, spacing, color)
            self._render_horizontal_lines(backend, start_y, spacing, color)
            
        except Exception as error:
            logger.warning(f"Grid rendering failed: {error}")
    
    def _render_vertical_lines(self, backend: BackendProtocol, start_x: float, spacing: int, color: Tuple[int, int, int]) -> None:
        """Render vertical grid lines."""
        x = start_x
        while x < self.config.window_width:
            if 0 <= x < self.config.window_width:
                backend.draw_line(
                    (int(x), 0),
                    (int(x), self.config.window_height),
                    1, color
                )
            x += spacing
    
    def _render_horizontal_lines(self, backend: BackendProtocol, start_y: float, spacing: int, color: Tuple[int, int, int]) -> None:
        """Render horizontal grid lines."""
        y = start_y
        while y < self.config.window_height:
            if 0 <= y < self.config.window_height:
                backend.draw_line(
                    (0, int(y)),
                    (self.config.window_width, int(y)),
                    1, color
                )
            y += spacing


class StrokeRenderer:
    """Renders drawing strokes with coordinate transformation."""
    
    def __init__(self, config: ApplicationConfig):
        self.config = config
    
    def render_strokes(self, backend: BackendProtocol, strokes: List[DrawingStroke], transformer: CoordinateTransformer) -> None:
        """Render all strokes with coordinate transformation."""
        for stroke in strokes:
            self._render_single_stroke(backend, stroke, transformer)
    
    def _render_single_stroke(self, backend: BackendProtocol, stroke: DrawingStroke, transformer: CoordinateTransformer) -> None:
        """Render single stroke."""
        try:
            screen_points = [transformer.world_to_screen(point) for point in stroke.points]
            visible_points = [p for p in screen_points if self._is_point_visible(p)]
            
            if not visible_points:
                return
            
            if len(visible_points) == 1:
                self._render_single_point(backend, visible_points[0], stroke)
            else:
                self._render_stroke_lines(backend, visible_points, stroke)
                
        except Exception as error:
            logger.debug(f"Stroke rendering error: {error}")
    
    def _render_single_point(self, backend: BackendProtocol, point: Point, stroke: DrawingStroke) -> None:
        """Render single point as circle."""
        backend.draw_circle(
            (int(point.x), int(point.y)),
            stroke.width // 2,
            stroke.color.to_tuple()
        )
    
    def _render_stroke_lines(self, backend: BackendProtocol, points: List[Point], stroke: DrawingStroke) -> None:
        """Render stroke as connected lines."""
        for i in range(len(points) - 1):
            start = points[i]
            end = points[i + 1]
            
            backend.draw_line(
                (int(start.x), int(start.y)),
                (int(end.x), int(end.y)),
                stroke.width,
                stroke.color.to_tuple()
            )
    
    def _is_point_visible(self, point: Point) -> bool:
        """Check if point is visible on screen."""
        margin = 50
        return (-margin <= point.x <= self.config.window_width + margin and
                -margin <= point.y <= self.config.window_height + margin)


class UserInterfaceRenderer:
    """Renders user interface elements."""
    
    def __init__(self, config: ApplicationConfig):
        self.config = config
        self.text_color = Color(255, 255, 255)
    
    def render_interface(self, backend: BackendProtocol, current_tool: str, brush_size: int, viewport_state: ViewportState) -> None:
        """Render complete user interface."""
        try:
            self._render_tool_info(backend, current_tool, brush_size)
            self._render_viewport_info(backend, viewport_state)
            self._render_controls_help(backend)
            
        except Exception as error:
            logger.warning(f"UI rendering failed: {error}")
    
    def _render_tool_info(self, backend: BackendProtocol, current_tool: str, brush_size: int) -> None:
        """Render tool and brush information."""
        backend.draw_text(f"Tool: {current_tool.title()}", (10, 10), 20, self.text_color.to_tuple())
        backend.draw_text(f"Size: {brush_size}", (10, 35), 20, self.text_color.to_tuple())
    
    def _render_viewport_info(self, backend: BackendProtocol, viewport_state: ViewportState) -> None:
        """Render viewport position information."""
        position_text = f"Position: ({viewport_state.offset_x:.0f}, {viewport_state.offset_y:.0f})"
        backend.draw_text(position_text, (10, 60), 18, Color(200, 200, 255).to_tuple())
    
    def _render_controls_help(self, backend: BackendProtocol) -> None:
        """Render controls help text."""
        help_text = "Controls: Right-drag/Arrows=Pan, T=Tool, Wheel=Size, Space=Clear, R=Reset"
        help_y = self.config.window_height - 25
        backend.draw_text(help_text, (10, help_y), 14, Color(180, 180, 180).to_tuple())


class ToolManager:
    """Manages drawing tools and brush settings."""
    
    def __init__(self, config: ApplicationConfig, validator: InputValidator):
        self.config = config
        self.validator = validator
        self.available_tools = ["brush", "eraser", "pan"]
        self.current_tool = "brush"
        self.current_tool_index = 0
        self.brush_size = 5
    
    def cycle_tool(self) -> str:
        """Cycle to next available tool."""
        self.current_tool_index = (self.current_tool_index + 1) % len(self.available_tools)
        self.current_tool = self.available_tools[self.current_tool_index]
        logger.info(f"Tool changed to: {self.current_tool}")
        return self.current_tool
    
    def set_tool(self, tool_name: str) -> bool:
        """Set specific tool by name."""
        if tool_name in self.available_tools:
            self.current_tool = tool_name
            self.current_tool_index = self.available_tools.index(tool_name)
            logger.info(f"Tool set to: {self.current_tool}")
            return True
        return False
    
    def adjust_brush_size(self, delta: int) -> int:
        """Adjust brush size by delta amount."""
        new_size = self.brush_size + delta
        self.brush_size = self.validator.validate_brush_size(
            new_size, self.config.min_brush_size, self.config.max_brush_size
        )
        logger.debug(f"Brush size adjusted to: {self.brush_size}")
        return self.brush_size
    
    def get_current_color(self) -> Color:
        """Get current drawing color based on tool."""
        if self.current_tool == "eraser":
            return self.config.background_color
        return Color(255, 0, 0)


class DrawingApplication:
    """Main drawing application with panning support."""
    
    def __init__(self, backend: BackendProtocol, config: ApplicationConfig = None):
        self.backend = backend
        self.config = config or ApplicationConfig()
        self.running = False
        
        self.validator = InputValidator()
        self.event_processor = EventProcessor()
        self.viewport_controller = ViewportController(self.config)
        self.drawing_engine = DrawingEngine(self.validator)
        self.tool_manager = ToolManager(self.config, self.validator)
        
        self.grid_renderer = GridRenderer(self.config)
        self.stroke_renderer = StrokeRenderer(self.config)
        self.ui_renderer = UserInterfaceRenderer(self.config)
        
        self.last_frame_time = time.time()
        
        logger.info("Drawing application initialized")
    
    def run(self) -> None:
        """Run main application loop."""
        self.running = True
        target_frame_time = 1.0 / self.config.target_fps
        
        logger.info("Starting drawing application")
        
        while self.running:
            frame_start = time.time()
            
            try:
                delta_time = self._calculate_delta_time()
                
                self._process_events()
                self._update_systems(delta_time)
                self._render_frame()
                
                self._manage_frame_timing(frame_start, target_frame_time)
                
            except Exception as error:
                logger.error(f"Application loop error: {error}")
                if hasattr(self.config, 'debug_mode') and self.config.debug_mode:
                    raise
        
        logger.info("Application loop ended")
    
    def _calculate_delta_time(self) -> float:
        """Calculate time since last frame."""
        current_time = time.time()
        delta_time = current_time - self.last_frame_time
        self.last_frame_time = current_time
        return delta_time
    
    def _process_events(self) -> None:
        """Process all input events."""
        try:
            events = self.backend.poll_events()
            
            for event in events:
                self._handle_single_event(event)
                
        except Exception as error:
            logger.warning(f"Event processing error: {error}")
    
    def _handle_single_event(self, event: Any) -> None:
        """Handle single input event."""
        if hasattr(event, 'type') and event.type == 'QUIT':
            self.running = False
            return
        
        mouse_event = self.event_processor.process_mouse_event(event)
        if mouse_event:
            self._handle_mouse_event(mouse_event)
            return
        
        keyboard_event = self.event_processor.process_keyboard_event(event)
        if keyboard_event:
            self._handle_keyboard_event(keyboard_event)
    
    def _handle_mouse_event(self, event: Dict[str, Any]) -> None:
        """Handle processed mouse event."""
        event_type = event['type']
        position = event['position']
        
        if event_type == 'mouse_press':
            self._handle_mouse_press(position, event.get('button', 1))
        elif event_type == 'mouse_release':
            self._handle_mouse_release(position, event.get('button', 1))
        elif event_type == 'mouse_move':
            self._handle_mouse_move(position)
    
    def _handle_mouse_press(self, position: Point, button: int) -> None:
        """Handle mouse press event."""
        if button == 3 or self.tool_manager.current_tool == "pan":
            self.viewport_controller.start_panning(position)
            return
        
        if button == 1 and self.tool_manager.current_tool in ["brush", "eraser"]:
            transformer = CoordinateTransformer(self.viewport_controller.viewport_state)
            world_position = transformer.screen_to_world(position)
            
            color = self.tool_manager.get_current_color()
            width = self.tool_manager.brush_size
            
            if self.tool_manager.current_tool == "eraser":
                width *= 2
            
            self.drawing_engine.start_stroke(world_position, color, width)
    
    def _handle_mouse_release(self, position: Point, button: int) -> None:
        """Handle mouse release event."""
        if button == 3 or self.tool_manager.current_tool == "pan":
            self.viewport_controller.stop_panning()
            return
        
        if button == 1 and self.drawing_engine.is_drawing:
            self.drawing_engine.finish_stroke()
    
    def _handle_mouse_move(self, position: Point) -> None:
        """Handle mouse move event."""
        if self.viewport_controller.update_panning(position):
            return
        
        if self.drawing_engine.is_drawing:
            transformer = CoordinateTransformer(self.viewport_controller.viewport_state)
            world_position = transformer.screen_to_world(position)
            self.drawing_engine.add_stroke_point(world_position)
    
    def _handle_keyboard_event(self, event: Dict[str, Any]) -> None:
        """Handle processed keyboard event."""
        event_type = event['type']
        key = event['key']
        
        if event_type == 'key_press':
            self._handle_key_press(key)
        elif event_type == 'key_release':
            self._handle_key_release(key)
    
    def _handle_key_press(self, key: str) -> None:
        """Handle key press event."""
        if self.viewport_controller.handle_key_press(key):
            return
        
        if key == 't':
            self.tool_manager.cycle_tool()
        elif key == 'p':
            self.tool_manager.set_tool("pan")
        elif key == 'r':
            self.viewport_controller.reset_viewport()
        elif key == 'space':
            self.drawing_engine.clear_canvas()
        elif key == 'escape':
            self.running = False
    
    def _handle_key_release(self, key: str) -> None:
        """Handle key release event."""
        self.viewport_controller.handle_key_release(key)
    
    def _update_systems(self, delta_time: float) -> None:
        """Update all application systems."""
        self.viewport_controller.update_keyboard_panning(delta_time)
    
    def _render_frame(self) -> None:
        """Render complete frame."""
        try:
            self.backend.clear(self.config.background_color.to_tuple())
            
            transformer = CoordinateTransformer(self.viewport_controller.viewport_state)
            
            self.grid_renderer.render_grid(self.backend, self.viewport_controller.viewport_state)
            self.stroke_renderer.render_strokes(self.backend, self.drawing_engine.strokes, transformer)
            
            if self.drawing_engine.is_drawing and self.drawing_engine.current_stroke_points:
                current_stroke = DrawingStroke(
                    points=self.drawing_engine.current_stroke_points,
                    color=self.drawing_engine.current_color,
                    width=self.drawing_engine.current_width
                )
                self.stroke_renderer._render_single_stroke(self.backend, current_stroke, transformer)
            
            self.ui_renderer.render_interface(
                self.backend,
                self.tool_manager.current_tool,
                self.tool_manager.brush_size,
                self.viewport_controller.viewport_state
            )
            
            self.backend.present()
            
        except Exception as error:
            logger.error(f"Frame rendering error: {error}")
    
    def _manage_frame_timing(self, frame_start: float, target_frame_time: float) -> None:
        """Manage frame timing for consistent framerate."""
        frame_time = time.time() - frame_start
        
        if frame_time < target_frame_time:
            time.sleep(target_frame_time - frame_time)


def create_drawing_application(backend: BackendProtocol, config: ApplicationConfig = None) -> DrawingApplication:
    """Create and configure drawing application."""
    config = config or ApplicationConfig()
    application = DrawingApplication(backend, config)
    
    logger.info("Drawing application created successfully")
    return application