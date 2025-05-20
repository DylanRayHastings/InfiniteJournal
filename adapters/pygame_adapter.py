"""
PyGame Adapter: Engine, Clock, and Input Implementations for Core Interfaces.

This module provides PyGame-based concrete implementations for rendering, event
handling, timing, and input translation. Intended to be used with abstract
interfaces defined in core.interfaces.
"""

import pygame
from core.interfaces import Engine, Clock, Event, InputAdapter
from core.events import EventBus

class PygameEngineAdapter(Engine):
    """
    PyGame-based implementation of the Engine interface.
    Responsible for rendering, event polling, and window management.
    """

    def __init__(self):
        self.screen = None

    def init_window(self, width: int, height: int, title: str) -> None:
        """Initialize the main PyGame window and set up fonts."""
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption(title)

    def poll_events(self):
        """
        Polls PyGame events and translates them to internal Event objects.
        Returns:
            List[Event]: List of translated events.
        """
        events = []
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                events.append(Event('QUIT', {}))
            elif e.type == pygame.MOUSEMOTION:
                events.append(Event('MOUSE_MOVE', {'pos': e.pos, 'rel': e.rel}))
            elif e.type == pygame.MOUSEBUTTONDOWN:
                events.append(Event('MOUSE_DOWN', {'pos': e.pos, 'button': e.button}))
            elif e.type == pygame.MOUSEBUTTONUP:
                events.append(Event('MOUSE_UP', {'pos': e.pos, 'button': e.button}))
            elif e.type == pygame.KEYDOWN:
                events.append(Event('KEY_PRESS', pygame.key.name(e.key)))
        return events

    def clear(self, color=(0, 0, 0)) -> None:
        """Fills the window with a background color (default: black)."""
        self.screen.fill(color)

    def present(self) -> None:
        """Updates the PyGame display."""
        pygame.display.flip()

    def draw_line(self, start, end, width: int, color=(255, 255, 255)) -> None:
        """Draws a line between two points."""
        pygame.draw.line(self.screen, color, start, end, width)

    def draw_circle(self, center, radius: int, color=(255, 255, 255), width: int = 1) -> None:
        """Draws a circle at the given center with specified radius and line width."""
        pygame.draw.circle(self.screen, color, center, radius, width)

    def draw_text(self, text: str, pos, font_size: int, color=(255, 255, 255)) -> None:
        """Renders and draws text at the specified position."""
        font = pygame.font.SysFont(None, font_size)
        surf = font.render(text, True, color)
        self.screen.blit(surf, pos)

    # Renderer interface compliance

    def draw_stroke(self, points, width: int, color=(255, 255, 255)) -> None:
        """
        Draws a continuous stroke by connecting each consecutive pair of points.
        Args:
            points: Sequence of (x, y) tuples.
            width: Stroke width in pixels.
            color: Color as (R, G, B).
        """
        if len(points) < 2:
            return
        for i in range(1, len(points)):
            self.draw_line(points[i - 1], points[i], width, color)

    def draw_cursor(self, pos, radius: int, color=(255, 255, 255)) -> None:
        """
        Draws the brush-size cursor indicator.
        Args:
            pos: (x, y) position of the cursor.
            radius: Brush radius in pixels.
            color: Color as (R, G, B).
        """
        self.draw_circle(pos, radius, color)

    def draw_ui(self, mode: str, timestamp: str, font_color=(255, 255, 255)) -> None:
        """
        Draws UI overlays for current mode and timestamp.
        Args:
            mode: Current tool/mode string.
            timestamp: Time string to show.
            font_color: (R, G, B) for text color.
        """
        # Draw mode in top-left
        self.draw_text(f"Mode: {mode}", (10, 10), 16, font_color)
        # Draw time in bottom-left
        height = self.screen.get_height()
        self.draw_text(timestamp, (10, height - 20), 14, font_color)

class PygameClockAdapter(Clock):
    """
    PyGame-based implementation of the Clock interface.
    Handles timing and frame rate management.
    """

    def __init__(self):
        super().__init__()
        self._clock = pygame.time.Clock()

    def tick(self, fps: int) -> None:
        """Limits the game loop to the given frames per second."""
        self._clock.tick(fps)

    def get_time(self) -> float:
        """Returns elapsed time in seconds since PyGame init."""
        return pygame.time.get_ticks() / 1000.0

class PygameInputAdapter(InputAdapter):
    """
    PyGame-based implementation of InputAdapter.
    Can be extended to translate low-level PyGame events to domain-specific events.
    """

    def translate(self, events):
        """
        Optionally translate a list of low-level events into higher-level events.
        Args:
            events: List of Event objects.
        Returns:
            List of Event objects (possibly transformed).
        """
        # Currently pass-through, but hook for future translation logic.
        return events
