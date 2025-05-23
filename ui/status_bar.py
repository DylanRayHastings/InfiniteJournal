"""
Production-ready StatusBar module for displaying elapsed time and notifications.

This module provides a complete status bar implementation that displays timing information
and optional status messages. The design emphasizes modularity, testability, and clear
extension points for team development.

Quick start:
    clock = SystemClock()
    renderer = GraphicsRenderer(screen)
    settings = ApplicationSettings()
    status_bar = StatusBar(clock, renderer, settings)
    status_bar.render_status_display()

Extension points:
    - Add new status indicators: Implement StatusIndicator interface
    - Add status messages: Use StatusMessageManager
    - Customize positioning: Modify StatusBarPosition
    - Add themes: Implement StatusBarTheme interface
"""

import logging
from typing import Protocol, Optional, Tuple, List
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class StatusBarError(Exception):
    """Base exception for status bar operations."""
    pass

class InvalidPositionError(StatusBarError):
    """Position coordinates are invalid."""
    pass

class RenderingError(StatusBarError):
    """Error occurred during rendering."""
    pass

@dataclass(frozen=True)
class StatusBarPosition:
    """Position configuration for status bar display."""
    x: int
    y: int
    
    def __post_init__(self) -> None:
        """Validate position coordinates."""
        if self.x < 0:
            raise InvalidPositionError(f"X position cannot be negative: {self.x}")
        if self.y < 0:
            raise InvalidPositionError(f"Y position cannot be negative: {self.y}")

@dataclass(frozen=True)
class TextStyle:
    """Text styling configuration."""
    font_size: int
    color: Tuple[int, int, int]
    
    def __post_init__(self) -> None:
        """Validate text style parameters."""
        if self.font_size <= 0:
            raise StatusBarError(f"Font size must be positive: {self.font_size}")
        
        if len(self.color) != 3:
            raise StatusBarError(f"Color must be RGB tuple: {self.color}")
        
        for component in self.color:
            if not 0 <= component <= 255:
                raise StatusBarError(f"Color components must be 0-255: {self.color}")

@dataclass(frozen=True)
class StatusBarConfiguration:
    """Complete configuration for status bar display."""
    margin_left: int = 10
    margin_bottom: int = 20
    default_font_size: int = 14
    default_text_color: Tuple[int, int, int] = (255, 255, 255)
    time_precision: int = 1
    
    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.margin_left < 0:
            raise StatusBarError(f"Left margin cannot be negative: {self.margin_left}")
        if self.margin_bottom < 0:
            raise StatusBarError(f"Bottom margin cannot be negative: {self.margin_bottom}")
        if self.time_precision < 0:
            raise StatusBarError(f"Time precision cannot be negative: {self.time_precision}")

class Clock(Protocol):
    """Interface for time providers."""
    
    def get_time(self) -> float:
        """Get current elapsed time in seconds."""
        ...

class Renderer(Protocol):
    """Interface for rendering operations."""
    
    def draw_text(self, text: str, position: Tuple[int, int], font_size: int, color: Tuple[int, int, int]) -> None:
        """Draw text at specified position with given style."""
        ...

class Settings(Protocol):
    """Interface for application settings."""
    
    @property
    def HEIGHT(self) -> int:
        """Get application height."""
        ...

class StatusIndicator(ABC):
    """Abstract base for status indicators."""
    
    @abstractmethod
    def get_display_text(self) -> str:
        """Get text to display for this indicator."""
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if this indicator should be displayed."""
        pass

class TimeIndicator(StatusIndicator):
    """Status indicator for elapsed time display."""
    
    def __init__(self, clock: Clock, precision: int = 1):
        self._clock = clock
        self._precision = precision
    
    def get_display_text(self) -> str:
        """Format elapsed time for display."""
        elapsed_seconds = self._get_elapsed_time()
        return f"Time: {elapsed_seconds:.{self._precision}f}s"
    
    def is_enabled(self) -> bool:
        """Time indicator is always enabled."""
        return True
    
    def _get_elapsed_time(self) -> float:
        """Get current elapsed time from clock."""
        try:
            return self._clock.get_time()
        except Exception as error:
            logger.warning(f"Failed to get elapsed time: {error}")
            return 0.0

def validate_clock_dependency(clock: Clock) -> None:
    """Validate clock dependency is properly configured."""
    if not hasattr(clock, 'get_time'):
        raise StatusBarError("Clock must implement get_time method")

def validate_renderer_dependency(renderer: Renderer) -> None:
    """Validate renderer dependency is properly configured."""
    if not hasattr(renderer, 'draw_text'):
        raise StatusBarError("Renderer must implement draw_text method")

def validate_settings_dependency(settings: Settings) -> None:
    """Validate settings dependency is properly configured."""
    if not hasattr(settings, 'HEIGHT'):
        raise StatusBarError("Settings must have HEIGHT attribute")

def calculate_status_bar_position(settings: Settings, config: StatusBarConfiguration) -> StatusBarPosition:
    """Calculate position for status bar based on settings and configuration."""
    x_position = config.margin_left
    y_position = settings.HEIGHT - config.margin_bottom
    
    return StatusBarPosition(x=x_position, y=y_position)

def create_default_text_style(config: StatusBarConfiguration) -> TextStyle:
    """Create default text style from configuration."""
    return TextStyle(
        font_size=config.default_font_size,
        color=config.default_text_color
    )

def render_text_safely(renderer: Renderer, text: str, position: StatusBarPosition, style: TextStyle) -> None:
    """Render text with comprehensive error handling."""
    try:
        renderer.draw_text(
            text=text,
            position=(position.x, position.y),
            font_size=style.font_size,
            color=style.color
        )
        logger.debug(f"Rendered text: '{text}' at position ({position.x}, {position.y})")
        
    except Exception as error:
        logger.error(f"Failed to render text '{text}': {error}")
        raise RenderingError(f"Text rendering failed: {error}") from error

def collect_enabled_indicators(indicators: List[StatusIndicator]) -> List[str]:
    """Collect display text from all enabled status indicators."""
    enabled_texts = []
    
    for indicator in indicators:
        if not indicator.is_enabled():
            continue
        
        try:
            display_text = indicator.get_display_text()
            enabled_texts.append(display_text)
        except Exception as error:
            logger.warning(f"Failed to get display text from indicator: {error}")
            continue
    
    return enabled_texts

class StatusMessageManager:
    """Manager for status messages and notifications."""
    
    def __init__(self):
        self._messages: List[str] = []
    
    def add_message(self, message: str) -> None:
        """Add status message to display queue."""
        if not message or not message.strip():
            return
        
        self._messages.append(message.strip())
        logger.debug(f"Added status message: {message}")
    
    def get_messages(self) -> List[str]:
        """Get all current status messages."""
        return self._messages.copy()
    
    def clear_messages(self) -> None:
        """Clear all status messages."""
        message_count = len(self._messages)
        self._messages.clear()
        logger.debug(f"Cleared {message_count} status messages")

class StatusBar:
    """
    Production-ready status bar component for displaying elapsed time and notifications.
    
    This class provides a complete status bar implementation with the following features:
    - Configurable positioning and styling
    - Multiple status indicators support
    - Comprehensive error handling and logging
    - Easy extension points for new functionality
    - Full type safety and validation
    
    The design follows dependency injection principles for easy testing and modularity.
    All configuration is externalized and validated. Error handling ensures graceful
    degradation when components fail.
    
    Args:
        clock: Time provider for elapsed time display
        renderer: Graphics renderer for drawing operations
        settings: Application settings for layout calculations
        config: Optional configuration override
    
    Example:
        clock = SystemClock()
        renderer = GraphicsRenderer(screen)
        settings = ApplicationSettings()
        
        status_bar = StatusBar(clock, renderer, settings)
        status_bar.render_status_display()
    
    Extension examples:
        
        # Add custom status indicator
        class NetworkIndicator(StatusIndicator):
            def get_display_text(self) -> str:
                return f"Network: {self.get_connection_status()}"
            
            def is_enabled(self) -> bool:
                return self.network_monitoring_enabled
        
        # Add to status bar
        status_bar.add_status_indicator(NetworkIndicator())
        
        # Add temporary status message
        status_bar.add_status_message("File saved successfully")
    """
    
    def __init__(
        self,
        clock: Clock,
        renderer: Renderer,
        settings: Settings,
        config: Optional[StatusBarConfiguration] = None
    ) -> None:
        self._validate_dependencies(clock, renderer, settings)
        
        self._clock = clock
        self._renderer = renderer
        self._settings = settings
        self._config = config or StatusBarConfiguration()
        
        self._status_indicators: List[StatusIndicator] = []
        self._message_manager = StatusMessageManager()
        
        self._initialize_default_indicators()
        
        logger.info("StatusBar initialized successfully")
    
    def add_status_indicator(self, indicator: StatusIndicator) -> None:
        """Add new status indicator to display."""
        if not isinstance(indicator, StatusIndicator):
            raise StatusBarError("Indicator must implement StatusIndicator interface")
        
        self._status_indicators.append(indicator)
        logger.debug(f"Added status indicator: {type(indicator).__name__}")
    
    def add_status_message(self, message: str) -> None:
        """Add temporary status message for display."""
        self._message_manager.add_message(message)
    
    def clear_status_messages(self) -> None:
        """Clear all temporary status messages."""
        self._message_manager.clear_messages()
    
    def render_status_display(self) -> None:
        """
        Render complete status bar display.
        
        This method orchestrates the entire rendering process:
        1. Calculate display position
        2. Collect status information
        3. Render all status elements
        4. Handle any rendering errors gracefully
        
        The method is designed to never fail completely - if individual
        components fail, they are logged and skipped to maintain
        overall application stability.
        """
        try:
            position = self._calculate_display_position()
            text_style = self._create_text_style()
            status_text = self._build_complete_status_text()
            
            self._render_status_text(status_text, position, text_style)
            
        except Exception as error:
            logger.error(f"Status bar rendering failed: {error}")
            self._render_fallback_display()
    
    def _validate_dependencies(self, clock: Clock, renderer: Renderer, settings: Settings) -> None:
        """Validate all required dependencies are properly configured."""
        validate_clock_dependency(clock)
        validate_renderer_dependency(renderer)
        validate_settings_dependency(settings)
    
    def _initialize_default_indicators(self) -> None:
        """Initialize default status indicators."""
        time_indicator = TimeIndicator(self._clock, self._config.time_precision)
        self.add_status_indicator(time_indicator)
    
    def _calculate_display_position(self) -> StatusBarPosition:
        """Calculate where to position the status bar."""
        return calculate_status_bar_position(self._settings, self._config)
    
    def _create_text_style(self) -> TextStyle:
        """Create text style configuration for rendering."""
        return create_default_text_style(self._config)
    
    def _build_complete_status_text(self) -> str:
        """Build complete status text from all enabled indicators and messages."""
        status_elements = []
        
        indicator_texts = collect_enabled_indicators(self._status_indicators)
        status_elements.extend(indicator_texts)
        
        message_texts = self._message_manager.get_messages()
        status_elements.extend(message_texts)
        
        return " | ".join(status_elements)
    
    def _render_status_text(self, text: str, position: StatusBarPosition, style: TextStyle) -> None:
        """Render status text at specified position with given style."""
        if not text.strip():
            logger.debug("No status text to render")
            return
        
        render_text_safely(self._renderer, text, position, style)
    
    def _render_fallback_display(self) -> None:
        """Render minimal fallback display when main rendering fails."""
        try:
            position = StatusBarPosition(x=10, y=self._settings.HEIGHT - 20)
            style = TextStyle(font_size=12, color=(255, 0, 0))
            fallback_text = "Status: Error"
            
            render_text_safely(self._renderer, fallback_text, position, style)
            logger.info("Rendered fallback status display")
            
        except Exception as error:
            logger.critical(f"Fallback rendering also failed: {error}")

class StatusBarFactory:
    """Factory for creating StatusBar instances with different configurations."""
    
    @staticmethod
    def create_production_status_bar(clock: Clock, renderer: Renderer, settings: Settings) -> StatusBar:
        """Create production status bar with standard configuration."""
        config = StatusBarConfiguration(
            margin_left=10,
            margin_bottom=20,
            default_font_size=14,
            default_text_color=(255, 255, 255),
            time_precision=1
        )
        
        return StatusBar(clock, renderer, settings, config)
    
    @staticmethod
    def create_debug_status_bar(clock: Clock, renderer: Renderer, settings: Settings) -> StatusBar:
        """Create status bar with debug configuration."""
        config = StatusBarConfiguration(
            margin_left=10,
            margin_bottom=20,
            default_font_size=12,
            default_text_color=(0, 255, 0),
            time_precision=3
        )
        
        return StatusBar(clock, renderer, settings, config)
    
    @staticmethod
    def create_minimal_status_bar(clock: Clock, renderer: Renderer, settings: Settings) -> StatusBar:
        """Create minimal status bar for performance-critical scenarios."""
        config = StatusBarConfiguration(
            margin_left=5,
            margin_bottom=15,
            default_font_size=10,
            default_text_color=(200, 200, 200),
            time_precision=0
        )
        
        return StatusBar(clock, renderer, settings, config)

class StatusBarTestHelpers:
    """Helper utilities for testing StatusBar functionality."""
    
    @staticmethod
    def create_mock_clock(elapsed_time: float = 123.4) -> Clock:
        """Create mock clock for testing."""
        class MockClock:
            def get_time(self) -> float:
                return elapsed_time
        
        return MockClock()
    
    @staticmethod
    def create_mock_renderer() -> Renderer:
        """Create mock renderer for testing."""
        class MockRenderer:
            def __init__(self):
                self.drawn_texts = []
            
            def draw_text(self, text: str, position: Tuple[int, int], font_size: int, color: Tuple[int, int, int]) -> None:
                self.drawn_texts.append({
                    'text': text,
                    'position': position,
                    'font_size': font_size,
                    'color': color
                })
        
        return MockRenderer()
    
    @staticmethod
    def create_mock_settings(height: int = 600) -> Settings:
        """Create mock settings for testing."""
        class MockSettings:
            @property
            def HEIGHT(self) -> int:
                return height
        
        return MockSettings()
    
    @staticmethod
    def create_test_status_bar() -> Tuple[StatusBar, Clock, Renderer, Settings]:
        """Create complete test setup for StatusBar."""
        clock = StatusBarTestHelpers.create_mock_clock()
        renderer = StatusBarTestHelpers.create_mock_renderer()
        settings = StatusBarTestHelpers.create_mock_settings()
        
        status_bar = StatusBar(clock, renderer, settings)
        
        return status_bar, clock, renderer, settings