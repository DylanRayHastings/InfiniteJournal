"""Journal service for recording, persisting, and rendering drawing strokes with persistent visibility."""

from core.event_bus import EventBus
from core.drawing.models import Page, Point
from services.database import CanvasDatabase
from services.tools import ToolService
from services.calculator import get_line, get_triangle, get_parabola
import logging
import time
from typing import List, Tuple, Any

# Constants for tool modes
_TOOL_MODES_SIMPLE = {'brush', 'eraser'}
_SHAPED_MODES = {'line', 'rect', 'circle', 'triangle', 'parabola'}

logger = logging.getLogger(__name__)


class JournalService:
    """
    Service for recording, persisting, and rendering drawing strokes with persistent visibility.

    Attributes:
        _bus: Event bus for publishing stroke events.
        _tool_service: Provides the current drawing tool mode.
        _database: CanvasDatabase instance for persistence.
        _page: Current Page containing strokes.
        _current_stroke: Stroke being drawn.
        _start_point: Starting Point of current stroke.
        _last_event_time: Time of last event to throttle publishing.
    """

    def __init__(self, bus: EventBus, tool_service: ToolService, database: CanvasDatabase) -> None:
        """
        Initialize JournalService with persistent rendering.

        Args:
            bus: Event bus for publishing stroke events.
            tool_service: ToolService providing current tool mode.
            database: CanvasDatabase for persisting strokes.

        Raises:
            ValueError: If any dependency is None.
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
        
        # Performance optimizations
        self._last_event_time = 0
        self._event_throttle_interval = 0.016  # ~60 FPS event throttling
        self._point_cache = []
        
        # Rendering optimization - but always render existing content
        self._stroke_cache = []  # Cache converted strokes for performance
        self._cache_valid = False
        
        logger.info("JournalService initialized with persistent rendering")

    def reset(self) -> None:
        """Clear current page and reset state."""
        self._page = Page()
        self._current_stroke = None
        self._start_point = None
        self._last_point = None
        self._point_cache.clear()
        self._stroke_cache.clear()
        self._cache_valid = False
        logger.info("Journal reset")

    def start_stroke(self, x: int, y: int, width: int, color: Tuple[int, int, int]) -> None:
        """
        Begin a new stroke at the given coordinates.

        Args:
            x: X-coordinate of stroke start.
            y: Y-coordinate of stroke start.
            width: Stroke width.
            color: RGB tuple for stroke.
        """
        mode = self._tool_service.current_tool_mode
        stroke_color = (0, 0, 0) if mode == 'eraser' else color

        self._current_stroke = self._page.new_stroke(stroke_color)
        self._start_point = Point(x, y, 0, width)  # z=0 for 2D drawing
        self._last_point = self._start_point
        self._point_cache.clear()
        
        # Invalidate cache since we're adding new content
        self._cache_valid = False

        if mode in _TOOL_MODES_SIMPLE:
            self._add_point(x, y, width)
        
        logger.debug("Started stroke at (%d, %d) with mode %s", x, y, mode)

    def add_point(self, x: int, y: int, width: int) -> None:
        """
        Add a point to the current stroke with performance optimizations.

        Args:
            x: X-coordinate of the point.
            y: Y-coordinate of the point.
            width: Stroke width.
        """
        if not self._current_stroke:
            logger.debug('add_point called without active stroke')
            return

        current_time = time.time()
        
        # For shaped tools, just update the end point
        if self._tool_service.current_tool_mode not in _TOOL_MODES_SIMPLE:
            self._last_point = Point(x, y, 0, width)
            return

        # Add point to cache first for faster access
        point = Point(x, y, 0, width)
        self._point_cache.append(point)
        
        # Batch add points to stroke for better performance
        if len(self._point_cache) >= 5 or current_time - self._last_event_time > 0.1:
            for cached_point in self._point_cache:
                self._current_stroke.add_point(cached_point)
            self._point_cache.clear()
            
            # Invalidate cache when adding new points
            self._cache_valid = False
            
            # Throttle event publishing for better performance
            if current_time - self._last_event_time > self._event_throttle_interval:
                self._bus.publish('stroke_added')
                self._last_event_time = current_time
        
        self._last_point = point
        logger.debug("Added point (%d, %d) to stroke", x, y)

    def end_stroke(self) -> None:
        """
        Finalize and persist the current stroke based on tool mode.
        """
        if not self._current_stroke or not self._start_point:
            logger.debug('end_stroke called without active stroke')
            return

        # Flush any remaining cached points
        if self._point_cache:
            for cached_point in self._point_cache:
                self._current_stroke.add_point(cached_point)
            self._point_cache.clear()

        mode = self._tool_service.current_tool_mode
        try:
            if mode in _SHAPED_MODES:
                self._apply_shape(mode)
                
            # Invalidate cache since stroke is complete
            self._cache_valid = False
                
            self._bus.publish('stroke_added')
            logger.info("Stroke completed with mode %s", mode)
        except Exception as e:
            logger.error('Failed to end stroke: %s', e, exc_info=True)
        finally:
            self._current_stroke = None
            self._start_point = None
            self._last_point = None

    def render(self, renderer: Any) -> None:
        """
        Render all strokes on the current page - ALWAYS render existing content.
        This ensures strokes remain visible between drawing operations.

        Args:
            renderer: Renderer with draw_stroke method.
        """
        # Always render existing strokes - this is crucial for persistent visibility
        if not self._page or not self._page.strokes:
            return
            
        # Use cached strokes if available and valid
        if self._cache_valid and self._stroke_cache:
            self._render_from_cache(renderer)
        else:
            self._render_and_cache(renderer)

    def _render_from_cache(self, renderer: Any) -> None:
        """Render strokes from cache for better performance."""
        stroke_count = 0
        
        for stroke_data in self._stroke_cache:
            try:
                points, color = stroke_data
                if points and hasattr(renderer, 'draw_stroke'):
                    renderer.draw_stroke(points, color, 3)
                    stroke_count += 1
            except Exception as e:
                logger.error("Error rendering cached stroke: %s", e)
                continue
                
        logger.debug("Rendered %d cached strokes", stroke_count)

    def _render_and_cache(self, renderer: Any) -> None:
        """Render strokes and update cache."""
        stroke_count = 0
        new_cache = []
        
        for stroke in self._page.strokes:
            if not stroke.points:
                continue
                
            try:
                # Convert stroke points
                points = self._convert_stroke_points(stroke.points)
                
                if points and hasattr(renderer, 'draw_stroke'):
                    # Ensure color is a valid tuple
                    color = stroke.color if isinstance(stroke.color, (tuple, list)) and len(stroke.color) == 3 else (255, 255, 255)
                    
                    # Render the stroke
                    renderer.draw_stroke(points, color, 3)
                    stroke_count += 1
                    
                    # Cache the converted stroke for next frame
                    new_cache.append((points, color))
                    
            except Exception as e:
                logger.error("Error rendering stroke: %s", e)
                continue  # Skip this stroke but continue with others
        
        # Update cache
        self._stroke_cache = new_cache
        self._cache_valid = True
                
        logger.debug("Rendered and cached %d strokes", stroke_count)

    def _convert_stroke_points(self, points: List[Point]) -> List[Tuple[float, float]]:
        """
        Convert Point objects to coordinate tuples efficiently.
        
        Args:
            points: List of Point objects.
            
        Returns:
            List of (x, y) coordinate tuples.
        """
        converted_points = []
        
        # Batch process points for better performance
        for p in points:
            try:
                if hasattr(p, 'x') and hasattr(p, 'y'):
                    converted_points.append((float(p.x), float(p.y)))
                elif isinstance(p, (tuple, list)) and len(p) >= 2:
                    converted_points.append((float(p[0]), float(p[1])))
                else:
                    logger.warning("Invalid point format in stroke: %r", p)
                    continue
            except (ValueError, TypeError) as e:
                logger.warning("Error converting point %r: %s", p, e)
                continue
                
        return converted_points

    def _add_point(self, x: int, y: int, width: int) -> None:
        """Internal helper to add a point to current stroke."""
        self.add_point(x, y, width)

    def _apply_shape(self, mode: str) -> None:
        """
        Compute and set points for shaped drawing tools.

        Args:
            mode: Tool mode indicating shape type.
        """
        if not self._last_point:
            # If no end point, use start point
            self._last_point = self._start_point
            
        start = self._start_point
        end = self._last_point
        
        try:
            shape_points = self._calculate_shape(mode, start.x, start.y, end.x, end.y)
            self._current_stroke.points = shape_points
            logger.debug("Applied shape %s with %d points", mode, len(shape_points))
        except Exception as e:
            logger.error("Error applying shape %s: %s", mode, e)
            # Fallback to simple line
            self._current_stroke.points = [start, end]

    @staticmethod
    def _calculate_shape(mode: str, x0: float, y0: float, x1: float, y1: float) -> List[Point]:
        """
        Return points for shapes based on mode with optimized calculations.

        Args:
            mode: Shape mode (e.g., 'line', 'triangle', 'parabola').
            x0: Start X.
            y0: Start Y.
            x1: End X.
            y1: End Y.

        Returns:
            List[Point]: Points defining the shape.
        """
        try:
            if mode == 'line':
                # Generate line points using calculator
                raw_points = get_line(int(x0), int(y0), int(x1), int(y1))
                return [Point(x, y, 0, 1) for x, y in raw_points]
            elif mode == 'triangle':
                # Generate triangle with third point offset
                x2, y2 = x1, y0  # Right angle triangle
                raw_points = get_triangle(int(x0), int(y0), int(x1), int(y1), int(x2), int(y2))
                return [Point(x, y, 0, 1) for x, y in raw_points]
            elif mode == 'parabola':
                # Generate parabola points with limited complexity for performance
                raw_points = get_parabola(1.0, 0.0, 0.0, float(min(x0, x1)), float(max(x0, x1)), 30)  # Reduced from 50 to 30
                return [Point(x, y, 0, 1) for x, y in raw_points]
            else:
                # Fallback to simple line
                return [Point(x0, y0, 0, 1), Point(x1, y1, 0, 1)]
        except Exception as e:
            logger.error("Error calculating shape %s: %s", mode, e)
            return [Point(x0, y0, 0, 1), Point(x1, y1, 0, 1)]

    def invalidate_cache(self) -> None:
        """Force cache invalidation for next render."""
        self._cache_valid = False

    def get_stroke_count(self) -> int:
        """Get the number of strokes in the current page."""
        return len(self._page.strokes) if self._page else 0