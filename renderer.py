import pygame
from config import COLORS, TOOL_BRUSH, TOOL_LINE, TOOL_RECT, TOOL_CIRCLE, TOOL_TRIANGLE, TOOL_PARABOLA
from grid import GridRenderer

class CanvasRenderer:
    """Draw the grid, strokes, shapes, preview, text, UI overlay, and brush preview."""
    def __init__(self, app):
        self.app = app
        self.grid = GridRenderer(app.screen)

    def render_frame(self):
        scr = self.app.screen

        # 1) background
        scr.fill(COLORS[f'bg_{self.app.grid_mode}'])

        # 2) notebook or graph grid
        if self.app.grid_mode == 'note':
            self.grid.draw_notebook()
        else:
            self.grid.draw_graph(self.app.camera_offset)

        # 3) freehand strokes
        for pos, color, size in self.app.strokes:
            screen_pos = pos - self.app.camera_offset
            pygame.draw.circle(scr, color, screen_pos, size)

        # 4) committed shapes
        for tool, start, end, color, size in self.app.shapes:
            s = pygame.Vector2(start) - self.app.camera_offset
            e = pygame.Vector2(end)   - self.app.camera_offset
            self._draw_shape(scr, tool, s, e, color, size)

        # 5) preview during drag
        if self.app.preview_shape:
            tool, start, end, color, size = self.app.preview_shape
            s = pygame.Vector2(start) - self.app.camera_offset
            e = pygame.Vector2(end)   - self.app.camera_offset
            self._draw_shape(scr, tool, s, e, color, size)

        # 6) text mode (unchanged)
        if self.app.tool_mode == 'text' and self.app.text_buffer:
            pos = self.app.text_world_pos - self.app.camera_offset
            scr.blit(
                self.app.font.render(self.app.text_buffer, True, self.app.brush_color),
                pos
            )

        # 7) UI overlay: show grid|tool and brush color swatch
        status = f"{self.app.grid_mode.upper()} | {self.app.current_tool.upper()}"
        scr.blit(
            self.app.font.render(status, True, (255,255,255)),
            (10, 10)
        )
        pygame.draw.rect(scr, self.app.brush_color, (200, 10, 30, 30))

        # 8) brush size preview circle
        preview_pos = (250, 25)
        pygame.draw.circle(scr, self.app.brush_color, preview_pos, self.app.brush_size)

    def _draw_shape(self, surface, tool, start, end, color, size):
        # line
        if tool == TOOL_LINE:
            pygame.draw.line(surface, color, start, end, size)

        # rectangle
        elif tool == TOOL_RECT:
            rect = pygame.Rect(start, (end[0]-start[0], end[1]-start[1]))
            rect.normalize()
            pygame.draw.rect(surface, color, rect, size)

        # circle
        elif tool == TOOL_CIRCLE:
            cx = (start[0] + end[0]) // 2
            cy = (start[1] + end[1]) // 2
            radius = int(((end[0]-start[0])**2 + (end[1]-start[1])**2)**0.5 / 2)
            pygame.draw.circle(surface, color, (cx, cy), radius, size)

        # triangle with orientation
        elif tool == TOOL_TRIANGLE:
            left = min(start[0], end[0])
            right = max(start[0], end[0])
            top = min(start[1], end[1])
            bottom = max(start[1], end[1])
            # drag up -> apex at top; drag down -> apex at bottom
            if end[1] < start[1]:
                apex_y = top
                base_y = bottom
            else:
                apex_y = bottom
                base_y = top
            apex = ((left + right) / 2, apex_y)
            bl = (left, base_y)
            br = (right, base_y)
            pygame.draw.polygon(surface, color, [apex, bl, br], size)

        # parabola with orientation
        elif tool == TOOL_PARABOLA:
            left = min(start[0], end[0])
            right = max(start[0], end[0])
            width = right - left
            if width <= 0:
                return
            top = min(start[1], end[1])
            bottom = max(start[1], end[1])
            h = (left + right) / 2
            # drag up -> opens downward; drag down -> opens upward
            if end[1] < start[1]:
                k = top
                a = (bottom - k) / ((width / 2) ** 2)
            else:
                k = bottom
                a = - (bottom - top) / ((width / 2) ** 2)
            points = []
            for i in range(int(width) + 1):
                x = left + i
                dx = x - h
                y = a * (dx * dx) + k
                points.append((int(x), int(y)))
            if len(points) > 1:
                pygame.draw.lines(surface, color, False, points, size)