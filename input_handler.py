import pygame
from config import (
    DEFAULT_TOOL,
    TOOL_BRUSH, TOOL_LINE, TOOL_RECT,
    TOOL_CIRCLE, TOOL_TRIANGLE, TOOL_PARABOLA,
    TOOLS, BRUSH_COLORS
)

class InputHandler:
    """Routes keyboard and mouse events to the InfiniteJournal app."""
    def __init__(self, app):
        self.app = app
        self.handlers = {
            pygame.MOUSEBUTTONDOWN: self._on_mouse_down,
            pygame.MOUSEBUTTONUP:   self._on_mouse_up,
            pygame.MOUSEMOTION:     self._on_mouse_motion,
            pygame.MOUSEWHEEL:      self._on_mouse_wheel,
        }

    def dispatch(self, event):
        # Mouse wheel: adjust brush size
        if event.type == pygame.MOUSEWHEEL:
            # increase on scroll up (+1), decrease on scroll down (-1)
            new_size = self.app.brush_size + event.y
            self.app.brush_size = max(1, min(new_size, 100))
            return

        # Number keys 1-5: change brush color
        if event.type == pygame.KEYDOWN and event.key in (
            pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5
        ):
            idx = event.key - pygame.K_0
            if idx in BRUSH_COLORS:
                self.app.brush_color = BRUSH_COLORS[idx]
                return

        # Ctrl+Shift+S: save screenshot
        if event.type == pygame.KEYDOWN:
            mods = event.mod
            if (event.key == pygame.K_s and
                mods & pygame.KMOD_CTRL and
                mods & pygame.KMOD_SHIFT):
                self.app.save_manager.save_full_canvas()
                return

        # Tab: toggle grid mode
        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            self.app.grid_mode = (
                'graph' if self.app.grid_mode == 'note' else 'note'
            )
            return

        # Backslash: cycle through drawing tools
        if event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSLASH:
            idx = TOOLS.index(self.app.current_tool)
            self.app.current_tool = TOOLS[(idx + 1) % len(TOOLS)]
            return

        # Direct tool shortcuts
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_b:
                self.app.current_tool = TOOL_BRUSH
                return
            elif event.key == pygame.K_l:
                self.app.current_tool = TOOL_LINE
                return
            elif event.key == pygame.K_r:
                self.app.current_tool = TOOL_RECT
                return
            elif event.key == pygame.K_c:
                self.app.current_tool = TOOL_CIRCLE
                return
            elif event.key == pygame.K_t:
                self.app.current_tool = TOOL_TRIANGLE
                return
            elif event.key == pygame.K_p:
                self.app.current_tool = TOOL_PARABOLA
                return

        # Delegate remaining mouse events
        handler = self.handlers.get(event.type)
        if handler:
            handler(event)

    def _on_mouse_down(self, event):
        self.app.handle_mouse_down(event)

    def _on_mouse_up(self, event):
        self.app.handle_mouse_up(event)

    def _on_mouse_motion(self, event):
        self.app.handle_mouse_move(event)

    def _on_mouse_wheel(self, event):
        # Already handled in dispatch
        pass