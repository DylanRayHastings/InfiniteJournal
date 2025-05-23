# adapters/pygame_adapter.py (CRITICAL FIXES - Drawing phasing and distortions)
"""
PyGame Adapter with CRITICAL FIXES for drawing phasing, distortions, and brush rendering.
"""

import pygame
import logging
import math
from typing import Any, Dict, List, Optional, Tuple
from icecream import ic
from core.interfaces import Engine, Clock, Event, InputAdapter
from core.event_bus import EventBus

logger = logging.getLogger(__name__)

# Constants
DEFAULT_CLEAR_COLOR: Tuple[int, int, int] = (0, 0, 0)
DEFAULT_DRAW_COLOR: Tuple[int, int, int] = (255, 255, 255)
DEFAULT_FONT_NAME: Optional[str] = None

# CRITICAL FIX: Optimized constants for smooth rendering
MAX_STROKE_SEGMENTS = 500  # Reduced for performance
STROKE_SMOOTHING_THRESHOLD = 3  # Reduced for smoother lines
BATCH_RENDER_SIZE = 25  # Smaller batches for stability

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
            try:
                font = pygame.font.SysFont(DEFAULT_FONT_NAME, size)
                cls._cache[size] = font
            except Exception as e:
                logger.error("Failed to create font size %d: %s", size, e)
                font = pygame.font.Font(None, 12)
        return font

class OptimizedPointCache:
    """CRITICAL FIX: Optimized point conversion for smooth rendering."""
    
    def __init__(self, max_size: int = 500):  # Smaller cache for performance
        self._cache = {}
        self._max_size = max_size
        
    def convert_point(self, pt: Any, default_width: int) -> Tuple[int, int, int]:
        """Convert point with CRITICAL optimizations."""
        try:
            if hasattr(pt, "x") and hasattr(pt, "y"):
                x = int(pt.x)
                y = int(pt.y)
                width = getattr(pt, "width", default_width)
            elif isinstance(pt, (tuple, list)) and len(pt) >= 2:
                x = int(pt[0])
                y = int(pt[1])
                width = pt[2] if len(pt) >= 3 else default_width
            else:
                return 100, 100, max(1, default_width)
            
            # CRITICAL FIX: Clamp values to prevent distortions
            x = max(0, min(9999, x))
            y = max(0, min(9999, y))
            width = max(1, min(100, int(width)))  # Limit max width to prevent distortions
            
            return x, y, width
            
        except (ValueError, TypeError, OverflowError):
            return 100, 100, max(1, default_width)

def validate_color(color: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Validate and ensure color is a proper RGB tuple."""
    if not isinstance(color, (tuple, list)) or len(color) != 3:
        return DEFAULT_DRAW_COLOR
    
    try:
        r, g, b = color
        r = max(0, min(255, int(r)))
        g = max(0, min(255, int(g)))
        b = max(0, min(255, int(b)))
        return (r, g, b)
    except (ValueError, TypeError):
        return DEFAULT_DRAW_COLOR

def interpolate_points_smooth(p1: Tuple[int, int], p2: Tuple[int, int]) -> List[Tuple[int, int]]:
    """CRITICAL FIX: Generate smooth interpolated points without distortions."""
    x1, y1 = p1
    x2, y2 = p2
    
    dx = x2 - x1
    dy = y2 - y1
    distance = math.sqrt(dx * dx + dy * dy)
    
    if distance < 1:
        return [p1]
    
    # CRITICAL FIX: Limit steps to prevent rendering distortions
    steps = max(2, min(int(distance / 2), 15))  # Limited steps for performance
    
    points = []
    for i in range(steps + 1):
        t = i / steps
        x = int(x1 + dx * t)
        y = int(y1 + dy * t)
        points.append((x, y))
    
    return points

# Mixins
class WindowMixin:
    """Provides window initialization methods."""

    def open_window(self, width: int, height: int, title: str) -> None:
        """Alias to init_window."""
        self.init_window(width, height, title)

    def init_window(self, width: int, height: int, title: str) -> None:
        """Initialize pygame window with stable settings."""
        if width <= 0 or height <= 0:
            raise AdapterError("Window dimensions must be positive")
            
        try:
            pygame.init()
            pygame.font.init()
            
            # CRITICAL FIX: Stable display flags to prevent phasing
            flags = pygame.DOUBLEBUF | pygame.HWSURFACE
            
            try:
                self.screen = pygame.display.set_mode((width, height), flags, vsync=1)
            except (TypeError, pygame.error):
                self.screen = pygame.display.set_mode((width, height), flags)
                    
            pygame.display.set_caption(title)
            pygame.display.flip()  # Initial flip
            
            logger.info("Window initialized: %dx%d '%s'", width, height, title)
            
        except Exception as e:
            logger.error("Failed to initialize window: %s", e)
            raise AdapterError(f"Window initialization failed: {e}") from e

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

    def present(self) -> None:
        """Present the rendered frame to the display."""
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        
        # CRITICAL FIX: Single flip for stable rendering
        pygame.display.flip()

class PollMixin:
    """Handles polling Pygame events."""

    def poll_events(self) -> List[Event]:
        """Poll pygame events and convert to core Events."""
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        
        events: List[Event] = []
        try:
            raw = pygame.event.get()
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
        except Exception as e:
            logger.error("Error polling events: %s", e)
            
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
            start_pos = (max(0, min(9999, int(start[0]))), max(0, min(9999, int(start[1]))))
            end_pos = (max(0, min(9999, int(end[0]))), max(0, min(9999, int(end[1]))))
            line_width = max(1, min(100, int(width)))  # CRITICAL: Limit width
            
            pygame.draw.line(self.screen, line_color, start_pos, end_pos, line_width)
        except Exception as e:
            logger.debug("Error drawing line: %s", e)

    def draw_circle(
        self, center: Tuple[int, int], radius: int,
        color: Optional[Tuple[int, int, int]] = None, width: int = 0
    ) -> None:
        """Draw a circle at the specified center with given radius."""
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        
        try:
            circle_color = validate_color(color) if color is not None else DEFAULT_DRAW_COLOR
            center_pos = (max(0, min(9999, int(center[0]))), max(0, min(9999, int(center[1]))))
            circle_radius = max(1, min(200, int(radius)))  # CRITICAL: Limit radius
            circle_width = max(0, min(50, int(width)))
            
            pygame.draw.circle(self.screen, circle_color, center_pos, circle_radius, circle_width)
        except Exception as e:
            logger.debug("Error drawing circle: %s", e)

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
            text_pos = (max(0, min(9999, int(pos[0]))), max(0, min(9999, int(pos[1]))))
            font_size = max(8, min(72, int(size)))
            safe_text = str(text)[:100]
            
            font = FontManager.get_font(font_size)
            surf = font.render(safe_text, True, text_color)
            self.screen.blit(surf, text_pos)
        except Exception as e:
            logger.debug("Error drawing text: %s", e)

class OptimizedStrokeMixin:
    """CRITICAL FIX: Optimized stroke drawing to prevent phasing and distortions."""
    
    def __init__(self):
        super().__init__()
        self._point_cache = OptimizedPointCache()

    def draw_stroke(
        self, points: List[Any], color: Optional[Tuple[int, int, int]] = None,
        default_width: int = 3
    ) -> None:
        """CRITICAL FIX: Draw stroke without phasing or distortions."""
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        
        if not points:
            return
            
        try:
            stroke_color = validate_color(color) if color is not None else DEFAULT_DRAW_COLOR
            
            # Skip gray preview lines
            if stroke_color == (128, 128, 128):
                return
            
            point_count = len(points)
            
            if point_count == 1:
                # CRITICAL FIX: Single point rendering
                self._draw_single_point_optimized(points[0], stroke_color, default_width)
                return
            
            # CRITICAL FIX: Optimized multi-point rendering
            self._draw_multi_point_optimized(points, stroke_color, default_width)
            
        except Exception as e:
            logger.error("Error drawing stroke: %s", e)

    def _draw_single_point_optimized(self, point: Any, color: Tuple[int, int, int], default_width: int) -> None:
        """CRITICAL FIX: Optimized single point rendering."""
        try:
            x, y, w = self._point_cache.convert_point(point, default_width)
            
            # CRITICAL FIX: Proper radius calculation to prevent distortions
            radius = max(1, min(50, w // 2))  # Limit radius to prevent distortions
            
            # Draw filled circle
            pygame.draw.circle(self.screen, color, (x, y), radius)
            
        except Exception as e:
            logger.error("Error drawing single point: %s", e)

    def _draw_multi_point_optimized(self, points: List[Any], color: Tuple[int, int, int], default_width: int) -> None:
        """CRITICAL FIX: Optimized multi-point rendering to prevent phasing."""
        try:
            # Convert points efficiently
            converted_points = []
            for point in points:
                try:
                    x, y, _ = self._point_cache.convert_point(point, default_width)
                    converted_points.append((x, y))
                except Exception:
                    continue
            
            if len(converted_points) < 2:
                return
            
            # CRITICAL FIX: Limit width to prevent distortions
            line_width = max(1, min(50, default_width))
            
            # CRITICAL FIX: Use optimized line drawing
            try:
                # Draw connected lines for smooth stroke
                for i in range(len(converted_points) - 1):
                    start_point = converted_points[i]
                    end_point = converted_points[i + 1]
                    
                    # CRITICAL FIX: Interpolate only if points are far apart
                    dx = end_point[0] - start_point[0]
                    dy = end_point[1] - start_point[1]
                    distance = math.sqrt(dx * dx + dy * dy)
                    
                    if distance > STROKE_SMOOTHING_THRESHOLD:
                        # Interpolate for smooth line
                        interpolated = interpolate_points_smooth(start_point, end_point)
                        for j in range(len(interpolated) - 1):
                            pygame.draw.line(self.screen, color, interpolated[j], interpolated[j + 1], line_width)
                    else:
                        # Direct line for close points
                        pygame.draw.line(self.screen, color, start_point, end_point, line_width)
                
                # CRITICAL FIX: Add end caps for smooth appearance
                if line_width > 2:
                    cap_radius = max(1, line_width // 2)
                    pygame.draw.circle(self.screen, color, converted_points[0], cap_radius)
                    pygame.draw.circle(self.screen, color, converted_points[-1], cap_radius)
                    
            except Exception as draw_error:
                logger.error("Error in optimized line drawing: %s", draw_error)
                # Fallback to simple lines
                for i in range(len(converted_points) - 1):
                    try:
                        pygame.draw.line(self.screen, color, converted_points[i], converted_points[i + 1], line_width)
                    except Exception:
                        continue
                    
        except Exception as e:
            logger.error("Error in multi-point rendering: %s", e)

class CursorMixin:
    """Provides cursor drawing method."""

    def draw_cursor(
        self, pos: Tuple[int, int], radius: int,
        color: Optional[Tuple[int, int, int]] = None
    ) -> None:
        """Draw a cursor at the specified position."""
        cursor_color = validate_color(color) if color is not None else DEFAULT_DRAW_COLOR
        try:
            safe_pos = (max(0, min(9999, int(pos[0]))), max(0, min(9999, int(pos[1]))))
            safe_radius = max(1, min(100, int(radius)))
            self.draw_circle(safe_pos, safe_radius, cursor_color)
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
            safe_mode = str(mode)[:20]
            safe_timestamp = str(timestamp)[:50]
            
            self.draw_text(f"Mode: {safe_mode}", (10, 10), 16, ui_color)
            height = self.screen.get_height()
            self.draw_text(safe_timestamp, (10, height - 20), 14, ui_color)
        except Exception as e:
            logger.error("Error drawing UI: %s", e)


class PygameEngineAdapter(
    WindowMixin, DisplayMixin, PollMixin,
    GraphicsMixin, TextMixin, OptimizedStrokeMixin,
    CursorMixin, UIMixin, Engine
):
    """Composite adapter with CRITICAL FIXES for smooth rendering."""
    screen: Optional[pygame.Surface] = None

    def __init__(self) -> None:
        """Initialize the pygame engine adapter."""
        super().__init__()
        self.screen = None
        logger.info("PygameEngineAdapter initialized with CRITICAL drawing fixes")


class PygameClockAdapter(Clock):
    """Clock implementation using Pygame."""

    def __init__(self) -> None:
        try:
            self._clock = pygame.time.Clock()
            self._last_tick_time = 0.0
            logger.info("PygameClockAdapter initialized")
        except Exception as e:
            logger.error("Failed to initialize clock: %s", e)
            raise

    def tick(self, target_fps: int) -> float:
        """Enforce target FPS and return actual frame time in seconds."""
        try:
            safe_fps = max(30, min(120, int(target_fps)))  # CRITICAL: Limit FPS range
            self._last_tick_time = self._clock.tick(safe_fps) / 1000.0
            return self._last_tick_time
        except Exception as e:
            logger.error("Error in clock tick: %s", e)
            return 0.016  # ~60 FPS fallback

    def get_time(self) -> float:
        """Get current time in seconds since pygame initialization."""
        try:
            time_ms = pygame.time.get_ticks()
            return time_ms / 1000.0
        except Exception as e:
            logger.error("Error getting time: %s", e)
            return 0.0

    def get_fps(self) -> float:
        """Get the current frames per second."""
        try:
            return self._clock.get_fps()
        except Exception as e:
            logger.error("Error getting FPS: %s", e)
            return 60.0


class PygameInputAdapter(InputAdapter):
    """Pass-through input adapter for pygame events."""

    def __init__(self) -> None:
        """Initialize the input adapter."""
        logger.info("PygameInputAdapter initialized")

    def translate(self, events: List[Event]) -> List[Event]:
        """Translate events."""
        return events