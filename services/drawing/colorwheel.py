"""
Circle Gradient Color Picker for InfiniteJournal
==============================================

Enhanced color wheel implementation that integrates with the InfiniteJournal
application architecture. Provides interactive color selection with gradient
picking, brightness/saturation controls, and integration with the drawing system.
"""

import math
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from enum import Enum
from pathlib import Path

# Import from application framework
try:
    from services.core import (
        UniversalService, ServiceConfiguration, ValidationService, 
        EventBus, validate_color
    )
    from services.drawing import ToolManager
    SERVICES_AVAILABLE = True
except ImportError:
    SERVICES_AVAILABLE = False

logger = logging.getLogger(__name__)


class ColorSpace(Enum):
    """Color space representations."""
    RGB = "rgb"
    HSV = "hsv"
    HSL = "hsl"
    LAB = "lab"


@dataclass
class ColorInfo:
    """Complete color information with multiple representations."""
    rgb: Tuple[int, int, int]
    hsv: Tuple[float, float, float]  # Hue 0-360, Sat/Val 0-1
    hex_code: str
    name: Optional[str] = None
    
    @classmethod
    def from_rgb(cls, r: int, g: int, b: int) -> 'ColorInfo':
        """Create ColorInfo from RGB values."""
        rgb = (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
        hsv = ColorMath.rgb_to_hsv(rgb)
        hex_code = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        return cls(rgb, hsv, hex_code)
    
    @classmethod
    def from_hsv(cls, h: float, s: float, v: float) -> 'ColorInfo':
        """Create ColorInfo from HSV values."""
        hsv = (h % 360, max(0, min(1, s)), max(0, min(1, v)))
        rgb = ColorMath.hsv_to_rgb(hsv)
        hex_code = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        return cls(rgb, hsv, hex_code)


class ColorMath:
    """Mathematical operations for color space conversions."""
    
    @staticmethod
    def rgb_to_hsv(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
        """Convert RGB to HSV color space."""
        r, g, b = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0
        
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        diff = max_val - min_val
        
        # Value
        v = max_val
        
        # Saturation
        s = 0 if max_val == 0 else diff / max_val
        
        # Hue
        if diff == 0:
            h = 0
        elif max_val == r:
            h = (60 * ((g - b) / diff) + 360) % 360
        elif max_val == g:
            h = (60 * ((b - r) / diff) + 120) % 360
        else:  # max_val == b
            h = (60 * ((r - g) / diff) + 240) % 360
        
        return (h, s, v)
    
    @staticmethod
    def hsv_to_rgb(hsv: Tuple[float, float, float]) -> Tuple[int, int, int]:
        """Convert HSV to RGB color space."""
        h, s, v = hsv
        h = h % 360
        
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c
        
        if 0 <= h < 60:
            r, g, b = c, x, 0
        elif 60 <= h < 120:
            r, g, b = x, c, 0
        elif 120 <= h < 180:
            r, g, b = 0, c, x
        elif 180 <= h < 240:
            r, g, b = 0, x, c
        elif 240 <= h < 300:
            r, g, b = x, 0, c
        else:  # 300 <= h < 360
            r, g, b = c, 0, x
        
        rgb = (
            int((r + m) * 255),
            int((g + m) * 255),
            int((b + m) * 255)
        )
        
        return rgb
    
    @staticmethod
    def interpolate_colors(color1: Tuple[int, int, int], color2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
        """Interpolate between two RGB colors."""
        t = max(0.0, min(1.0, t))
        return (
            int(color1[0] + (color2[0] - color1[0]) * t),
            int(color1[1] + (color2[1] - color1[1]) * t),
            int(color1[2] + (color2[2] - color1[2]) * t)
        )


class ColorWheelRenderer:
    """
    Renders color wheel with 6 primary color segments.
    
    Provides efficient rendering of a 6-color wheel displaying Red, Green, Blue, 
    Cyan, Violet, and Yellow with brightness and saturation controls for each color.
    """
    
    def __init__(self, center_x: int, center_y: int, radius: int):
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius
        self.inner_radius = radius * 0.3  # For brightness/saturation triangle
        
        # Rendering configuration
        self.hue_ring_width = radius * 0.25
        self.render_quality = 2  # Render scale for smoothness
        
        # Define exactly 6 primary colors for the wheel
        self.color_count = 6
        self.predefined_colors = self._build_primary_color_palette()
        
        # Cache for rendered segments
        self._segment_cache: Dict[int, Tuple[int, int, int]] = {}
        self._cache_valid = False
        
        logger.debug(f"ColorWheelRenderer initialized: center=({center_x}, {center_y}), radius={radius}, colors={self.color_count} primary colors")
    
    def _build_primary_color_palette(self) -> List[Tuple[int, int, int]]:
        """Build the standard 6 primary color palette: Red, Green, Blue, Cyan, Violet, Yellow."""
        # Define the 6 primary colors with their exact RGB values
        primary_colors = [
            (255, 0, 0),    # Red (0°)
            (255, 255, 0),  # Yellow (60°) 
            (0, 255, 0),    # Green (120°)
            (0, 255, 255),  # Cyan (180°)
            (0, 0, 255),    # Blue (240°)
            (255, 0, 255),  # Violet/Magenta (300°)
        ]
        
        return primary_colors
    
    def render_color_wheel(self, backend: Any, current_color: Optional[ColorInfo] = None) -> None:
        """Render the complete color wheel interface."""
        try:
            # Render hue ring
            self._render_hue_ring(backend)
            
            # Render saturation/brightness triangle
            if current_color:
                self._render_sb_triangle(backend, current_color.hsv[0])
            else:
                self._render_sb_triangle(backend, 0)  # Default to red hue
            
            # Render center circle
            self._render_center_circle(backend)
            
            # Render current color indicator
            if current_color:
                self._render_color_indicator(backend, current_color)
            
        except Exception as error:
            logger.error(f"Color wheel rendering failed: {error}")
    
    def _render_hue_ring(self, backend: Any) -> None:
        """Render the outer ring with 6 primary color segments."""
        if not hasattr(backend, 'draw_circle'):
            logger.warning("Backend does not support circle drawing")
            return
        
        # Calculate angle for each of the 6 color segments
        angle_step = 360.0 / self.color_count
        
        for i in range(self.color_count):
            # Get predefined color for this segment
            color_rgb = self.predefined_colors[i]
            
            # Calculate center angle for this segment
            center_angle = i * angle_step
            
            # Draw multiple points to fill the segment arc
            points_per_segment = max(8, int(angle_step / 3))  # More points per segment for better coverage
            
            for point in range(points_per_segment):
                # Calculate angle for this point within the segment
                angle_offset = (point / points_per_segment - 0.5) * angle_step * 0.9  # 90% coverage
                angle = center_angle + angle_offset
                angle_rad = math.radians(angle)
                
                # Calculate position in the ring
                ring_radius = self.radius - self.hue_ring_width / 2
                segment_x = self.center_x + ring_radius * math.cos(angle_rad)
                segment_y = self.center_y + ring_radius * math.sin(angle_rad)
                
                try:
                    backend.draw_circle(
                        (int(segment_x), int(segment_y)),
                        max(3, int(self.hue_ring_width / 5)),
                        color_rgb
                    )
                except Exception as draw_error:
                    logger.debug(f"Failed to draw color segment {i}, point {point}: {draw_error}")
    
    def _render_sb_triangle(self, backend: Any, hue: float) -> None:
        """Render saturation/brightness selection triangle."""
        # Simplified implementation: render as gradient square for now
        # In advanced implementation, this would be a proper HSV triangle
        
        triangle_size = int(self.inner_radius * 1.4)
        start_x = self.center_x - triangle_size // 2
        start_y = self.center_y - triangle_size // 2
        
        # Render gradient square showing saturation (x-axis) and brightness (y-axis)
        step_size = max(1, triangle_size // 20)  # Limit resolution for performance
        
        for y in range(0, triangle_size, step_size):
            for x in range(0, triangle_size, step_size):
                # Calculate saturation and value from position
                saturation = x / triangle_size
                value = 1.0 - (y / triangle_size)  # Invert Y so bright colors are at top
                
                # Skip if outside circle
                dx = x - triangle_size // 2
                dy = y - triangle_size // 2
                distance = math.sqrt(dx*dx + dy*dy)
                if distance > triangle_size // 2:
                    continue
                
                color_info = ColorInfo.from_hsv(hue, saturation, value)
                
                try:
                    backend.draw_circle(
                        (start_x + x, start_y + y),
                        step_size // 2,
                        color_info.rgb
                    )
                except Exception as draw_error:
                    logger.debug(f"Failed to draw SB triangle point: {draw_error}")
    
    def _render_center_circle(self, backend: Any) -> None:
        """Render center circle for UI clarity."""
        if hasattr(backend, 'draw_circle'):
            try:
                # Draw white center circle with black border
                backend.draw_circle(
                    (self.center_x, self.center_y),
                    int(self.inner_radius * 0.3),
                    (255, 255, 255)
                )
                backend.draw_circle(
                    (self.center_x, self.center_y),
                    int(self.inner_radius * 0.3),
                    (0, 0, 0),
                    width=2
                )
            except Exception as draw_error:
                logger.debug(f"Failed to draw center circle: {draw_error}")
    
    def _render_color_indicator(self, backend: Any, color: ColorInfo) -> None:
        """Render indicator showing current color selection."""
        try:
            # Draw indicator on hue ring
            hue_angle = math.radians(color.hsv[0])
            hue_x = self.center_x + (self.radius - self.hue_ring_width/2) * math.cos(hue_angle)
            hue_y = self.center_y + (self.radius - self.hue_ring_width/2) * math.sin(hue_angle)
            
            if hasattr(backend, 'draw_circle'):
                # Draw white circle with black border as indicator
                backend.draw_circle((int(hue_x), int(hue_y)), 6, (255, 255, 255))
                backend.draw_circle((int(hue_x), int(hue_y)), 6, (0, 0, 0), width=2)
            
            # Draw indicator in saturation/brightness area
            triangle_size = int(self.inner_radius * 1.4)
            sb_x = self.center_x - triangle_size // 2 + int(color.hsv[1] * triangle_size)
            sb_y = self.center_y - triangle_size // 2 + int((1.0 - color.hsv[2]) * triangle_size)
            
            if hasattr(backend, 'draw_circle'):
                backend.draw_circle((sb_x, sb_y), 4, (255, 255, 255))
                backend.draw_circle((sb_x, sb_y), 4, (0, 0, 0), width=2)
                
        except Exception as draw_error:
            logger.debug(f"Failed to draw color indicator: {draw_error}")
    
    def get_color_at_position(self, x: int, y: int) -> Optional[ColorInfo]:
        """Get color information at screen position."""
        try:
            dx = x - self.center_x
            dy = y - self.center_y
            distance = math.sqrt(dx*dx + dy*dy)
            
            # Check if click is in hue ring
            if (self.radius - self.hue_ring_width) <= distance <= self.radius:
                angle = math.atan2(dy, dx)
                hue = (math.degrees(angle) + 360) % 360
                return ColorInfo.from_hsv(hue, 1.0, 1.0)
            
            # Check if click is in saturation/brightness area
            elif distance <= self.inner_radius:
                triangle_size = int(self.inner_radius * 1.4)
                
                # Convert to triangle coordinates
                local_x = dx + triangle_size // 2
                local_y = dy + triangle_size // 2
                
                if 0 <= local_x <= triangle_size and 0 <= local_y <= triangle_size:
                    saturation = local_x / triangle_size
                    value = 1.0 - (local_y / triangle_size)
                    
                    # Use current hue (would need to be passed in or stored)
                    # For now, default to red hue
                    return ColorInfo.from_hsv(0, saturation, value)
            
            return None
            
        except Exception as error:
            logger.error(f"Failed to get color at position ({x}, {y}): {error}")
            return None


class ColorPickerWidget:
    """
    Interactive color picker widget with event handling.
    
    Combines ColorWheelRenderer with interaction logic and integrates
    with the application's event system.
    """
    
    def __init__(
        self, 
        x: int, 
        y: int, 
        radius: int,
        event_bus: Optional[EventBus] = None,
        on_color_changed: Optional[Callable[[ColorInfo], None]] = None
    ):
        self.x = x
        self.y = y
        self.radius = radius
        self.event_bus = event_bus
        self.on_color_changed = on_color_changed
        
        # Create renderer
        self.renderer = ColorWheelRenderer(x, y, radius)
        
        # Current state
        self.current_color = ColorInfo.from_rgb(255, 255, 255)  # Default to white
        self.is_visible = True
        self.is_dragging = False
        self.drag_mode = None  # 'hue' or 'sb' (saturation/brightness)
        
        # UI state
        self.last_render_time = 0
        self.render_throttle = 1.0 / 30.0  # 30 FPS max
        
        logger.info(f"ColorPickerWidget created at ({x}, {y}) with radius {radius}")
    
    def handle_mouse_event(self, event_type: str, x: int, y: int, button: int = 1) -> bool:
        """Handle mouse interaction events."""
        if not self.is_visible:
            return False
        
        try:
            if event_type == 'MOUSE_DOWN' and button == 1:
                return self._handle_mouse_down(x, y)
            elif event_type == 'MOUSE_UP' and button == 1:
                return self._handle_mouse_up(x, y)
            elif event_type == 'MOUSE_MOVE' and self.is_dragging:
                return self._handle_mouse_drag(x, y)
            
            return False
            
        except Exception as error:
            logger.error(f"Mouse event handling failed: {error}")
            return False
    
    def _handle_mouse_down(self, x: int, y: int) -> bool:
        """Handle mouse down event."""
        dx = x - self.x
        dy = y - self.y
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Check if click is within color wheel area
        if distance <= self.radius:
            color_at_pos = self.renderer.get_color_at_position(x, y)
            
            if color_at_pos:
                self.is_dragging = True
                
                # Determine drag mode based on position
                if (self.radius - self.renderer.hue_ring_width) <= distance <= self.radius:
                    self.drag_mode = 'hue'
                elif distance <= self.renderer.inner_radius:
                    self.drag_mode = 'sb'
                
                self._update_color(color_at_pos)
                return True
        
        return False
    
    def _handle_mouse_up(self, x: int, y: int) -> bool:
        """Handle mouse up event."""
        if self.is_dragging:
            self.is_dragging = False
            self.drag_mode = None
            
            # Publish final color selection event
            if self.event_bus:
                self.event_bus.publish('color_picker_selection_complete', {
                    'color': self.current_color,
                    'widget_id': id(self)
                })
            
            return True
        
        return False
    
    def _handle_mouse_drag(self, x: int, y: int) -> bool:
        """Handle mouse drag event."""
        if not self.is_dragging:
            return False
        
        if self.drag_mode == 'hue':
            # Update hue based on angle
            dx = x - self.x
            dy = y - self.y
            angle = math.atan2(dy, dx)
            hue = (math.degrees(angle) + 360) % 360
            
            new_color = ColorInfo.from_hsv(hue, self.current_color.hsv[1], self.current_color.hsv[2])
            self._update_color(new_color)
            
        elif self.drag_mode == 'sb':
            # Update saturation and brightness
            triangle_size = int(self.renderer.inner_radius * 1.4)
            local_x = (x - self.x) + triangle_size // 2
            local_y = (y - self.y) + triangle_size // 2
            
            if 0 <= local_x <= triangle_size and 0 <= local_y <= triangle_size:
                saturation = max(0, min(1, local_x / triangle_size))
                value = max(0, min(1, 1.0 - (local_y / triangle_size)))
                
                new_color = ColorInfo.from_hsv(self.current_color.hsv[0], saturation, value)
                self._update_color(new_color)
        
        return True
    
    def _update_color(self, new_color: ColorInfo) -> None:
        """Update current color and notify listeners."""
        self.current_color = new_color
        
        # Call callback if provided
        if self.on_color_changed:
            try:
                self.on_color_changed(new_color)
            except Exception as callback_error:
                logger.error(f"Color change callback failed: {callback_error}")
        
        # Publish event
        if self.event_bus:
            self.event_bus.publish('color_picker_changed', {
                'color': new_color,
                'widget_id': id(self)
            })
        
        logger.debug(f"Color updated to RGB{new_color.rgb} HSV{new_color.hsv}")
    
    def render(self, backend: Any) -> None:
        """Render the color picker widget."""
        if not self.is_visible:
            return
        
        # Throttle rendering for performance
        current_time = time.time()
        if current_time - self.last_render_time < self.render_throttle:
            return
        
        try:
            self.renderer.render_color_wheel(backend, self.current_color)
            self.last_render_time = current_time
            
        except Exception as render_error:
            logger.error(f"Color picker rendering failed: {render_error}")
    
    def set_color(self, color: Union[ColorInfo, Tuple[int, int, int]]) -> None:
        """Set the current color programmatically."""
        try:
            if isinstance(color, tuple):
                self.current_color = ColorInfo.from_rgb(*color)
            else:
                self.current_color = color
            
            logger.debug(f"Color set programmatically to RGB{self.current_color.rgb}")
            
        except Exception as error:
            logger.error(f"Failed to set color: {error}")
    
    def get_color(self) -> ColorInfo:
        """Get the current color."""
        return self.current_color
    
    def show(self) -> None:
        """Show the color picker widget."""
        self.is_visible = True
    
    def hide(self) -> None:
        """Hide the color picker widget."""
        self.is_visible = False
        self.is_dragging = False
        self.drag_mode = None


if SERVICES_AVAILABLE:
    class ColorPickerService(UniversalService):
        """
        Service integration for color picker functionality.
        
        Manages color picker widgets and integrates with the drawing system
        and tool management.
        """
        
        def __init__(
            self,
            config: ServiceConfiguration,
            validation_service: Optional[ValidationService] = None,
            event_bus: Optional[EventBus] = None
        ):
            super().__init__(config, validation_service, event_bus)
            
            self.color_pickers: Dict[str, ColorPickerWidget] = {}
            self.active_picker: Optional[str] = None
            self.current_drawing_color = ColorInfo.from_rgb(255, 255, 255)
            
        def _initialize_service(self) -> None:
            """Initialize color picker service."""
            if self.event_bus:
                self.event_bus.subscribe('color_picker_changed', self._handle_color_change)
                self.event_bus.subscribe('color_picker_request', self._handle_picker_request)
                self.event_bus.subscribe('mouse_event', self._handle_mouse_event)
            
            logger.info("ColorPickerService initialized")
        
        def _cleanup_service(self) -> None:
            """Clean up color picker service."""
            self.color_pickers.clear()
            self.active_picker = None
            logger.info("ColorPickerService cleaned up")
        
        def create_color_picker(
            self,
            picker_id: str,
            x: int,
            y: int,
            radius: int = 100
        ) -> ColorPickerWidget:
            """Create a new color picker widget."""
            try:
                picker = ColorPickerWidget(
                    x, y, radius,
                    event_bus=self.event_bus,
                    on_color_changed=self._on_picker_color_changed
                )
                
                self.color_pickers[picker_id] = picker
                logger.info(f"Created color picker '{picker_id}' at ({x}, {y})")
                
                return picker
                
            except Exception as error:
                logger.error(f"Failed to create color picker '{picker_id}': {error}")
                raise
        
        def get_color_picker(self, picker_id: str) -> Optional[ColorPickerWidget]:
            """Get color picker by ID."""
            return self.color_pickers.get(picker_id)
        
        def activate_picker(self, picker_id: str) -> bool:
            """Activate a color picker for interaction."""
            if picker_id in self.color_pickers:
                self.active_picker = picker_id
                self.color_pickers[picker_id].show()
                logger.debug(f"Activated color picker '{picker_id}'")
                return True
            return False
        
        def deactivate_picker(self, picker_id: str) -> bool:
            """Deactivate a color picker."""
            if picker_id in self.color_pickers:
                self.color_pickers[picker_id].hide()
                if self.active_picker == picker_id:
                    self.active_picker = None
                logger.debug(f"Deactivated color picker '{picker_id}'")
                return True
            return False
        
        def render_active_picker(self, backend: Any) -> None:
            """Render the currently active color picker."""
            if self.active_picker and self.active_picker in self.color_pickers:
                self.color_pickers[self.active_picker].render(backend)
        
        def get_current_drawing_color(self) -> ColorInfo:
            """Get the current drawing color."""
            return self.current_drawing_color
        
        def set_drawing_color(self, color: Union[ColorInfo, Tuple[int, int, int]]) -> None:
            """Set the current drawing color."""
            try:
                if isinstance(color, tuple):
                    self.current_drawing_color = ColorInfo.from_rgb(*color)
                else:
                    self.current_drawing_color = color
                
                # Notify drawing system
                if self.event_bus:
                    self.event_bus.publish('drawing_color_changed', {
                        'color': self.current_drawing_color.rgb
                    })
                
                logger.debug(f"Drawing color set to RGB{self.current_drawing_color.rgb}")
                
            except Exception as error:
                logger.error(f"Failed to set drawing color: {error}")
        
        def _handle_color_change(self, data: Dict[str, Any]) -> None:
            """Handle color picker color change events."""
            color_info = data.get('color')
            if color_info:
                self.set_drawing_color(color_info)
        
        def _handle_picker_request(self, data: Dict[str, Any]) -> None:
            """Handle requests to show/hide color picker."""
            action = data.get('action')
            picker_id = data.get('picker_id', 'default')
            
            if action == 'show':
                if picker_id not in self.color_pickers:
                    # Create default picker if it doesn't exist
                    x = data.get('x', 100)
                    y = data.get('y', 100)
                    radius = data.get('radius', 100)
                    self.create_color_picker(picker_id, x, y, radius)
                
                self.activate_picker(picker_id)
            elif action == 'hide':
                self.deactivate_picker(picker_id)
        
        def _handle_mouse_event(self, data: Dict[str, Any]) -> None:
            """Handle mouse events for active color picker."""
            if self.active_picker and self.active_picker in self.color_pickers:
                event_type = data.get('type')
                x = data.get('x', 0)
                y = data.get('y', 0)
                button = data.get('button', 1)
                
                self.color_pickers[self.active_picker].handle_mouse_event(
                    event_type, x, y, button
                )
        
        def _on_picker_color_changed(self, color: ColorInfo) -> None:
            """Callback for when picker color changes."""
            self.set_drawing_color(color)


# Factory functions for easy integration
def create_color_picker_widget(
    x: int, 
    y: int, 
    radius: int = 100,
    event_bus: Optional[EventBus] = None
) -> ColorPickerWidget:
    """Create a color picker widget with standard configuration."""
    return ColorPickerWidget(x, y, radius, event_bus)


def create_color_picker_service(
    validation_service: Optional[ValidationService] = None,
    event_bus: Optional[EventBus] = None
) -> 'ColorPickerService':
    """Create color picker service with standard configuration."""
    if not SERVICES_AVAILABLE:
        raise ImportError("Services framework not available")
    
    config = ServiceConfiguration(
        service_name="color_picker_service",
        debug_mode=False,
        auto_start=True
    )
    
    return ColorPickerService(config, validation_service, event_bus)


# Utility functions for common color operations
def get_complementary_color(color: ColorInfo) -> ColorInfo:
    """Get complementary color (opposite on color wheel)."""
    h, s, v = color.hsv
    comp_hue = (h + 180) % 360
    return ColorInfo.from_hsv(comp_hue, s, v)


def get_triadic_colors(color: ColorInfo) -> List[ColorInfo]:
    """Get triadic color scheme (3 colors equally spaced on wheel)."""
    h, s, v = color.hsv
    return [
        color,
        ColorInfo.from_hsv((h + 120) % 360, s, v),
        ColorInfo.from_hsv((h + 240) % 360, s, v)
    ]


def get_analogous_colors(color: ColorInfo, count: int = 5) -> List[ColorInfo]:
    """Get analogous color scheme (adjacent colors on wheel)."""
    h, s, v = color.hsv
    step = 30  # degrees
    start_hue = h - (count // 2) * step
    
    colors = []
    for i in range(count):
        hue = (start_hue + i * step) % 360
        colors.append(ColorInfo.from_hsv(hue, s, v))
    
    return colors


def blend_colors(color1: ColorInfo, color2: ColorInfo, ratio: float = 0.5) -> ColorInfo:
    """Blend two colors with specified ratio (0.0 = color1, 1.0 = color2)."""
    ratio = max(0.0, min(1.0, ratio))
    
    # Blend in RGB space for simplicity
    r = int(color1.rgb[0] + (color2.rgb[0] - color1.rgb[0]) * ratio)
    g = int(color1.rgb[1] + (color2.rgb[1] - color1.rgb[1]) * ratio)
    b = int(color1.rgb[2] + (color2.rgb[2] - color1.rgb[2]) * ratio)
    
    return ColorInfo.from_rgb(r, g, b)