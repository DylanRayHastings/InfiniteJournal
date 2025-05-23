# services/journal.py (CRITICAL FIX - Dynamic brush width during drawing)
"""Journal service with DYNAMIC brush width changes during active drawing."""

from core.event_bus import EventBus
from core.drawing.models import Page, Point, Stroke
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
    Service for recording, persisting, and rendering drawing strokes with DYNAMIC brush width changes.
    """

    def __init__(self, bus: EventBus, tool_service: ToolService, database: CanvasDatabase) -> None:
        """
        Initialize JournalService with DYNAMIC brush width system.
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
        
        # CRITICAL FIX: Disable preview system completely to prevent gray lines
        self._preview_stroke = None
        self._is_drawing_shape = False
        self._preview_start_point = None
        self._preview_end_point = None
        
        # Performance optimizations
        self._last_event_time = 0
        self._event_throttle_interval = 0.016  # ~60 FPS for smooth updates
        
        # Rendering optimization
        self._stroke_cache = []
        self._cache_valid = True
        
        # CRITICAL FIX: Dynamic brush width system
        self._current_brush_width = 5
        self._is_drawing = False  # Track if currently drawing
        
        bus.subscribe('brush_width_changed', self._on_brush_width_changed)
        
        logger.info("JournalService initialized with DYNAMIC brush width system")

    def _on_brush_width_changed(self, width: int) -> None:
        """CRITICAL FIX: Handle brush width changes - affects current stroke too."""
        try:
            if isinstance(width, (int, float)) and 1 <= width <= 200:
                old_width = self._current_brush_width
                self._current_brush_width = int(width)
                
                # CRITICAL FIX: Update current stroke width if drawing
                if self._is_drawing and self._current_stroke:
                    self._current_stroke.width = self._current_brush_width
                    logger.debug("DYNAMIC width change during drawing: %d -> %d", old_width, self._current_brush_width)
                else:
                    logger.debug("Brush width updated for new strokes: %d", self._current_brush_width)
        except Exception as e:
            logger.error("Error handling brush width change: %s", e)

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
        self._is_drawing = False
        self._stroke_cache.clear()
        self._cache_valid = False
        logger.info("Journal reset")

    def start_stroke(self, x: int, y: int, width: int, color: Tuple[int, int, int]) -> None:
        """
        Begin a new stroke with DYNAMIC width support.
        """
        try:
            mode = self._tool_service.current_tool_mode
            stroke_color = (0, 0, 0) if mode == 'eraser' else color
            
            # CRITICAL FIX: Use current brush width and enable dynamic updates
            actual_width = self._current_brush_width
            self._is_drawing = True  # Enable dynamic width changes
            
            logger.debug("Started DYNAMIC stroke with width: %d (mode: %s)", actual_width, mode)

            # Create stroke with current width
            self._current_stroke = self._page.new_stroke(stroke_color, actual_width)
            self._start_point = Point(x, y, 0, actual_width)
            self._last_point = self._start_point
            
            # CRITICAL FIX: NO PREVIEW for shapes to prevent gray lines
            self._is_drawing_shape = mode in _SHAPED_MODES
            if self._is_drawing_shape:
                self._preview_start_point = Point(x, y, 0, actual_width)
                self._preview_end_point = Point(x, y, 0, actual_width)
                # NO preview stroke creation
                self._preview_stroke = None
            
            self._cache_valid = False

            if mode in _TOOL_MODES_SIMPLE:
                # Add initial point with current width
                self._current_stroke.add_point(self._start_point)
                logger.debug("Added initial point with DYNAMIC width: %d", actual_width)

        except Exception as e:
            logger.error("Error starting stroke: %s", e)
            self._is_drawing = False

    def add_point(self, x: int, y: int, width: int) -> None:
        """
        Add a point with DYNAMIC width (uses current brush width).
        """
        if not self._current_stroke:
            return

        try:
            # CRITICAL FIX: ALWAYS use current brush width for dynamic changes
            current_width = self._current_brush_width
            current_time = time.time()
            
            # For shaped tools, just update end point
            if self._is_drawing_shape:
                self._preview_end_point = Point(x, y, 0, current_width)
                # NO preview rendering
                return

            # CRITICAL FIX: For brush/eraser - Add point with CURRENT width
            point = Point(x, y, 0, current_width)
            self._current_stroke.add_point(point)
            self._last_point = point
            
            # CRITICAL FIX: Also update stroke's default width for consistency
            self._current_stroke.width = current_width
            
            # Throttle event publishing for smooth performance
            if current_time - self._last_event_time > self._event_throttle_interval:
                self._bus.publish('stroke_added')
                self._last_event_time = current_time

        except Exception as e:
            logger.error("Error adding point: %s", e)

    def end_stroke(self) -> None:
        """
        Finalize stroke and disable dynamic width changes.
        """
        if not self._current_stroke or not self._start_point:
            return

        mode = self._tool_service.current_tool_mode
        try:
            if mode in _SHAPED_MODES and self._preview_end_point:
                # Apply final shape with current width
                self._apply_final_shape(mode)
                
            self._cache_valid = False
            self._bus.publish('stroke_added')
            logger.debug("Stroke completed with final width: %d", self._current_brush_width)
        except Exception as e:
            logger.error('Failed to end stroke: %s', e)
        finally:
            # CRITICAL FIX: Disable dynamic width changes
            self._is_drawing = False
            
            # Clean up all state
            self._current_stroke = None
            self._preview_stroke = None
            self._start_point = None
            self._last_point = None
            self._is_drawing_shape = False
            self._preview_start_point = None
            self._preview_end_point = None

    def _apply_final_shape(self, mode: str) -> None:
        """Apply final shape with current brush width."""
        if not self._preview_end_point:
            self._preview_end_point = self._start_point
            
        start = self._start_point
        end = self._preview_end_point
        
        try:
            # Calculate final shape with CURRENT width
            shape_points = self._calculate_shape(
                mode, start.x, start.y, end.x, end.y, 
                width=self._current_brush_width
            )
            self._current_stroke.points = shape_points
            self._current_stroke.width = self._current_brush_width
            logger.debug("Applied final shape %s with CURRENT width: %d", mode, self._current_brush_width)
        except Exception as e:
            logger.error("Error applying final shape %s: %s", mode, e)
            # Fallback to simple line with current width
            self._current_stroke.points = [
                Point(start.x, start.y, 0, self._current_brush_width),
                Point(end.x, end.y, 0, self._current_brush_width)
            ]

    def render(self, renderer: Any) -> None:
        """
        Render all strokes with proper width handling.
        """
        if not self._page:
            return
            
        # Render completed strokes ONLY
        self._render_strokes(renderer)

    def _render_strokes(self, renderer: Any) -> None:
        """CRITICAL FIX: Render strokes with proper width and smooth rendering."""
        for stroke in self._page.strokes:
            if not stroke.points:
                continue
                
            try:
                # CRITICAL FIX: Handle mixed-width points properly
                points_with_widths = []
                for p in stroke.points:
                    if hasattr(p, 'x') and hasattr(p, 'y'):
                        # Use point's individual width if available, fallback to stroke width
                        point_width = getattr(p, 'width', stroke.width)
                        points_with_widths.append((float(p.x), float(p.y), point_width))
                
                if points_with_widths and hasattr(renderer, 'draw_stroke'):
                    # Use stroke's color
                    color = stroke.color if isinstance(stroke.color, (tuple, list)) and len(stroke.color) == 3 else (255, 255, 255)
                    
                    # CRITICAL: Skip gray preview artifacts
                    if color == (128, 128, 128):
                        continue
                    
                    # CRITICAL FIX: Render with individual point widths for dynamic brush
                    if self._has_varying_widths(points_with_widths):
                        self._render_variable_width_stroke(renderer, points_with_widths, color)
                    else:
                        # Uniform width - use standard rendering
                        points = [(p[0], p[1]) for p in points_with_widths]
                        width = points_with_widths[0][2] if points_with_widths else stroke.width
                        renderer.draw_stroke(points, color, width)
                    
            except Exception as e:
                logger.error("Error rendering stroke: %s", e)
                continue

    def _has_varying_widths(self, points_with_widths: List[Tuple[float, float, int]]) -> bool:
        """Check if stroke has varying widths (dynamic brush was used)."""
        if len(points_with_widths) < 2:
            return False
        
        first_width = points_with_widths[0][2]
        return any(p[2] != first_width for p in points_with_widths[1:])

    def _render_variable_width_stroke(self, renderer: Any, points_with_widths: List[Tuple[float, float, int]], color: Tuple[int, int, int]) -> None:
        """CRITICAL FIX: Render stroke with varying widths smoothly."""
        try:
            # Render segments with individual widths
            for i in range(len(points_with_widths) - 1):
                p1 = points_with_widths[i]
                p2 = points_with_widths[i + 1]
                
                # Use average width for segment
                avg_width = (p1[2] + p2[2]) // 2
                
                # Draw line segment
                try:
                    renderer.draw_line((int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), avg_width, color)
                except Exception:
                    continue
            
            # Add end caps with appropriate sizes
            if len(points_with_widths) >= 2:
                start_point = points_with_widths[0]
                end_point = points_with_widths[-1]
                
                start_radius = max(1, start_point[2] // 2)
                end_radius = max(1, end_point[2] // 2)
                
                try:
                    renderer.draw_circle((int(start_point[0]), int(start_point[1])), start_radius, color)
                    renderer.draw_circle((int(end_point[0]), int(end_point[1])), end_radius, color)
                except Exception:
                    pass
                    
        except Exception as e:
            logger.error("Error rendering variable width stroke: %s", e)

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

    def is_drawing(self) -> bool:
        """Check if currently drawing (for dynamic width changes)."""
        return self._is_drawing