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
DEFAULT_CLEAR_COLOR: Tuple[int, int, int] = (0, 0, 0)
DEFAULT_DRAW_COLOR: Tuple[int, int, int] = (255, 255, 255)
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
        """Unpack a point object into (x, y, width) tuple."""
        try:
            if hasattr(pt, "x") and hasattr(pt, "y"):
                width = getattr(pt, "width", default_width)
                return int(pt.x), int(pt.y), int(width)
            if isinstance(pt, (tuple, list)):
                if len(pt) >= 3:
                    return int(pt[0]), int(pt[1]), int(pt[2])
                elif len(pt) >= 2:
                    return int(pt[0]), int(pt[1]), default_width
                else:
                    logger.error("Point tuple too short: %r", pt)
                    raise AdapterError(f"Point tuple must have at least 2 elements: {pt}")
            else:
                logger.error("Invalid point format: %r (type: %s)", pt, type(pt))
                raise AdapterError(f"Unsupported point format: {pt}")
        except (ValueError, TypeError) as e:
            logger.error("Error unpacking point %r: %s", pt, e)
            raise AdapterError(f"Failed to unpack point {pt}: {e}") from e

def validate_color(color: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Validate and ensure color is a proper RGB tuple."""
    if not isinstance(color, (tuple, list)) or len(color) != 3:
        logger.error("Invalid color format: %r", color)
        return DEFAULT_DRAW_COLOR
    
    try:
        r, g, b = color
        # Clamp values to 0-255 range
        r = max(0, min(255, int(r)))
        g = max(0, min(255, int(g)))
        b = max(0, min(255, int(b)))
        return (r, g, b)
    except (ValueError, TypeError) as e:
        logger.error("Error validating color %r: %s", color, e)
        return DEFAULT_DRAW_COLOR

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

    def get_size(self) -> Tuple[int, int]:
        """Get the current window/screen size."""
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        return self.screen.get_size()

class DisplayMixin:
    """Provides screen clear and present methods."""

    def clear(self, color: Optional[Tuple[int, int, int]] = None) -> None:
        """Clear the screen with the specified color."""
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        clear_color = validate_color(color) if color is not None else DEFAULT_CLEAR_COLOR
        self.screen.fill(clear_color)
        logger.debug("Screen cleared with color %s", clear_color)

    def present(self) -> None:
        """Present the rendered frame to the display."""
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        pygame.display.flip()
        logger.debug("Screen presented")

class PollMixin:
    """Handles polling Pygame events and mapping to core.Event."""

    def poll_events(self) -> List[Event]:
        """Poll pygame events and convert to core Events."""
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
                if e.button in (4, 5):
                    code = 'SCROLL_UP' if e.button == 4 else 'SCROLL_DOWN'
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
        self, start: Tuple[int, int], end: Tuple[int, int], width: int,
        color: Optional[Tuple[int, int, int]] = None
    ) -> None:
        """Draw a line between two points."""
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        
        # Validate and convert parameters
        try:
            line_color = validate_color(color) if color is not None else DEFAULT_DRAW_COLOR
            start_pos = (int(start[0]), int(start[1]))
            end_pos = (int(end[0]), int(end[1]))
            line_width = max(1, int(width))  # Ensure width is at least 1
            
            pygame.draw.line(self.screen, line_color, start_pos, end_pos, line_width)
            logger.debug("Line %s->%s width=%d color=%s", start_pos, end_pos, line_width, line_color)
        except (ValueError, TypeError, IndexError) as e:
            logger.error("Error drawing line from %s to %s: %s", start, end, e)
            raise AdapterError(f"Failed to draw line: {e}") from e

    def draw_circle(
        self, center: Tuple[int, int], radius: int,
        color: Optional[Tuple[int, int, int]] = None, width: int = 0
    ) -> None:
        """Draw a circle at the specified center with given radius."""
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        
        try:
            circle_color = validate_color(color) if color is not None else DEFAULT_DRAW_COLOR
            center_pos = (int(center[0]), int(center[1]))
            circle_radius = max(1, int(radius))
            circle_width = max(0, int(width))
            
            pygame.draw.circle(self.screen, circle_color, center_pos, circle_radius, circle_width)
            logger.debug("Circle at %s radius=%d color=%s", center_pos, circle_radius, circle_color)
        except (ValueError, TypeError, IndexError) as e:
            logger.error("Error drawing circle at %s radius %d: %s", center, radius, e)
            raise AdapterError(f"Failed to draw circle: {e}") from e

class TextMixin:
    """Provides text rendering method."""

    def draw_text(
        self, text: str, pos: Tuple[int, int], size: int,
        color: Optional[Tuple[int, int, int]] = None
    ) -> None:
        """Render text at the specified position."""
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        
        try:
            text_color = validate_color(color) if color is not None else DEFAULT_DRAW_COLOR
            text_pos = (int(pos[0]), int(pos[1]))
            font_size = max(8, int(size))  # Minimum font size
            
            font = FontManager.get_font(font_size)
            surf = font.render(str(text), True, text_color)
            self.screen.blit(surf, text_pos)
            logger.debug("Text '%s' at %s size=%d color=%s", text, text_pos, font_size, text_color)
        except (ValueError, TypeError, IndexError) as e:
            logger.error("Error drawing text '%s' at %s: %s", text, pos, e)
            raise AdapterError(f"Failed to draw text: {e}") from e

class StrokeMixin:
    """Provides stroke drawing method."""

    def draw_stroke(
        self, points: List[Any], color: Optional[Tuple[int, int, int]] = None,
        default_width: int = 3
    ) -> None:
        """Draw a stroke connecting multiple points."""
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        
        try:
            stroke_color = validate_color(color) if color is not None else DEFAULT_DRAW_COLOR
            count = len(points)
            
            if count == 0:
                return
            
            if count == 1:
                # Single point - draw as circle
                if isinstance(points[0], (tuple, list)) and len(points[0]) >= 2:
                    x, y = int(points[0][0]), int(points[0][1])
                    self.draw_circle((x, y), default_width, stroke_color)
                else:
                    x, y, w = PointUnpacker.unpack(points[0], default_width)
                    self.draw_circle((x, y), w, stroke_color)
                return
            
            # Multiple points - draw lines between them
            for i in range(count - 1):
                try:
                    # Handle both tuple and Point object formats
                    if isinstance(points[i], (tuple, list)) and len(points[i]) >= 2:
                        x0, y0 = int(points[i][0]), int(points[i][1])
                        w0 = default_width
                    else:
                        x0, y0, w0 = PointUnpacker.unpack(points[i], default_width)
                    
                    if isinstance(points[i + 1], (tuple, list)) and len(points[i + 1]) >= 2:
                        x1, y1 = int(points[i + 1][0]), int(points[i + 1][1])
                        w1 = default_width
                    else:
                        x1, y1, w1 = PointUnpacker.unpack(points[i + 1], default_width)
                    
                    # Draw line and circles at endpoints
                    line_width = max(1, min(w0, w1, 10))  # Limit line width
                    self.draw_line((x0, y0), (x1, y1), line_width, stroke_color)
                    self.draw_circle((x0, y0), max(1, w0), stroke_color)
                    
                    # Draw circle at final point
                    if i == count - 2:
                        self.draw_circle((x1, y1), max(1, w1), stroke_color)
                        
                except Exception as e:
                    logger.error("Error drawing stroke segment %d: %s", i, e)
                    continue  # Skip this segment but continue with the rest
            
            logger.debug("Stroke drawn with %d segments, color=%s", count-1, stroke_color)
        except Exception as e:
            logger.error("Error drawing stroke: %s", e)
            # Don't re-raise here to avoid breaking the render loop

class CursorMixin:
    """Provides cursor drawing method."""

    def draw_cursor(
        self, pos: Tuple[int, int], radius: int,
        color: Optional[Tuple[int, int, int]] = None
    ) -> None:
        """Draw a cursor at the specified position."""
        cursor_color = validate_color(color) if color is not None else DEFAULT_DRAW_COLOR
        try:
            self.draw_circle(pos, radius, cursor_color)
            logger.debug("Cursor at %s r=%d color=%s", pos, radius, cursor_color)
        except Exception as e:
            logger.error("Error drawing cursor: %s", e)

class UIMixin:
    """Provides UI overlay drawing method."""

    def draw_ui(
        self, mode: str, timestamp: str,
        color: Optional[Tuple[int, int, int]] = None
    ) -> None:
        """Draw UI overlay with mode and timestamp information."""
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        
        try:
            ui_color = validate_color(color) if color is not None else DEFAULT_DRAW_COLOR
            self.draw_text(f"Mode: {mode}", (10, 10), 16, ui_color)
            height = self.screen.get_height()
            self.draw_text(timestamp, (10, height - 20), 14, ui_color)
            logger.debug("UI overlay drawn with mode=%s", mode)
        except Exception as e:
            logger.error("Error drawing UI: %s", e)


class PygameEngineAdapter(
    WindowMixin, DisplayMixin, PollMixin,
    GraphicsMixin, TextMixin, StrokeMixin,
    CursorMixin, UIMixin, Engine
):
    """Composite adapter implementing Engine via mixins."""
    screen: Optional[pygame.Surface] = None

    def __init__(self) -> None:
        """Initialize the pygame engine adapter."""
        self.screen = None
        logger.info("PygameEngineAdapter initialized")


class PygameClockAdapter(Clock):
    """Clock implementation using Pygame."""

    def __init__(self) -> None:
        self._clock = pygame.time.Clock()
        self._last_tick_time = 0.0
        logger.info("PygameClockAdapter initialized")

    def tick(self, target_fps: int) -> float:
        """Enforce target FPS and return actual frame time in seconds."""
        self._last_tick_time = self._clock.tick(target_fps) / 1000.0
        logger.debug("Tick %d FPS, actual time: %.3fs", target_fps, self._last_tick_time)
        return self._last_tick_time

    def get_time(self) -> float:
        """Get current time in seconds since pygame initialization."""
        time_ms = pygame.time.get_ticks()
        time_s = time_ms / 1000.0
        logger.debug("Current time: %.3fs", time_s)
        return time_s

    def get_fps(self) -> float:
        """Get the current frames per second."""
        fps = self._clock.get_fps()
        logger.debug("Current FPS: %.1f", fps)
        return fps


class PygameInputAdapter(InputAdapter):
    """Pass-through input adapter for pygame events."""

    def __init__(self) -> None:
        """Initialize the input adapter."""
        logger.info("PygameInputAdapter initialized")

    def translate(self, events: List[Event]) -> List[Event]:
        """Translate events (currently pass-through, override as needed)."""
        logger.debug("Translating %d events", len(events))
        return events