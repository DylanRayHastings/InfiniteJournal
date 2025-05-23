"""Simplified drawing engine."""

import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional
from ..core import UniversalService, ServiceConfiguration

logger = logging.getLogger(__name__)


@dataclass
class DrawingConfiguration:
    """Drawing configuration."""
    stroke_smoothing: bool = True
    default_color: Tuple[int, int, int] = (255, 255, 255)
    default_width: int = 3


class CoordinateSystem:
    """Simple coordinate system."""
    
    def __init__(self, width, height):
        self.screen_width = width
        self.screen_height = height


@dataclass
class Stroke:
    """Drawing stroke."""
    points: List[Tuple[int, int]]
    color: Tuple[int, int, int]
    width: int
    completed: bool = False


class DrawingEngine(UniversalService):
    """Simplified drawing engine."""
    
    def __init__(self, config, backend, validation_service=None, event_bus=None, drawing_config=None):
        super().__init__(config, validation_service, event_bus)
        self.backend = backend
        self.drawing_config = drawing_config or DrawingConfiguration()
        self.coordinate_system = None
        self.strokes = []
        self.current_stroke = None
        self.is_drawing = False
        
    def _initialize_service(self):
        """Initialize drawing engine."""
        self.coordinate_system = CoordinateSystem(800, 600)
        
    def _cleanup_service(self):
        """Clean up drawing engine."""
        if self.current_stroke:
            self.finish_current_stroke()
            
    def set_screen_size(self, width, height):
        """Set screen size."""
        if self.coordinate_system:
            self.coordinate_system.screen_width = width
            self.coordinate_system.screen_height = height
            
    def start_stroke(self, pos, color, width):
        """Start new stroke."""
        if self.current_stroke:
            self.finish_current_stroke()
            
        self.current_stroke = Stroke([pos], color, width)
        self.is_drawing = True
        logger.info(f"Started stroke at {pos} with color {color}, width {width}")
        
    def add_stroke_point(self, pos):
        """Add point to current stroke."""
        if self.current_stroke:
            self.current_stroke.points.append(pos)
            logger.debug(f"Added point {pos} to current stroke (total points: {len(self.current_stroke.points)})")
            
    def finish_current_stroke(self):
        """Finish current stroke."""
        if self.current_stroke:
            self.current_stroke.completed = True
            self.strokes.append(self.current_stroke)
            logger.info(f"Finished stroke with {len(self.current_stroke.points)} points (total strokes: {len(self.strokes)})")
            self.current_stroke = None
            self.is_drawing = False
            
    def clear_canvas(self):
        """Clear canvas."""
        self.strokes.clear()
        self.current_stroke = None
        self.is_drawing = False
        
    def render_frame(self):
        """Render frame."""
        # Clear background
        if hasattr(self.backend, 'clear'):
            self.backend.clear((0, 0, 0))
        
        # Render all strokes
        rendered_strokes = 0
        for stroke in self.strokes:
            self._render_stroke(stroke)
            rendered_strokes += 1
            
        # Render current stroke
        if self.current_stroke:
            self._render_stroke(self.current_stroke)
            rendered_strokes += 1
        
        # Present frame
        if hasattr(self.backend, 'present'):
            self.backend.present()
        
        # Log occasionally to avoid spam
        if rendered_strokes > 0:
            logger.debug(f"Rendered {rendered_strokes} strokes")
            
    def _render_stroke(self, stroke):
        """Render individual stroke."""
        points = stroke.points
        if len(points) < 2:
            if points and hasattr(self.backend, 'draw_circle'):
                self.backend.draw_circle(points[0], stroke.width//2, stroke.color)
                logger.debug(f"Drew circle at {points[0]}")
            return
            
        # Draw lines between points
        if hasattr(self.backend, 'draw_line'):
            lines_drawn = 0
            for i in range(len(points) - 1):
                self.backend.draw_line(points[i], points[i+1], stroke.width, stroke.color)
                lines_drawn += 1
            logger.debug(f"Drew {lines_drawn} lines for stroke with {len(points)} points")
        else:
            logger.warning("Backend does not have draw_line method")


def create_drawing_engine(backend, validation_service=None, event_bus=None):
    """Create drawing engine."""
    config = ServiceConfiguration("drawing_engine")
    return DrawingEngine(config, backend, validation_service, event_bus)
