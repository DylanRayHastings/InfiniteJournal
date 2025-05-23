# services/journal.py (Fixed brush width persistence and preview system)
"""Journal service with fixed brush width persistence and robust shape preview."""

from core.event_bus import EventBus
from core.drawing.models import Page, Point
from core.interfaces import Stroke
from services.database import CanvasDatabase
from services.tools import ToolService
from services.calculator import get_line, get_triangle, get_parabola, get_rectangle, get_circle
import logging
import time
import math
from typing import List, Tuple, Any, Optional

# Constants for tool modes
_TOOL_MODES_SIMPLE = {'brush', 'eraser'}
_SHAPED_MODES = {'line', 'rect', 'circle', 'triangle', 'parabola'}

logger = logging.getLogger(__name__)


class JournalService:
    """
    Service for recording, persisting, and rendering drawing strokes with fixed brush width and preview.
    """

    def __init__(self, bus: EventBus, tool_service: ToolService, database: CanvasDatabase) -> None:
        """
        Initialize JournalService with fixed brush width handling.
        """
        if bus is None:
            raise ValueError('bus must not be None')
        if tool_service is None:
            raise ValueError('tool_service must not be None')
        if database is None:
            raise ValueError('database must not be None')

        self._bus = bus
        self._tool_service = tool_service
        self._database = database
        self._page = Page()
        self._current_stroke = None
        self._start_point = None
        self._last_point = None
        
        # Shape preview system - more robust
        self._preview_stroke = None
        self._is_drawing_shape = False
        self._preview_start_point = None
        self._preview_end_point = None
        
        # Performance optimizations
        self._last_event_time = 0
        self._event_throttle_interval = 0.05  # 20 FPS for events
        
        # Rendering optimization
        self._stroke_cache = []
        self._cache_valid = True
        
        # Dynamic brush width tracking - FIXED
        self._current_brush_width = 5
        bus.subscribe('brush_width_changed', self._on_brush_width_changed)
        
        logger.info("JournalService initialized with fixed brush width handling")

    def _on_brush_width_changed(self, width: int) -> None:
        """Handle brush width changes from hotbar."""
        self._current_brush_width = width
        logger.debug("Journal brush width updated to: %d", width)

    def reset(self) -> None:
        """Clear current page and reset state."""
        self._page = Page()
        self._current_stroke = None
        self._preview_stroke = None
        self._start_point = None
        self._last_point = None
        self._is_drawing_shape = False
        self._preview_start_point = None
        self._preview_end_point = None
        self._stroke_cache.clear()
        self._cache_valid = False
        logger.info("Journal reset")

    def start_stroke(self, x: int, y: int, width: int, color: Tuple[int, int, int]) -> None:
        """
        Begin a new stroke with FIXED width handling.
        """
        mode = self._tool_service.current_tool_mode
        stroke_color = (0, 0, 0) if mode == 'eraser' else color
        
        # Use current brush width from hotbar - CRITICAL FIX
        actual_width = self._current_brush_width
        logger.debug("Starting stroke with width: %d (mode: %s)", actual_width, mode)

        # Create stroke with proper width
        self._current_stroke = self._page.new_stroke(stroke_color, actual_width)
        self._start_point = Point(x, y, 0, actual_width)
        self._last_point = self._start_point
        
        # Shape preview system - FIXED
        self._is_drawing_shape = mode in _SHAPED_MODES
        if self._is_drawing_shape:
            # Store preview points separately
            self._preview_start_point = Point(x, y, 0, 1)  # Thin preview
            self._preview_end_point = Point(x, y, 0, 1)
            # Create preview stroke that won't interfere with main stroke
            self._preview_stroke = Stroke(color=(128, 128, 128), width=1)  # Gray, thin
            logger.debug("Started shape preview for mode: %s", mode)
        
        self._cache_valid = False

        if mode in _TOOL_MODES_SIMPLE:
            # Add initial point for brush/eraser with correct width
            self._current_stroke.add_point(self._start_point)
            logger.debug("Added initial point with width: %d", actual_width)

    def add_point(self, x: int, y: int, width: int) -> None:
        """
        Add a point with FIXED width handling.
        """
        if not self._current_stroke:
            return

        # ALWAYS use current brush width - ignore parameter
        actual_width = self._current_brush_width
        current_time = time.time()
        
        # For shaped tools, update preview
        if self._is_drawing_shape:
            self._preview_end_point = Point(x, y, 0, 1)
            self._update_shape_preview()
            return

        # For brush/eraser: Add point with correct width
        point = Point(x, y, 0, actual_width)
        self._current_stroke.add_point(point)
        self._last_point = point
        
        # Throttle event publishing
        if current_time - self._last_event_time > self._event_throttle_interval:
            self._bus.publish('stroke_added')
            self._last_event_time = current_time

    def end_stroke(self) -> None:
        """
        Finalize stroke with FIXED preview handling.
        """
        if not self._current_stroke or not self._start_point:
            return

        mode = self._tool_service.current_tool_mode
        try:
            if mode in _SHAPED_MODES and self._preview_end_point:
                # Apply final shape with proper width
                self._apply_final_shape(mode)
                
            self._cache_valid = False
            self._bus.publish('stroke_added')
            logger.debug("Stroke completed with mode: %s", mode)
        except Exception as e:
            logger.error('Failed to end stroke: %s', e)
        finally:
            # Clean up all state
            self._current_stroke = None
            self._preview_stroke = None
            self._start_point = None
            self._last_point = None
            self._is_drawing_shape = False
            self._preview_start_point = None
            self._preview_end_point = None

    def _update_shape_preview(self) -> None:
        """Update shape preview - ROBUST version."""
        if not self._is_drawing_shape or not self._preview_start_point or not self._preview_end_point:
            return
            
        mode = self._tool_service.current_tool_mode
        
        try:
            # Calculate preview shape points
            preview_points = self._calculate_shape(
                mode, 
                self._preview_start_point.x, self._preview_start_point.y,
                self._preview_end_point.x, self._preview_end_point.y,
                width=1  # Thin preview
            )
            
            # Update preview stroke points
            if self._preview_stroke:
                self._preview_stroke.points = preview_points
                
        except Exception as e:
            logger.error("Error updating shape preview: %s", e)

    def _apply_final_shape(self, mode: str) -> None:
        """Apply final shape with proper width."""
        if not self._preview_end_point:
            self._preview_end_point = self._start_point
            
        start = self._start_point
        end = self._preview_end_point
        
        try:
            # Calculate final shape with proper width
            shape_points = self._calculate_shape(
                mode, start.x, start.y, end.x, end.y, 
                width=self._current_brush_width
            )
            self._current_stroke.points = shape_points
            logger.debug("Applied final shape %s with width: %d", mode, self._current_brush_width)
        except Exception as e:
            logger.error("Error applying final shape %s: %s", mode, e)
            # Fallback to simple line with correct width
            self._current_stroke.points = [
                Point(start.x, start.y, 0, self._current_brush_width),
                Point(end.x, end.y, 0, self._current_brush_width)
            ]

    def render(self, renderer: Any) -> None:
        """
        Render all strokes with FIXED width handling.
        """
        if not self._page:
            return
            
        # Render completed strokes
        self._render_strokes(renderer)
        
        # Render shape preview if active
        if self._is_drawing_shape and self._preview_stroke and self._preview_stroke.points:
            self._render_preview(renderer)

    def _render_strokes(self, renderer: Any) -> None:
        """Render completed strokes with proper width."""
        for stroke in self._page.strokes:
            if not stroke.points:
                continue
                
            try:
                # Convert points
                points = [(float(p.x), float(p.y)) for p in stroke.points 
                         if hasattr(p, 'x') and hasattr(p, 'y')]
                
                if points and hasattr(renderer, 'draw_stroke'):
                    # Use stroke width (which is properly maintained)
                    color = stroke.color if isinstance(stroke.color, (tuple, list)) and len(stroke.color) == 3 else (255, 255, 255)
                    width = stroke.width  # Use the stroke's width property
                    
                    renderer.draw_stroke(points, color, width)
                    
            except Exception as e:
                logger.error("Error rendering stroke: %s", e)
                continue

    def _render_preview(self, renderer: Any) -> None:
        """Render shape preview with thin gray line."""
        try:
            points = [(float(p.x), float(p.y)) for p in self._preview_stroke.points 
                     if hasattr(p, 'x') and hasattr(p, 'y')]
            
            if points and hasattr(renderer, 'draw_stroke'):
                # Gray preview with thin line
                renderer.draw_stroke(points, (128, 128, 128), 1)
                
        except Exception as e:
            logger.error("Error rendering preview: %s", e)

    @staticmethod
    def _calculate_shape(mode: str, x0: float, y0: float, x1: float, y1: float, width: int = 1) -> List[Point]:
        """
        Calculate shape points with specified width.
        """
        try:
            if mode == 'line':
                raw_points = get_line(int(x0), int(y0), int(x1), int(y1))
                return [Point(x, y, 0, width) for x, y in raw_points]
            elif mode == 'rect':
                raw_points = get_rectangle(int(x0), int(y0), int(x1), int(y1))
                return [Point(x, y, 0, width) for x, y in raw_points]
            elif mode == 'circle':
                center_x = (x0 + x1) / 2
                center_y = (y0 + y1) / 2
                radius = int(math.sqrt((x1 - x0)**2 + (y1 - y0)**2) / 2)
                raw_points = get_circle(int(center_x), int(center_y), max(radius, 1))
                return [Point(x, y, 0, width) for x, y in raw_points]
            elif mode == 'triangle':
                x2, y2 = x1, y0  # Right angle triangle
                raw_points = get_triangle(int(x0), int(y0), int(x1), int(y1), int(x2), int(y2))
                return [Point(x, y, 0, width) for x, y in raw_points]
            elif mode == 'parabola':
                raw_points = get_parabola(1.0, 0.0, 0.0, float(min(x0, x1)), float(max(x0, x1)), 30)
                return [Point(x, y, 0, width) for x, y in raw_points]
            else:
                return [Point(x0, y0, 0, width), Point(x1, y1, 0, width)]
        except Exception as e:
            logger.error("Error calculating shape %s: %s", mode, e)
            return [Point(x0, y0, 0, width), Point(x1, y1, 0, width)]

    def invalidate_cache(self) -> None:
        """Force cache invalidation for next render."""
        self._cache_valid = False

    def get_stroke_count(self) -> int:
        """Get the number of strokes in the current page."""
        return len(self._page.strokes) if self._page else 0