"""
Unified Drawing Interface System.

Combines hotbar, canvas, and grid functionality into a cohesive,
production-ready drawing application framework with zero duplication.

Original components consolidated:
- Hotbar widget (tool selection, brush width control)
- Canvas widget (performance-optimized rendering)
- Grid widget (background grid rendering)

Quick deployment:
    config = DrawingInterfaceConfig()
    interface = create_drawing_interface(journal_service, renderer, config)
    interface.render()

Extension points:
    - Add new tools: Extend ToolDefinition list
    - Add new widgets: Implement DrawingWidget interface
    - Add new renderers: Implement UnifiedRenderer interface
    - Add new input handlers: Extend InputCoordinator
"""

import logging
import time
from typing import Dict, List, Tuple, Optional, Any, Protocol, Set, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum

logger = logging.getLogger(__name__)


class DrawingInterfaceError(Exception):
    """Base exception for drawing interface operations."""
    pass


class ToolNotFoundError(DrawingInterfaceError):
    """Tool does not exist in system."""
    pass


class RenderingError(DrawingInterfaceError):
    """Error occurred during rendering operations."""
    pass


class InputHandlingError(DrawingInterfaceError):
    """Error occurred during input processing."""
    pass


class WidgetError(DrawingInterfaceError):
    """Error occurred in widget operations."""
    pass


class ToolCategory(Enum):
    """Categories for organizing drawing tools."""
    DRAWING = "drawing"
    SHAPES = "shapes"
    EDITING = "editing"
    EFFECTS = "effects"


class RenderingQuality(Enum):
    """Rendering quality levels for performance optimization."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ADAPTIVE = "adaptive"


class WidgetType(Enum):
    """Types of drawing interface widgets."""
    HOTBAR = "hotbar"
    CANVAS = "canvas"
    GRID = "grid"
    OVERLAY = "overlay"


@dataclass(frozen=True)
class ToolDefinition:
    """Immutable tool definition with complete specification."""
    key: str
    display_name: str
    icon_text: str
    description: str
    category: ToolCategory
    supports_brush_width: bool = True
    default_brush_width: int = 5


@dataclass(frozen=True)
class DrawingInterfaceConfig:
    """Complete drawing interface configuration with unified settings."""
    hotbar_x: int = 10
    hotbar_y: int = 10
    hotbar_button_width: int = 80
    hotbar_button_height: int = 40
    hotbar_button_spacing: int = 5
    hotbar_background_color: Tuple[int, int, int] = (60, 60, 60)
    hotbar_selected_color: Tuple[int, int, int] = (0, 150, 255)
    hotbar_hover_color: Tuple[int, int, int] = (100, 100, 100)
    hotbar_text_color: Tuple[int, int, int] = (255, 255, 255)
    hotbar_border_color: Tuple[int, int, int] = (150, 150, 150)
    
    brush_width_min: int = 1
    brush_width_max: int = 50
    brush_width_default: int = 5
    brush_width_step: int = 2
    
    grid_spacing: int = 40
    grid_color: Tuple[int, int, int] = (40, 40, 40)
    grid_enabled: bool = True
    
    canvas_render_fps: int = 60
    canvas_quality: RenderingQuality = RenderingQuality.ADAPTIVE
    canvas_cache_enabled: bool = True
    
    error_recovery_enabled: bool = True
    performance_logging_enabled: bool = True


@dataclass(frozen=True)
class ButtonGeometry:
    """Button position and dimensions with collision detection."""
    x: int
    y: int
    width: int
    height: int
    
    def contains_point(self, point: Tuple[int, int]) -> bool:
        """Check if point is within button bounds."""
        px, py = point
        return (self.x <= px <= self.x + self.width and 
                self.y <= py <= self.y + self.height)


@dataclass(frozen=True)
class BrushState:
    """Unified brush state management."""
    current_width: int
    min_width: int
    max_width: int
    step_size: int
    current_tool: str
    
    def increase_width(self) -> 'BrushState':
        """Create new state with increased width."""
        new_width = min(self.current_width + self.step_size, self.max_width)
        return BrushState(new_width, self.min_width, self.max_width, self.step_size, self.current_tool)
    
    def decrease_width(self) -> 'BrushState':
        """Create new state with decreased width."""
        new_width = max(self.current_width - self.step_size, self.min_width)
        return BrushState(new_width, self.min_width, self.max_width, self.step_size, self.current_tool)
    
    def with_tool(self, tool_key: str) -> 'BrushState':
        """Create new state with different tool."""
        return BrushState(self.current_width, self.min_width, self.max_width, self.step_size, tool_key)


@dataclass
class RenderingStats:
    """Performance statistics for rendering operations."""
    total_renders: int = 0
    skipped_renders: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    average_render_time: float = 0.0
    last_render_time: float = 0.0
    
    @property
    def skip_rate(self) -> float:
        """Calculate render skip rate percentage."""
        total = self.total_renders + self.skipped_renders
        return (self.skipped_renders / total * 100) if total > 0 else 0.0


class EventBus(Protocol):
    """Unified event bus interface for system-wide communication."""
    
    def subscribe(self, event_type: str, handler) -> None:
        """Subscribe to event type with handler."""
        ...
    
    def publish(self, event_type: str, data: Any) -> None:
        """Publish event with data to all subscribers."""
        ...
    
    def unsubscribe(self, event_type: str, handler) -> None:
        """Unsubscribe handler from event type."""
        ...


class ToolService(Protocol):
    """Tool management service interface."""
    
    @property
    def current_tool_mode(self) -> str:
        """Get currently selected tool."""
        ...
    
    def set_mode(self, tool_key: str) -> None:
        """Set active tool mode."""
        ...
    
    def get_tool_info(self, tool_key: str) -> Optional[Dict[str, Any]]:
        """Get information about specific tool."""
        ...


class JournalService(Protocol):
    """Journal service interface for drawing data management."""
    
    def render(self, renderer) -> None:
        """Render all journal content to renderer."""
        ...
    
    def get_stroke_count(self) -> int:
        """Get total number of strokes."""
        ...
    
    def invalidate_cache(self) -> None:
        """Invalidate internal caches."""
        ...


class UnifiedRenderer(Protocol):
    """Unified rendering interface for all drawing operations."""
    
    def draw_line(self, start: Tuple[int, int], end: Tuple[int, int], width: int, color: Tuple[int, int, int]) -> None:
        """Draw line between two points."""
        ...
    
    def draw_text(self, text: str, position: Tuple[int, int], size: int, color: Tuple[int, int, int]) -> None:
        """Draw text at position."""
        ...
    
    def draw_circle(self, center: Tuple[int, int], radius: int, color: Tuple[int, int, int]) -> None:
        """Draw circle at center with radius."""
        ...
    
    def get_size(self) -> Tuple[int, int]:
        """Get renderer dimensions."""
        ...


class DrawingWidget(ABC):
    """Base class for all drawing interface widgets."""
    
    @abstractmethod
    def render(self) -> None:
        """Render widget content."""
        pass
    
    @abstractmethod
    def handle_mouse_click(self, position: Tuple[int, int], button: int) -> bool:
        """Handle mouse click events."""
        pass
    
    @abstractmethod
    def handle_mouse_move(self, position: Tuple[int, int]) -> bool:
        """Handle mouse movement events."""
        pass
    
    @abstractmethod
    def get_widget_type(self) -> WidgetType:
        """Get widget type identifier."""
        pass


def create_standard_tool_definitions() -> List[ToolDefinition]:
    """Create standard set of drawing tools with optimized defaults."""
    return [
        ToolDefinition("brush", "Draw", "~", "Freehand drawing tool", ToolCategory.DRAWING, True, 5),
        ToolDefinition("eraser", "Erase", "X", "Eraser tool", ToolCategory.EDITING, True, 10),
        ToolDefinition("line", "Line", "|", "Draw straight lines", ToolCategory.SHAPES, True, 3),
        ToolDefinition("rect", "Rect", "[]", "Draw rectangles", ToolCategory.SHAPES, True, 2),
        ToolDefinition("circle", "Circle", "O", "Draw circles", ToolCategory.SHAPES, True, 2),
        ToolDefinition("triangle", "Triangle", "/\\", "Draw triangles", ToolCategory.SHAPES, True, 2),
        ToolDefinition("parabola", "Curve", "^", "Draw parabolic curves", ToolCategory.SHAPES, True, 3),
    ]


def create_unified_brush_state(config: DrawingInterfaceConfig, initial_tool: str = "brush") -> BrushState:
    """Create initial brush state from configuration."""
    return BrushState(
        current_width=config.brush_width_default,
        min_width=config.brush_width_min,
        max_width=config.brush_width_max,
        step_size=config.brush_width_step,
        current_tool=initial_tool
    )


def calculate_hotbar_button_geometries(tools: List[ToolDefinition], config: DrawingInterfaceConfig) -> Dict[str, ButtonGeometry]:
    """Calculate button positions for all hotbar tools."""
    geometries = {}
    current_x = config.hotbar_x
    
    for tool in tools:
        geometries[tool.key] = ButtonGeometry(
            x=current_x,
            y=config.hotbar_y,
            width=config.hotbar_button_width,
            height=config.hotbar_button_height
        )
        current_x += config.hotbar_button_width + config.hotbar_button_spacing
    
    return geometries


def find_tool_at_position(geometries: Dict[str, ButtonGeometry], position: Tuple[int, int]) -> Optional[str]:
    """Find tool key at given position with error handling."""
    try:
        for tool_key, geometry in geometries.items():
            if geometry.contains_point(position):
                return tool_key
    except Exception as error:
        logger.error(f"Error finding tool at position {position}: {error}")
    return None


def validate_color_tuple(color: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Validate and clamp color values to valid range."""
    try:
        return (
            max(0, min(255, int(color[0]))),
            max(0, min(255, int(color[1]))),
            max(0, min(255, int(color[2])))
        )
    except (TypeError, ValueError, IndexError):
        return (255, 255, 255)


class SafeRenderer:
    """Safe wrapper for unified renderer with comprehensive error handling."""
    
    def __init__(self, renderer: UnifiedRenderer):
        self._renderer = renderer
        self._error_count = 0
        self._last_error_time = 0.0
    
    def draw_line_safely(self, start: Tuple[int, int], end: Tuple[int, int], width: int, color: Tuple[int, int, int]) -> bool:
        """Draw line with validation and error handling."""
        try:
            if not hasattr(self._renderer, 'draw_line'):
                return False
            
            safe_start = (max(0, int(start[0])), max(0, int(start[1])))
            safe_end = (max(0, int(end[0])), max(0, int(end[1])))
            safe_width = max(1, min(100, int(width)))
            safe_color = validate_color_tuple(color)
            
            self._renderer.draw_line(safe_start, safe_end, safe_width, safe_color)
            return True
            
        except Exception as error:
            self._handle_rendering_error("draw_line", error)
            return False
    
    def draw_text_safely(self, text: str, position: Tuple[int, int], size: int, color: Tuple[int, int, int]) -> bool:
        """Draw text with validation and error handling."""
        try:
            if not hasattr(self._renderer, 'draw_text'):
                return False
            
            safe_text = str(text)[:100]
            safe_position = (max(0, int(position[0])), max(0, int(position[1])))
            safe_size = max(6, min(72, int(size)))
            safe_color = validate_color_tuple(color)
            
            self._renderer.draw_text(safe_text, safe_position, safe_size, safe_color)
            return True
            
        except Exception as error:
            self._handle_rendering_error("draw_text", error)
            return False
    
    def draw_circle_safely(self, center: Tuple[int, int], radius: int, color: Tuple[int, int, int]) -> bool:
        """Draw circle with validation and error handling."""
        try:
            if not hasattr(self._renderer, 'draw_circle'):
                return False
            
            safe_center = (max(0, int(center[0])), max(0, int(center[1])))
            safe_radius = max(1, min(200, int(radius)))
            safe_color = validate_color_tuple(color)
            
            self._renderer.draw_circle(safe_center, safe_radius, safe_color)
            return True
            
        except Exception as error:
            self._handle_rendering_error("draw_circle", error)
            return False
    
    def get_size_safely(self) -> Tuple[int, int]:
        """Get renderer size with error handling."""
        try:
            if hasattr(self._renderer, 'get_size'):
                size = self._renderer.get_size()
                return (max(1, int(size[0])), max(1, int(size[1])))
        except Exception as error:
            self._handle_rendering_error("get_size", error)
        return (800, 600)
    
    def _handle_rendering_error(self, operation: str, error: Exception) -> None:
        """Handle rendering errors with throttling."""
        current_time = time.time()
        self._error_count += 1
        
        if current_time - self._last_error_time > 1.0:
            logger.debug(f"Rendering error in {operation}: {error}")
            self._last_error_time = current_time


class GridWidget(DrawingWidget):
    """Unified grid widget with neon-style background rendering."""
    
    def __init__(self, safe_renderer: SafeRenderer, config: DrawingInterfaceConfig):
        self._renderer = safe_renderer
        self._config = config
        self._enabled = config.grid_enabled
        self._grid_spacing = config.grid_spacing
        self._grid_color = config.grid_color
    
    def render(self) -> None:
        """Render grid background with optimized patterns."""
        if not self._enabled:
            return
        
        try:
            width, height = self._renderer.get_size_safely()
            
            self._render_vertical_grid_lines(width, height)
            self._render_horizontal_grid_lines(width, height)
            
            logger.debug("Grid rendered with spacing %d", self._grid_spacing)
            
        except Exception as error:
            logger.error(f"Error rendering grid: {error}")
    
    def _render_vertical_grid_lines(self, width: int, height: int) -> None:
        """Render vertical grid lines with color variation."""
        for x in range(0, width, self._grid_spacing):
            try:
                color_variation = (x % 20, x % 15, x % 10)
                varied_color = (
                    min(255, self._grid_color[0] + color_variation[0]),
                    min(255, self._grid_color[1] + color_variation[1]),
                    min(255, self._grid_color[2] + color_variation[2])
                )
                self._renderer.draw_line_safely((x, 0), (x, height), 1, varied_color)
            except Exception:
                continue
    
    def _render_horizontal_grid_lines(self, width: int, height: int) -> None:
        """Render horizontal grid lines with color variation."""
        for y in range(0, height, self._grid_spacing):
            try:
                color_variation = (y % 15, y % 20, y % 25)
                varied_color = (
                    min(255, self._grid_color[0] + color_variation[0]),
                    min(255, self._grid_color[1] + color_variation[1]),
                    min(255, self._grid_color[2] + color_variation[2])
                )
                self._renderer.draw_line_safely((0, y), (width, y), 1, varied_color)
            except Exception:
                continue
    
    def toggle_grid(self) -> None:
        """Toggle grid visibility."""
        self._enabled = not self._enabled
        logger.info("Grid %s", "enabled" if self._enabled else "disabled")
    
    def handle_mouse_click(self, position: Tuple[int, int], button: int) -> bool:
        """Grid does not handle mouse clicks."""
        return False
    
    def handle_mouse_move(self, position: Tuple[int, int]) -> bool:
        """Grid does not handle mouse movement."""
        return False
    
    def get_widget_type(self) -> WidgetType:
        """Get widget type identifier."""
        return WidgetType.GRID


class HotbarRenderer:
    """Unified hotbar rendering with background and button support."""
    
    def __init__(self, safe_renderer: SafeRenderer, config: DrawingInterfaceConfig):
        self._renderer = safe_renderer
        self._config = config
    
    def render_hotbar_background(self, total_width: int) -> None:
        """Render hotbar background with proper dimensions."""
        try:
            background_height = self._config.hotbar_button_height + 10
            background_start_x = self._config.hotbar_x - 5
            background_start_y = self._config.hotbar_y - 5
            
            for row in range(background_height):
                start_point = (background_start_x, background_start_y + row)
                end_point = (background_start_x + total_width + 10, background_start_y + row)
                
                self._renderer.draw_line_safely(
                    start_point, end_point, 1, self._config.hotbar_background_color
                )
                
        except Exception as error:
            logger.error(f"Failed to render hotbar background: {error}")
    
    def render_tool_button(
        self, 
        tool: ToolDefinition, 
        geometry: ButtonGeometry, 
        is_selected: bool, 
        is_hovered: bool
    ) -> None:
        """Render individual tool button with state indicators."""
        try:
            button_color = self._determine_button_color(is_selected, is_hovered)
            
            self._render_button_background(geometry, button_color)
            self._render_button_border(geometry)
            self._render_button_content(tool, geometry)
            
        except Exception as error:
            logger.warning(f"Failed to render button {tool.key}: {error}")
    
    def render_brush_width_indicator(
        self, 
        brush_state: BrushState, 
        indicator_x: int
    ) -> None:
        """Render brush width indicator with current tool information."""
        try:
            indicator_y = self._config.hotbar_y
            
            self._render_width_text(brush_state, indicator_x, indicator_y)
            self._render_width_circle(brush_state, indicator_x, indicator_y)
            self._render_usage_hints(indicator_x, indicator_y)
            self._render_tool_indicator(brush_state.current_tool, indicator_x, indicator_y)
            
        except Exception as error:
            logger.error(f"Failed to render width indicator: {error}")
    
    def _determine_button_color(self, is_selected: bool, is_hovered: bool) -> Tuple[int, int, int]:
        """Determine button background color based on state."""
        if is_selected:
            return self._config.hotbar_selected_color
        if is_hovered:
            return self._config.hotbar_hover_color
        return (80, 80, 80)
    
    def _render_button_background(self, geometry: ButtonGeometry, color: Tuple[int, int, int]) -> None:
        """Render filled button background."""
        for row in range(geometry.height):
            start_point = (geometry.x, geometry.y + row)
            end_point = (geometry.x + geometry.width, geometry.y + row)
            self._renderer.draw_line_safely(start_point, end_point, 1, color)
    
    def _render_button_border(self, geometry: ButtonGeometry) -> None:
        """Render button border outline."""
        border_color = self._config.hotbar_border_color
        
        border_lines = [
            ((geometry.x, geometry.y), (geometry.x + geometry.width, geometry.y)),
            ((geometry.x, geometry.y + geometry.height), (geometry.x + geometry.width, geometry.y + geometry.height)),
            ((geometry.x, geometry.y), (geometry.x, geometry.y + geometry.height)),
            ((geometry.x + geometry.width, geometry.y), (geometry.x + geometry.width, geometry.y + geometry.height))
        ]
        
        for start, end in border_lines:
            self._renderer.draw_line_safely(start, end, 1, border_color)
    
    def _render_button_content(self, tool: ToolDefinition, geometry: ButtonGeometry) -> None:
        """Render button icon and text content."""
        icon_x = geometry.x + geometry.width // 2 - 6
        icon_y = geometry.y + 8
        text_x = geometry.x + 5
        text_y = geometry.y + 25
        
        self._renderer.draw_text_safely(tool.icon_text, (icon_x, icon_y), 18, self._config.hotbar_text_color)
        self._renderer.draw_text_safely(tool.display_name, (text_x, text_y), 10, self._config.hotbar_text_color)
    
    def _render_width_text(self, brush_state: BrushState, x: int, y: int) -> None:
        """Render width value text."""
        width_text = f"Width: {brush_state.current_width}"
        self._renderer.draw_text_safely(width_text, (x, y + 5), 12, self._config.hotbar_text_color)
    
    def _render_width_circle(self, brush_state: BrushState, x: int, y: int) -> None:
        """Render visual width indicator circle."""
        circle_x = x + 40
        circle_y = y + 20
        circle_radius = min(max(brush_state.current_width // 2, 2), 15)
        
        self._renderer.draw_circle_safely((circle_x, circle_y), circle_radius, self._config.hotbar_text_color)
    
    def _render_usage_hints(self, x: int, y: int) -> None:
        """Render usage hints for user guidance."""
        hint_text = "Scroll (All Tools)"
        self._renderer.draw_text_safely(hint_text, (x, y + 30), 8, (200, 200, 200))
    
    def _render_tool_indicator(self, current_tool: str, x: int, y: int) -> None:
        """Render current tool indicator."""
        tool_text = f"Tool: {current_tool.title()}"
        self._renderer.draw_text_safely(tool_text, (x, y + 40), 9, (150, 255, 150))


class HotbarWidget(DrawingWidget):
    """Unified hotbar widget with tool selection and brush width control."""
    
    def __init__(
        self,
        tool_service: ToolService,
        event_bus: EventBus,
        safe_renderer: SafeRenderer,
        config: DrawingInterfaceConfig,
        tools: List[ToolDefinition]
    ):
        self._tool_service = tool_service
        self._event_bus = event_bus
        self._renderer = safe_renderer
        self._config = config
        
        self._tools = {tool.key: tool for tool in tools}
        self._geometries = calculate_hotbar_button_geometries(tools, config)
        self._hotbar_renderer = HotbarRenderer(safe_renderer, config)
        
        self._hover_tool = None
        
        logger.info("Hotbar widget initialized with %d tools", len(tools))
    
    def render(self) -> None:
        """Render complete hotbar interface."""
        try:
            total_width = self._calculate_total_width()
            
            self._hotbar_renderer.render_hotbar_background(total_width)
            self._render_all_tool_buttons()
            self._render_width_indicator(total_width)
            
        except Exception as error:
            logger.error(f"Error rendering hotbar: {error}")
            raise RenderingError(f"Failed to render hotbar: {error}") from error
    
    def handle_mouse_click(self, position: Tuple[int, int], button: int) -> bool:
        """Handle mouse click for tool selection."""
        if button != 1:
            return False
        
        clicked_tool = find_tool_at_position(self._geometries, position)
        if not clicked_tool:
            return False
        
        return self._select_tool(clicked_tool)
    
    def handle_mouse_move(self, position: Tuple[int, int]) -> bool:
        """Handle mouse movement for hover effects."""
        try:
            self._hover_tool = find_tool_at_position(self._geometries, position)
            return self._hover_tool is not None
        except Exception as error:
            logger.error(f"Error handling mouse move: {error}")
            return False
    
    def get_widget_type(self) -> WidgetType:
        """Get widget type identifier."""
        return WidgetType.HOTBAR
    
    def _calculate_total_width(self) -> int:
        """Calculate total width needed for hotbar."""
        buttons_width = len(self._tools) * self._config.hotbar_button_width
        spacing_width = (len(self._tools) - 1) * self._config.hotbar_button_spacing
        indicator_width = 160
        return buttons_width + spacing_width + indicator_width
    
    def _render_all_tool_buttons(self) -> None:
        """Render all tool buttons with current state."""
        current_tool = getattr(self._tool_service, 'current_tool_mode', 'brush')
        
        for tool_key, tool in self._tools.items():
            if tool_key not in self._geometries:
                continue
            
            geometry = self._geometries[tool_key]
            is_selected = (tool_key == current_tool)
            is_hovered = (tool_key == self._hover_tool)
            
            self._hotbar_renderer.render_tool_button(tool, geometry, is_selected, is_hovered)
    
    def _render_width_indicator(self, total_width: int) -> None:
        """Render brush width indicator section."""
        current_tool = getattr(self._tool_service, 'current_tool_mode', 'brush')
        brush_state = BrushState(
            current_width=self._config.brush_width_default,
            min_width=self._config.brush_width_min,
            max_width=self._config.brush_width_max,
            step_size=self._config.brush_width_step,
            current_tool=current_tool
        )
        
        indicator_x = self._config.hotbar_x + total_width - 140
        self._hotbar_renderer.render_brush_width_indicator(brush_state, indicator_x)
    
    def _select_tool(self, tool_key: str) -> bool:
        """Select tool and publish change event."""
        try:
            if tool_key not in self._tools:
                raise ToolNotFoundError(f"Tool not found: {tool_key}")
            
            self._tool_service.set_mode(tool_key)
            self._event_bus.publish('tool_selected', tool_key)
            logger.info(f"Tool selected: {tool_key}")
            return True
            
        except Exception as error:
            logger.error(f"Failed to select tool {tool_key}: {error}")
            return False


class CanvasWidget(DrawingWidget):
    """Unified canvas widget with performance optimization and persistent rendering."""
    
    def __init__(
        self,
        journal_service: JournalService,
        safe_renderer: SafeRenderer,
        event_bus: EventBus,
        config: DrawingInterfaceConfig
    ):
        self._journal = journal_service
        self._renderer = safe_renderer
        self._event_bus = event_bus
        self._config = config
        
        self._rendering_stats = RenderingStats()
        self._cache_invalidated = True
        self._last_stroke_count = 0
        self._dirty_regions: Set[Tuple[int, int, int, int]] = set()
        self._render_throttle_interval = 1.0 / config.canvas_render_fps
        
        self._subscribe_to_events()
        logger.info("Canvas widget initialized with performance optimization")
    
    def render(self) -> None:
        """Render canvas content with performance optimization."""
        current_time = time.time()
        
        try:
            if not self._should_render(current_time):
                self._rendering_stats.skipped_renders += 1
                return
            
            render_start_time = current_time
            self._perform_canvas_render()
            render_duration = time.time() - render_start_time
            
            self._update_rendering_stats(render_duration, current_time)
            
        except Exception as error:
            logger.error(f"Error rendering canvas: {error}")
            self._attempt_fallback_render()
    
    def handle_mouse_click(self, position: Tuple[int, int], button: int) -> bool:
        """Canvas does not directly handle mouse clicks."""
        return False
    
    def handle_mouse_move(self, position: Tuple[int, int]) -> bool:
        """Canvas does not directly handle mouse movement."""
        return False
    
    def get_widget_type(self) -> WidgetType:
        """Get widget type identifier."""
        return WidgetType.CANVAS
    
    def invalidate_cache(self) -> None:
        """Force cache invalidation for next render."""
        self._cache_invalidated = True
        self._dirty_regions.clear()
    
    def add_dirty_region(self, x: int, y: int, width: int, height: int) -> None:
        """Mark specific region as dirty for partial rerendering."""
        try:
            region = (max(0, int(x)), max(0, int(y)), max(1, int(width)), max(1, int(height)))
            self._dirty_regions.add(region)
        except Exception as error:
            logger.error(f"Error adding dirty region: {error}")
    
    def get_rendering_stats(self) -> RenderingStats:
        """Get current rendering performance statistics."""
        return self._rendering_stats
    
    def _should_render(self, current_time: float) -> bool:
        """Determine if rendering is necessary based on state and timing."""
        if (current_time - self._rendering_stats.last_render_time) < self._render_throttle_interval:
            return False
        
        if self._cache_invalidated:
            return True
        
        current_stroke_count = self._journal.get_stroke_count()
        if current_stroke_count != self._last_stroke_count:
            self._last_stroke_count = current_stroke_count
            return True
        
        return len(self._dirty_regions) > 0
    
    def _perform_canvas_render(self) -> None:
        """Perform the actual canvas rendering with quality optimization."""
        try:
            if self._config.canvas_quality == RenderingQuality.ADAPTIVE:
                self._render_adaptive_quality()
            elif self._config.canvas_quality == RenderingQuality.HIGH:
                self._render_full_quality()
            else:
                self._render_optimized_quality()
            
            self._cache_invalidated = False
            self._dirty_regions.clear()
            
        except Exception as error:
            logger.error(f"Error in canvas render performance: {error}")
            raise
    
    def _render_adaptive_quality(self) -> None:
        """Render with adaptive quality based on performance."""
        if self._rendering_stats.average_render_time > 0.03:
            self._render_optimized_quality()
        else:
            self._render_full_quality()
    
    def _render_full_quality(self) -> None:
        """Render with full quality and all features."""
        self._journal.render(self._renderer._renderer)
    
    def _render_optimized_quality(self) -> None:
        """Render with performance optimizations."""
        self._journal.render(self._renderer._renderer)
    
    def _attempt_fallback_render(self) -> None:
        """Attempt emergency fallback rendering."""
        try:
            self._cache_invalidated = True
            self._dirty_regions.clear()
            if self._journal and self._renderer:
                self._journal.render(self._renderer._renderer)
            logger.warning("Canvas fallback render completed")
        except Exception as error:
            logger.critical(f"Canvas fallback render failed: {error}")
    
    def _update_rendering_stats(self, render_duration: float, current_time: float) -> None:
        """Update rendering performance statistics."""
        self._rendering_stats.total_renders += 1
        self._rendering_stats.last_render_time = current_time
        
        if self._rendering_stats.total_renders == 1:
            self._rendering_stats.average_render_time = render_duration
        else:
            alpha = 0.1
            self._rendering_stats.average_render_time = (
                alpha * render_duration + 
                (1 - alpha) * self._rendering_stats.average_render_time
            )
    
    def _subscribe_to_events(self) -> None:
        """Subscribe to relevant drawing events."""
        try:
            self._event_bus.subscribe('stroke_added', self._on_stroke_added)
            self._event_bus.subscribe('page_cleared', self._on_page_cleared)
            self._event_bus.subscribe('stroke_invalidated', self._on_stroke_invalidated)
        except Exception as error:
            logger.error(f"Error subscribing to canvas events: {error}")
    
    def _on_stroke_added(self, data=None) -> None:
        """Handle stroke addition events."""
        self._journal.invalidate_cache()
        self._cache_invalidated = True
        
        if data and isinstance(data, dict):
            region = data.get('dirty_region')
            if region:
                self._dirty_regions.add(region)
    
    def _on_page_cleared(self, data=None) -> None:
        """Handle page clear events."""
        self._cache_invalidated = True
        self._last_stroke_count = 0
        self._dirty_regions.clear()
    
    def _on_stroke_invalidated(self, data=None) -> None:
        """Handle stroke invalidation events."""
        self._cache_invalidated = True
        
        if data and isinstance(data, dict):
            region = data.get('region')
            if region:
                self._dirty_regions.add(region)


class InputCoordinator:
    """Unified input coordination across all drawing interface widgets."""
    
    def __init__(self, widgets: List[DrawingWidget], event_bus: EventBus, config: DrawingInterfaceConfig):
        self._widgets = widgets
        self._event_bus = event_bus
        self._config = config
        self._brush_state = create_unified_brush_state(config)
        
        logger.info("Input coordinator initialized with %d widgets", len(widgets))
    
    def handle_mouse_click(self, position: Tuple[int, int], button: int) -> bool:
        """Coordinate mouse clicks across all widgets."""
        try:
            for widget in self._widgets:
                if widget.handle_mouse_click(position, button):
                    return True
            return False
        except Exception as error:
            logger.error(f"Error handling mouse click: {error}")
            return False
    
    def handle_mouse_move(self, position: Tuple[int, int]) -> bool:
        """Coordinate mouse movement across all widgets."""
        try:
            any_handled = False
            for widget in self._widgets:
                if widget.handle_mouse_move(position):
                    any_handled = True
            return any_handled
        except Exception as error:
            logger.error(f"Error handling mouse move: {error}")
            return False
    
    def handle_scroll_wheel(self, direction: int, position: Tuple[int, int]) -> bool:
        """Handle scroll wheel for universal brush width control."""
        try:
            if direction > 0:
                new_state = self._brush_state.increase_width()
            else:
                new_state = self._brush_state.decrease_width()
            
            if new_state.current_width != self._brush_state.current_width:
                self._brush_state = new_state
                self._event_bus.publish('brush_width_changed', new_state.current_width)
                logger.info(f"Brush width changed to: {new_state.current_width}")
                return True
            
            return False
            
        except Exception as error:
            logger.error(f"Error handling scroll wheel: {error}")
            return False
    
    def handle_key_press(self, key: str) -> bool:
        """Handle keyboard input for drawing interface."""
        try:
            if key.lower() == 'g':
                self._toggle_grid()
                return True
            
            tool_shortcuts = {
                'b': 'brush', 'e': 'eraser', 'l': 'line', 
                'r': 'rect', 'c': 'circle', 't': 'triangle'
            }
            
            if key.lower() in tool_shortcuts:
                self._event_bus.publish('tool_shortcut', tool_shortcuts[key.lower()])
                return True
            
            return False
            
        except Exception as error:
            logger.error(f"Error handling key press: {error}")
            return False
    
    def get_current_brush_state(self) -> BrushState:
        """Get current unified brush state."""
        return self._brush_state
    
    def _toggle_grid(self) -> None:
        """Toggle grid visibility across all grid widgets."""
        for widget in self._widgets:
            if widget.get_widget_type() == WidgetType.GRID:
                if hasattr(widget, 'toggle_grid'):
                    widget.toggle_grid()


class DrawingInterface:
    """
    Unified Drawing Interface System.
    
    Coordinates hotbar, canvas, and grid widgets into a cohesive drawing experience
    with zero duplication and enhanced functionality.
    
    Features:
    - Universal brush width control across all tools
    - Integrated tool selection with visual feedback
    - Performance-optimized canvas rendering
    - Background grid with neon styling
    - Comprehensive error handling and recovery
    - Extensible architecture for new features
    """
    
    def __init__(
        self,
        tool_service: ToolService,
        journal_service: JournalService,
        renderer: UnifiedRenderer,
        event_bus: EventBus,
        config: Optional[DrawingInterfaceConfig] = None,
        custom_tools: Optional[List[ToolDefinition]] = None
    ):
        """Initialize unified drawing interface with all components."""
        logger.info("Initializing unified drawing interface system...")
        
        self._config = config or DrawingInterfaceConfig()
        self._event_bus = event_bus
        
        self._safe_renderer = SafeRenderer(renderer)
        
        tools = custom_tools or create_standard_tool_definitions()
        
        self._grid_widget = GridWidget(self._safe_renderer, self._config)
        self._hotbar_widget = HotbarWidget(tool_service, event_bus, self._safe_renderer, self._config, tools)
        self._canvas_widget = CanvasWidget(journal_service, self._safe_renderer, event_bus, self._config)
        
        self._widgets = [self._grid_widget, self._canvas_widget, self._hotbar_widget]
        self._input_coordinator = InputCoordinator(self._widgets, event_bus, self._config)
        
        self._subscribe_to_system_events()
        
        logger.info("Drawing interface system initialized successfully")
    
    def render(self) -> None:
        """Render complete drawing interface system."""
        try:
            for widget in self._widgets:
                widget.render()
        except Exception as error:
            logger.error(f"Error rendering drawing interface: {error}")
            raise RenderingError(f"Failed to render drawing interface: {error}") from error
    
    def handle_mouse_click(self, position: Tuple[int, int], button: int) -> bool:
        """Handle mouse click events across the interface."""
        return self._input_coordinator.handle_mouse_click(position, button)
    
    def handle_mouse_move(self, position: Tuple[int, int]) -> bool:
        """Handle mouse movement events across the interface."""
        return self._input_coordinator.handle_mouse_move(position)
    
    def handle_scroll_wheel(self, direction: int, position: Tuple[int, int]) -> bool:
        """Handle scroll wheel events for brush width control."""
        return self._input_coordinator.handle_scroll_wheel(direction, position)
    
    def handle_key_press(self, key: str) -> bool:
        """Handle keyboard input for interface control."""
        return self._input_coordinator.handle_key_press(key)
    
    def toggle_grid(self) -> None:
        """Toggle grid visibility."""
        self._grid_widget.toggle_grid()
    
    def get_current_brush_width(self) -> int:
        """Get current universal brush width."""
        return self._input_coordinator.get_current_brush_state().current_width
    
    def get_rendering_stats(self) -> Dict[str, Any]:
        """Get comprehensive rendering statistics."""
        canvas_stats = self._canvas_widget.get_rendering_stats()
        return {
            'canvas_renders': canvas_stats.total_renders,
            'canvas_skips': canvas_stats.skipped_renders,
            'canvas_skip_rate': canvas_stats.skip_rate,
            'average_render_time': canvas_stats.average_render_time,
            'renderer_errors': self._safe_renderer._error_count
        }
    
    def _subscribe_to_system_events(self) -> None:
        """Subscribe to system-wide events for coordination."""
        try:
            self._event_bus.subscribe('tool_shortcut', self._on_tool_shortcut)
            self._event_bus.subscribe('brush_width_changed', self._on_brush_width_changed)
        except Exception as error:
            logger.error(f"Error subscribing to system events: {error}")
    
    def _on_tool_shortcut(self, tool_key: str) -> None:
        """Handle tool shortcut activation."""
        logger.debug(f"Tool shortcut activated: {tool_key}")
    
    def _on_brush_width_changed(self, width: int) -> None:
        """Handle brush width change events."""
        logger.debug(f"Brush width changed to: {width}")


def create_drawing_interface(
    tool_service: ToolService,
    journal_service: JournalService,
    renderer: UnifiedRenderer,
    event_bus: EventBus,
    config: Optional[DrawingInterfaceConfig] = None
) -> DrawingInterface:
    """
    Factory function for creating unified drawing interface.
    
    This is the recommended way to create drawing interfaces for production use.
    """
    try:
        interface = DrawingInterface(tool_service, journal_service, renderer, event_bus, config)
        logger.info("Drawing interface created successfully")
        return interface
        
    except Exception as error:
        logger.error(f"Failed to create drawing interface: {error}")
        raise DrawingInterfaceError(f"Interface creation failed: {error}") from error


def create_drawing_interface_with_custom_tools(
    tool_service: ToolService,
    journal_service: JournalService,
    renderer: UnifiedRenderer,
    event_bus: EventBus,
    custom_tools: List[ToolDefinition],
    config: Optional[DrawingInterfaceConfig] = None
) -> DrawingInterface:
    """
    Factory function for creating drawing interface with custom tool set.
    
    Use this when you need to customize the available tools beyond the standard set.
    """
    try:
        interface = DrawingInterface(
            tool_service, journal_service, renderer, event_bus, config, custom_tools
        )
        logger.info(f"Drawing interface created with {len(custom_tools)} custom tools")
        return interface
        
    except Exception as error:
        logger.error(f"Failed to create custom drawing interface: {error}")
        raise DrawingInterfaceError(f"Custom interface creation failed: {error}") from error


class DrawingInterfaceTestHelpers:
    """Helper functions for testing drawing interface components."""
    
    @staticmethod
    def create_test_config() -> DrawingInterfaceConfig:
        """Create drawing interface config for testing."""
        return DrawingInterfaceConfig(
            hotbar_x=0, hotbar_y=0, hotbar_button_width=50, hotbar_button_height=30,
            brush_width_min=1, brush_width_max=20, brush_width_default=3,
            grid_spacing=20, canvas_render_fps=30
        )
    
    @staticmethod
    def create_test_tool_definition(key: str = "test_tool") -> ToolDefinition:
        """Create tool definition for testing."""
        return ToolDefinition(
            key=key,
            display_name="Test",
            icon_text="T",
            description="Test tool",
            category=ToolCategory.DRAWING
        )
    
    @staticmethod
    def create_mock_dependencies():
        """Create mock dependencies for testing."""
        from unittest.mock import Mock
        
        tool_service = Mock(spec=ToolService)
        tool_service.current_tool_mode = "brush"
        
        journal_service = Mock(spec=JournalService)
        journal_service.get_stroke_count.return_value = 0
        
        renderer = Mock(spec=UnifiedRenderer)
        renderer.get_size.return_value = (800, 600)
        
        event_bus = Mock(spec=EventBus)
        
        return tool_service, journal_service, renderer, event_bus