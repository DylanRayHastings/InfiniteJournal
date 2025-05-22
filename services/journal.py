from core.event_bus import EventBus
from core.drawing.models import Page, Point
from services.database import CanvasDatabase
from services.tools import ToolService
from services.calculator import get_line, get_triangle, get_parabola
import logging

# Constants for tool modes
_TOOL_MODES_SIMPLE = {'brush', 'eraser'}
_SHAPED_MODES = {'line', 'rect', 'circle', 'triangle', 'parabola'}

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
        _logger: Logger for internal diagnostics.
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
        self._logger = logging.getLogger(__name__)

    def reset(self) -> None:
        """Clear current page and reset state."""
        self._page = Page()
        self._current_stroke = None
        self._start_point = None

    def start_stroke(self, x: int, y: int, width: int, color: tuple) -> None:
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
        self._start_point = Point(x, y, width)

        if mode in _TOOL_MODES_SIMPLE:
            self._add_point(x, y, width)

    def add_point(self, x: int, y: int, width: int) -> None:
        """
        Add a point to the current stroke.

        Args:
            x: X-coordinate of the point.
            y: Y-coordinate of the point.
            width: Stroke width.
        """
        if not self._current_stroke:
            self._logger.debug('add_point called without active stroke')
            return

        if self._tool_service.current_tool_mode not in _TOOL_MODES_SIMPLE:
            return

        point = Point(x, y, width)
        self._current_stroke.add_point(point)
        self._bus.publish('stroke_added')

    def end_stroke(self) -> None:
        """
        Finalize and persist the current stroke based on tool mode.
        """
        if not self._current_stroke or not self._start_point:
            self._logger.debug('end_stroke called without active stroke')
            return

        mode = self._tool_service.current_tool_mode
        try:
            if mode in _SHAPED_MODES:
                self._apply_shape(mode)
            self._database.add_stroke(self._current_stroke)
            self._bus.publish('stroke_added')
        except Exception as e:
            self._logger.error('Failed to end stroke: %s', e, exc_info=True)
        finally:
            self._current_stroke = None
            self._start_point = None

    def render(self, renderer) -> None:
        """
        Render all strokes on the current page.

        Args:
            renderer: Renderer with draw_stroke method.
        """
        for stroke in self._page.strokes:
            renderer.draw_stroke(stroke.points, stroke.color)

    def _add_point(self, x: int, y: int, width: int) -> None:
        """Internal helper to add a point to current stroke."""
        self.add_point(x, y, width)

    def _apply_shape(self, mode: str) -> None:
        """
        Compute and set points for shaped drawing tools.

        Args:
            mode: Tool mode indicating shape type.
        """
        start = self._start_point
        last = self._current_stroke.points[-1] if self._current_stroke.points else start
        shape_points = self._calculate_shape(mode, start.x, start.y, last.x, last.y)
        self._current_stroke.points = shape_points

    @staticmethod
    def _calculate_shape(mode: str, x0: int, y0: int, x1: int, y1: int) -> list:
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
        start = Point(x0, y0, 1)
        end = Point(x1, y1, 1)
        if mode == 'line':
            return get_line(start, end)
        if mode == 'triangle':
            return get_triangle(start, end)
        if mode == 'parabola':
            return get_parabola(start, end)
        # TODO: Implement rect and circle in calculator module
        return [start, end]
