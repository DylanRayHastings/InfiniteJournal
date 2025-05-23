"""
Fixed PyGame Adapter - Simplified and focused on rendering only.

This adapter handles ONLY pygame-specific rendering and input translation.
All drawing logic is handled by the SimpleDrawingService.
"""

import pygame
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from core.interfaces import Engine, Clock, Event, InputAdapter

logger = logging.getLogger(__name__)

# Constants
DEFAULT_CLEAR_COLOR: Tuple[int, int, int] = (0, 0, 0)
DEFAULT_DRAW_COLOR: Tuple[int, int, int] = (255, 255, 255)


class PygameEngineAdapter(Engine):
    """
    Simplified pygame engine adapter focused on rendering.
    
    Does NOT handle drawing logic - that's handled by SimpleDrawingService.
    """
    
    def __init__(self) -> None:
        """Initialize the pygame engine adapter."""
        self.screen: Optional[pygame.Surface] = None
        self._font_cache: Dict[int, pygame.font.Font] = {}
        logger.info("PygameEngineAdapter initialized")

    def init_window(self, width: int, height: int, title: str) -> None:
        """Initialize pygame window."""
        if width <= 0 or height <= 0:
            raise ValueError("Window dimensions must be positive")
            
        try:
            pygame.init()
            pygame.font.init()
            
            # Initialize display
            flags = pygame.DOUBLEBUF | pygame.HWSURFACE
            
            try:
                self.screen = pygame.display.set_mode((width, height), flags, vsync=1)
            except (TypeError, pygame.error):
                self.screen = pygame.display.set_mode((width, height), flags)
                    
            pygame.display.set_caption(title)
            pygame.display.flip()
            
            logger.info("Window initialized: %dx%d '%s'", width, height, title)
            
        except Exception as e:
            logger.error("Failed to initialize window: %s", e)
            raise RuntimeError(f"Window initialization failed: {e}") from e

    def poll_events(self) -> List[Event]:
        """Poll pygame events and convert to our Event format."""
        if not self.screen:
            return []
        
        events: List[Event] = []
        try:
            raw = pygame.event.get()
            for e in raw:
                if e.type == pygame.QUIT:
                    events.append(Event('QUIT', {}))
                elif e.type == pygame.MOUSEMOTION:
                    events.append(Event('MOUSE_MOVE', {'pos': e.pos, 'rel': e.rel}))
                elif e.type == pygame.MOUSEBUTTONDOWN:
                    if e.button in (4, 5):  # Scroll wheel
                        direction = 1 if e.button == 4 else -1
                        events.append(Event('SCROLL_WHEEL', {'direction': direction, 'pos': e.pos}))
                    else:
                        events.append(Event('MOUSE_DOWN', {'pos': e.pos, 'button': e.button}))
                elif e.type == pygame.MOUSEBUTTONUP:
                    events.append(Event('MOUSE_UP', {'pos': e.pos, 'button': e.button}))
                elif e.type == pygame.KEYDOWN:
                    events.append(Event('KEY_PRESS', pygame.key.name(e.key)))
        except Exception as e:
            logger.error("Error polling events: %s", e)
            
        return events

    def clear(self, color: Optional[Tuple[int, int, int]] = None) -> None:
        """Clear the screen."""
        if not self.screen:
            return
        
        clear_color = color if color is not None else DEFAULT_CLEAR_COLOR
        self.screen.fill(clear_color)

    def present(self) -> None:
        """Present the rendered frame."""
        if not self.screen:
            return
        
        try:
            pygame.display.flip()
        except Exception as e:
            logger.error("Error presenting frame: %s", e)

    def draw_line(self, start: Tuple[int, int], end: Tuple[int, int], width: int,
                  color: Optional[Tuple[int, int, int]] = None) -> None:
        """Draw a line."""
        if not self.screen:
            return
        
        try:
            line_color = color if color is not None else DEFAULT_DRAW_COLOR
            safe_width = max(1, int(width))
            
            pygame.draw.line(self.screen, line_color, start, end, safe_width)
            
        except Exception as e:
            logger.debug("Error drawing line: %s", e)

    def draw_circle(self, center: Tuple[int, int], radius: int,
                   color: Optional[Tuple[int, int, int]] = None) -> None:
        """Draw a circle."""
        if not self.screen:
            return
        
        try:
            circle_color = color if color is not None else DEFAULT_DRAW_COLOR
            safe_radius = max(1, min(200, int(radius)))
            
            pygame.draw.circle(self.screen, circle_color, center, safe_radius)
            
        except Exception as e:
            logger.debug("Error drawing circle: %s", e)

    def draw_text(self, text: str, pos: Tuple[int, int], size: int,
                  color: Optional[Tuple[int, int, int]] = None) -> None:
        """Render text at the specified position."""
        if not self.screen:
            return
        
        try:
            text_color = color if color is not None else DEFAULT_DRAW_COLOR
            safe_text = str(text)[:100]  # Limit text length
            safe_size = max(8, min(72, int(size)))
            
            font = self._get_font(safe_size)
            surf = font.render(safe_text, True, text_color)
            self.screen.blit(surf, pos)
            
        except Exception as e:
            logger.debug("Error drawing text: %s", e)

    def draw_stroke_enhanced(self, points: List[Tuple[int, int]], 
                           color: Optional[Tuple[int, int, int]] = None,
                           width: int = 3) -> None:
        """Draw a stroke as connected line segments with end caps."""
        if not self.screen or not points:
            return
            
        try:
            stroke_color = color if color is not None else DEFAULT_DRAW_COLOR
            safe_width = max(1, int(width))
            
            if len(points) == 1:
                # Single point - draw as circle
                radius = max(1, safe_width // 2)
                pygame.draw.circle(self.screen, stroke_color, points[0], radius)
            else:
                # Multi-point stroke
                for i in range(len(points) - 1):
                    pygame.draw.line(self.screen, stroke_color, points[i], points[i + 1], safe_width)
                    
                # Add end caps for smooth appearance
                if safe_width > 2:
                    cap_radius = max(1, safe_width // 2)
                    pygame.draw.circle(self.screen, stroke_color, points[0], cap_radius)
                    pygame.draw.circle(self.screen, stroke_color, points[-1], cap_radius)
                    
        except Exception as e:
            logger.error("Error drawing enhanced stroke: %s", e)

    def get_size(self) -> Tuple[int, int]:
        """Get the current window/screen size."""
        if not self.screen:
            raise RuntimeError("Screen not initialized")
        return self.screen.get_size()

    def _get_font(self, size: int) -> pygame.font.Font:
        """Get or create a font of the specified size."""
        if size not in self._font_cache:
            try:
                self._font_cache[size] = pygame.font.SysFont(None, size)
            except Exception:
                self._font_cache[size] = pygame.font.Font(None, size)
        return self._font_cache[size]


class PygameClockAdapter(Clock):
    """Clock implementation using Pygame."""

    def __init__(self) -> None:
        try:
            self._clock = pygame.time.Clock()
            logger.info("PygameClockAdapter initialized")
        except Exception as e:
            logger.error("Failed to initialize clock: %s", e)
            raise

    def tick(self, target_fps: int) -> float:
        """Enforce target FPS and return frame time."""
        try:
            safe_fps = max(1, min(240, int(target_fps)))
            frame_time_ms = self._clock.tick(safe_fps)
            return frame_time_ms / 1000.0
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
    """Input adapter for pygame events."""

    def __init__(self) -> None:
        """Initialize the input adapter."""
        logger.info("PygameInputAdapter initialized")

    def translate(self, events: List[Event]) -> List[Event]:
        """Translate events (pass through for now)."""
        return events