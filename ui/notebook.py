"""
Notebook system for canvas-based drawing applications.

This module provides a complete notebook abstraction with grid management,
rendering capabilities, and extensible architecture for drawing applications.

Quick start:
    config = NotebookConfig.create_default()
    factory = NotebookFactory(config)
    notebook = factory.create_notebook(width=800, height=600)
    notebook.render_to_canvas(renderer)

Extension points:
    - Add new grid types: Implement GridProvider interface
    - Add new rendering features: Extend NotebookRenderer methods
    - Add new notebook features: Add methods to NotebookService
    - Add new validation rules: Create new validate_* functions
"""

import logging
from typing import Protocol, Iterator, Tuple, Optional, List, Dict, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

logger = logging.getLogger(__name__)


class NotebookError(Exception):
    """Base exception for notebook operations."""
    pass


class InvalidDimensionsError(NotebookError):
    """Notebook dimensions are invalid."""
    pass


class RenderingError(NotebookError):
    """Error occurred during rendering operations."""
    pass


class GridGenerationError(NotebookError):
    """Error occurred during grid generation."""
    pass


@dataclass(frozen=True)
class Point:
    """Immutable point representation."""
    x: float
    y: float
    
    def __post_init__(self) -> None:
        """Validate point coordinates."""
        if not isinstance(self.x, (int, float)):
            raise ValueError("Point x coordinate must be numeric")
        if not isinstance(self.y, (int, float)):
            raise ValueError("Point y coordinate must be numeric")


@dataclass(frozen=True)
class Color:
    """Immutable color representation."""
    red: int
    green: int
    blue: int
    alpha: int = 255
    
    def __post_init__(self) -> None:
        """Validate color values."""
        for component in [self.red, self.green, self.blue, self.alpha]:
            if not isinstance(component, int) or not 0 <= component <= 255:
                raise ValueError("Color components must be integers between 0 and 255")
    
    def to_hex(self) -> str:
        """Convert color to hex representation."""
        return f"#{self.red:02x}{self.green:02x}{self.blue:02x}"


@dataclass(frozen=True)
class GridLine:
    """Immutable grid line representation."""
    start_point: Point
    end_point: Point
    color: Color
    
    def __post_init__(self) -> None:
        """Validate grid line components."""
        if not isinstance(self.start_point, Point):
            raise ValueError("Start point must be a Point instance")
        if not isinstance(self.end_point, Point):
            raise ValueError("End point must be a Point instance")
        if not isinstance(self.color, Color):
            raise ValueError("Color must be a Color instance")


@dataclass
class NotebookConfig:
    """Notebook system configuration."""
    min_width: int = 1
    max_width: int = 10000
    min_height: int = 1
    max_height: int = 10000
    default_grid_spacing: int = 20
    default_grid_color: Color = Color(100, 100, 100, 128)
    
    @classmethod
    def create_default(cls) -> 'NotebookConfig':
        """Create default configuration."""
        return cls()
    
    @classmethod
    def create_from_environment(cls) -> 'NotebookConfig':
        """Create configuration from environment variables."""
        import os
        
        return cls(
            min_width=int(os.getenv('NOTEBOOK_MIN_WIDTH', '1')),
            max_width=int(os.getenv('NOTEBOOK_MAX_WIDTH', '10000')),
            min_height=int(os.getenv('NOTEBOOK_MIN_HEIGHT', '1')),
            max_height=int(os.getenv('NOTEBOOK_MAX_HEIGHT', '10000')),
            default_grid_spacing=int(os.getenv('NOTEBOOK_GRID_SPACING', '20'))
        )


class RendererProtocol(Protocol):
    """Protocol defining renderer interface for notebook rendering."""
    
    def draw_line(self, start_point: Point, end_point: Point, width: int, color: Color) -> None:
        """
        Draw line on the rendering surface.
        
        Args:
            start_point: Line starting position
            end_point: Line ending position  
            width: Line width in pixels
            color: Line color
        """
        ...


class GridProvider(ABC):
    """Abstract interface for grid generation."""
    
    @abstractmethod
    def generate_grid_lines(self, width: int, height: int) -> Iterator[GridLine]:
        """
        Generate grid lines for given dimensions.
        
        Args:
            width: Canvas width
            height: Canvas height
            
        Yields:
            GridLine instances representing the grid
        """
        pass


def validate_notebook_width(width: int, config: NotebookConfig) -> None:
    """Validate notebook width against configuration."""
    if not isinstance(width, int):
        raise InvalidDimensionsError("Width must be an integer")
    
    if width < config.min_width:
        raise InvalidDimensionsError(f"Width {width} below minimum {config.min_width}")
    
    if width > config.max_width:
        raise InvalidDimensionsError(f"Width {width} exceeds maximum {config.max_width}")


def validate_notebook_height(height: int, config: NotebookConfig) -> None:
    """Validate notebook height against configuration."""
    if not isinstance(height, int):
        raise InvalidDimensionsError("Height must be an integer")
    
    if height < config.min_height:
        raise InvalidDimensionsError(f"Height {height} below minimum {config.min_height}")
    
    if height > config.max_height:
        raise InvalidDimensionsError(f"Height {height} exceeds maximum {config.max_height}")


def validate_notebook_dimensions(width: int, height: int, config: NotebookConfig) -> None:
    """Validate notebook dimensions completely."""
    validate_notebook_width(width, config)
    validate_notebook_height(height, config)


def validate_renderer_interface(renderer: Any) -> None:
    """Validate renderer implements required interface."""
    if not hasattr(renderer, 'draw_line'):
        raise RenderingError("Renderer must implement draw_line method")
    
    if not callable(getattr(renderer, 'draw_line')):
        raise RenderingError("Renderer draw_line must be callable")


class NeonGridProvider(GridProvider):
    """Grid provider that generates neon-style grid lines."""
    
    def __init__(self, spacing: int, color: Color):
        self.spacing = spacing
        self.color = color
        
        if spacing <= 0:
            raise ValueError("Grid spacing must be positive")
    
    def generate_grid_lines(self, width: int, height: int) -> Iterator[GridLine]:
        """Generate neon grid lines for canvas."""
        try:
            yield from self._generate_vertical_lines(width, height)
            yield from self._generate_horizontal_lines(width, height)
            logger.debug(f"Generated grid lines for {width}x{height} canvas")
        except Exception as error:
            logger.error(f"Failed to generate grid lines: {error}")
            raise GridGenerationError(f"Grid generation failed: {error}") from error
    
    def _generate_vertical_lines(self, width: int, height: int) -> Iterator[GridLine]:
        """Generate vertical grid lines."""
        x_position = 0
        
        while x_position <= width:
            yield GridLine(
                start_point=Point(x_position, 0),
                end_point=Point(x_position, height),
                color=self.color
            )
            x_position += self.spacing
    
    def _generate_horizontal_lines(self, width: int, height: int) -> Iterator[GridLine]:
        """Generate horizontal grid lines."""
        y_position = 0
        
        while y_position <= height:
            yield GridLine(
                start_point=Point(0, y_position),
                end_point=Point(width, y_position),
                color=self.color
            )
            y_position += self.spacing


class NotebookRenderer:
    """Handles notebook rendering operations."""
    
    def __init__(self, grid_provider: GridProvider):
        self.grid_provider = grid_provider
    
    def render_grid_to_canvas(self, renderer: RendererProtocol, width: int, height: int) -> None:
        """Render grid lines to canvas using provided renderer."""
        validate_renderer_interface(renderer)
        
        try:
            grid_lines = self.grid_provider.generate_grid_lines(width, height)
            self._draw_grid_lines_on_canvas(renderer, grid_lines)
            logger.info(f"Grid rendered successfully for {width}x{height} canvas")
            
        except GridGenerationError:
            raise
        except Exception as error:
            logger.error(f"Grid rendering failed: {error}")
            raise RenderingError(f"Failed to render grid: {error}") from error
    
    def _draw_grid_lines_on_canvas(self, renderer: RendererProtocol, grid_lines: Iterator[GridLine]) -> None:
        """Draw individual grid lines on canvas."""
        lines_drawn = 0
        
        for grid_line in grid_lines:
            try:
                renderer.draw_line(
                    start_point=grid_line.start_point,
                    end_point=grid_line.end_point,
                    width=1,
                    color=grid_line.color
                )
                lines_drawn += 1
                
            except Exception as error:
                logger.warning(f"Failed to draw grid line: {error}")
                continue
        
        logger.debug(f"Drew {lines_drawn} grid lines")


@dataclass(frozen=True)
class NotebookDimensions:
    """Immutable notebook dimensions."""
    width: int
    height: int
    
    def __post_init__(self) -> None:
        """Validate dimensions on creation."""
        if self.width <= 0:
            raise ValueError("Width must be positive")
        if self.height <= 0:
            raise ValueError("Height must be positive")


class NotebookService:
    """Core notebook business logic coordinator."""
    
    def __init__(self, config: NotebookConfig, renderer: NotebookRenderer):
        self.config = config
        self.renderer = renderer
    
    def create_notebook_with_dimensions(self, width: int, height: int) -> 'Notebook':
        """Create notebook with validated dimensions."""
        validate_notebook_dimensions(width, height, self.config)
        
        dimensions = NotebookDimensions(width, height)
        notebook = Notebook(dimensions, self.renderer)
        
        logger.info(f"Created notebook with dimensions {width}x{height}")
        return notebook
    
    def render_notebook_to_canvas(self, notebook: 'Notebook', renderer: RendererProtocol) -> None:
        """Render complete notebook to canvas."""
        try:
            notebook.render_to_canvas(renderer)
            logger.info("Notebook rendered successfully")
            
        except (RenderingError, GridGenerationError):
            raise
        except Exception as error:
            logger.error(f"Notebook rendering failed unexpectedly: {error}")
            raise RenderingError(f"Notebook rendering failed: {error}") from error


class Notebook:
    """
    Notebook abstraction managing grid and drawing layers.
    
    This class represents a canvas-based notebook with grid background
    and extensible support for additional drawing features.
    
    Args:
        dimensions: The notebook canvas dimensions
        renderer: The notebook renderer for grid operations
    """
    
    def __init__(self, dimensions: NotebookDimensions, renderer: NotebookRenderer):
        self.dimensions = dimensions
        self.renderer = renderer
        logger.debug(f"Notebook initialized with {dimensions.width}x{dimensions.height}")
    
    def render_to_canvas(self, canvas_renderer: RendererProtocol) -> None:
        """
        Render complete notebook to canvas.
        
        Args:
            canvas_renderer: Renderer implementing RendererProtocol for drawing operations
        """
        self._render_background_grid(canvas_renderer)
        self._render_drawing_layers(canvas_renderer)
    
    def _render_background_grid(self, canvas_renderer: RendererProtocol) -> None:
        """Render background grid on canvas."""
        try:
            self.renderer.render_grid_to_canvas(
                canvas_renderer,
                self.dimensions.width,
                self.dimensions.height
            )
        except Exception as error:
            logger.error(f"Background grid rendering failed: {error}")
            raise RenderingError(f"Failed to render background grid: {error}") from error
    
    def _render_drawing_layers(self, canvas_renderer: RendererProtocol) -> None:
        """Render additional drawing layers on canvas."""
        # EXPANSION POINT: Add support for strokes, selections, annotations
        # - Add stroke rendering: self._render_strokes(canvas_renderer)
        # - Add selection rendering: self._render_selections(canvas_renderer)  
        # - Add annotation rendering: self._render_annotations(canvas_renderer)
        logger.debug("Drawing layers rendering complete")
    
    def get_canvas_dimensions(self) -> NotebookDimensions:
        """Get notebook canvas dimensions."""
        return self.dimensions


class NotebookFactory:
    """Factory for creating notebook instances with dependencies."""
    
    def __init__(self, config: NotebookConfig):
        self.config = config
        self.grid_provider = self._create_grid_provider()
        self.renderer = self._create_notebook_renderer()
        self.service = self._create_notebook_service()
    
    def create_notebook(self, width: int, height: int) -> Notebook:
        """Create notebook instance with validation."""
        return self.service.create_notebook_with_dimensions(width, height)
    
    def create_notebook_with_custom_grid(self, width: int, height: int, grid_provider: GridProvider) -> Notebook:
        """Create notebook with custom grid provider."""
        validate_notebook_dimensions(width, height, self.config)
        
        custom_renderer = NotebookRenderer(grid_provider)
        dimensions = NotebookDimensions(width, height)
        
        return Notebook(dimensions, custom_renderer)
    
    def _create_grid_provider(self) -> GridProvider:
        """Create default grid provider."""
        return NeonGridProvider(
            spacing=self.config.default_grid_spacing,
            color=self.config.default_grid_color
        )
    
    def _create_notebook_renderer(self) -> NotebookRenderer:
        """Create notebook renderer with default grid provider."""
        return NotebookRenderer(self.grid_provider)
    
    def _create_notebook_service(self) -> NotebookService:
        """Create notebook service with dependencies."""
        return NotebookService(self.config, self.renderer)


class NotebookTestHelpers:
    """Helper functions for testing notebook operations."""
    
    @staticmethod
    def create_test_notebook(width: int = 800, height: int = 600) -> Notebook:
        """Create notebook instance for testing."""
        config = NotebookConfig.create_default()
        factory = NotebookFactory(config)
        return factory.create_notebook(width, height)
    
    @staticmethod
    def create_mock_renderer() -> 'MockRenderer':
        """Create mock renderer for testing."""
        return MockRenderer()
    
    @staticmethod
    def create_test_dimensions(width: int = 800, height: int = 600) -> NotebookDimensions:
        """Create test dimensions."""
        return NotebookDimensions(width, height)


class MockRenderer:
    """Mock renderer for testing purposes."""
    
    def __init__(self):
        self.drawn_lines: List[Dict[str, Any]] = []
    
    def draw_line(self, start_point: Point, end_point: Point, width: int, color: Color) -> None:
        """Record line drawing for test verification."""
        self.drawn_lines.append({
            'start_point': start_point,
            'end_point': end_point,
            'width': width,
            'color': color
        })
    
    def get_drawn_lines_count(self) -> int:
        """Get number of lines drawn."""
        return len(self.drawn_lines)
    
    def clear_drawn_lines(self) -> None:
        """Clear recorded lines."""
        self.drawn_lines.clear()


# EXPANSION POINTS clearly marked for team development:

# 1. ADD NEW GRID TYPES: Implement GridProvider interface
#    - DottedGridProvider: Grid with dots instead of lines
#    - HexagonalGridProvider: Hexagonal grid pattern
#    - CustomSpacingGridProvider: Variable spacing grid

# 2. ADD NEW DRAWING FEATURES: Extend Notebook class
#    - add_stroke(stroke: Stroke) -> None
#    - add_selection(selection: Selection) -> None  
#    - add_annotation(annotation: Annotation) -> None

# 3. ADD NEW RENDERING BACKENDS: Implement RendererProtocol
#    - SVGRenderer: Render to SVG format
#    - CanvasRenderer: HTML5 Canvas rendering
#    - ImageRenderer: Render to image files

# 4. ADD NEW VALIDATION RULES: Create new validate_* functions
#    - validate_stroke_data(stroke_data: Dict) -> None
#    - validate_selection_bounds(selection: Selection) -> None

# 5. ADD NEW CONFIGURATION OPTIONS: Extend NotebookConfig
#    - stroke_settings: StrokeConfig
#    - selection_settings: SelectionConfig
#    - export_settings: ExportConfig


def create_production_notebook(width: int, height: int) -> Notebook:
    """
    Create production-ready notebook instance.
    
    Args:
        width: Notebook width in pixels
        height: Notebook height in pixels
        
    Returns:
        Configured notebook ready for production use
    """
    config = NotebookConfig.create_from_environment()
    factory = NotebookFactory(config)
    return factory.create_notebook(width, height)


def create_test_notebook_system() -> tuple[Notebook, MockRenderer, NotebookFactory]:
    """
    Create complete notebook system for testing.
    
    Returns:
        Tuple of (notebook, mock_renderer, factory) for comprehensive testing
    """
    config = NotebookConfig.create_default()
    factory = NotebookFactory(config)
    notebook = factory.create_notebook(800, 600)
    mock_renderer = NotebookTestHelpers.create_mock_renderer()
    
    return notebook, mock_renderer, factory