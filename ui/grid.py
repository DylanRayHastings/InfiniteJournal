"""
Grid widget rendering system for visual background grids.

This module provides a production-ready grid rendering system that handles
various engine types, supports different grid styles, and provides clear
expansion points for new grid features.

Quick start:
    renderer = GridRendererFactory.create_production_renderer()
    widget = GridWidget(renderer, GridConfig.from_defaults())
    widget.render_grid()

Extension points:
    - Add new grid styles: Implement GridStyleProtocol
    - Add new rendering engines: Implement RenderingEngineProtocol  
    - Add new grid patterns: Create new pattern classes
    - Add animation: Implement AnimatedGridRenderer
"""

import logging
from typing import Protocol, Optional, Tuple, List
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

logger = logging.getLogger(__name__)

class GridRenderingError(Exception):
    """Base exception for grid rendering operations."""
    pass

class EngineNotAvailable(GridRenderingError):
    """Rendering engine is not available."""
    pass

class InvalidGridConfiguration(GridRenderingError):
    """Grid configuration is invalid."""
    pass

class RenderingFailure(GridRenderingError):
    """Grid rendering operation failed."""
    pass

class GridPattern(Enum):
    """Available grid pattern types."""
    LINES = "lines"
    DOTS = "dots"
    CROSSES = "crosses"
    SQUARES = "squares"

@dataclass(frozen=True)
class GridDimensions:
    """Grid rendering dimensions."""
    width: int
    height: int
    spacing: int
    
    def __post_init__(self) -> None:
        """Validate grid dimensions after creation."""
        validate_grid_dimensions(self.width, self.height, self.spacing)

@dataclass(frozen=True)
class GridColor:
    """RGB color representation for grid elements."""
    red: int
    green: int
    blue: int
    
    def __post_init__(self) -> None:
        """Validate color values after creation."""
        validate_color_components(self.red, self.green, self.blue)
    
    @property
    def as_tuple(self) -> Tuple[int, int, int]:
        """Get color as RGB tuple."""
        return (self.red, self.green, self.blue)

@dataclass(frozen=True)
class GridConfig:
    """Complete grid rendering configuration."""
    dimensions: GridDimensions
    color: GridColor
    pattern: GridPattern
    line_thickness: int = 1
    
    @classmethod
    def from_defaults(cls) -> 'GridConfig':
        """Create grid configuration with sensible defaults."""
        return cls(
            dimensions=GridDimensions(width=800, height=600, spacing=40),
            color=GridColor(red=30, green=30, blue=30),
            pattern=GridPattern.LINES,
            line_thickness=1
        )
    
    @classmethod
    def create_dot_grid(cls, width: int, height: int) -> 'GridConfig':
        """Create dot pattern grid configuration."""
        return cls(
            dimensions=GridDimensions(width=width, height=height, spacing=20),
            color=GridColor(red=50, green=50, blue=50),
            pattern=GridPattern.DOTS,
            line_thickness=2
        )

class RenderingEngineProtocol(Protocol):
    """Protocol for rendering engine implementations."""
    
    def get_screen_size(self) -> Tuple[int, int]:
        """Get current screen dimensions."""
        ...
    
    def draw_line(self, start_point: Tuple[int, int], end_point: Tuple[int, int], 
                  thickness: int, color: Tuple[int, int, int]) -> None:
        """Draw line on screen."""
        ...
    
    def draw_circle(self, center: Tuple[int, int], radius: int, 
                   color: Tuple[int, int, int]) -> None:
        """Draw filled circle on screen."""
        ...
    
    def is_available(self) -> bool:
        """Check if rendering engine is available."""
        ...

class GridStyleProtocol(Protocol):
    """Protocol for grid style implementations."""
    
    def render_pattern(self, engine: RenderingEngineProtocol, config: GridConfig) -> None:
        """Render specific grid pattern."""
        ...

def validate_grid_dimensions(width: int, height: int, spacing: int) -> None:
    """Validate grid dimension values."""
    if width <= 0:
        raise InvalidGridConfiguration("Grid width must be positive")
    
    if height <= 0:
        raise InvalidGridConfiguration("Grid height must be positive")
    
    if spacing <= 0:
        raise InvalidGridConfiguration("Grid spacing must be positive")
    
    if spacing > min(width, height):
        raise InvalidGridConfiguration("Grid spacing cannot exceed dimensions")

def validate_color_components(red: int, green: int, blue: int) -> None:
    """Validate RGB color component values."""
    for component, name in [(red, "red"), (green, "green"), (blue, "blue")]:
        if not 0 <= component <= 255:
            raise InvalidGridConfiguration(f"Color {name} must be between 0 and 255")

def validate_line_thickness(thickness: int) -> None:
    """Validate line thickness value."""
    if thickness <= 0:
        raise InvalidGridConfiguration("Line thickness must be positive")
    
    if thickness > 10:
        raise InvalidGridConfiguration("Line thickness cannot exceed 10")

def check_engine_availability(engine: RenderingEngineProtocol) -> None:
    """Check if rendering engine is available for use."""
    if not engine.is_available():
        raise EngineNotAvailable("Rendering engine is not available")

def calculate_grid_points(dimensions: GridDimensions) -> List[int]:
    """Calculate grid line positions for given dimensions."""
    return list(range(0, max(dimensions.width, dimensions.height), dimensions.spacing))

def create_vertical_line_endpoints(x_position: int, height: int) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """Create start and end points for vertical grid line."""
    return (x_position, 0), (x_position, height)

def create_horizontal_line_endpoints(y_position: int, width: int) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """Create start and end points for horizontal grid line."""
    return (0, y_position), (width, y_position)

def draw_single_line_safely(engine: RenderingEngineProtocol, start_point: Tuple[int, int], 
                           end_point: Tuple[int, int], thickness: int, color: Tuple[int, int, int]) -> None:
    """Draw single line with error handling."""
    try:
        engine.draw_line(start_point, end_point, thickness, color)
    except Exception as error:
        logger.debug("Failed to draw line from %s to %s: %s", start_point, end_point, error)

def draw_single_circle_safely(engine: RenderingEngineProtocol, center: Tuple[int, int], 
                             radius: int, color: Tuple[int, int, int]) -> None:
    """Draw single circle with error handling."""
    try:
        engine.draw_circle(center, radius, color)
    except Exception as error:
        logger.debug("Failed to draw circle at %s: %s", center, error)

class LineGridRenderer:
    """Renderer for line-based grid patterns."""
    
    def render_pattern(self, engine: RenderingEngineProtocol, config: GridConfig) -> None:
        """Render line grid pattern."""
        self._render_vertical_lines(engine, config)
        self._render_horizontal_lines(engine, config)
    
    def _render_vertical_lines(self, engine: RenderingEngineProtocol, config: GridConfig) -> None:
        """Render all vertical grid lines."""
        grid_points = calculate_grid_points(config.dimensions)
        
        for x_position in grid_points:
            if x_position >= config.dimensions.width:
                continue
                
            start_point, end_point = create_vertical_line_endpoints(x_position, config.dimensions.height)
            draw_single_line_safely(engine, start_point, end_point, config.line_thickness, config.color.as_tuple)
    
    def _render_horizontal_lines(self, engine: RenderingEngineProtocol, config: GridConfig) -> None:
        """Render all horizontal grid lines."""
        grid_points = calculate_grid_points(config.dimensions)
        
        for y_position in grid_points:
            if y_position >= config.dimensions.height:
                continue
                
            start_point, end_point = create_horizontal_line_endpoints(y_position, config.dimensions.width)
            draw_single_line_safely(engine, start_point, end_point, config.line_thickness, config.color.as_tuple)

class DotGridRenderer:
    """Renderer for dot-based grid patterns."""
    
    def render_pattern(self, engine: RenderingEngineProtocol, config: GridConfig) -> None:
        """Render dot grid pattern."""
        grid_points = calculate_grid_points(config.dimensions)
        radius = max(1, config.line_thickness)
        
        for x_position in grid_points:
            if x_position >= config.dimensions.width:
                continue
                
            for y_position in grid_points:
                if y_position >= config.dimensions.height:
                    continue
                    
                center = (x_position, y_position)
                draw_single_circle_safely(engine, center, radius, config.color.as_tuple)

class CrossGridRenderer:
    """Renderer for cross-based grid patterns."""
    
    def render_pattern(self, engine: RenderingEngineProtocol, config: GridConfig) -> None:
        """Render cross grid pattern."""
        grid_points = calculate_grid_points(config.dimensions)
        cross_size = config.line_thickness * 3
        
        for x_position in grid_points:
            if x_position >= config.dimensions.width:
                continue
                
            for y_position in grid_points:
                if y_position >= config.dimensions.height:
                    continue
                    
                self._draw_cross_at_position(engine, x_position, y_position, cross_size, config)
    
    def _draw_cross_at_position(self, engine: RenderingEngineProtocol, x: int, y: int, 
                               size: int, config: GridConfig) -> None:
        """Draw cross pattern at specific position."""
        horizontal_start = (x - size, y)
        horizontal_end = (x + size, y)
        draw_single_line_safely(engine, horizontal_start, horizontal_end, config.line_thickness, config.color.as_tuple)
        
        vertical_start = (x, y - size)
        vertical_end = (x, y + size)
        draw_single_line_safely(engine, vertical_start, vertical_end, config.line_thickness, config.color.as_tuple)

class SquareGridRenderer:
    """Renderer for square-based grid patterns."""
    
    def render_pattern(self, engine: RenderingEngineProtocol, config: GridConfig) -> None:
        """Render square grid pattern."""
        grid_points = calculate_grid_points(config.dimensions)
        square_size = config.dimensions.spacing // 4
        
        for x_position in grid_points:
            if x_position >= config.dimensions.width:
                continue
                
            for y_position in grid_points:
                if y_position >= config.dimensions.height:
                    continue
                    
                self._draw_square_at_position(engine, x_position, y_position, square_size, config)
    
    def _draw_square_at_position(self, engine: RenderingEngineProtocol, x: int, y: int, 
                                size: int, config: GridConfig) -> None:
        """Draw square pattern at specific position."""
        half_size = size // 2
        
        top_line = ((x - half_size, y - half_size), (x + half_size, y - half_size))
        bottom_line = ((x - half_size, y + half_size), (x + half_size, y + half_size))
        left_line = ((x - half_size, y - half_size), (x - half_size, y + half_size))
        right_line = ((x + half_size, y - half_size), (x + half_size, y + half_size))
        
        for start_point, end_point in [top_line, bottom_line, left_line, right_line]:
            draw_single_line_safely(engine, start_point, end_point, config.line_thickness, config.color.as_tuple)

def create_pattern_renderer(pattern: GridPattern) -> GridStyleProtocol:
    """Create appropriate renderer for grid pattern."""
    pattern_renderers = {
        GridPattern.LINES: LineGridRenderer(),
        GridPattern.DOTS: DotGridRenderer(),
        GridPattern.CROSSES: CrossGridRenderer(),
        GridPattern.SQUARES: SquareGridRenderer()
    }
    
    renderer = pattern_renderers.get(pattern)
    if not renderer:
        raise InvalidGridConfiguration(f"Unsupported grid pattern: {pattern}")
    
    return renderer

class GridRenderer:
    """Core grid rendering coordinator."""
    
    def __init__(self, engine: RenderingEngineProtocol):
        self._engine = engine
    
    def render_grid(self, config: GridConfig) -> None:
        """Render grid with specified configuration."""
        check_engine_availability(self._engine)
        self._validate_configuration(config)
        
        updated_config = self._update_config_with_screen_size(config)
        pattern_renderer = create_pattern_renderer(updated_config.pattern)
        
        try:
            pattern_renderer.render_pattern(self._engine, updated_config)
            logger.debug("Grid rendered successfully with pattern: %s", updated_config.pattern.value)
        except Exception as error:
            logger.error("Grid rendering failed: %s", error)
            raise RenderingFailure(f"Failed to render grid: {error}") from error
    
    def _validate_configuration(self, config: GridConfig) -> None:
        """Validate grid configuration before rendering."""
        validate_line_thickness(config.line_thickness)
    
    def _update_config_with_screen_size(self, config: GridConfig) -> GridConfig:
        """Update configuration with actual screen dimensions."""
        try:
            screen_width, screen_height = self._engine.get_screen_size()
            
            updated_dimensions = GridDimensions(
                width=screen_width,
                height=screen_height,
                spacing=config.dimensions.spacing
            )
            
            return GridConfig(
                dimensions=updated_dimensions,
                color=config.color,
                pattern=config.pattern,
                line_thickness=config.line_thickness
            )
        except Exception as error:
            logger.warning("Could not get screen size, using config dimensions: %s", error)
            return config

class LegacyEngineAdapter:
    """Adapter for legacy rendering engines."""
    
    def __init__(self, legacy_engine):
        self._legacy_engine = legacy_engine
    
    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen size from legacy engine."""
        if hasattr(self._legacy_engine, 'get_size'):
            return self._legacy_engine.get_size()
        
        if hasattr(self._legacy_engine, 'screen'):
            return self._legacy_engine.screen.get_size()
        
        return (800, 600)
    
    def draw_line(self, start_point: Tuple[int, int], end_point: Tuple[int, int], 
                  thickness: int, color: Tuple[int, int, int]) -> None:
        """Draw line using legacy engine."""
        if hasattr(self._legacy_engine, 'draw_line'):
            self._legacy_engine.draw_line(start_point, end_point, thickness, color)
    
    def draw_circle(self, center: Tuple[int, int], radius: int, 
                   color: Tuple[int, int, int]) -> None:
        """Draw circle using legacy engine."""
        if hasattr(self._legacy_engine, 'draw_circle'):
            self._legacy_engine.draw_circle(center, radius, color)
    
    def is_available(self) -> bool:
        """Check if legacy engine is available."""
        return self._legacy_engine is not None

class GridWidget:
    """High-level grid widget for easy integration."""
    
    def __init__(self, renderer: GridRenderer, config: GridConfig):
        self._renderer = renderer
        self._config = config
    
    def render_grid(self) -> None:
        """Render grid using configured renderer."""
        try:
            self._renderer.render_grid(self._config)
            logger.info("Grid widget rendered successfully")
        except GridRenderingError:
            logger.warning("Grid widget rendering failed, continuing without grid")
        except Exception as error:
            logger.error("Unexpected error in grid widget: %s", error)
    
    def update_config(self, new_config: GridConfig) -> None:
        """Update grid configuration."""
        self._config = new_config
        logger.debug("Grid widget configuration updated")

class MockRenderingEngine:
    """Mock rendering engine for testing and development."""
    
    def __init__(self, width: int = 800, height: int = 600):
        self._width = width
        self._height = height
        self._available = True
        self.draw_calls = []
    
    def get_screen_size(self) -> Tuple[int, int]:
        """Get mock screen dimensions."""
        return (self._width, self._height)
    
    def draw_line(self, start_point: Tuple[int, int], end_point: Tuple[int, int], 
                  thickness: int, color: Tuple[int, int, int]) -> None:
        """Record line drawing call for testing."""
        self.draw_calls.append({
            'type': 'line',
            'start': start_point,
            'end': end_point,
            'thickness': thickness,
            'color': color
        })
    
    def draw_circle(self, center: Tuple[int, int], radius: int, 
                   color: Tuple[int, int, int]) -> None:
        """Record circle drawing call for testing."""
        self.draw_calls.append({
            'type': 'circle',
            'center': center,
            'radius': radius,
            'color': color
        })
    
    def is_available(self) -> bool:
        """Check if mock engine is available."""
        return self._available
    
    def set_availability(self, available: bool) -> None:
        """Set mock engine availability for testing."""
        self._available = available
    
    def clear_draw_calls(self) -> None:
        """Clear recorded draw calls."""
        self.draw_calls.clear()

class ProductionRenderingEngine:
    """Production rendering engine with fallback support."""
    
    def __init__(self):
        self._pygame_engine = self._initialize_pygame_engine()
        self._fallback_engine = MockRenderingEngine()
    
    def _initialize_pygame_engine(self):
        """Initialize pygame engine if available."""
        try:
            import pygame
            if pygame.get_init():
                return pygame
        except ImportError:
            logger.debug("Pygame not available, using fallback engine")
        return None
    
    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen dimensions from available engine."""
        if self._pygame_engine:
            return self._get_pygame_screen_size()
        return self._fallback_engine.get_screen_size()
    
    def _get_pygame_screen_size(self) -> Tuple[int, int]:
        """Get screen size from pygame."""
        try:
            display_info = self._pygame_engine.display.Info()
            return (display_info.current_w, display_info.current_h)
        except Exception:
            return (800, 600)
    
    def draw_line(self, start_point: Tuple[int, int], end_point: Tuple[int, int], 
                  thickness: int, color: Tuple[int, int, int]) -> None:
        """Draw line using available engine."""
        if self._pygame_engine:
            self._draw_pygame_line(start_point, end_point, thickness, color)
        else:
            self._fallback_engine.draw_line(start_point, end_point, thickness, color)
    
    def _draw_pygame_line(self, start_point: Tuple[int, int], end_point: Tuple[int, int], 
                         thickness: int, color: Tuple[int, int, int]) -> None:
        """Draw line using pygame."""
        try:
            screen = self._pygame_engine.display.get_surface()
            if screen:
                self._pygame_engine.draw.line(screen, color, start_point, end_point, thickness)
        except Exception as error:
            logger.debug("Pygame line drawing failed: %s", error)
    
    def draw_circle(self, center: Tuple[int, int], radius: int, 
                   color: Tuple[int, int, int]) -> None:
        """Draw circle using available engine."""
        if self._pygame_engine:
            self._draw_pygame_circle(center, radius, color)
        else:
            self._fallback_engine.draw_circle(center, radius, color)
    
    def _draw_pygame_circle(self, center: Tuple[int, int], radius: int, 
                           color: Tuple[int, int, int]) -> None:
        """Draw circle using pygame."""
        try:
            screen = self._pygame_engine.display.get_surface()
            if screen:
                self._pygame_engine.draw.circle(screen, color, center, radius)
        except Exception as error:
            logger.debug("Pygame circle drawing failed: %s", error)
    
    def is_available(self) -> bool:
        """Check if any rendering engine is available."""
        return self._pygame_engine is not None or self._fallback_engine.is_available()

class GridRendererFactory:
    """Factory for creating grid renderers with different engines."""
    
    @staticmethod
    def create_with_legacy_engine(legacy_engine) -> GridRenderer:
        """Create grid renderer with legacy engine."""
        adapted_engine = LegacyEngineAdapter(legacy_engine)
        return GridRenderer(adapted_engine)
    
    @staticmethod
    def create_production_renderer() -> GridRenderer:
        """Create production grid renderer with automatic engine detection."""
        engine = ProductionRenderingEngine()
        return GridRenderer(engine)
    
    @staticmethod
    def create_test_renderer(width: int = 800, height: int = 600) -> GridRenderer:
        """Create test grid renderer with mock engine."""
        engine = MockRenderingEngine(width, height)
        return GridRenderer(engine)
    
    @staticmethod
    def create_mock_renderer_for_testing() -> Tuple[GridRenderer, MockRenderingEngine]:
        """Create grid renderer with mock engine for testing."""
        mock_engine = MockRenderingEngine()
        renderer = GridRenderer(mock_engine)
        return renderer, mock_engine

class GridWidgetFactory:
    """Factory for creating complete grid widgets."""
    
    @staticmethod
    def create_simple_grid_widget(legacy_engine) -> GridWidget:
        """Create simple grid widget compatible with legacy systems."""
        renderer = GridRendererFactory.create_with_legacy_engine(legacy_engine)
        config = GridConfig.from_defaults()
        return GridWidget(renderer, config)
    
    @staticmethod
    def create_custom_grid_widget(engine, pattern: GridPattern, spacing: int) -> GridWidget:
        """Create custom grid widget with specific pattern and spacing."""
        renderer = GridRendererFactory.create_with_legacy_engine(engine)
        
        screen_width, screen_height = renderer._engine.get_screen_size()
        config = GridConfig(
            dimensions=GridDimensions(width=screen_width, height=screen_height, spacing=spacing),
            color=GridColor(red=30, green=30, blue=30),
            pattern=pattern
        )
        
        return GridWidget(renderer, config)

class GridTestHelpers:
    """Helper functions for testing grid operations."""
    
    @staticmethod
    def create_test_config(pattern: GridPattern = GridPattern.LINES) -> GridConfig:
        """Create grid configuration for testing."""
        return GridConfig(
            dimensions=GridDimensions(width=400, height=300, spacing=20),
            color=GridColor(red=50, green=50, blue=50),
            pattern=pattern,
            line_thickness=1
        )
    
    @staticmethod
    def create_grid_widget_for_testing() -> Tuple[GridWidget, MockRenderingEngine]:
        """Create grid widget with mock engine for testing."""
        renderer, mock_engine = GridRendererFactory.create_mock_renderer_for_testing()
        config = GridTestHelpers.create_test_config()
        widget = GridWidget(renderer, config)
        return widget, mock_engine
    
    @staticmethod
    def count_draw_calls_by_type(mock_engine: MockRenderingEngine, call_type: str) -> int:
        """Count specific type of draw calls in mock engine."""
        return len([call for call in mock_engine.draw_calls if call['type'] == call_type])

def demonstrate_basic_usage():
    """Demonstrate basic grid widget usage."""
    print("Creating production grid widget...")
    
    try:
        renderer = GridRendererFactory.create_production_renderer()
        config = GridConfig.from_defaults()
        widget = GridWidget(renderer, config)
        
        print("Rendering grid...")
        widget.render_grid()
        print("Grid rendered successfully!")
        
    except Exception as error:
        print(f"Grid rendering failed: {error}")

def demonstrate_custom_patterns():
    """Demonstrate different grid patterns."""
    patterns_to_test = [
        GridPattern.LINES,
        GridPattern.DOTS, 
        GridPattern.CROSSES,
        GridPattern.SQUARES
    ]
    
    for pattern in patterns_to_test:
        print(f"Testing {pattern.value} pattern...")
        
        try:
            renderer = GridRendererFactory.create_test_renderer()
            config = GridConfig(
                dimensions=GridDimensions(width=200, height=200, spacing=30),
                color=GridColor(red=100, green=100, blue=100),
                pattern=pattern,
                line_thickness=2
            )
            
            widget = GridWidget(renderer, config)
            widget.render_grid()
            print(f"  {pattern.value} pattern rendered successfully!")
            
        except Exception as error:
            print(f"  {pattern.value} pattern failed: {error}")

def demonstrate_legacy_integration():
    """Demonstrate integration with legacy rendering systems."""
    print("Testing legacy engine integration...")
    
    class LegacyEngine:
        """Simulated legacy engine."""
        
        def get_size(self):
            return (640, 480)
        
        def draw_line(self, start, end, thickness, color):
            print(f"Legacy: Drawing line from {start} to {end}")
    
    try:
        legacy_engine = LegacyEngine()
        widget = GridWidgetFactory.create_simple_grid_widget(legacy_engine)
        widget.render_grid()
        print("Legacy integration successful!")
        
    except Exception as error:
        print(f"Legacy integration failed: {error}")

if __name__ == "__main__":
    print("Grid Widget System - Production Ready Implementation")
    print("=" * 55)
    
    demonstrate_basic_usage()
    print()
    
    demonstrate_custom_patterns()
    print()
    
    demonstrate_legacy_integration()
    print()
    
    print("All demonstrations completed!")

# EXPANSION POINTS clearly marked for team development:

# 1. ADD NEW GRID PATTERNS: Implement GridStyleProtocol
#    Example: Create DiagonalGridRenderer, HexagonalGridRenderer
# 2. ADD NEW RENDERING ENGINES: Implement RenderingEngineProtocol  
#    Example: Create OpenGLRenderer, CanvasRenderer, SVGRenderer
# 3. ADD ANIMATION: Create AnimatedGridRenderer class
#    Example: Pulsing grids, moving patterns, fade effects
# 4. ADD GRID THEMES: Create GridTheme dataclass with color schemes
#    Example: DarkTheme, LightTheme, HighContrastTheme
# 5. ADD PERFORMANCE OPTIMIZATION: Implement GridCache for static grids
#    Example: Cache rendered grids, dirty region updates
# 6. ADD INTERACTIVE GRIDS: Create InteractiveGridWidget with mouse events
#    Example: Click to highlight grid cells, drag to pan
# 7. ADD GRID PERSISTENCE: Create GridConfigRepository for saving layouts
#    Example: Save/load grid configurations to JSON files
# 8. ADD GRID ANALYTICS: Create GridRenderingMetrics for performance tracking
#    Example: Track render times, frame rates, error counts