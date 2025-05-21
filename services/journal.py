from core.events import EventBus
from core.models import Page, Point
from services.database import CanvasDatabase
from services.tools import ToolService
from services.calculator import get_line, get_triangle, get_parabola

class JournalService:
    def __init__(self, bus: EventBus, tool_service: ToolService, databse: CanvasDatabase):
        self._bus = bus
        self._tool_service = tool_service
        self._page = Page()
        self._current = None
        self.database = databse
        self.start_point = None

    def reset(self):
        self._page = Page()
        self._current = None
        self.start_point = None

    def start_stroke(self, x: int, y: int, width: int, color: tuple):
        tool_mode = self._tool_service.current_tool_mode
        stroke_color = (0, 0, 0) if tool_mode == 'eraser' else color
        self._current = self._page.new_stroke(stroke_color)
        self.start_point = (x, y)

        if tool_mode in ['brush', 'eraser']:
            self.add_point(x, y, width)

    def add_point(self, x: int, y: int, width: int):
        if not self._current:
            return
        tool_mode = self._tool_service.current_tool_mode
        if tool_mode in ['brush', 'eraser']:
            self._current.add_point(Point(x, y, width))
            self._bus.publish('stroke_added')

    def end_stroke(self):
        if not self._current or not self.start_point:
            return

        tool_mode = self._tool_service.current_tool_mode
        x0, y0 = self.start_point
        end = self._current.points[-1] if self._current.points else None
        end_x, end_y = (end.x, end.y) if end else (x0, y0)

        if tool_mode in ['line', 'rect', 'circle', 'triangle', 'parabola']:
            shape_points = self._calculate_shape(tool_mode, x0, y0, end_x, end_y)
            self._current.points = shape_points

        self.database.add_stroke(self._current)
        self._bus.publish('stroke_added')
        self._current = None
        self.start_point = None

    def _calculate_shape(self, mode, x0, y0, x1, y1):
        start = Point(x0, y0, 1)
        end = Point(x1, y1, 1)
        if mode == 'line':
            return get_line(start, end)
        elif mode == 'triangle':
            return get_triangle(start, end)
        elif mode == 'parabola':
            return get_parabola(start, end)
        # Placeholder for rect, circle etc. (implement if needed)
        return [start, end]

    def render(self, renderer):
        for stroke in self._page.strokes:
            renderer.draw_stroke(stroke.points, stroke.color)
