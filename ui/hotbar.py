"""
Hotbar Widget for visibility and rendering.
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from core.event_bus import EventBus

logger = logging.getLogger(__name__)

@dataclass
class ToolButton:
    """Represents a tool button in the hotbar."""
    key: str
    display_name: str
    icon_text: str
    description: str
    category: str = "drawing"
    
@dataclass
class HotbarConfig:
    """Configuration for hotbar appearance and behavior."""
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


class HotbarWidget:
    """
    Visual hotbar with CRITICAL FIXES for visibility.
    """
    
    # Mathematical symbols for tools
    TOOL_DEFINITIONS = [
        ToolButton("brush", "Draw", "~", "Freehand drawing tool", "drawing"),
        ToolButton("eraser", "Erase", "X", "Eraser tool", "drawing"),
        ToolButton("line", "Line", "|", "Draw straight lines", "shapes"),
        ToolButton("rect", "Rect", "[]", "Draw rectangles", "shapes"),
        ToolButton("circle", "Circle", "O", "Draw circles", "shapes"),
        ToolButton("triangle", "Triangle", "/\\", "Draw triangles", "shapes"),
        ToolButton("parabola", "Curve", "^", "Draw parabolic curves", "shapes"),
    ]
    
    def __init__(
        self,
        tool_service: Any,
        renderer: Any,
        bus: EventBus,
        config: Optional[HotbarConfig] = None
    ):
        """
        Initialize the hotbar widget with CRITICAL FIXES.
        """
        logger.info("Initializing HotbarWidget...")
        
        self.tool_service = tool_service
        self.renderer = renderer
        self.bus = bus
        self.config = config or HotbarConfig()
        
        # State
        self.buttons: Dict[str, ToolButton] = {btn.key: btn for btn in self.TOOL_DEFINITIONS}
        self.button_rects: Dict[str, Tuple[int, int, int, int]] = {}
        self.hover_button: Optional[str] = None
        self.brush_width = 5
        self.brush_width_min = 1
        self.brush_width_max = 50
        self._mouse_over_hotbar = False
        
        # Subscribe to events
        try:
            bus.subscribe('mode_changed', self._on_mode_changed)
            logger.info("Subscribed to mode_changed events")
        except Exception as e:
            logger.error("Failed to subscribe to events: %s", e)
        
        # Calculate button positions
        self._calculate_button_positions()
        
        # Initialize brush width
        try:
            self.bus.publish('brush_width_changed', self.brush_width)
        except Exception as e:
            logger.error("Failed to publish initial brush width: %s", e)
        
        logger.info("HotbarWidget initialized successfully")
    
    def _calculate_button_positions(self) -> None:
        """Calculate bounding rectangles for all buttons."""
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
    
    def _on_mode_changed(self, mode: str) -> None:
        """Handle tool mode changes."""
        logger.debug("Hotbar mode changed to: %s", mode)
    
    def handle_mouse_click(self, pos: Tuple[int, int], button: int) -> bool:
        """Handle mouse clicks on hotbar buttons."""
        try:
            if button != 1:
                return False
                
            clicked_tool = self._get_button_at_position(pos)
            if clicked_tool:
                self.tool_service.set_mode(clicked_tool)
                logger.info("Tool selected via hotbar: %s", clicked_tool)
                return True
            return False
        except Exception as e:
            logger.error("Error handling mouse click: %s", e)
            return False
    
    def handle_mouse_move(self, pos: Tuple[int, int]) -> bool:
        """Handle mouse movement for hover effects."""
        try:
            self.hover_button = self._get_button_at_position(pos)
            self._mouse_over_hotbar = self.hover_button is not None
            return self._mouse_over_hotbar
        except Exception as e:
            logger.error("Error handling mouse move: %s", e)
            return False
    
    def handle_scroll_wheel(self, direction: int, pos: Tuple[int, int]) -> bool:
        """Handle scroll wheel for brush width adjustment."""
        try:
            current_tool = self.tool_service.current_tool_mode
            if current_tool in ['brush', 'eraser']:
                old_width = self.brush_width
                
                if direction > 0:
                    self.brush_width = min(self.brush_width + 2, self.brush_width_max)
                else:
                    self.brush_width = max(self.brush_width - 2, self.brush_width_min)
                
                if self.brush_width != old_width:
                    self.bus.publish('brush_width_changed', self.brush_width)
                    logger.info("Brush width changed via scroll to: %d", self.brush_width)
                return True
            return False
        except Exception as e:
            logger.error("Error handling scroll wheel: %s", e)
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
            logger.debug("Error getting button at position: %s", e)
            return None
    
    def is_mouse_over_hotbar(self) -> bool:
        """Check if mouse is currently over the hotbar area."""
        return self._mouse_over_hotbar
    
    def render(self) -> None:
        """CRITICAL FIX: Render the hotbar with forced visibility."""
        try:
            logger.debug("Rendering hotbar...")
            
            # CRITICAL FIX: Always render background first
            self._render_background()
            
            # CRITICAL FIX: Always render buttons
            self._render_buttons()
            
            # CRITICAL FIX: Always render brush width indicator
            self._render_brush_width_indicator()
            
            logger.debug("Hotbar rendered successfully")
            
        except Exception as e:
            logger.error("CRITICAL ERROR rendering hotbar: %s", e)
    
    def _render_background(self) -> None:
        """Render the hotbar background."""
        try:
            total_width = (
                len(self.buttons) * self.config.button_width + 
                (len(self.buttons) - 1) * self.config.button_spacing +
                140
            )
            
            # CRITICAL FIX: Draw thick background for visibility
            for i in range(self.config.button_height + 10):
                try:
                    self._safe_draw_line(
                        (self.config.x - 5, self.config.y - 5 + i),
                        (self.config.x + total_width + 5, self.config.y - 5 + i),
                        1,
                        self.config.background_color
                    )
                except Exception:
                    continue
                    
        except Exception as e:
            logger.error("Error rendering hotbar background: %s", e)
    
    def _render_buttons(self) -> None:
        """Render all tool buttons."""
        try:
            current_tool = getattr(self.tool_service, 'current_tool_mode', 'brush')
            
            for btn_key, button in self.buttons.items():
                try:
                    if btn_key not in self.button_rects:
                        continue
                        
                    bx, by, bw, bh = self.button_rects[btn_key]
                    
                    # Determine button color
                    if btn_key == current_tool:
                        bg_color = self.config.selected_color
                    elif btn_key == self.hover_button:
                        bg_color = self.config.hover_color
                    else:
                        bg_color = (80, 80, 80)  # Darker gray for visibility
                    
                    # CRITICAL FIX: Draw filled button background
                    for i in range(bh):
                        try:
                            self._safe_draw_line(
                                (bx, by + i),
                                (bx + bw, by + i),
                                1,
                                bg_color
                            )
                        except Exception:
                            continue
                    
                    # Draw button border
                    self._draw_rect_outline(bx, by, bw, bh, self.config.border_color)
                    
                    # Draw mathematical symbol (centered)
                    icon_x = bx + bw // 2 - 6
                    icon_y = by + 8
                    text_x = bx + 5
                    text_y = by + 25
                    
                    # Draw symbol and text
                    self._safe_draw_text(button.icon_text, (icon_x, icon_y), 18, self.config.text_color)
                    self._safe_draw_text(button.display_name, (text_x, text_y), 10, self.config.text_color)
                    
                except Exception as e:
                    logger.warning("Error rendering button %s: %s", btn_key, e)
                    continue
                    
        except Exception as e:
            logger.error("Error rendering hotbar buttons: %s", e)
    
    def _render_brush_width_indicator(self) -> None:
        """Render brush width indicator for drawing tools."""
        try:
            current_tool = getattr(self.tool_service, 'current_tool_mode', 'brush')
            if current_tool not in ['brush', 'eraser']:
                return
            
            indicator_x = (
                self.config.x + 
                len(self.buttons) * (self.config.button_width + self.config.button_spacing) +
                20
            )
            indicator_y = self.config.y
            
            # Draw width text
            width_text = f"Size: {self.brush_width}"
            self._safe_draw_text(width_text, (indicator_x, indicator_y + 5), 12, self.config.text_color)
            
            # Draw visual width indicator (circle)
            circle_x = indicator_x + 30
            circle_y = indicator_y + 20
            circle_radius = min(max(self.brush_width // 2, 2), 15)
            
            self._safe_draw_circle((circle_x, circle_y), circle_radius, self.config.text_color)
            
            # Draw scroll hint
            self._safe_draw_text("Scroll", (indicator_x, indicator_y + 30), 8, (200, 200, 200))
            
        except Exception as e:
            logger.error("Error rendering brush width indicator: %s", e)
    
    def _draw_rect_outline(self, x: int, y: int, width: int, height: int, color: Tuple[int, int, int]) -> None:
        """Draw rectangle outline."""
        try:
            # Top
            self._safe_draw_line((x, y), (x + width, y), 1, color)
            # Bottom
            self._safe_draw_line((x, y + height), (x + width, y + height), 1, color)
            # Left
            self._safe_draw_line((x, y), (x, y + height), 1, color)
            # Right
            self._safe_draw_line((x + width, y), (x + width, y + height), 1, color)
        except Exception as e:
            logger.debug("Error drawing rectangle outline: %s", e)
    
    def _safe_draw_line(self, start: Tuple[int, int], end: Tuple[int, int], width: int, color: Tuple[int, int, int]) -> None:
        """Safely draw a line."""
        try:
            if hasattr(self.renderer, 'draw_line'):
                self.renderer.draw_line(start, end, width, color)
        except Exception as e:
            logger.debug("Error drawing line: %s", e)
    
    def _safe_draw_text(self, text: str, pos: Tuple[int, int], size: int, color: Tuple[int, int, int]) -> None:
        """Safely draw text."""
        try:
            if hasattr(self.renderer, 'draw_text'):
                safe_text = str(text)[:50]
                safe_pos = (max(0, int(pos[0])), max(0, int(pos[1])))
                safe_size = max(8, min(72, int(size)))
                self.renderer.draw_text(safe_text, safe_pos, safe_size, color)
        except Exception as e:
            logger.debug("Error drawing text '%s': %s", text, e)
    
    def _safe_draw_circle(self, center: Tuple[int, int], radius: int, color: Tuple[int, int, int]) -> None:
        """Safely draw a circle."""
        try:
            if hasattr(self.renderer, 'draw_circle'):
                safe_center = (max(0, int(center[0])), max(0, int(center[1])))
                safe_radius = max(1, min(100, int(radius)))
                self.renderer.draw_circle(safe_center, safe_radius, color)
        except Exception as e:
            logger.debug("Error drawing circle: %s", e)

    def get_current_brush_width(self) -> int:
        """Get the current brush width."""
        return self.brush_width