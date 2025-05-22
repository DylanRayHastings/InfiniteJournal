"""
shop/ui_elements/pygame_adapter.py

PyGame Adapter: Engine, Clock, and Input Implementations for Core Interfaces.

This module provides PyGame-based concrete implementations for rendering, event
handling, timing, and input translation. Intended to be used with abstract
interfaces defined in core.interfaces.
"""

import pygame
import logging
from typing import Any, Dict, List, Optional, Tuple
from icecream import ic
from core.interfaces import Engine, Clock, Event, InputAdapter
from core.event_bus import EventBus

logger = logging.getLogger(__name__)
if logger.isEnabledFor(logging.DEBUG):
    ic.configureOutput(prefix='[pygame_adapter] ')
    logger.setLevel(logging.DEBUG)

# Constants
DEFAULT_CLEAR_COLOR: Tuple[int,int,int] = (0, 0, 0)
DEFAULT_DRAW_COLOR: Tuple[int,int,int] = (255, 255, 255)
DEFAULT_FONT_NAME: Optional[str] = None  # System default

# Exceptions
class AdapterError(Exception):
    """Base exception for adapter failures."""
    pass

class NotInitializedError(AdapterError):
    """Raised when operations are attempted before initialization."""
    pass

# Utilities
class FontManager:
    """Caches and provides Pygame fonts by size."""
    _cache: Dict[int, pygame.font.Font] = {}

    @classmethod
    def get_font(cls, size: int) -> pygame.font.Font:
        font = cls._cache.get(size)
        if font is None:
            font = pygame.font.SysFont(DEFAULT_FONT_NAME, size)
            cls._cache[size] = font
            logger.debug("Font cached size=%d", size)
        return font

class PointUnpacker:
    """Converts points into (x, y, width) tuples."""

    @staticmethod
    def unpack(pt: Any, default_width: int) -> Tuple[int, int, int]:
        if hasattr(pt, "x") and hasattr(pt, "y"):
            width = getattr(pt, "width", default_width)
            return pt.x, pt.y, width
        if isinstance(pt, (tuple, list)):
            if len(pt) == 3:
                return pt[0], pt[1], pt[2]
            if len(pt) == 2:
                return pt[0], pt[1], default_width
        logger.error("Invalid point format: %r", pt)
        raise AdapterError(f"Unsupported point format: {pt}")

# Mixins
class WindowMixin:
    """Provides window initialization methods."""

    def open_window(self, width: int, height: int, title: str) -> None:
        """Alias to init_window."""
        self.init_window(width, height, title)

    def init_window(self, width: int, height: int, title: str) -> None:
        """Initialize pygame window."""
        if width <= 0 or height <= 0:
            logger.error("Invalid window size %dx%d", width, height)
            raise AdapterError("Window dimensions must be positive")
        pygame.init()
        pygame.font.init()
        flags = pygame.SCALED | pygame.RESIZABLE | pygame.DOUBLEBUF | pygame.HWSURFACE
        try:
            self.screen = pygame.display.set_mode((width, height), flags, vsync=1)
        except TypeError:
            self.screen = pygame.display.set_mode((width, height), flags)
            logger.warning("Vsync unsupported")
        pygame.display.set_caption(title)
        logger.info("Window open %dx%d title=%s", width, height, title)

class DisplayMixin:
    """Provides screen clear and present methods."""

    def clear(self, color: Tuple[int,int,int]=DEFAULT_CLEAR_COLOR) -> None:
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        self.screen.fill(color)
        logger.debug("Screen cleared")

    def present(self) -> None:
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        pygame.display.flip()
        logger.debug("Screen presented")

class PollMixin:
    """Handles polling Pygame events and mapping to core.Event."""

    def poll_events(self) -> List[Event]:
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        raw = pygame.event.get()
        events: List[Event] = []
        for e in raw:
            if e.type == pygame.QUIT:
                events.append(Event('QUIT', {}))
            elif e.type == pygame.MOUSEMOTION:
                events.append(Event('MOUSE_MOVE', {'pos': e.pos, 'rel': e.rel}))
            elif e.type == pygame.MOUSEBUTTONDOWN:
                if e.button in (4,5):
                    code = 'SCROLL_UP' if e.button==4 else 'SCROLL_DOWN'
                    events.append(Event('KEY_PRESS', code))
                else:
                    events.append(Event('MOUSE_DOWN', {'pos': e.pos, 'button': e.button}))
            elif e.type == pygame.MOUSEBUTTONUP:
                events.append(Event('MOUSE_UP', {'pos': e.pos, 'button': e.button}))
            elif e.type == pygame.KEYDOWN:
                events.append(Event('KEY_PRESS', pygame.key.name(e.key)))
        logger.debug("Polled %d events", len(events))
        return events

class GraphicsMixin:
    """Provides basic shape drawing methods."""

    def draw_line(
        self, start: Tuple[int,int], end: Tuple[int,int], width: int,
        color: Tuple[int,int,int]=DEFAULT_DRAW_COLOR
    ) -> None:
        if self.screen is None:
            raise NotInitializedError("Screen not initialized")
        pygame.draw.line(self.screen, color, start, end, width)
        logger.debug("Line %s->%s width=%d", start, end, width)

    def draw_circle(
        self, center: Tuple[int,int], radius: int,
        color: Tuple[int,int,int]=DEFAULT_DRAW_COLOR, width: int=0
    ) -> None:
        if self.screen is None:
            raise NotInitializedError("Screen not initialized")
        try:
            pygame.draw.circle(self.screen, color, center, radius, width)
        except pygame.error:
            logger.exception("Circle failed at %s radius=%d", center, radius)
            raise

class TextMixin:
    """Provides text rendering method."""

    def draw_text(
        self, text: str, pos: Tuple[int,int], size: int,
        color: Tuple[int,int,int]=DEFAULT_DRAW_COLOR
    ) -> None:
        if self.screen is None:
            raise NotInitializedError("Screen not initialized")
        font = FontManager.get_font(size)
        surf = font.render(text, True, color)
        self.screen.blit(surf, pos)
        logger.debug("Text '%s' at %s size=%d", text, pos, size)

class StrokeMixin:
    """Provides stroke drawing method."""

    def draw_stroke(
        self, points: List[Any], color: Tuple[int,int,int]=DEFAULT_DRAW_COLOR,
        default_width: int=3
    ) -> None:
        count = len(points)
        if count == 0:
            return
        if count == 1:
            x,y,w = PointUnpacker.unpack(points[0], default_width)
            self.draw_circle((x,y), w, color)
            return
        for prev, curr in zip(points, points[1:]):
            x0,y0,w0 = PointUnpacker.unpack(prev, default_width)
            x1,y1,w1 = PointUnpacker.unpack(curr, default_width)
            self.draw_line((x0,y0),(x1,y1), w0, color)
            self.draw_circle((x0,y0), w0, color)
        x_end,y_end,w_end = PointUnpacker.unpack(points[-1], default_width)
        self.draw_circle((x_end,y_end), w_end, color)
        logger.debug("Stroke drawn %d segments", count-1)

class CursorMixin:
    """Provides cursor drawing method."""

    def draw_cursor(
        self, pos: Tuple[int,int], radius: int,
        color: Tuple[int,int,int]=DEFAULT_DRAW_COLOR
    ) -> None:
        self.draw_circle(pos, radius, color)
        logger.debug("Cursor at %s r=%d", pos, radius)

class UIMixin:
    """Provides UI overlay drawing method."""

    def draw_ui(
        self, mode: str, timestamp: str,
        color: Tuple[int,int,int]=DEFAULT_DRAW_COLOR
    ) -> None:
        self.draw_text(f"Mode: {mode}", (10,10), 16, color)
        height = self.screen.get_height()
        self.draw_text(timestamp, (10, height-20), 14, color)
        logger.debug("UI overlay")


class PygameEngineAdapter(
    WindowMixin, DisplayMixin, PollMixin,
    GraphicsMixin, TextMixin, StrokeMixin,
    CursorMixin, UIMixin, Engine
):
    """Composite adapter implementing Engine via mixins."""
    screen: Optional[pygame.Surface] = None


class PygameClockAdapter(Clock):
    """Clock implementation using Pygame."""

    def __init__(self) -> None:
        self._clock = pygame.time.Clock()
        logger.info("Clock initialized")

    def tick(self, fps: int) -> None:
        self._clock.tick(fps)
        logger.debug("Tick %d FPS", fps)

    def get_time(self) -> float:
        t = pygame.time.get_ticks() / 1000.0
        logger.debug("Time %.3f", t)
        return t


class PygameInputAdapter(InputAdapter):
    """Pass-through input adapter (override translate as needed)."""

    def translate(self, events: List[Event]) -> List[Event]:
        logger.debug("Translate %d events", len(events))
        return events
