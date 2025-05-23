"""
Pygame Engine Adapter
Integrates pygame with the Universal Services Framework.

This adapter was missing and causing import errors in main.py.
"""

import logging
import pygame
from typing import List, Tuple, Optional, Any, Dict

logger = logging.getLogger(__name__)


class PygameEvent:
    """Wrapper for pygame events to match expected interface."""
    
    def __init__(self, pygame_event):
        self.pygame_event = pygame_event
        self.type = self._convert_event_type(pygame_event.type)
        self.data = self._extract_event_data(pygame_event)
    
    def _convert_event_type(self, pygame_type) -> str:
        """Convert pygame event type to universal format."""
        type_mapping = {
            pygame.QUIT: 'QUIT',
            pygame.MOUSEBUTTONDOWN: 'MOUSE_DOWN',
            pygame.MOUSEBUTTONUP: 'MOUSE_UP', 
            pygame.MOUSEMOTION: 'MOUSE_MOVE',
            pygame.KEYDOWN: 'KEY_PRESS',
            pygame.KEYUP: 'KEY_RELEASE',
            pygame.MOUSEWHEEL: 'SCROLL_WHEEL'
        }
        return type_mapping.get(pygame_type, f'UNKNOWN_{pygame_type}')
    
    def _extract_event_data(self, event) -> Dict[str, Any]:
        """Extract relevant data from pygame event."""
        data = {}
        
        if hasattr(event, 'pos'):
            data['pos'] = event.pos
            
        if hasattr(event, 'button'):
            data['button'] = event.button
            
        if hasattr(event, 'rel'):
            data['rel'] = event.rel
            
        if hasattr(event, 'key'):
            data['key'] = pygame.key.name(event.key) if event.key else ''
            
        if hasattr(event, 'y'):  # Mouse wheel
            data['direction'] = event.y
            
        return data


class PygameEngineAdapter:
    """
    Pygame engine adapter for Universal Services Framework.
    
    Provides the rendering backend interface that the application expects.
    """
    
    def __init__(self):
        self.screen = None
        self.clock = None
        self.window_width = 1280
        self.window_height = 720
        self.window_title = "InfiniteJournal"
        self.is_initialized = False
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def init_window(self, width: int, height: int, title: str):
        """Initialize pygame window."""
        try:
            if not self.is_initialized:
                pygame.init()
                self.is_initialized = True
                
            self.window_width = width
            self.window_height = height
            self.window_title = title
            
            # Create display
            self.screen = pygame.display.set_mode((width, height))
            pygame.display.set_caption(title)
            
            # Create clock for frame rate control
            self.clock = pygame.time.Clock()
            
            self.logger.info(f"Pygame window initialized: {width}x{height} '{title}'")
            
        except Exception as error:
            self.logger.error(f"Failed to initialize pygame window: {error}")
            raise
    
    def open_window(self, width: int, height: int, title: str):
        """Alternative method name for window initialization."""
        self.init_window(width, height, title)
    
    def clear(self, color: Optional[Tuple[int, int, int]] = None):
        """Clear the rendering surface."""
        if not self.screen:
            return
            
        clear_color = color or (0, 0, 0)  # Default to black
        self.screen.fill(clear_color)
    
    def present(self):
        """Present the rendered frame."""
        if self.screen:
            pygame.display.flip()
    
    def flip(self):
        """Alternative method name for present."""
        self.present()
    
    def draw_line(self, start: Tuple[int, int], end: Tuple[int, int], 
                  width: int, color: Tuple[int, int, int]):
        """Draw line between two points."""
        if self.screen:
            pygame.draw.line(self.screen, color, start, end, width)
    
    def draw_circle(self, center: Tuple[int, int], radius: int, 
                   color: Tuple[int, int, int], width: int = 0):
        """Draw circle at center with radius."""
        if self.screen:
            pygame.draw.circle(self.screen, color, center, radius, width)
    
    def draw_rect(self, rect: Tuple[int, int, int, int], 
                  color: Tuple[int, int, int], width: int = 0):
        """Draw rectangle."""
        if self.screen:
            pygame.draw.rect(self.screen, color, rect, width)
    
    def draw_text(self, text: str, pos: Tuple[int, int], 
                  size: int, color: Tuple[int, int, int]):
        """Draw text at position."""
        if self.screen:
            try:
                font = pygame.font.Font(None, size)
                text_surface = font.render(text, True, color)
                self.screen.blit(text_surface, pos)
            except Exception as error:
                self.logger.warning(f"Failed to draw text: {error}")
    
    def poll_events(self) -> List[PygameEvent]:
        """Poll input events."""
        events = []
        
        for pygame_event in pygame.event.get():
            wrapped_event = PygameEvent(pygame_event)
            events.append(wrapped_event)
            
        return events
    
    def tick(self, fps: int = 60) -> float:
        """Tick the clock and return delta time."""
        if self.clock:
            return self.clock.tick(fps) / 1000.0  # Convert to seconds
        return 1.0 / fps
    
    def get_screen_size(self) -> Tuple[int, int]:
        """Get current screen size."""
        return (self.window_width, self.window_height)
    
    def quit(self):
        """Shutdown pygame."""
        if self.is_initialized:
            pygame.quit()
            self.is_initialized = False
            self.logger.info("Pygame shutdown")


class PygameInputAdapter:
    """Input adapter for pygame integration."""
    
    def __init__(self, engine_adapter: PygameEngineAdapter):
        self.engine_adapter = engine_adapter
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def poll_events(self) -> List[PygameEvent]:
        """Poll events from pygame."""
        return self.engine_adapter.poll_events()
    
    def get_mouse_pos(self) -> Tuple[int, int]:
        """Get current mouse position."""
        return pygame.mouse.get_pos()
    
    def is_mouse_pressed(self, button: int = 1) -> bool:
        """Check if mouse button is pressed."""
        buttons = pygame.mouse.get_pressed()
        return buttons[button - 1] if button <= len(buttons) else False
    
    def get_keys_pressed(self) -> Dict[str, bool]:
        """Get currently pressed keys."""
        pressed = pygame.key.get_pressed()
        return {pygame.key.name(i): pressed[i] for i in range(len(pressed)) if pressed[i]}


class PygameClock:
    """Clock wrapper for frame rate management."""
    
    def __init__(self):
        self.pygame_clock = pygame.time.Clock()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def tick(self, fps: int = 60) -> float:
        """Tick the clock and return delta time."""
        return self.pygame_clock.tick(fps) / 1000.0
    
    def get_fps(self) -> float:
        """Get current FPS."""
        return self.pygame_clock.get_fps()
    
    def get_time(self) -> int:
        """Get time since last tick."""
        return self.pygame_clock.get_time()


# Factory functions for creating pygame components
def create_pygame_adapter() -> PygameEngineAdapter:
    """Create pygame engine adapter."""
    return PygameEngineAdapter()


def create_pygame_input_adapter(engine_adapter: PygameEngineAdapter) -> PygameInputAdapter:
    """Create pygame input adapter."""
    return PygameInputAdapter(engine_adapter)


def create_pygame_clock() -> PygameClock:
    """Create pygame clock."""
    return PygameClock()


def create_pygame_bus() -> Any:
    """Create simple event bus for pygame integration."""
    # This is a placeholder - the actual event bus would come from services
    class SimpleBus:
        def __init__(self):
            self.events = []
        
        def publish(self, event_name: str, data: Any = None):
            self.events.append((event_name, data))
        
        def subscribe(self, event_name: str, handler):
            pass  # Simplified for compatibility
    
    return SimpleBus()


# Compatibility exports
__all__ = [
    'PygameEngineAdapter',
    'PygameInputAdapter', 
    'PygameClock',
    'PygameEvent',
    'create_pygame_adapter',
    'create_pygame_input_adapter',
    'create_pygame_clock',
    'create_pygame_bus'
]