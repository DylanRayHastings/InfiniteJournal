"""Journal service for recording, persisting, and rendering drawing strokes."""

from core.event_bus import EventBus
from core.drawing.models import Page, Point
from services.database import CanvasDatabase
from services.tools import ToolService
from services.calculator import get_line, get_triangle, get_parabola
import logging
from typing import List, Tuple, Any

# Constants for tool modes
_TOOL_MODES_SIMPLE = {'brush', 'eraser'}
_SHAPED_MODES = {'line', 'rect', 'circle', 'triangle', 'parabola'}

logger = logging.getLogger(__name__)


class JournalService:
    """
    Service for recording, persisting, and rendering drawing strokes.

    Attributes:
        _bus: Event bus for publishing stroke events.
        _tool_service: Provides the current drawing tool mode.
        _database: CanvasDatabase instance for persistence.
        _page: Current Page containing strokes.
        _current_stroke: Stroke being drawn.
        _start_point: Starting Point of current stroke.
    """

    def __init__(self, bus: EventBus, tool_service: ToolService, database: CanvasDatabase) -> None:
        """
        Initialize JournalService.

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
        logger.info("JournalService initialized")

    def reset(self) -> None:
        """Clear current page and reset state."""
        self._page = Page()
        self._current_stroke = None
        self._start_point = None
        self._last_point = None
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

        if mode in _TOOL_MODES_SIMPLE:
            self._add_point(x, y, width)
        
        logger.debug("Started stroke at (%d, %d) with mode %s", x, y, mode)

    def add_point(self, x: int, y: int, width: int) -> None:
        """
        Add a point to the current stroke.

        Args:
            x: X-coordinate of the point.
            y: Y-coordinate of the point.
            width: Stroke width.
        """
        if not self._current_stroke:
            logger.debug('add_point called without active stroke')
            return

        if self._tool_service.current_tool_mode not in _TOOL_MODES_SIMPLE:
            # For shaped tools, just update the end point
            self._last_point = Point(x, y, 0, width)
            return

        point = Point(x, y, 0, width)
        self._current_stroke.add_point(point)
        self._last_point = point
        self._bus.publish('stroke_added')
        logger.debug("Added point (%d, %d) to stroke", x, y)

    def end_stroke(self) -> None:
        """
        Finalize and persist the current stroke based on tool mode.
        """
        if not self._current_stroke or not self._start_point:
            logger.debug('end_stroke called without active stroke')
            return

        mode = self._tool_service.current_tool_mode
        try:
            if mode in _SHAPED_MODES:
                self._apply_shape(mode)
            self._database.add_stroke(self._current_stroke)
            self._bus.publish('stroke_added')
            logger.info("Stroke completed and saved with mode %s", mode)
        except Exception as e:
            logger.error('Failed to end stroke: %s', e, exc_info=True)
        finally:
            self._current_stroke = None
            self._start_point = None
            self._last_point = None

    def render(self, renderer: Any) -> None:
        """
        Render all strokes on the current page.

        Args:
            renderer: Renderer with draw_stroke method.
        """
        if not self._page or not self._page.strokes:
            return
            
        for stroke in self._page.strokes:
            if not stroke.points:
                continue
                
            try:
                # Convert Point objects to simple (x, y) tuples for renderer
                points = []
                for p in stroke.points:
                    if hasattr(p, 'x') and hasattr(p, 'y'):
                        points.append((float(p.x), float(p.y)))
                    elif isinstance(p, (tuple, list)) and len(p) >= 2:
                        points.append((float(p[0]), float(p[1])))
                    else:
                        logger.warning("Invalid point format in stroke: %r", p)
                        continue
                
                if points and hasattr(renderer, 'draw_stroke'):
                    # Ensure color is a valid tuple
                    color = stroke.color if isinstance(stroke.color, (tuple, list)) and len(stroke.color) == 3 else (255, 255, 255)
                    renderer.draw_stroke(points, color, 3)
                    
            except Exception as e:
                logger.error("Error rendering stroke: %s", e)
                continue  # Skip this stroke but continue with others
                
        logger.debug("Rendered %d strokes", len(self._page.strokes))

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
        Return points for shapes based on mode.

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
                # Generate parabola points
                raw_points = get_parabola(1.0, 0.0, 0.0, float(min(x0, x1)), float(max(x0, x1)), 50)
                return [Point(x, y, 0, 1) for x, y in raw_points]
            else:
                # Fallback to simple line
                return [Point(x0, y0, 0, 1), Point(x1, y1, 0, 1)]
        except Exception as e:
            logger.error("Error calculating shape %s: %s", mode, e)
            return [Point(x0, y0, 0, 1), Point(x1, y1, 0, 1)]