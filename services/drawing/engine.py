"""
Unified Drawing Engine
Eliminates ALL drawing service duplication through unified architecture.

This module consolidates drawing patterns from across the application into a
single, high-performance drawing system with universal coordinate handling.
"""

import logging
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Protocol, TypeVar
from enum import Enum

from ..core import UniversalService, ServiceConfiguration, ValidationService, EventBus

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DrawingError(Exception):
    """Base exception for drawing operations."""
    pass


class CoordinateSystemError(DrawingError):
    """Raised when coordinate system operations fail.""" 
    pass


class RenderingError(DrawingError):
    """Raised when rendering operations fail."""
    pass


@dataclass(frozen=True)
class WorldCoordinate:
    """World space coordinate with infinite precision."""
    x: float
    y: float
    
    @classmethod
    def from_world(cls, x: float, y: float) -> 'WorldCoordinate':
        """Create world coordinate from world space values."""
        return cls(float(x), float(y))
    
    def distance_to(self, other: 'WorldCoordinate') -> float:
        """Calculate distance to another coordinate."""
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)
    
    def translate(self, dx: float, dy: float) -> 'WorldCoordinate':
        """Translate coordinate by offset."""
        return WorldCoordinate(self.x + dx, self.y + dy)


@dataclass(frozen=True)
class ScreenCoordinate:
    """Screen space coordinate for rendering."""
    x: int
    y: int
    
    @classmethod
    def from_screen(cls, x: int, y: int) -> 'ScreenCoordinate':
        """Create screen coordinate from screen values."""
        return cls(int(x), int(y))
    
    def to_tuple(self) -> Tuple[int, int]:
        """Convert to tuple for rendering APIs."""
        return (self.x, self.y)


@dataclass
class ViewportState:
    """Current viewport transformation state."""
    offset_x: float = 0.0
    offset_y: float = 0.0
    scale: float = 1.0
    rotation: float = 0.0
    
    def apply_pan(self, dx: float, dy: float):
        """Apply pan transformation to viewport."""
        self.offset_x += dx
        self.offset_y += dy
    
    def apply_zoom(self, factor: float, center_x: float = 0.0, center_y: float = 0.0):
        """Apply zoom transformation around center point."""
        old_scale = self.scale
        self.scale *= factor
        
        # Adjust offset to zoom around center
        if center_x != 0.0 or center_y != 0.0:
            scale_delta = self.scale - old_scale
            self.offset_x -= center_x * scale_delta
            self.offset_y -= center_y * scale_delta


class CoordinateSystem:
    """Universal coordinate system with viewport transformations."""
    
    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.viewport = ViewportState()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def world_to_screen(self, world_coord: WorldCoordinate) -> ScreenCoordinate:
        """Transform world coordinate to screen coordinate."""
        try:
            # Apply viewport transformations
            transformed_x = (world_coord.x + self.viewport.offset_x) * self.viewport.scale
            transformed_y = (world_coord.y + self.viewport.offset_y) * self.viewport.scale
            
            # Convert to screen space
            screen_x = int(transformed_x + self.screen_width / 2)
            screen_y = int(transformed_y + self.screen_height / 2)
            
            return ScreenCoordinate(screen_x, screen_y)
            
        except Exception as error:
            raise CoordinateSystemError(f"World to screen conversion failed: {error}")
    
    def screen_to_world(self, screen_coord: ScreenCoordinate) -> WorldCoordinate:
        """Transform screen coordinate to world coordinate."""
        try:
            # Convert from screen space
            normalized_x = screen_coord.x - self.screen_width / 2
            normalized_y = screen_coord.y - self.screen_height / 2
            
            # Apply inverse viewport transformations
            world_x = (normalized_x / self.viewport.scale) - self.viewport.offset_x
            world_y = (normalized_y / self.viewport.scale) - self.viewport.offset_y
            
            return WorldCoordinate(world_x, world_y)
            
        except Exception as error:
            raise CoordinateSystemError(f"Screen to world conversion failed: {error}")
    
    def pan_viewport(self, dx: int, dy: int):
        """Pan viewport by screen pixel offset."""
        world_dx = dx / self.viewport.scale
        world_dy = dy / self.viewport.scale
        self.viewport.apply_pan(world_dx, world_dy)
        self.logger.debug(f"Viewport panned by ({world_dx:.2f}, {world_dy:.2f})")
    
    def zoom_viewport(self, factor: float, center_screen: Optional[ScreenCoordinate] = None):
        """Zoom viewport around center point."""
        if center_screen is None:
            center_screen = ScreenCoordinate(self.screen_width // 2, self.screen_height // 2)
        
        center_world = self.screen_to_world(center_screen)
        self.viewport.apply_zoom(factor, center_world.x, center_world.y)
        self.logger.debug(f"Viewport zoomed by {factor:.2f} around {center_world}")


class RenderingBackend(Protocol):
    """Protocol for rendering backends (pygame, OpenGL, etc.)."""
    
    def clear(self, color: Optional[Tuple[int, int, int]] = None) -> None:
        """Clear the rendering surface."""
        ...
    
    def present(self) -> None:
        """Present the rendered frame."""
        ...
    
    def draw_line(self, start: Tuple[int, int], end: Tuple[int, int], 
                  width: int, color: Tuple[int, int, int]) -> None:
        """Draw line between two points."""
        ...
    
    def draw_circle(self, center: Tuple[int, int], radius: int, 
                   color: Tuple[int, int, int], width: int = 0) -> None:
        """Draw circle at center with radius."""
        ...
    
    def draw_rect(self, rect: Tuple[int, int, int, int], 
                  color: Tuple[int, int, int], width: int = 0) -> None:
        """Draw rectangle."""
        ...
    
    def draw_text(self, text: str, pos: Tuple[int, int], 
                  size: int, color: Tuple[int, int, int]) -> None:
        """Draw text at position."""
        ...


@dataclass(frozen=True)
class DrawingConfiguration:
    """Configuration for drawing operations."""
    stroke_smoothing: bool = True
    max_stroke_points: int = 1000
    point_distance_threshold: float = 2.0
    default_color: Tuple[int, int, int] = (255, 255, 255)
    default_width: int = 3
    anti_aliasing: bool = True
    

class Stroke:
    """Individual stroke with points and styling."""
    
    def __init__(self, color: Tuple[int, int, int], width: int):
        self.color = color
        self.width = width
        self.points: List[WorldCoordinate] = []
        self.completed = False
    
    def add_point(self, coord: WorldCoordinate):
        """Add point to stroke."""
        self.points.append(coord)
    
    def get_bounds(self) -> Optional[Tuple[float, float, float, float]]:
        """Get stroke bounding box."""
        if not self.points:
            return None
        
        x_coords = [p.x for p in self.points]
        y_coords = [p.y for p in self.points]
        
        return (
            min(x_coords), min(y_coords),
            max(x_coords), max(y_coords)
        )
    
    def smooth_points(self, threshold: float = 2.0) -> List[WorldCoordinate]:
        """Apply smoothing to stroke points."""
        if len(self.points) < 3:
            return self.points
        
        smoothed = [self.points[0]]  # Always keep first point
        
        for i in range(1, len(self.points) - 1):
            current = self.points[i]
            prev = smoothed[-1]
            
            # Only add point if it's far enough from previous
            if current.distance_to(prev) >= threshold:
                smoothed.append(current)
        
        smoothed.append(self.points[-1])  # Always keep last point
        return smoothed


class DrawingCanvas:
    """Canvas holding all drawing data."""
    
    def __init__(self):
        self.strokes: List[Stroke] = []
        self.current_stroke: Optional[Stroke] = None
        self.background_color: Tuple[int, int, int] = (0, 0, 0)
        self.modified = False
    
    def start_stroke(self, color: Tuple[int, int, int], width: int) -> Stroke:
        """Start new stroke."""
        self.current_stroke = Stroke(color, width)
        return self.current_stroke
    
    def add_point_to_current_stroke(self, coord: WorldCoordinate):
        """Add point to current stroke."""
        if self.current_stroke:
            self.current_stroke.add_point(coord)
            self.modified = True
    
    def finish_current_stroke(self):
        """Finish current stroke and add to canvas."""
        if self.current_stroke:
            self.current_stroke.completed = True
            self.strokes.append(self.current_stroke)
            self.current_stroke = None
            self.modified = True
    
    def clear(self):
        """Clear all strokes."""
        self.strokes.clear()
        self.current_stroke = None
        self.modified = True
    
    def get_bounds(self) -> Optional[Tuple[float, float, float, float]]:
        """Get canvas bounding box."""
        if not self.strokes:
            return None
        
        all_bounds = [stroke.get_bounds() for stroke in self.strokes]
        valid_bounds = [b for b in all_bounds if b is not None]
        
        if not valid_bounds:
            return None
        
        min_x = min(b[0] for b in valid_bounds)
        min_y = min(b[1] for b in valid_bounds)
        max_x = max(b[2] for b in valid_bounds)
        max_y = max(b[3] for b in valid_bounds)
        
        return (min_x, min_y, max_x, max_y)


class DrawingEngine(UniversalService):
    """
    Unified drawing engine eliminating all drawing service duplication.
    
    Provides universal drawing operations, coordinate transformation,
    and rendering backend abstraction.
    """
    
    def __init__(
        self,
        config: ServiceConfiguration,
        backend: RenderingBackend,
        validation_service: ValidationService = None,
        event_bus: EventBus = None,
        drawing_config: DrawingConfiguration = None
    ):
        super().__init__(config, validation_service, event_bus)
        
        self.backend = backend
        self.drawing_config = drawing_config or DrawingConfiguration()
        self.coordinate_system: Optional[CoordinateSystem] = None
        self.canvas = DrawingCanvas()
        self.is_drawing = False
        
    def _initialize_service(self) -> None:
        """Initialize drawing engine service."""
        # Initialize with default screen size - will be updated when backend provides size
        self.coordinate_system = CoordinateSystem(800, 600)
        
        # Subscribe to relevant events
        if self.event_bus:
            self.event_bus.subscribe('window_resized', self._handle_window_resize)
            self.event_bus.subscribe('viewport_pan', self._handle_viewport_pan)
            self.event_bus.subscribe('viewport_zoom', self._handle_viewport_zoom)
        
        self.logger.info("Drawing engine initialized")
    
    def _cleanup_service(self) -> None:
        """Clean up drawing engine resources."""
        self.finish_current_stroke()
        self.logger.info("Drawing engine cleaned up")
    
    def set_screen_size(self, width: int, height: int):
        """Update screen size for coordinate system."""
        if self.coordinate_system:
            self.coordinate_system.screen_width = width
            self.coordinate_system.screen_height = height
            self.logger.debug(f"Screen size updated to {width}x{height}")
    
    def start_stroke(self, screen_pos: Tuple[int, int], color: Tuple[int, int, int], width: int):
        """Start new drawing stroke."""
        def _start_stroke():
            if self.is_drawing:
                self.finish_current_stroke()
            
            screen_coord = ScreenCoordinate.from_screen(*screen_pos)
            world_coord = self.coordinate_system.screen_to_world(screen_coord)
            
            self.canvas.start_stroke(color, width)
            self.canvas.add_point_to_current_stroke(world_coord)
            self.is_drawing = True
            
            if self.event_bus:
                self.event_bus.publish('stroke_started', {
                    'position': world_coord,
                    'color': color,
                    'width': width
                })
        
        return self.execute_with_error_handling("start_stroke", _start_stroke)
    
    def add_stroke_point(self, screen_pos: Tuple[int, int]):
        """Add point to current stroke."""
        def _add_point():
            if not self.is_drawing or not self.canvas.current_stroke:
                return
            
            screen_coord = ScreenCoordinate.from_screen(*screen_pos)
            world_coord = self.coordinate_system.screen_to_world(screen_coord)
            
            # Apply distance threshold if smoothing enabled
            if self.drawing_config.stroke_smoothing and self.canvas.current_stroke.points:
                last_point = self.canvas.current_stroke.points[-1]
                if world_coord.distance_to(last_point) < self.drawing_config.point_distance_threshold:
                    return
            
            self.canvas.add_point_to_current_stroke(world_coord)
            
            if self.event_bus:
                self.event_bus.publish('stroke_point_added', {
                    'position': world_coord,
                    'stroke_id': id(self.canvas.current_stroke)
                })
        
        return self.execute_with_error_handling("add_stroke_point", _add_point)
    
    def finish_current_stroke(self):
        """Finish current drawing stroke."""
        def _finish_stroke():
            if not self.is_drawing:
                return
            
            self.canvas.finish_current_stroke()
            self.is_drawing = False
            
            if self.event_bus:
                self.event_bus.publish('stroke_finished', {
                    'stroke_count': len(self.canvas.strokes)
                })
        
        return self.execute_with_error_handling("finish_stroke", _finish_stroke)
    
    def render_frame(self):
        """Render complete frame to backend."""
        def _render():
            # Clear background
            self.backend.clear(self.canvas.background_color)
            
            # Render all completed strokes
            for stroke in self.canvas.strokes:
                self._render_stroke(stroke)
            
            # Render current stroke if drawing
            if self.canvas.current_stroke and self.canvas.current_stroke.points:
                self._render_stroke(self.canvas.current_stroke)
            
            # Present frame
            self.backend.present()
        
        return self.execute_with_error_handling("render_frame", _render)
    
    def _render_stroke(self, stroke: Stroke):
        """Render individual stroke to backend."""
        if len(stroke.points) < 2:
            if len(stroke.points) == 1:
                # Render single point as small circle
                world_coord = stroke.points[0]
                screen_coord = self.coordinate_system.world_to_screen(world_coord)
                radius = max(1, stroke.width // 2)
                self.backend.draw_circle(screen_coord.to_tuple(), radius, stroke.color)
            return
        
        # Get points to render (smoothed if enabled)
        points_to_render = stroke.points
        if self.drawing_config.stroke_smoothing:
            points_to_render = stroke.smooth_points(self.drawing_config.point_distance_threshold)
        
        # Convert to screen coordinates
        screen_points = []
        for world_coord in points_to_render:
            screen_coord = self.coordinate_system.world_to_screen(world_coord)
            screen_points.append(screen_coord.to_tuple())
        
        # Render stroke as connected lines
        for i in range(len(screen_points) - 1):
            self.backend.draw_line(
                screen_points[i],
                screen_points[i + 1],
                stroke.width,
                stroke.color
            )
    
    def clear_canvas(self):
        """Clear entire drawing canvas."""
        def _clear():
            self.canvas.clear()
            self.is_drawing = False
            
            if self.event_bus:
                self.event_bus.publish('canvas_cleared', {})
        
        return self.execute_with_error_handling("clear_canvas", _clear)
    
    def pan_viewport(self, dx: int, dy: int):
        """Pan viewport by pixel offset."""
        def _pan():
            self.coordinate_system.pan_viewport(dx, dy)
            
            if self.event_bus:
                self.event_bus.publish('viewport_panned', {
                    'delta_x': dx,
                    'delta_y': dy
                })
        
        return self.execute_with_error_handling("pan_viewport", _pan)
    
    def zoom_viewport(self, factor: float, center: Optional[Tuple[int, int]] = None):
        """Zoom viewport around center point."""
        def _zoom():
            center_coord = None
            if center:
                center_coord = ScreenCoordinate.from_screen(*center)
            
            self.coordinate_system.zoom_viewport(factor, center_coord)
            
            if self.event_bus:
                self.event_bus.publish('viewport_zoomed', {
                    'factor': factor,
                    'center': center
                })
        
        return self.execute_with_error_handling("zoom_viewport", _zoom)
    
    def _handle_window_resize(self, data: Dict[str, Any]):
        """Handle window resize event."""
        width = data.get('width', 800)
        height = data.get('height', 600)
        self.set_screen_size(width, height)
    
    def _handle_viewport_pan(self, data: Dict[str, Any]):
        """Handle viewport pan event."""
        dx = data.get('dx', 0)
        dy = data.get('dy', 0)
        self.pan_viewport(dx, dy)
    
    def _handle_viewport_zoom(self, data: Dict[str, Any]):
        """Handle viewport zoom event."""
        factor = data.get('factor', 1.0)
        center = data.get('center')
        self.zoom_viewport(factor, center)


# Factory functions
def create_drawing_engine(
    backend: RenderingBackend,
    validation_service: ValidationService = None,
    event_bus: EventBus = None,
    drawing_config: DrawingConfiguration = None
) -> DrawingEngine:
    """Create drawing engine with standard configuration."""
    config = ServiceConfiguration(
        service_name="drawing_engine",
        debug_mode=False,
        auto_start=True
    )
    
    return DrawingEngine(
        config=config,
        backend=backend,
        validation_service=validation_service,
        event_bus=event_bus,
        drawing_config=drawing_config
    )


def create_pygame_backend():
    """Create pygame rendering backend."""
    # This would be implemented to wrap the pygame adapter
    # For now, return None as placeholder
    return None