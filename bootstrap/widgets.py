"""
Widget initialization for proper rendering order and visibility.
"""

import logging
from typing import Any, List, Tuple

logger = logging.getLogger(__name__)

def init_widgets(
    journal_service: Any,
    engine: Any,
    bus: Any,
    clock: Any,
    settings: Any,
    tool_service: Any,
) -> List[Any]:
    """Instantiate UI widgets in CORRECT ORDER with CRITICAL FIXES."""
    
    widgets = []
    logger.info("Initializing widgets...")
    
    # CRITICAL FIX: Grid widget FIRST (background layer)
    try:
        grid_widget = SimpleGridWidget(engine, settings)
        widgets.append(grid_widget)
        logger.info("Grid widget added (background)")
    except Exception as e:
        logger.warning("Failed to create grid widget: %s", e)
    
    # Canvas widget for drawing (middle layer)
    try:
        from ui.drawing_interface import CanvasWidget
        canvas_widget = CanvasWidget(journal_service, engine, bus)
        widgets.append(canvas_widget)
        logger.info("Canvas widget added")
    except Exception as e:
        logger.error("Failed to create canvas widget: %s", e)
    
    # CRITICAL FIX: Hotbar widget (top layer - MUST BE VISIBLE)
    try:
        from ui.hotbar import HotbarWidget
        hotbar_widget = HotbarWidget(tool_service, engine, bus)
        widgets.append(hotbar_widget)
        logger.info("HOTBAR widget added - should be VISIBLE")
    except Exception as e:
        logger.error("CRITICAL: Failed to create hotbar widget: %s", e)
        # Try to create a minimal hotbar as fallback
        try:
            hotbar_widget = MinimalHotbarWidget(tool_service, engine, bus)
            widgets.append(hotbar_widget)
            logger.warning("Created minimal hotbar fallback")
        except Exception as fallback_error:
            logger.error("Even fallback hotbar failed: %s", fallback_error)
    
    # CRITICAL FIX: Remove status bar to eliminate "Time" display
    # Status bar widget is COMMENTED OUT to remove time display
    # try:
    #     from ui.status_bar import StatusBar
    #     status_widget = StatusBar(clock, engine, settings)
    #     widgets.append(status_widget)
    #     logger.info("Status bar widget added")
    # except Exception as e:
    #     logger.error("Failed to create status bar widget: %s", e)
    
    logger.info("Widgets initialized: %s", [type(w).__name__ for w in widgets])
    return widgets


class SimpleGridWidget:
    """Simple grid background renderer that ALWAYS WORKS."""
    
    def __init__(self, engine: Any, settings: Any):
        self.engine = engine
        self.settings = settings
        self.grid_spacing = 40
        self.grid_color = (30, 30, 30)  # Dark gray grid
        logger.info("SimpleGridWidget initialized")
        
    def render(self) -> None:
        """Render a simple grid background."""
        try:
            if not hasattr(self.engine, 'get_size'):
                return
                
            width, height = self.engine.get_size()
            
            # Draw vertical lines
            for x in range(0, width, self.grid_spacing):
                try:
                    self.engine.draw_line((x, 0), (x, height), 1, self.grid_color)
                except Exception:
                    continue
            
            # Draw horizontal lines  
            for y in range(0, height, self.grid_spacing):
                try:
                    self.engine.draw_line((0, y), (width, y), 1, self.grid_color)
                except Exception:
                    continue
                    
        except Exception as e:
            logger.debug("Error rendering simple grid: %s", e)


class MinimalHotbarWidget:
    """Minimal hotbar widget fallback that ALWAYS RENDERS."""
    
    def __init__(self, tool_service: Any, engine: Any, bus: Any):
        self.tool_service = tool_service
        self.engine = engine
        self.bus = bus
        self.brush_width = 5
        self.hover_button = None
        self._mouse_over_hotbar = False
        
        # Simple button definitions
        self.tools = ["brush", "eraser", "line", "rect", "circle"]
        self.button_width = 60
        self.button_height = 30
        self.x = 10
        self.y = 10
        
        logger.warning("MinimalHotbarWidget created as fallback")
    
    def render(self) -> None:
        """Render minimal hotbar that ALWAYS WORKS."""
        try:
            current_tool = getattr(self.tool_service, 'current_tool_mode', 'brush')
            
            x = self.x
            y = self.y
            
            # Draw background
            bg_width = len(self.tools) * (self.button_width + 5) + 100
            for i in range(self.button_height + 10):
                try:
                    self.engine.draw_line(
                        (x - 5, y - 5 + i),
                        (x + bg_width, y - 5 + i),
                        1,
                        (60, 60, 60)
                    )
                except Exception:
                    continue
            
            # Draw tool buttons
            for i, tool in enumerate(self.tools):
                btn_x = x + i * (self.button_width + 5)
                btn_y = y
                
                # Button color
                if tool == current_tool:
                    color = (0, 150, 255)  # Blue for selected
                else:
                    color = (100, 100, 100)  # Gray for unselected
                
                # Draw button background
                for j in range(self.button_height):
                    try:
                        self.engine.draw_line(
                            (btn_x, btn_y + j),
                            (btn_x + self.button_width, btn_y + j),
                            1,
                            color
                        )
                    except Exception:
                        continue
                
                # Draw tool name
                try:
                    self.engine.draw_text(tool[:4], (btn_x + 5, btn_y + 8), 12, (255, 255, 255))
                except Exception:
                    pass
            
            # Draw brush width indicator
            try:
                indicator_x = x + len(self.tools) * (self.button_width + 5) + 10
                self.engine.draw_text(f"Size:{self.brush_width}", (indicator_x, y + 5), 10, (255, 255, 255))
            except Exception:
                pass
                
        except Exception as e:
            logger.error("Error rendering minimal hotbar: %s", e)
    
    def handle_mouse_click(self, pos: Tuple[int, int], button: int) -> bool:
        """Handle mouse clicks."""
        try:
            if button != 1:
                return False
            
            x, y = pos
            
            # Check if click is on any tool button
            for i, tool in enumerate(self.tools):
                btn_x = self.x + i * (self.button_width + 5)
                btn_y = self.y
                
                if (btn_x <= x <= btn_x + self.button_width and 
                    btn_y <= y <= btn_y + self.button_height):
                    self.tool_service.set_mode(tool)
                    logger.info("Tool selected via minimal hotbar: %s", tool)
                    return True
            
            return False
        except Exception as e:
            logger.error("Error in minimal hotbar click: %s", e)
            return False
    
    def handle_mouse_move(self, pos: Tuple[int, int]) -> bool:
        """Handle mouse movement."""
        try:
            x, y = pos
            
            # Check if mouse is over hotbar area
            hotbar_width = len(self.tools) * (self.button_width + 5) + 100
            self._mouse_over_hotbar = (
                self.x - 5 <= x <= self.x + hotbar_width and
                self.y - 5 <= y <= self.y + self.button_height + 5
            )
            
            return self._mouse_over_hotbar
        except Exception:
            return False
    
    def handle_scroll_wheel(self, direction: int, pos: Tuple[int, int]) -> bool:
        """Handle scroll wheel."""
        try:
            current_tool = getattr(self.tool_service, 'current_tool_mode', 'brush')
            if current_tool in ['brush', 'eraser'] and direction != 0:
                if direction > 0:
                    self.brush_width = min(self.brush_width + 2, 50)
                else:
                    self.brush_width = max(self.brush_width - 2, 1)
                
                self.bus.publish('brush_width_changed', self.brush_width)
                return True
            return False
        except Exception:
            return False
    
    def is_mouse_over_hotbar(self) -> bool:
        """Check if mouse is over hotbar."""
        return self._mouse_over_hotbar
    
    def get_current_brush_width(self) -> int:
        """Get current brush width."""
        return self.brush_width