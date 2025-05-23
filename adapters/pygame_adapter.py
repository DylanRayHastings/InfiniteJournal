"""
PyGame Adapter for single point rendering and improved stroke smoothing.
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
STROKE_SMOOTHING_THRESHOLD = 6  # Optimized for better smoothing
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
    """Caches and provides Pygame fonts by size with proper cleanup."""
    _cache: Dict[int, pygame.font.Font] = {}

    @classmethod
    def get_font(cls, size: int) -> pygame.font.Font:
        """Get or create a font of the specified size."""
        font = cls._cache.get(size)
        if font is None:
            try:
                font = pygame.font.SysFont(DEFAULT_FONT_NAME, size)
                cls._cache[size] = font
                logger.debug("Font cached size=%d", size)
            except Exception as e:
                logger.error("Failed to create font size %d: %s", size, e)
                # Fallback to default size
                font = cls._cache.get(12)
                if font is None:
                    font = pygame.font.Font(None, 12)
                    cls._cache[12] = font
        return font

    @classmethod
    def clear_cache(cls) -> None:
        """Clear font cache to free memory."""
        cls._cache.clear()

class PointCache:
    """Optimized point conversion with LRU cache and proper error handling."""
    
    def __init__(self, max_size: int = 1000):
        self._cache = {}
        self._access_order = []
        self._max_size = max_size
        
    def convert_point(self, pt: Any, default_width: int) -> Tuple[int, int, int]:
        """Convert and cache point conversions with proper error handling."""
        # Generate cache key
        if hasattr(pt, "x") and hasattr(pt, "y"):
            key = (pt.x, pt.y, getattr(pt, "width", default_width))
        elif isinstance(pt, (tuple, list)) and len(pt) >= 2:
            key = tuple(pt[:3]) if len(pt) >= 3 else (*pt[:2], default_width)
        else:
            return self._convert_uncached(pt, default_width)
            
        # Check cache
        if key in self._cache:
            # Move to end (most recently used)
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]
            
        # Convert and cache
        result = self._convert_uncached(pt, default_width)
        
        # Manage cache size (LRU eviction)
        if len(self._cache) >= self._max_size:
            oldest_key = self._access_order.pop(0)
            del self._cache[oldest_key]
                
        self._cache[key] = result
        self._access_order.append(key)
        return result
    
    def _convert_uncached(self, pt: Any, default_width: int) -> Tuple[int, int, int]:
        """Convert point without caching with comprehensive error handling."""
        try:
            if hasattr(pt, "x") and hasattr(pt, "y"):
                width = getattr(pt, "width", default_width)
                # Ensure valid coordinates
                x = max(0, min(9999, int(pt.x)))
                y = max(0, min(9999, int(pt.y)))
                w = max(1, min(200, int(width)))
                return x, y, w
                
            if isinstance(pt, (tuple, list)):
                if len(pt) >= 3:
                    x = max(0, min(9999, int(pt[0])))
                    y = max(0, min(9999, int(pt[1])))
                    w = max(1, min(200, int(pt[2])))
                    return x, y, w
                elif len(pt) >= 2:
                    x = max(0, min(9999, int(pt[0])))
                    y = max(0, min(9999, int(pt[1])))
                    w = max(1, min(200, default_width))
                    return x, y, w
                else:
                    logger.error("Point tuple too short: %r", pt)
                    raise AdapterError(f"Point tuple must have at least 2 elements: {pt}")
            else:
                logger.error("Invalid point format: %r (type: %s)", pt, type(pt))
                raise AdapterError(f"Unsupported point format: {pt}")
                
        except (ValueError, TypeError, OverflowError) as e:
            logger.error("Error unpacking point %r: %s", pt, e)
            # Return safe default
            return 100, 100, max(1, default_width)

def validate_color(color: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Validate and ensure color is a proper RGB tuple with proper error handling."""
    if not isinstance(color, (tuple, list)) or len(color) != 3:
        logger.warning("Invalid color format: %r, using default", color)
        return DEFAULT_DRAW_COLOR
    
    try:
        r, g, b = color
        r = max(0, min(255, int(r)))
        g = max(0, min(255, int(g)))
        b = max(0, min(255, int(b)))
        return (r, g, b)
    except (ValueError, TypeError) as e:
        logger.warning("Error validating color %r: %s, using default", color, e)
        return DEFAULT_DRAW_COLOR

def interpolate_points(p1: Tuple[int, int], p2: Tuple[int, int]) -> List[Tuple[int, int]]:
    """Generate smoothly interpolated points between two points with optimized algorithm."""
    x1, y1 = p1
    x2, y2 = p2
    
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    
    # Optimized step calculation for smoother lines
    distance = math.sqrt(dx * dx + dy * dy)
    if distance < 1:
        return [p1]
    
    # Dynamic step size based on distance for optimal smoothness
    steps = max(int(distance / 2), 5, min(int(distance), 20))
    
    points = []
    x_step = (x2 - x1) / steps
    y_step = (y2 - y1) / steps
    
    for i in range(steps + 1):
        x = int(x1 + i * x_step)
        y = int(y1 + i * y_step)
        points.append((x, y))
    
    return points

# Mixins with improved error handling
class WindowMixin:
    """Provides window initialization methods with comprehensive error handling."""

    def open_window(self, width: int, height: int, title: str) -> None:
        """Alias to init_window."""
        self.init_window(width, height, title)

    def init_window(self, width: int, height: int, title: str) -> None:
        """Initialize pygame window with robust error handling."""
        if width <= 0 or height <= 0:
            logger.error("Invalid window size %dx%d", width, height)
            raise AdapterError("Window dimensions must be positive")
            
        try:
            pygame.init()
            pygame.font.init()
            
            # Try different display configurations for compatibility
            flags = pygame.SCALED | pygame.RESIZABLE | pygame.DOUBLEBUF | pygame.HWSURFACE
            
            try:
                self.screen = pygame.display.set_mode((width, height), flags, vsync=1)
                logger.info("Window initialized with vsync")
            except (TypeError, pygame.error):
                try:
                    self.screen = pygame.display.set_mode((width, height), flags)
                    logger.warning("Vsync unsupported, falling back")
                except pygame.error:
                    # Minimal fallback
                    self.screen = pygame.display.set_mode((width, height))
                    logger.warning("Advanced flags unsupported, using basic mode")
                    
            pygame.display.set_caption(title)
            logger.info("Window initialized successfully: %dx%d '%s'", width, height, title)
            
        except Exception as e:
            logger.error("Failed to initialize window: %s", e)
            raise AdapterError(f"Window initialization failed: {e}") from e

    def get_size(self) -> Tuple[int, int]:
        """Get the current window/screen size with error handling."""
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        try:
            return self.screen.get_size()
        except Exception as e:
            logger.error("Failed to get screen size: %s", e)
            return (800, 600)  # Safe fallback

class DisplayMixin:
    """Provides screen clear and present methods with error handling."""

    def clear(self, color: Optional[Tuple[int, int, int]] = None) -> None:
        """Clear the screen with the specified color."""
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        try:
            clear_color = validate_color(color) if color is not None else DEFAULT_CLEAR_COLOR
            self.screen.fill(clear_color)
            logger.debug("Screen cleared with color %s", clear_color)
        except Exception as e:
            logger.error("Failed to clear screen: %s", e)

    def present(self) -> None:
        """Present the rendered frame to the display."""
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        try:
            pygame.display.flip()
            logger.debug("Screen presented")
        except Exception as e:
            logger.error("Failed to present screen: %s", e)

class PollMixin:
    """Handles polling Pygame events and mapping to core.Event with error handling."""

    def poll_events(self) -> List[Event]:
        """Poll pygame events and convert to core Events with error handling."""
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        
        events: List[Event] = []
        try:
            raw = pygame.event.get()
            for e in raw:
                try:
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
                except Exception as event_error:
                    logger.warning("Error processing event %s: %s", e.type, event_error)
                    continue
                    
            logger.debug("Polled %d events", len(events))
        except Exception as e:
            logger.error("Error polling events: %s", e)
            
        return events

class GraphicsMixin:
    """Provides basic shape drawing methods with error handling."""

    def draw_line(
        self, start: Tuple[int, int], end: Tuple[int, int], width: int,
        color: Optional[Tuple[int, int, int]] = None
    ) -> None:
        """Draw a line between two points with error handling."""
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        
        try:
            line_color = validate_color(color) if color is not None else DEFAULT_DRAW_COLOR
            start_pos = (max(0, min(9999, int(start[0]))), max(0, min(9999, int(start[1]))))
            end_pos = (max(0, min(9999, int(end[0]))), max(0, min(9999, int(end[1]))))
            line_width = max(1, min(50, int(width)))
            
            pygame.draw.line(self.screen, line_color, start_pos, end_pos, line_width)
            logger.debug("Line %s->%s width=%d color=%s", start_pos, end_pos, line_width, line_color)
        except (ValueError, TypeError, IndexError) as e:
            logger.error("Error drawing line from %s to %s: %s", start, end, e)
            # Don't raise - continue rendering
        except Exception as e:
            logger.error("Unexpected error drawing line: %s", e)

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
            circle_radius = max(1, min(500, int(radius)))
            circle_width = max(0, min(50, int(width)))
            
            pygame.draw.circle(self.screen, circle_color, center_pos, circle_radius, circle_width)
            logger.debug("Circle at %s radius=%d color=%s", center_pos, circle_radius, circle_color)
        except (ValueError, TypeError, IndexError) as e:
            logger.error("Error drawing circle at %s radius %d: %s", center, radius, e)
        except Exception as e:
            logger.error("Unexpected error drawing circle: %s", e)

class TextMixin:
    """Provides text rendering method with error handling."""

    def draw_text(
        self, text: str, pos: Tuple[int, int], size: int,
        color: Optional[Tuple[int, int, int]] = None
    ) -> None:
        """Render text at the specified position with error handling."""
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        
        try:
            text_color = validate_color(color) if color is not None else DEFAULT_DRAW_COLOR
            text_pos = (max(0, min(9999, int(pos[0]))), max(0, min(9999, int(pos[1]))))
            font_size = max(8, min(72, int(size)))
            safe_text = str(text)[:100]  # Limit text length
            
            font = FontManager.get_font(font_size)
            surf = font.render(safe_text, True, text_color)
            self.screen.blit(surf, text_pos)
            logger.debug("Text '%s' at %s size=%d color=%s", safe_text[:20], text_pos, font_size, text_color)
        except (ValueError, TypeError, IndexError) as e:
            logger.error("Error drawing text '%s' at %s: %s", text, pos, e)
        except Exception as e:
            logger.error("Unexpected error drawing text: %s", e)

class OptimizedStrokeMixin:
    """Provides optimized stroke drawing methods with CRITICAL FIXES."""
    
    def __init__(self):
        super().__init__()
        self._point_cache = PointCache()
        self._stroke_buffer = []

    def draw_stroke(
        self, points: List[Any], color: Optional[Tuple[int, int, int]] = None,
        default_width: int = 3
    ) -> None:
        """Draw an optimized stroke with CRITICAL FIX for single point rendering."""
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        
        if not points:
            return
            
        try:
            stroke_color = validate_color(color) if color is not None else DEFAULT_DRAW_COLOR
            point_count = len(points)
            
            if point_count == 1:
                # CRITICAL FIX: Single point rendering with CORRECT radius calculation
                self._draw_single_point_critical_fix(points[0], stroke_color, default_width)
                return
            
            # Convert points efficiently
            converted_points = self._convert_points_batch(points, default_width)
            
            if len(converted_points) < 2:
                # Handle edge case: if conversion fails, try single point
                if points:
                    self._draw_single_point_critical_fix(points[0], stroke_color, default_width)
                return
                
            # Draw optimized stroke with improved smoothing
            self._draw_optimized_stroke_smooth(converted_points, stroke_color, default_width)
            
            logger.debug("Optimized stroke drawn with %d points, color=%s", point_count, stroke_color)
            
        except Exception as e:
            logger.error("Error drawing optimized stroke: %s", e)
            # Fallback to simple stroke
            self._draw_stroke_fallback(points, stroke_color, default_width)

    def _draw_single_point_critical_fix(self, point: Any, color: Tuple[int, int, int], default_width: int) -> None:
        """CRITICAL FIX: Draw a single point as a circle with CORRECT radius calculation."""
        try:
            x, y, w = self._point_cache.convert_point(point, default_width)
            
            # CRITICAL FIX: Use width/2 as radius for proper single point display
            # This was the bug - was using full width as radius, making points huge
            radius = max(1, w // 2)  # <<<< CRITICAL FIX: width/2, not full width
            
            # Draw filled circle for single point
            self.draw_circle((x, y), radius, color)
            logger.debug("FIXED single point drawn at (%d, %d) with radius %d (width %d)", x, y, radius, w)
            
        except Exception as e:
            logger.error("Error drawing single point: %s", e)
            # Ultra-safe fallback
            try:
                self.draw_circle((100, 100), max(1, default_width // 2), color)
            except:
                pass

    def _convert_points_batch(self, points: List[Any], default_width: int) -> List[Tuple[int, int]]:
        """Convert points in batches for better performance with error handling."""
        converted = []
        
        for i in range(0, len(points), BATCH_RENDER_SIZE):
            batch = points[i:i + BATCH_RENDER_SIZE]
            for point in batch:
                try:
                    x, y, _ = self._point_cache.convert_point(point, default_width)
                    converted.append((x, y))
                except Exception as e:
                    logger.debug("Skipping invalid point in batch: %s", e)
                    continue
                    
        return converted

    def _draw_optimized_stroke_smooth(self, points: List[Tuple[int, int]], color: Tuple[int, int, int], width: int) -> None:
        """Draw stroke with IMPROVED smoothing algorithm."""
        if len(points) < 2:
            return
            
        try:
            # Apply improved smoothing
            smoothed_points = self._smooth_stroke_optimized(points)
            
            if len(smoothed_points) >= 2:
                line_width = max(1, min(width, 50))  # Clamp width for safety
                
                # Draw main stroke line with error handling
                try:
                    pygame.draw.lines(self.screen, color, False, smoothed_points, line_width)
                except ValueError as e:
                    # Fallback to individual line segments
                    logger.debug("Lines drawing failed, using fallback: %s", e)
                    for i in range(len(smoothed_points) - 1):
                        try:
                            pygame.draw.line(self.screen, color, smoothed_points[i], smoothed_points[i+1], line_width)
                        except:
                            continue
                
                # Add end caps for better appearance
                if line_width > 2:
                    start_point = smoothed_points[0]
                    end_point = smoothed_points[-1]
                    cap_radius = max(1, line_width // 2)
                    
                    try:
                        pygame.draw.circle(self.screen, color, start_point, cap_radius)
                        pygame.draw.circle(self.screen, color, end_point, cap_radius)
                    except:
                        pass  # End caps are optional
                    
        except Exception as e:
            logger.error("Error in optimized stroke drawing: %s", e)
            self._draw_stroke_fallback(points, color, width)

    def _smooth_stroke_optimized(self, points: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """OPTIMIZED: Advanced stroke smoothing with adaptive interpolation."""
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
            
            # Adaptive smoothing based on distance and angle
            if distance > STROKE_SMOOTHING_THRESHOLD:
                interpolated = interpolate_points(prev_point, curr_point)
                # Add interpolated points (skip first to avoid duplicate)
                smoothed.extend(interpolated[1:])
            else:
                smoothed.append(curr_point)
                
        return smoothed

    def _draw_stroke_fallback(self, points: List[Any], color: Tuple[int, int, int], default_width: int) -> None:
        """Fallback stroke drawing method with comprehensive error handling."""
        if len(points) == 1:
            self._draw_single_point_critical_fix(points[0], color, default_width)
            return
            
        try:
            for i in range(len(points) - 1):
                try:
                    x0, y0, w0 = self._point_cache.convert_point(points[i], default_width)
                    x1, y1, w1 = self._point_cache.convert_point(points[i + 1], default_width)
                    
                    line_width = max(1, min(min(w0, w1), 50))
                    self.draw_line((x0, y0), (x1, y1), line_width, color)
                    
                except Exception as e:
                    logger.debug("Error drawing stroke segment %d: %s", i, e)
                    continue
                    
        except Exception as e:
            logger.error("Critical error in fallback stroke drawing: %s", e)

class CursorMixin:
    """Provides cursor drawing method with error handling."""

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
            logger.debug("Cursor at %s r=%d color=%s", safe_pos, safe_radius, cursor_color)
        except Exception as e:
            logger.error("Error drawing cursor: %s", e)

class UIMixin:
    """Provides UI overlay drawing method with error handling."""

    def draw_ui(
        self, mode: str, timestamp: str,
        color: Optional[Tuple[int, int, int]] = None
    ) -> None:
        """Draw UI overlay with mode and timestamp information."""
        if not hasattr(self, 'screen') or self.screen is None:
            raise NotInitializedError("Screen not initialized")
        
        try:
            ui_color = validate_color(color) if color is not None else DEFAULT_DRAW_COLOR
            safe_mode = str(mode)[:20]  # Limit string length
            safe_timestamp = str(timestamp)[:50]
            
            self.draw_text(f"Mode: {safe_mode}", (10, 10), 16, ui_color)
            height = self.screen.get_height()
            self.draw_text(safe_timestamp, (10, height - 20), 14, ui_color)
            logger.debug("UI overlay drawn with mode=%s", safe_mode)
        except Exception as e:
            logger.error("Error drawing UI: %s", e)


class PygameEngineAdapter(
    WindowMixin, DisplayMixin, PollMixin,
    GraphicsMixin, TextMixin, OptimizedStrokeMixin,
    CursorMixin, UIMixin, Engine
):
    """Composite adapter implementing Engine via mixins with CRITICAL FIXES."""
    screen: Optional[pygame.Surface] = None

    def __init__(self) -> None:
        """Initialize the pygame engine adapter."""
        super().__init__()
        self.screen = None
        logger.info("PygameEngineAdapter initialized with CRITICAL FIXES")

    def __del__(self):
        """Cleanup resources on destruction."""
        try:
            FontManager.clear_cache()
        except:
            pass


class PygameClockAdapter(Clock):
    """Clock implementation using Pygame with error handling."""

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
            safe_fps = max(1, min(240, int(target_fps)))
            self._last_tick_time = self._clock.tick(safe_fps) / 1000.0
            logger.debug("Tick %d FPS, actual time: %.3fs", safe_fps, self._last_tick_time)
            return self._last_tick_time
        except Exception as e:
            logger.error("Error in clock tick: %s", e)
            return 0.016  # ~60 FPS fallback

    def get_time(self) -> float:
        """Get current time in seconds since pygame initialization."""
        try:
            time_ms = pygame.time.get_ticks()
            time_s = time_ms / 1000.0
            logger.debug("Current time: %.3fs", time_s)
            return time_s
        except Exception as e:
            logger.error("Error getting time: %s", e)
            return 0.0

    def get_fps(self) -> float:
        """Get the current frames per second."""
        try:
            fps = self._clock.get_fps()
            logger.debug("Current FPS: %.1f", fps)
            return fps
        except Exception as e:
            logger.error("Error getting FPS: %s", e)
            return 60.0


class PygameInputAdapter(InputAdapter):
    """Pass-through input adapter for pygame events with error handling."""

    def __init__(self) -> None:
        """Initialize the input adapter."""
        logger.info("PygameInputAdapter initialized")

    def translate(self, events: List[Event]) -> List[Event]:
        """Translate events with error handling."""
        try:
            logger.debug("Translating %d events", len(events))
            return events
        except Exception as e:
            logger.error("Error translating events: %s", e)
            return []