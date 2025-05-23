# adapters/pygame_adapter.py (Fixed single point rendering and smoothing)
"""
PyGame Adapter: Engine, Clock, and Input Implementations with fixed stroke rendering.
"""

import pygame
import logging
import threading
import queue
import math
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
DEFAULT_FONT_NAME: Optional[str] = None

# Performance constants - improved smoothing
MAX_STROKE_SEGMENTS = 1000
STROKE_SMOOTHING_THRESHOLD = 8  # Increased for better smoothing
BATCH_RENDER_SIZE = 50

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

class PointCache:
    """Optimized point conversion and caching."""
    
    def __init__(self, max_size: int = 1000):
        self._cache = {}
        self._max_size = max_size
        
    def convert_point(self, pt: Any, default_width: int) -> Tuple[int, int, int]:
        """Convert and cache point conversions."""
        if hasattr(pt, "x") and hasattr(pt, "y"):
            key = (pt.x, pt.y, getattr(pt, "width", default_width))
        elif isinstance(pt, (tuple, list)) and len(pt) >= 2:
            key = tuple(pt[:3]) if len(pt) >= 3 else (*pt[:2], default_width)
        else:
            return self._convert_uncached(pt, default_width)
            
        if key in self._cache:
            return self._cache[key]
            
        result = self._convert_uncached(pt, default_width)
        
        if len(self._cache) >= self._max_size:
            old_keys = list(self._cache.keys())[:self._max_size // 2]
            for old_key in old_keys:
                del self._cache[old_key]
                
        self._cache[key] = result
        return result
    
    def _convert_uncached(self, pt: Any, default_width: int) -> Tuple[int, int, int]:
        """Convert point without caching."""
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
        r = max(0, min(255, int(r)))
        g = max(0, min(255, int(g)))
        b = max(0, min(255, int(b)))
        return (r, g, b)
    except (ValueError, TypeError) as e:
        logger.error("Error validating color %r: %s", color, e)
        return DEFAULT_DRAW_COLOR

def interpolate_points(p1: Tuple[int, int], p2: Tuple[int, int]) -> List[Tuple[int, int]]:
    """Generate smoothly interpolated points between two points."""
    x1, y1 = p1
    x2, y2 = p2
    
    points = []
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    
    steps = max(dx, dy)
    if steps == 0:
        return [p1]
    
    # Use more steps for smoother lines
    steps = max(steps, 10)  # Minimum smoothing
    
    x_step = (x2 - x1) / steps
    y_step = (y2 - y1) / steps
    
    for i in range(steps + 1):
        x = int(x1 + i * x_step)
        y = int(y1 + i * y_step)
        points.append((x, y))
    
    return points

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
                    direction = 1 if e.button == 4 else -1
                    events.append(Event('SCROLL_WHEEL', {'direction': direction, 'pos': e.pos}))
                else:
                    events.append(Event('MOUSE_DOWN', {'pos': e.pos, 'button': e.button}))
                    events.append(Event('MOUSE_CLICK', {'pos': e.pos, 'button': e.button}))
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
        
        try:
            line_color = validate_color(color) if color is not None else DEFAULT_DRAW_COLOR
            start_pos = (int(start[0]), int(start[1]))
            end_pos = (int(end[0]), int(end[1]))
            line_width = max(1, int(width))
            
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
            font_size = max(8, int(size))
            
            font = FontManager.get_font(font_size)
            surf = font.render(str(text), True, text_color)
            self.screen.blit(surf, text_pos)
            logger.debug("Text '%s' at %s size=%d color=%s", text, text_pos, font_size, text_color)
        except (ValueError, TypeError, IndexError) as e:
            logger.error("Error drawing text '%s' at %s: %s", text, pos, e)
            raise AdapterError(f"Failed to draw text: {e}") from e

class OptimizedStrokeMixin:
    """Provides optimized stroke drawing methods with FIXED single point rendering."""
    
    def __init__(self):
        super().__init__()
        self._point_cache = PointCache()
        self._stroke_buffer = []

    def draw_stroke(
        self, points: List[Any], color: Optional[Tuple[int, int, int]] = None,
        default_width: int = 3
    ) -> None:
        """Draw an optimized stroke with FIXED single point rendering."""
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        
        if not points:
            return
            
        try:
            stroke_color = validate_color(color) if color is not None else DEFAULT_DRAW_COLOR
            point_count = len(points)
            
            if point_count == 1:
                # FIXED: Single point rendering
                self._draw_single_point_fixed(points[0], stroke_color, default_width)
                return
            
            # Convert points efficiently
            converted_points = self._convert_points_batch(points, default_width)
            
            if len(converted_points) < 2:
                return
                
            # Draw optimized stroke with improved smoothing
            self._draw_optimized_stroke_smooth(converted_points, stroke_color, default_width)
            
            logger.debug("Optimized stroke drawn with %d points, color=%s", point_count, stroke_color)
            
        except Exception as e:
            logger.error("Error drawing optimized stroke: %s", e)
            self._draw_stroke_fallback(points, stroke_color, default_width)

    def _draw_single_point_fixed(self, point: Any, color: Tuple[int, int, int], default_width: int) -> None:
        """FIXED: Draw a single point as a circle with proper radius."""
        try:
            x, y, w = self._point_cache.convert_point(point, default_width)
            # CRITICAL FIX: Use width/2 as radius, not full width
            radius = max(1, w // 2)
            self.draw_circle((x, y), radius, color)
            logger.debug("Single point drawn at (%d, %d) with radius %d", x, y, radius)
        except Exception as e:
            logger.error("Error drawing single point: %s", e)

    def _convert_points_batch(self, points: List[Any], default_width: int) -> List[Tuple[int, int]]:
        """Convert points in batches for better performance."""
        converted = []
        
        for i in range(0, len(points), BATCH_RENDER_SIZE):
            batch = points[i:i + BATCH_RENDER_SIZE]
            for point in batch:
                try:
                    x, y, _ = self._point_cache.convert_point(point, default_width)
                    converted.append((x, y))
                except Exception as e:
                    logger.warning("Skipping invalid point in batch: %s", e)
                    continue
                    
        return converted

    def _draw_optimized_stroke_smooth(self, points: List[Tuple[int, int]], color: Tuple[int, int, int], width: int) -> None:
        """Draw stroke with IMPROVED smoothing."""
        if len(points) < 2:
            return
            
        try:
            # Apply aggressive smoothing
            smoothed_points = self._smooth_stroke_aggressive(points)
            
            if len(smoothed_points) >= 2:
                line_width = max(1, min(width, 20))  # Allow larger brush sizes
                
                # Draw main stroke line
                pygame.draw.lines(self.screen, color, False, smoothed_points, line_width)
                
                # Add end caps for better appearance
                if line_width > 2:
                    start_point = smoothed_points[0]
                    end_point = smoothed_points[-1]
                    cap_radius = max(1, line_width // 2)
                    
                    pygame.draw.circle(self.screen, color, start_point, cap_radius)
                    pygame.draw.circle(self.screen, color, end_point, cap_radius)
                    
        except Exception as e:
            logger.error("Error in optimized stroke drawing: %s", e)
            self._draw_stroke_fallback(points, color, width)

    def _smooth_stroke_aggressive(self, points: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """IMPROVED: Aggressive stroke smoothing to eliminate gaps and sharp edges."""
        if len(points) < 2:
            return points
            
        smoothed = [points[0]]
        
        for i in range(1, len(points)):
            prev_point = smoothed[-1]
            curr_point = points[i]
            
            # Calculate distance between points
            dx = curr_point[0] - prev_point[0]
            dy = curr_point[1] - prev_point[1]
            distance = math.sqrt(dx * dx + dy * dy)
            
            # If points are far apart, interpolate with MORE points
            if distance > STROKE_SMOOTHING_THRESHOLD:
                interpolated = interpolate_points(prev_point, curr_point)
                smoothed.extend(interpolated[1:])  # Skip first point to avoid duplicate
            else:
                smoothed.append(curr_point)
                
        return smoothed

    def _draw_stroke_fallback(self, points: List[Any], color: Tuple[int, int, int], default_width: int) -> None:
        """Fallback stroke drawing method."""
        try:
            for i in range(len(points) - 1):
                try:
                    x0, y0, w0 = self._point_cache.convert_point(points[i], default_width)
                    x1, y1, w1 = self._point_cache.convert_point(points[i + 1], default_width)
                    
                    line_width = max(1, min(w0, w1, 20))
                    self.draw_line((x0, y0), (x1, y1), line_width, color)
                    
                except Exception as e:
                    logger.error("Error drawing stroke segment %d: %s", i, e)
                    continue
                    
        except Exception as e:
            logger.error("Error in fallback stroke drawing: %s", e)

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
    GraphicsMixin, TextMixin, OptimizedStrokeMixin,
    CursorMixin, UIMixin, Engine
):
    """Composite adapter implementing Engine via mixins."""
    screen: Optional[pygame.Surface] = None

    def __init__(self) -> None:
        """Initialize the pygame engine adapter."""
        super().__init__()
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