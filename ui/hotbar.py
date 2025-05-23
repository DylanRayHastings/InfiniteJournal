# ui/hotbar.py (Comprehensive fixes for width synchronization and visual feedback)
"""
Enhanced Hotbar Widget with robust real-time width synchronization and comprehensive visual feedback.
"""

import logging
import time
import math
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from core.event_bus import EventBus
from core.interfaces import Renderer
from services.tools import ToolService

logger = logging.getLogger(__name__)

@dataclass
class ToolButton:
    """Represents a tool button in the hotbar with enhanced metadata."""
    key: str
    display_name: str
    icon_text: str
    description: str
    category: str = "drawing"
    hotkey: Optional[str] = None
    
@dataclass
class HotbarConfig:
    """Enhanced configuration for hotbar appearance and behavior."""
    x: int = 10
    y: int = 10
    button_width: int = 80
    button_height: int = 40
    button_spacing: int = 5
    background_color: Tuple[int, int, int] = (40, 40, 40)
    selected_color: Tuple[int, int, int] = (0, 150, 255)
    hover_color: Tuple[int, int, int] = (80, 80, 80)
    text_color: Tuple[int, int, int] = (255, 255, 255)
    border_color: Tuple[int, int, int] = (100, 100, 100)
    # Enhanced visual feedback colors
    active_drawing_color: Tuple[int, int, int] = (255, 100, 0)
    width_indicator_color: Tuple[int, int, int] = (0, 255, 150)
    width_change_color: Tuple[int, int, int] = (255, 200, 0)
    error_color: Tuple[int, int, int] = (255, 50, 50)

class HotbarWidget:
    """
    Enhanced visual hotbar with robust real-time width updates and comprehensive mathematical symbols.
    """
    
    # Enhanced mathematical symbols with hotkeys
    TOOL_DEFINITIONS = [
        ToolButton("brush", "Draw", "~", "Freehand drawing tool", "drawing", "B"),
        ToolButton("eraser", "Erase", "X", "Eraser tool", "drawing", "E"),
        ToolButton("line", "Line", "|", "Draw straight lines", "shapes", "L"),
        ToolButton("rect", "Rect", "□", "Draw rectangles", "shapes", "R"),
        ToolButton("circle", "Circle", "○", "Draw circles", "shapes", "C"),
        ToolButton("triangle", "Triangle", "△", "Draw triangles", "shapes", "T"),
        ToolButton("parabola", "Curve", "⌒", "Draw parabolic curves", "shapes", "P"),
    ]
    
    def __init__(
        self,
        tool_service: ToolService,
        renderer: Renderer,
        bus: EventBus,
        config: Optional[HotbarConfig] = None
    ):
        """
        Initialize the enhanced hotbar widget with robust error handling.
        """
        self.tool_service = tool_service
        self.renderer = renderer
        self.bus = bus
        self.config = config or HotbarConfig()
        
        # Enhanced state management with validation
        self.buttons: Dict[str, ToolButton] = {btn.key: btn for btn in self.TOOL_DEFINITIONS}
        self.button_rects: Dict[str, Tuple[int, int, int, int]] = {}
        self.hover_button: Optional[str] = None
        self.brush_width = 5
        self.brush_width_min = 1
        self.brush_width_max = 50
        self._mouse_over_hotbar = False
        
        # Enhanced width change tracking and animation
        self._width_change_animation = 0.0
        self._last_width_change_time = 0.0
        self._is_drawing_active = False
        self._width_history = []  # Track recent width changes
        self._error_animation = 0.0
        self._last_error_time = 0.0
        
        # Performance and error tracking
        self._stats = {
            'button_clicks': 0,
            'width_changes': 0,
            'render_calls': 0,
            'errors': 0
        }
        
        # Subscribe to enhanced events with error handling
        try:
            bus.subscribe('mode_changed', self._on_mode_changed)
            bus.subscribe('stroke_added', self._on_stroke_activity)
            bus.subscribe('page_cleared', self._on_page_cleared)
            bus.subscribe('brush_width_changed', self._on_external_width_change)
        except Exception as e:
            logger.error("Failed to subscribe to events: %s", e)
            self._stats['errors'] += 1
        
        # Calculate button positions
        self._calculate_button_positions()
        
        # Initialize brush width with validation
        self._validate_and_set_width(self.brush_width)
        
        # Publish initial brush width
        try:
            self.bus.publish('brush_width_changed', self.brush_width)
        except Exception as e:
            logger.error("Failed to publish initial brush width: %s", e)
        
        logger.info("Enhanced HotbarWidget initialized with robust width synchronization")
    
    def _validate_and_set_width(self, width: int) -> int:
        """Validate and set brush width with bounds checking."""
        try:
            validated_width = max(self.brush_width_min, min(width, self.brush_width_max))
            if validated_width != width:
                logger.warning("Brush width %d clamped to %d", width, validated_width)
            return validated_width
        except Exception as e:
            logger.error("Error validating width %d: %s", width, e)
            return self.brush_width_min
    
    def _calculate_button_positions(self) -> None:
        """Calculate bounding rectangles for all buttons with enhanced layout."""
        try:
            self.button_rects.clear()
            x = self.config.x
            y = self.config.y
            
            for btn_key in self.buttons:
                self.button_rects[btn_key] = (
                    x, y, 
                    self.config.button_width, 
                    self.config.button_height
                )
                x += self.config.button_width + self.config.button_spacing
                
            logger.debug("Calculated positions for %d buttons", len(self.button_rects))
        except Exception as e:
            logger.error("Error calculating button positions: %s", e)
            self._stats['errors'] += 1
    
    def _on_mode_changed(self, mode: str) -> None:
        """Handle tool mode changes with enhanced feedback."""
        try:
            logger.debug("Hotbar detected mode change to: %s", mode)
            # Reset drawing activity when mode changes
            self._is_drawing_active = False
        except Exception as e:
            logger.error("Error handling mode change: %s", e)
    
    def _on_stroke_activity(self, _) -> None:
        """Handle stroke activity for visual feedback."""
        try:
            self._is_drawing_active = True
        except Exception as e:
            logger.error("Error handling stroke activity: %s", e)
            
    def _on_page_cleared(self, _) -> None:
        """Handle page clear events."""
        try:
            self._is_drawing_active = False
        except Exception as e:
            logger.error("Error handling page clear: %s", e)
    
    def _on_external_width_change(self, width: int) -> None:
        """Handle external brush width changes for synchronization."""
        try:
            old_width = self.brush_width
            self.brush_width = self._validate_and_set_width(width)
            
            if old_width != self.brush_width:
                self._trigger_width_change_animation()
                self._width_history.append((time.time(), self.brush_width))
                # Keep only recent history
                if len(self._width_history) > 20:
                    self._width_history = self._width_history[-10:]
                logger.debug("External width change synchronized: %d -> %d", old_width, self.brush_width)
        except Exception as e:
            logger.error("Error handling external width change: %s", e)
            self._stats['errors'] += 1
    
    def _trigger_width_change_animation(self):
        """Trigger width change animation."""
        try:
            self._last_width_change_time = time.time()
            self._width_change_animation = 1.0
            self._stats['width_changes'] += 1
        except Exception as e:
            logger.error("Error triggering width animation: %s", e)
    
    def _trigger_error_animation(self):
        """Trigger error animation for invalid operations."""
        try:
            self._last_error_time = time.time()
            self._error_animation = 1.0
            self._stats['errors'] += 1
        except Exception as e:
            logger.error("Error triggering error animation: %s", e)
    
    def handle_mouse_click(self, pos: Tuple[int, int], button: int) -> bool:
        """Handle mouse clicks on hotbar buttons with enhanced feedback."""
        try:
            if button != 1:
                return False
                
            clicked_tool = self._get_button_at_position(pos)
            if clicked_tool:
                try:
                    self.tool_service.set_mode(clicked_tool)
                    self._stats['button_clicks'] += 1
                    logger.info("Tool selected via enhanced hotbar: %s", clicked_tool)
                    return True
                except Exception as e:
                    logger.error("Error setting tool mode %s: %s", clicked_tool, e)
                    self._trigger_error_animation()
                    return False
            return False
        except Exception as e:
            logger.error("Error handling mouse click: %s", e)
            return False
    
    def handle_mouse_move(self, pos: Tuple[int, int]) -> bool:
        """Handle mouse movement for enhanced hover effects."""
        try:
            old_hover = self.hover_button
            self.hover_button = self._get_button_at_position(pos)
            self._mouse_over_hotbar = self.hover_button is not None
            
            # Log hover changes for debugging
            if old_hover != self.hover_button and self.hover_button:
                logger.debug("Hovering over tool: %s", self.hover_button)
                
            return self._mouse_over_hotbar
        except Exception as e:
            logger.error("Error handling mouse move: %s", e)
            return False
    
    def handle_scroll_wheel(self, direction: int, pos: Tuple[int, int]) -> bool:
        """Handle scroll wheel for enhanced brush width adjustment."""
        try:
            current_tool = self.tool_service.current_tool_mode
            if current_tool not in ['brush', 'eraser']:
                return False
                
            old_width = self.brush_width
            
            # Enhanced step size calculation
            if self.brush_width <= 5:
                step_size = 1  # Fine control for small brushes
            elif self.brush_width <= 20:
                step_size = 2  # Medium control
            else:
                step_size = max(2, self.brush_width // 10)  # Adaptive for large brushes
            
            if direction > 0:
                new_width = self.brush_width + step_size
            else:
                new_width = self.brush_width - step_size
            
            # Validate and apply new width
            self.brush_width = self._validate_and_set_width(new_width)
            
            if self.brush_width != old_width:
                self._trigger_width_change_animation()
                
                try:
                    self.bus.publish('brush_width_changed', self.brush_width)
                    logger.info("Enhanced brush width changed via scroll: %d -> %d", old_width, self.brush_width)
                except Exception as e:
                    logger.error("Failed to publish width change: %s", e)
                    # Revert on publish failure
                    self.brush_width = old_width
                    self._trigger_error_animation()
                    
                return True
            else:
                # Width hit bounds - show error feedback
                if (direction > 0 and new_width > self.brush_width_max) or \
                   (direction < 0 and new_width < self.brush_width_min):
                    self._trigger_error_animation()
                    
        except Exception as e:
            logger.error("Error handling scroll wheel: %s", e)
            self._trigger_error_animation()
            
        return False
    
    def _get_button_at_position(self, pos: Tuple[int, int]) -> Optional[str]:
        """Get the button key at the given position, if any."""
        try:
            x, y = pos
            
            for btn_key, (bx, by, bw, bh) in self.button_rects.items():
                if bx <= x <= bx + bw and by <= y <= by + bh:
                    return btn_key
            return None
        except Exception as e:
            logger.error("Error getting button at position %s: %s", pos, e)
            return None
    
    def is_mouse_over_hotbar(self) -> bool:
        """Check if mouse is currently over the hotbar area."""
        return self._mouse_over_hotbar
    
    def render(self) -> None:
        """Render the enhanced hotbar with comprehensive visual feedback."""
        try:
            self._stats['render_calls'] += 1
            
            # Update animation states
            self._update_animations()
            
            self._render_background()
            self._render_buttons()
            self._render_enhanced_brush_width_indicator()
            self._render_tooltips()
            
        except Exception as e:
            logger.error("Error rendering enhanced hotbar: %s", e)
            self._stats['errors'] += 1
    
    def _update_animations(self) -> None:
        """Update animation states for enhanced visual feedback."""
        try:
            current_time = time.time()
            
            # Decay width change animation
            if self._width_change_animation > 0:
                elapsed = current_time - self._last_width_change_time
                self._width_change_animation = max(0, 1.0 - elapsed * 3.0)  # 0.33 second decay
            
            # Decay error animation
            if self._error_animation > 0:
                elapsed = current_time - self._last_error_time
                self._error_animation = max(0, 1.0 - elapsed * 4.0)  # 0.25 second decay
            
            # Reset drawing activity after delay
            if self._is_drawing_active and current_time - self._last_width_change_time > 0.2:
                self._is_drawing_active = False
                
        except Exception as e:
            logger.error("Error updating animations: %s", e)
    
    def _render_background(self) -> None:
        """Render the enhanced hotbar background with dynamic effects."""
        try:
            total_width = (
                len(self.buttons) * self.config.button_width + 
                (len(self.buttons) - 1) * self.config.button_spacing +
                200  # Extra space for enhanced width indicator
            )
            
            # Enhanced background with dynamic effects
            bg_color = list(self.config.background_color)
            
            # Pulse effect during drawing
            if self._is_drawing_active:
                pulse_intensity = int(20 * math.sin(time.time() * 10))
                bg_color = [min(255, c + pulse_intensity) for c in bg_color]
            
            # Error tint
            if self._error_animation > 0:
                error_intensity = int(self._error_animation * 30)
                bg_color[0] = min(255, bg_color[0] + error_intensity)
            
            self._draw_rect(
                self.config.x - 5, 
                self.config.y - 5,
                total_width + 10,
                self.config.button_height + 10,
                tuple(bg_color)
            )
        except Exception as e:
            logger.error("Error rendering background: %s", e)
    
    def _render_buttons(self) -> None:
        """Render all tool buttons with enhanced mathematical symbols and visual feedback."""
        try:
            current_tool = self.tool_service.current_tool_mode
            
            for btn_key, button in self.buttons.items():
                if btn_key not in self.button_rects:
                    continue
                    
                bx, by, bw, bh = self.button_rects[btn_key]
                
                # Enhanced button color determination
                if btn_key == current_tool:
                    if self._is_drawing_active and btn_key in ['brush', 'eraser']:
                        bg_color = self.config.active_drawing_color
                    else:
                        bg_color = self.config.selected_color
                elif btn_key == self.hover_button:
                    bg_color = self.config.hover_color
                else:
                    bg_color = (60, 60, 60)
                
                # Apply error tint if needed
                if self._error_animation > 0 and btn_key == current_tool:
                    error_intensity = int(self._error_animation * 50)
                    bg_color = tuple(min(255, c + error_intensity) if i == 0 else c 
                                   for i, c in enumerate(bg_color))
                
                # Draw button background
                self._draw_rect(bx, by, bw, bh, bg_color)
                
                # Enhanced button border with animation
                border_color = list(self.config.border_color)
                if btn_key == current_tool and self._width_change_animation > 0:
                    # Animated border during width changes
                    animation_intensity = int(self._width_change_animation * 100)
                    border_color[1] = min(255, border_color[1] + animation_intensity)
                
                self._draw_rect_outline(bx, by, bw, bh, tuple(border_color))
                
                # Draw mathematical symbol with enhanced positioning
                icon_x = bx + bw // 2 - 8  # Better centering
                icon_y = by + 6
                text_x = bx + 4
                text_y = by + 26
                
                # Enhanced symbol rendering with animation
                symbol_color = list(self.config.text_color)
                if btn_key == current_tool:
                    if self._width_change_animation > 0:
                        glow_intensity = int(self._width_change_animation * 50)
                        symbol_color = [min(255, c + glow_intensity) for c in symbol_color]
                    else:
                        symbol_color = [255, 255, 255]  # Brighter for selected tool
                
                self.renderer.draw_text(
                    button.icon_text, 
                    (icon_x, icon_y), 
                    20,  # Larger for better visibility
                    tuple(symbol_color)
                )
                
                # Draw tool name
                self.renderer.draw_text(
                    button.display_name, 
                    (text_x, text_y), 
                    10, 
                    tuple(symbol_color)
                )
                
                # Draw hotkey if available
                if button.hotkey:
                    hotkey_x = bx + bw - 15
                    hotkey_y = by + 5
                    self.renderer.draw_text(
                        button.hotkey,
                        (hotkey_x, hotkey_y),
                        8,
                        (180, 180, 180)
                    )
        except Exception as e:
            logger.error("Error rendering buttons: %s", e)
    
    def _render_enhanced_brush_width_indicator(self) -> None:
        """Render enhanced brush width indicator with comprehensive real-time updates."""
        try:
            current_tool = self.tool_service.current_tool_mode
            if current_tool not in ['brush', 'eraser']:
                return
            
            indicator_x = (
                self.config.x + 
                len(self.buttons) * (self.config.button_width + self.config.button_spacing) +
                20
            )
            indicator_y = self.config.y
            
            # Enhanced width text with animation and bounds display
            width_text = f"Size: {self.brush_width}"
            bounds_text = f"({self.brush_width_min}-{self.brush_width_max})"
            
            # Dynamic text color based on state
            text_color = list(self.config.text_color)
            
            if self._width_change_animation > 0:
                # Animated text color during width changes
                animation_intensity = int(self._width_change_animation * 100)
                text_color[1] = min(255, text_color[1] + animation_intensity)
                text_color[2] = min(255, text_color[2] + animation_intensity)
            
            if self._error_animation > 0:
                # Red tint for errors (bounds hit)
                error_intensity = int(self._error_animation * 100)
                text_color[0] = min(255, text_color[0] + error_intensity)
                text_color[1] = max(0, text_color[1] - error_intensity // 2)
                text_color[2] = max(0, text_color[2] - error_intensity // 2)
            
            self.renderer.draw_text(
                width_text,
                (indicator_x, indicator_y + 5),
                12,
                tuple(text_color)
            )
            
            # Enhanced visual width indicator with animation
            circle_x = indicator_x + 70
            circle_y = indicator_y + 20
            
            # Animated circle radius and color
            base_radius = min(max(self.brush_width // 2, 2), 18)
            circle_radius = base_radius
            
            if self._width_change_animation > 0:
                # Pulse effect during width changes
                pulse = int(self._width_change_animation * 4)
                circle_radius = base_radius + pulse
            
            # Enhanced circle color with state indication
            circle_color = list(self.config.width_indicator_color)
            
            if self._is_drawing_active:
                circle_color = list(self.config.active_drawing_color)
            elif self._width_change_animation > 0:
                # Bright highlight during width changes
                intensity = int(self._width_change_animation * 100)
                circle_color = [min(255, c + intensity) for c in circle_color]
            elif self._error_animation > 0:
                # Red indication for errors
                circle_color = list(self.config.error_color)
            
            # Draw the circle with proper bounds checking
            try:
                self.renderer.draw_circle(
                    (circle_x, circle_y),
                    max(1, circle_radius),
                    tuple(circle_color)
                )
            except Exception as e:
                logger.error("Error drawing width indicator circle: %s", e)
            
            # Enhanced scroll hint with dynamic visibility
            hint_color = (150, 150, 150)
            if self._width_change_animation > 0:
                hint_color = (200, 200, 200)
            elif self._error_animation > 0:
                hint_color = (255, 150, 150)
            
            self.renderer.draw_text(
                "Scroll to resize",
                (indicator_x + 10, indicator_y + 35),
                8,
                hint_color
            )
            
            # Bounds indicator
            self.renderer.draw_text(
                bounds_text,
                (indicator_x, indicator_y + 48),
                8,
                (120, 120, 120)
            )
            
            # Width history visualization (mini bars showing recent changes)
            if len(self._width_history) > 1:
                self._render_width_history(indicator_x + 100, indicator_y + 10)
                
        except Exception as e:
            logger.error("Error rendering enhanced brush width indicator: %s", e)
    
    def _render_width_history(self, x: int, y: int) -> None:
        """Render a small visualization of recent width changes."""
        try:
            if len(self._width_history) < 2:
                return
                
            # Take last 10 width changes
            recent_history = self._width_history[-10:]
            bar_width = 2
            bar_spacing = 3
            max_height = 15
            
            # Find min/max for scaling
            widths = [w for _, w in recent_history]
            min_width = min(widths)
            max_width = max(widths)
            width_range = max(1, max_width - min_width)
            
            for i, (timestamp, width) in enumerate(recent_history):
                # Calculate bar height
                if width_range > 0:
                    normalized = (width - min_width) / width_range
                    bar_height = max(1, int(normalized * max_height))
                else:
                    bar_height = max_height // 2
                
                # Age-based alpha (newer = brighter)
                age_factor = (i + 1) / len(recent_history)
                alpha_intensity = int(age_factor * 255)
                
                bar_x = x + i * (bar_width + bar_spacing)
                bar_y = y + max_height - bar_height
                
                # Draw mini bar
                color = (alpha_intensity, alpha_intensity, alpha_intensity)
                for h in range(bar_height):
                    self.renderer.draw_line(
                        (bar_x, bar_y + h),
                        (bar_x + bar_width, bar_y + h),
                        1,
                        color
                    )
                    
        except Exception as e:
            logger.error("Error rendering width history: %s", e)
    
    def _render_tooltips(self) -> None:
        """Render tooltips for hovered buttons."""
        try:
            if not self.hover_button or self.hover_button not in self.buttons:
                return
                
            button = self.buttons[self.hover_button]
            if not hasattr(button, 'description'):
                return
                
            # Get button rect for positioning
            if self.hover_button not in self.button_rects:
                return
                
            bx, by, bw, bh = self.button_rects[self.hover_button]
            
            # Tooltip positioning (below button)
            tooltip_x = bx
            tooltip_y = by + bh + 5
            
            # Render tooltip background
            tooltip_text = button.description
            text_width = len(tooltip_text) * 6  # Rough estimation
            text_height = 12
            
            # Background rect
            self._draw_rect(
                tooltip_x - 2,
                tooltip_y - 2,
                text_width + 4,
                text_height + 4,
                (60, 60, 60)
            )
            
            # Border
            self._draw_rect_outline(
                tooltip_x - 2,
                tooltip_y - 2,
                text_width + 4,
                text_height + 4,
                (120, 120, 120)
            )
            
            # Tooltip text
            self.renderer.draw_text(
                tooltip_text,
                (tooltip_x, tooltip_y),
                10,
                (255, 255, 255)
            )
            
        except Exception as e:
            logger.error("Error rendering tooltips: %s", e)
    
    def _draw_rect(self, x: int, y: int, width: int, height: int, color: Tuple[int, int, int]) -> None:
        """Draw a filled rectangle with enhanced error handling."""
        try:
            # Validate inputs
            if width <= 0 or height <= 0:
                return
                
            for i in range(height):
                self.renderer.draw_line(
                    (x, y + i),
                    (x + width, y + i),
                    1,
                    color
                )
        except Exception as e:
            logger.error("Error drawing rectangle: %s", e)
    
    def _draw_rect_outline(self, x: int, y: int, width: int, height: int, color: Tuple[int, int, int]) -> None:
        """Draw rectangle outline with enhanced border rendering."""
        try:
            # Validate inputs
            if width <= 0 or height <= 0:
                return
                
            # Top
            self.renderer.draw_line((x, y), (x + width, y), 1, color)
            # Bottom
            self.renderer.draw_line((x, y + height), (x + width, y + height), 1, color)
            # Left
            self.renderer.draw_line((x, y), (x, y + height), 1, color)
            # Right
            self.renderer.draw_line((x + width, y), (x + width, y + height), 1, color)
        except Exception as e:
            logger.error("Error drawing rectangle outline: %s", e)

    def get_current_brush_width(self) -> int:
        """Get the current brush width."""
        return self.brush_width
    
    def set_brush_width(self, width: int) -> None:
        """Set brush width with validation and animation trigger."""
        try:
            old_width = self.brush_width
            self.brush_width = self._validate_and_set_width(width)
            
            if old_width != self.brush_width:
                self._trigger_width_change_animation()
                logger.debug("Brush width set to: %d", self.brush_width)
        except Exception as e:
            logger.error("Error setting brush width: %s", e)
            self._trigger_error_animation()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive hotbar statistics."""
        try:
            stats = self._stats.copy()
            stats.update({
                'current_brush_width': self.brush_width,
                'width_min': self.brush_width_min,
                'width_max': self.brush_width_max,
                'current_tool': self.tool_service.current_tool_mode,
                'hover_button': self.hover_button,
                'is_drawing_active': self._is_drawing_active,
                'mouse_over_hotbar': self._mouse_over_hotbar,
                'width_history_length': len(self._width_history),
                'animation_states': {
                    'width_change': self._width_change_animation,
                    'error': self._error_animation
                }
            })
            return stats
        except Exception as e:
            logger.error("Error getting statistics: %s", e)
            return {'error': str(e)}