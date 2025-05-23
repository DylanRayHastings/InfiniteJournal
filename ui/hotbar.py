"""
Production-ready hotbar widget system for drawing applications.

This module provides a complete hotbar interface with universal brush width control,
tool selection, and visual feedback. Designed for immediate team productivity and
confident expansion.

Quick start:
    config = HotbarConfig()
    widget = create_hotbar_widget(tool_service, renderer, event_bus, config)
    widget.render()

Extension points:
    - Add new tools: Extend TOOL_DEFINITIONS list
    - Add new hotbar features: Implement HotbarFeature interface
    - Add new renderers: Implement HotbarRenderer interface
    - Add new input handlers: Implement InputHandler interface
"""

import logging
from typing import Dict, List, Tuple, Optional, Any, Protocol
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

logger = logging.getLogger(__name__)


class HotbarError(Exception):
    """Base exception for hotbar operations."""
    pass


class ToolNotFoundError(HotbarError):
    """Tool does not exist in hotbar."""
    pass


class RenderingError(HotbarError):
    """Error occurred during hotbar rendering."""
    pass


class InputHandlingError(HotbarError):
    """Error occurred during input processing."""
    pass


class ToolCategory(Enum):
    """Categories for organizing tools."""
    DRAWING = "drawing"
    SHAPES = "shapes"
    EDITING = "editing"
    EFFECTS = "effects"


@dataclass(frozen=True)
class ToolDefinition:
    """Immutable tool definition with complete specification."""
    key: str
    display_name: str
    icon_text: str
    description: str
    category: ToolCategory
    supports_brush_width: bool = True


@dataclass(frozen=True)
class HotbarConfig:
    """Complete hotbar configuration with sensible defaults."""
    x: int = 10
    y: int = 10
    button_width: int = 80
    button_height: int = 40
    button_spacing: int = 5
    background_color: Tuple[int, int, int] = (60, 60, 60)
    selected_color: Tuple[int, int, int] = (0, 150, 255)
    hover_color: Tuple[int, int, int] = (100, 100, 100)
    text_color: Tuple[int, int, int] = (255, 255, 255)
    border_color: Tuple[int, int, int] = (150, 150, 150)
    brush_width_min: int = 1
    brush_width_max: int = 50
    brush_width_default: int = 5
    brush_width_step: int = 2


@dataclass(frozen=True)
class ButtonGeometry:
    """Button position and dimensions."""
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
class BrushWidthState:
    """Current brush width state."""
    current_width: int
    min_width: int
    max_width: int
    step_size: int
    
    def increase_width(self) -> 'BrushWidthState':
        """Create new state with increased width."""
        new_width = min(self.current_width + self.step_size, self.max_width)
        return BrushWidthState(new_width, self.min_width, self.max_width, self.step_size)
    
    def decrease_width(self) -> 'BrushWidthState':
        """Create new state with decreased width."""
        new_width = max(self.current_width - self.step_size, self.min_width)
        return BrushWidthState(new_width, self.min_width, self.max_width, self.step_size)


class EventBus(Protocol):
    """Event bus interface for publishing system events."""
    
    def subscribe(self, event_type: str, handler) -> None:
        """Subscribe to event type."""
        ...
    
    def publish(self, event_type: str, data: Any) -> None:
        """Publish event with data."""
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


class HotbarRenderer(Protocol):
    """Hotbar rendering interface."""
    
    def draw_line(self, start: Tuple[int, int], end: Tuple[int, int], width: int, color: Tuple[int, int, int]) -> None:
        """Draw line between two points."""
        ...
    
    def draw_text(self, text: str, position: Tuple[int, int], size: int, color: Tuple[int, int, int]) -> None:
        """Draw text at position."""
        ...
    
    def draw_circle(self, center: Tuple[int, int], radius: int, color: Tuple[int, int, int]) -> None:
        """Draw circle at center with radius."""
        ...


def create_standard_tool_definitions() -> List[ToolDefinition]:
    """Create standard set of drawing tools."""
    return [
        ToolDefinition("brush", "Draw", "~", "Freehand drawing tool", ToolCategory.DRAWING),
        ToolDefinition("eraser", "Erase", "X", "Eraser tool", ToolCategory.EDITING),
        ToolDefinition("line", "Line", "|", "Draw straight lines", ToolCategory.SHAPES),
        ToolDefinition("rect", "Rect", "[]", "Draw rectangles", ToolCategory.SHAPES),
        ToolDefinition("circle", "Circle", "O", "Draw circles", ToolCategory.SHAPES),
        ToolDefinition("triangle", "Triangle", "/\\", "Draw triangles", ToolCategory.SHAPES),
        ToolDefinition("parabola", "Curve", "^", "Draw parabolic curves", ToolCategory.SHAPES),
    ]


def create_brush_width_state(config: HotbarConfig) -> BrushWidthState:
    """Create initial brush width state from configuration."""
    return BrushWidthState(
        current_width=config.brush_width_default,
        min_width=config.brush_width_min,
        max_width=config.brush_width_max,
        step_size=config.brush_width_step
    )


def calculate_button_geometries(tools: List[ToolDefinition], config: HotbarConfig) -> Dict[str, ButtonGeometry]:
    """Calculate button positions for all tools."""
    geometries = {}
    current_x = config.x
    
    for tool in tools:
        geometries[tool.key] = ButtonGeometry(
            x=current_x,
            y=config.y,
            width=config.button_width,
            height=config.button_height
        )
        current_x += config.button_width + config.button_spacing
    
    return geometries


def find_tool_at_position(geometries: Dict[str, ButtonGeometry], position: Tuple[int, int]) -> Optional[str]:
    """Find tool key at given position."""
    for tool_key, geometry in geometries.items():
        if geometry.contains_point(position):
            return tool_key
    return None


def is_position_over_hotbar(geometries: Dict[str, ButtonGeometry], position: Tuple[int, int]) -> bool:
    """Check if position is over any hotbar button."""
    return find_tool_at_position(geometries, position) is not None


class SafeRenderer:
    """Safe wrapper for hotbar renderer with error handling."""
    
    def __init__(self, renderer: HotbarRenderer):
        self._renderer = renderer
    
    def draw_line_safely(self, start: Tuple[int, int], end: Tuple[int, int], width: int, color: Tuple[int, int, int]) -> bool:
        """Draw line with error handling."""
        try:
            if hasattr(self._renderer, 'draw_line'):
                self._renderer.draw_line(start, end, width, color)
                return True
        except Exception as error:
            logger.debug(f"Failed to draw line: {error}")
        return False
    
    def draw_text_safely(self, text: str, position: Tuple[int, int], size: int, color: Tuple[int, int, int]) -> bool:
        """Draw text with error handling and validation."""
        try:
            if not hasattr(self._renderer, 'draw_text'):
                return False
            
            safe_text = str(text)[:50]
            safe_position = (max(0, int(position[0])), max(0, int(position[1])))
            safe_size = max(8, min(72, int(size)))
            
            self._renderer.draw_text(safe_text, safe_position, safe_size, color)
            return True
            
        except Exception as error:
            logger.debug(f"Failed to draw text '{text}': {error}")
        return False
    
    def draw_circle_safely(self, center: Tuple[int, int], radius: int, color: Tuple[int, int, int]) -> bool:
        """Draw circle with error handling and validation."""
        try:
            if not hasattr(self._renderer, 'draw_circle'):
                return False
            
            safe_center = (max(0, int(center[0])), max(0, int(center[1])))
            safe_radius = max(1, min(100, int(radius)))
            
            self._renderer.draw_circle(safe_center, safe_radius, color)
            return True
            
        except Exception as error:
            logger.debug(f"Failed to draw circle: {error}")
        return False


class HotbarBackgroundRenderer:
    """Handles hotbar background rendering."""
    
    def __init__(self, safe_renderer: SafeRenderer, config: HotbarConfig):
        self._renderer = safe_renderer
        self._config = config
    
    def render_background(self, total_width: int) -> None:
        """Render hotbar background with proper dimensions."""
        try:
            background_height = self._config.button_height + 10
            background_start_x = self._config.x - 5
            background_start_y = self._config.y - 5
            
            for row in range(background_height):
                start_point = (background_start_x, background_start_y + row)
                end_point = (background_start_x + total_width + 10, background_start_y + row)
                
                self._renderer.draw_line_safely(
                    start_point, end_point, 1, self._config.background_color
                )
                
        except Exception as error:
            logger.error(f"Failed to render background: {error}")


class HotbarButtonRenderer:
    """Handles individual button rendering."""
    
    def __init__(self, safe_renderer: SafeRenderer, config: HotbarConfig):
        self._renderer = safe_renderer
        self._config = config
    
    def render_button(
        self, 
        tool: ToolDefinition, 
        geometry: ButtonGeometry, 
        is_selected: bool, 
        is_hovered: bool
    ) -> None:
        """Render single tool button with state."""
        try:
            button_color = self._determine_button_color(is_selected, is_hovered)
            
            self._render_button_background(geometry, button_color)
            self._render_button_border(geometry)
            self._render_button_content(tool, geometry)
            
        except Exception as error:
            logger.warning(f"Failed to render button {tool.key}: {error}")
    
    def _determine_button_color(self, is_selected: bool, is_hovered: bool) -> Tuple[int, int, int]:
        """Determine button background color based on state."""
        if is_selected:
            return self._config.selected_color
        if is_hovered:
            return self._config.hover_color
        return (80, 80, 80)
    
    def _render_button_background(self, geometry: ButtonGeometry, color: Tuple[int, int, int]) -> None:
        """Render filled button background."""
        for row in range(geometry.height):
            start_point = (geometry.x, geometry.y + row)
            end_point = (geometry.x + geometry.width, geometry.y + row)
            self._renderer.draw_line_safely(start_point, end_point, 1, color)
    
    def _render_button_border(self, geometry: ButtonGeometry) -> None:
        """Render button border outline."""
        border_color = self._config.border_color
        
        top_line = ((geometry.x, geometry.y), (geometry.x + geometry.width, geometry.y))
        bottom_line = ((geometry.x, geometry.y + geometry.height), (geometry.x + geometry.width, geometry.y + geometry.height))
        left_line = ((geometry.x, geometry.y), (geometry.x, geometry.y + geometry.height))
        right_line = ((geometry.x + geometry.width, geometry.y), (geometry.x + geometry.width, geometry.y + geometry.height))
        
        for start, end in [top_line, bottom_line, left_line, right_line]:
            self._renderer.draw_line_safely(start, end, 1, border_color)
    
    def _render_button_content(self, tool: ToolDefinition, geometry: ButtonGeometry) -> None:
        """Render button icon and text content."""
        icon_x = geometry.x + geometry.width // 2 - 6
        icon_y = geometry.y + 8
        text_x = geometry.x + 5
        text_y = geometry.y + 25
        
        self._renderer.draw_text_safely(tool.icon_text, (icon_x, icon_y), 18, self._config.text_color)
        self._renderer.draw_text_safely(tool.display_name, (text_x, text_y), 10, self._config.text_color)


class BrushWidthIndicatorRenderer:
    """Handles brush width indicator rendering."""
    
    def __init__(self, safe_renderer: SafeRenderer, config: HotbarConfig):
        self._renderer = safe_renderer
        self._config = config
    
    def render_width_indicator(
        self, 
        brush_state: BrushWidthState, 
        current_tool: str, 
        indicator_x: int
    ) -> None:
        """Render complete brush width indicator."""
        try:
            indicator_y = self._config.y
            
            self._render_width_text(brush_state, indicator_x, indicator_y)
            self._render_width_circle(brush_state, indicator_x, indicator_y)
            self._render_usage_hint(indicator_x, indicator_y)
            self._render_tool_indicator(current_tool, indicator_x, indicator_y)
            
        except Exception as error:
            logger.error(f"Failed to render width indicator: {error}")
    
    def _render_width_text(self, brush_state: BrushWidthState, x: int, y: int) -> None:
        """Render width value text."""
        width_text = f"Width: {brush_state.current_width}"
        self._renderer.draw_text_safely(width_text, (x, y + 5), 12, self._config.text_color)
    
    def _render_width_circle(self, brush_state: BrushWidthState, x: int, y: int) -> None:
        """Render visual width indicator circle."""
        circle_x = x + 40
        circle_y = y + 20
        circle_radius = min(max(brush_state.current_width // 2, 2), 15)
        
        self._renderer.draw_circle_safely((circle_x, circle_y), circle_radius, self._config.text_color)
    
    def _render_usage_hint(self, x: int, y: int) -> None:
        """Render scroll wheel usage hint."""
        hint_text = "Scroll (All Tools)"
        self._renderer.draw_text_safely(hint_text, (x, y + 30), 8, (200, 200, 200))
    
    def _render_tool_indicator(self, current_tool: str, x: int, y: int) -> None:
        """Render current tool indicator."""
        tool_text = f"Tool: {current_tool.title()}"
        self._renderer.draw_text_safely(tool_text, (x, y + 40), 9, (150, 255, 150))


class HotbarInputHandler:
    """Handles hotbar input events with clear separation."""
    
    def __init__(
        self, 
        tool_service: ToolService, 
        event_bus: EventBus,
        tools: Dict[str, ToolDefinition],
        geometries: Dict[str, ButtonGeometry]
    ):
        self._tool_service = tool_service
        self._event_bus = event_bus
        self._tools = tools
        self._geometries = geometries
    
    def handle_mouse_click(self, position: Tuple[int, int], button: int) -> bool:
        """Handle mouse click for tool selection."""
        if button != 1:
            return False
        
        clicked_tool = find_tool_at_position(self._geometries, position)
        if not clicked_tool:
            return False
        
        return self._select_tool(clicked_tool)
    
    def handle_scroll_wheel(self, direction: int, brush_state: BrushWidthState) -> Optional[BrushWidthState]:
        """Handle scroll wheel for brush width adjustment."""
        try:
            if direction > 0:
                new_state = brush_state.increase_width()
            else:
                new_state = brush_state.decrease_width()
            
            if new_state.current_width != brush_state.current_width:
                self._publish_brush_width_change(new_state.current_width)
                logger.info(f"Brush width changed to: {new_state.current_width}")
                return new_state
            
            return brush_state
            
        except Exception as error:
            logger.error(f"Failed to handle scroll wheel: {error}")
            return brush_state
    
    def _select_tool(self, tool_key: str) -> bool:
        """Select tool and publish change."""
        try:
            if tool_key not in self._tools:
                raise ToolNotFoundError(f"Tool not found: {tool_key}")
            
            self._tool_service.set_mode(tool_key)
            logger.info(f"Tool selected: {tool_key}")
            return True
            
        except Exception as error:
            logger.error(f"Failed to select tool {tool_key}: {error}")
            return False
    
    def _publish_brush_width_change(self, width: int) -> None:
        """Publish brush width change event."""
        try:
            self._event_bus.publish('brush_width_changed', width)
        except Exception as error:
            logger.error(f"Failed to publish brush width change: {error}")


class HotbarWidget:
    """
    Main hotbar widget coordinating all hotbar functionality.
    
    This widget provides:
    - Universal brush width control for all tools
    - Visual tool selection with hover feedback
    - Extensible tool system with clear addition points
    - Safe rendering with comprehensive error handling
    
    Extension points:
    1. Add new tools: Extend tool definitions list
    2. Add new features: Implement additional renderer classes
    3. Add new input types: Extend input handler
    4. Add new visual styles: Modify configuration
    """
    
    def __init__(
        self,
        tool_service: ToolService,
        renderer: HotbarRenderer,
        event_bus: EventBus,
        config: Optional[HotbarConfig] = None,
        tool_definitions: Optional[List[ToolDefinition]] = None
    ):
        """Initialize hotbar widget with all dependencies."""
        logger.info("Initializing production-ready hotbar widget...")
        
        self._tool_service = tool_service
        self._event_bus = event_bus
        self._config = config or HotbarConfig()
        
        self._tools = {tool.key: tool for tool in (tool_definitions or create_standard_tool_definitions())}
        self._geometries = calculate_button_geometries(list(self._tools.values()), self._config)
        self._brush_state = create_brush_width_state(self._config)
        
        self._safe_renderer = SafeRenderer(renderer)
        self._background_renderer = HotbarBackgroundRenderer(self._safe_renderer, self._config)
        self._button_renderer = HotbarButtonRenderer(self._safe_renderer, self._config)
        self._width_renderer = BrushWidthIndicatorRenderer(self._safe_renderer, self._config)
        self._input_handler = HotbarInputHandler(tool_service, event_bus, self._tools, self._geometries)
        
        self._hover_tool = None
        
        self._subscribe_to_events()
        self._publish_initial_brush_width()
        
        logger.info("Hotbar widget initialized successfully")
    
    def handle_mouse_click(self, position: Tuple[int, int], button: int) -> bool:
        """Handle mouse click events."""
        try:
            return self._input_handler.handle_mouse_click(position, button)
        except Exception as error:
            logger.error(f"Error handling mouse click: {error}")
            return False
    
    def handle_mouse_move(self, position: Tuple[int, int]) -> bool:
        """Handle mouse movement for hover effects."""
        try:
            self._hover_tool = find_tool_at_position(self._geometries, position)
            return is_position_over_hotbar(self._geometries, position)
        except Exception as error:
            logger.error(f"Error handling mouse move: {error}")
            return False
    
    def handle_scroll_wheel(self, direction: int, position: Tuple[int, int]) -> bool:
        """Handle scroll wheel for universal brush width control."""
        try:
            new_state = self._input_handler.handle_scroll_wheel(direction, self._brush_state)
            if new_state != self._brush_state:
                self._brush_state = new_state
            return True
        except Exception as error:
            logger.error(f"Error handling scroll wheel: {error}")
            return False
    
    def is_mouse_over_hotbar(self) -> bool:
        """Check if mouse is currently over hotbar area."""
        return self._hover_tool is not None
    
    def get_current_brush_width(self) -> int:
        """Get current universal brush width."""
        return self._brush_state.current_width
    
    def render(self) -> None:
        """Render complete hotbar interface."""
        try:
            logger.debug("Rendering hotbar interface...")
            
            total_width = self._calculate_total_width()
            
            self._background_renderer.render_background(total_width)
            self._render_all_buttons()
            self._render_width_indicator(total_width)
            
            logger.debug("Hotbar rendered successfully")
            
        except Exception as error:
            logger.error(f"Critical error rendering hotbar: {error}")
            raise RenderingError(f"Failed to render hotbar: {error}") from error
    
    def _calculate_total_width(self) -> int:
        """Calculate total width needed for hotbar."""
        buttons_width = len(self._tools) * self._config.button_width
        spacing_width = (len(self._tools) - 1) * self._config.button_spacing
        indicator_width = 160
        return buttons_width + spacing_width + indicator_width
    
    def _render_all_buttons(self) -> None:
        """Render all tool buttons with current state."""
        current_tool = getattr(self._tool_service, 'current_tool_mode', 'brush')
        
        for tool_key, tool in self._tools.items():
            if tool_key not in self._geometries:
                continue
            
            geometry = self._geometries[tool_key]
            is_selected = (tool_key == current_tool)
            is_hovered = (tool_key == self._hover_tool)
            
            self._button_renderer.render_button(tool, geometry, is_selected, is_hovered)
    
    def _render_width_indicator(self, total_width: int) -> None:
        """Render brush width indicator section."""
        current_tool = getattr(self._tool_service, 'current_tool_mode', 'brush')
        indicator_x = self._config.x + total_width - 140
        
        self._width_renderer.render_width_indicator(
            self._brush_state, current_tool, indicator_x
        )
    
    def _subscribe_to_events(self) -> None:
        """Subscribe to relevant system events."""
        try:
            self._event_bus.subscribe('mode_changed', self._on_mode_changed)
            logger.info("Subscribed to system events")
        except Exception as error:
            logger.error(f"Failed to subscribe to events: {error}")
    
    def _publish_initial_brush_width(self) -> None:
        """Publish initial brush width to system."""
        try:
            self._event_bus.publish('brush_width_changed', self._brush_state.current_width)
        except Exception as error:
            logger.error(f"Failed to publish initial brush width: {error}")
    
    def _on_mode_changed(self, mode: str) -> None:
        """Handle tool mode change events."""
        logger.debug(f"Tool mode changed to: {mode}")


def create_hotbar_widget(
    tool_service: ToolService,
    renderer: HotbarRenderer,
    event_bus: EventBus,
    config: Optional[HotbarConfig] = None
) -> HotbarWidget:
    """
    Factory function for creating hotbar widget with dependencies.
    
    This is the recommended way to create hotbar widgets for production use.
    """
    try:
        widget = HotbarWidget(tool_service, renderer, event_bus, config)
        logger.info("Hotbar widget created successfully")
        return widget
        
    except Exception as error:
        logger.error(f"Failed to create hotbar widget: {error}")
        raise HotbarError(f"Widget creation failed: {error}") from error


def create_hotbar_widget_with_custom_tools(
    tool_service: ToolService,
    renderer: HotbarRenderer,
    event_bus: EventBus,
    custom_tools: List[ToolDefinition],
    config: Optional[HotbarConfig] = None
) -> HotbarWidget:
    """
    Factory function for creating hotbar widget with custom tool set.
    
    Use this when you need to customize the available tools beyond the standard set.
    """
    try:
        widget = HotbarWidget(tool_service, renderer, event_bus, config, custom_tools)
        logger.info(f"Hotbar widget created with {len(custom_tools)} custom tools")
        return widget
        
    except Exception as error:
        logger.error(f"Failed to create custom hotbar widget: {error}")
        raise HotbarError(f"Custom widget creation failed: {error}") from error


class HotbarTestHelpers:
    """Helper functions for testing hotbar components."""
    
    @staticmethod
    def create_test_config() -> HotbarConfig:
        """Create hotbar config for testing."""
        return HotbarConfig(
            x=0, y=0, button_width=50, button_height=30,
            brush_width_min=1, brush_width_max=20, brush_width_default=3
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
        
        renderer = Mock(spec=HotbarRenderer)
        event_bus = Mock(spec=EventBus)
        
        return tool_service, renderer, event_bus