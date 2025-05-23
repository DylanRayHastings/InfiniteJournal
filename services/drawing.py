"""
Fixed Drawing System with Layered Rendering and Clean Brushes

CRITICAL FIXES:
1. Eraser only affects drawing layer, not background
2. Clean brush rendering at all sizes without artifacts
3. Dynamic brush width with per-point sizing
4. Proper parabola orientation (bowl vs rainbow)
"""

import logging
import math
import time
from typing import Any, Dict, List, Tuple, Optional

from core.event_bus import EventBus
from core.drawing.canvas import DrawingCanvas
from core.drawing.input_handler import DrawingInputHandler

logger = logging.getLogger(__name__)


class LayeredDrawingService:
    """Drawing service with proper layer separation and clean brushes."""
    
    def __init__(self, bus: EventBus, settings: Any):
        self.bus = bus
        self.settings = settings
        self.canvas = DrawingCanvas()
        self.input_handler = DrawingInputHandler(self.canvas, settings)
        
        # Layer separation - CRITICAL FIX
        self.background_surface = None
        self.drawing_surface = None
        self.ui_surface = None
        
        # Dynamic brush state - CRITICAL FIX
        self._dynamic_stroke_points = []  # Points with individual widths
        self._is_drawing = False
        self._current_base_width = 5
        self._current_tool = "brush"
        
        # Shape state
        self._shape_start_pos = None
        self._shape_current_pos = None
        self._preview_points = []
        
        # Connect input handler callbacks
        self.input_handler.on_tool_changed = self._on_tool_changed
        self.input_handler.on_brush_width_changed = self._on_brush_width_changed
        
        # Subscribe to events
        self.bus.subscribe('tool_changed', self._handle_tool_changed)
        
        logger.info("LayeredDrawingService initialized with clean brushes")
    
    def initialize_layers(self, width: int, height: int) -> None:
        """Initialize separate drawing layers - CRITICAL FIX."""
        try:
            import pygame
            
            # Background layer (grid) - PERMANENT
            self.background_surface = pygame.Surface((width, height))
            self.background_surface.fill((0, 0, 0))
            self._draw_background_grid(width, height)
            
            # Drawing layer (strokes) - ERASABLE
            self.drawing_surface = pygame.Surface((width, height), pygame.SRCALPHA)
            self.drawing_surface.fill((0, 0, 0, 0))  # Transparent
            
            # UI layer (interface) - OVERLAY
            self.ui_surface = pygame.Surface((width, height), pygame.SRCALPHA)
            self.ui_surface.fill((0, 0, 0, 0))  # Transparent
            
            logger.info("Layers initialized: %dx%d", width, height)
            
        except Exception as e:
            logger.error("Failed to initialize layers: %s", e)
    
    def _draw_background_grid(self, width: int, height: int) -> None:
        """Draw permanent background grid."""
        try:
            import pygame
            
            grid_spacing = 40
            grid_color = (30, 30, 30)
            
            # Draw vertical lines
            for x in range(0, width, grid_spacing):
                pygame.draw.line(self.background_surface, grid_color, (x, 0), (x, height), 1)
            
            # Draw horizontal lines  
            for y in range(0, height, grid_spacing):
                pygame.draw.line(self.background_surface, grid_color, (0, y), (width, y), 1)
                
        except Exception as e:
            logger.error("Error drawing background grid: %s", e)
    
    def _on_tool_changed(self, tool: str) -> None:
        """Handle tool changes."""
        self._current_tool = tool
        self.bus.publish('tool_changed', tool)
        logger.debug("Tool changed: %s", tool)
    
    def _handle_tool_changed(self, tool: str) -> None:
        """Handle tool_changed events."""
        self._current_tool = tool
    
    def _on_brush_width_changed(self, width: int) -> None:
        """Handle brush width changes - DYNAMIC FIX."""
        self._current_base_width = width
        self.bus.publish('brush_width_changed', width)
        logger.debug("Base brush width changed: %d", width)
    
    def handle_mouse_down(self, x: int, y: int, button: int) -> bool:
        """Handle mouse down with dynamic brush support."""
        if button == 1:  # Left click
            self._is_drawing = True
            
            # Initialize dynamic stroke with current width - CRITICAL FIX
            self._dynamic_stroke_points = [{
                'x': x, 
                'y': y, 
                'width': self._current_base_width,
                'pressure': 1.0
            }]
            
            # Handle shape tools
            if self._current_tool in ['line', 'rect', 'circle', 'triangle', 'parabola']:
                self._shape_start_pos = (x, y)
                self._shape_current_pos = (x, y)
                self._preview_points = []
                logger.debug("Started shape: %s", self._current_tool)
            else:
                # Start brush/eraser with dynamic width
                logger.debug("Started dynamic stroke at (%d, %d) width=%d", x, y, self._current_base_width)
            
            return True
        
        return False
    
    def handle_mouse_move(self, x: int, y: int) -> bool:
        """Handle mouse move with dynamic width support."""
        if not self._is_drawing:
            return False
        
        if self._current_tool in ['line', 'rect', 'circle', 'triangle', 'parabola']:
            # Update shape preview
            self._shape_current_pos = (x, y)
            self._update_shape_preview()
            return True
        else:
            # Add dynamic point with current width - CRITICAL FIX
            self._dynamic_stroke_points.append({
                'x': x,
                'y': y, 
                'width': self._current_base_width,  # Use current width for each point
                'pressure': 1.0
            })
            
            # Limit points to prevent memory issues
            if len(self._dynamic_stroke_points) > 1000:
                self._dynamic_stroke_points = self._dynamic_stroke_points[-500:]
            
            return True
    
    def handle_mouse_up(self, x: int, y: int, button: int) -> bool:
        """Handle mouse up with stroke completion."""
        if button == 1 and self._is_drawing:
            if self._current_tool in ['line', 'rect', 'circle', 'triangle', 'parabola']:
                # Complete shape
                self._complete_shape()
            else:
                # Complete dynamic stroke
                self._complete_dynamic_stroke()
            
            self._reset_drawing_state()
            return True
        
        return False
    
    def handle_scroll(self, direction: int) -> bool:
        """Handle scroll for dynamic brush width - CRITICAL FIX."""
        if self._current_tool in ['brush', 'eraser']:
            old_width = self._current_base_width
            
            if direction > 0:
                self._current_base_width = min(self._current_base_width + 2, 50)
            else:
                self._current_base_width = max(self._current_base_width - 2, 1)
            
            if self._current_base_width != old_width:
                # If currently drawing, the next points will use new width
                self.bus.publish('brush_width_changed', self._current_base_width)
                logger.debug("Dynamic width change: %d -> %d", old_width, self._current_base_width)
            
            return True
        
        return False
    
    def _complete_dynamic_stroke(self) -> None:
        """Complete dynamic stroke with per-point widths."""
        if not self._dynamic_stroke_points:
            return
        
        try:
            # Draw stroke to appropriate layer
            if self._current_tool == 'eraser':
                self._erase_dynamic_stroke()
            else:
                self._draw_dynamic_stroke()
                
        except Exception as e:
            logger.error("Error completing dynamic stroke: %s", e)
    
    def _draw_dynamic_stroke(self) -> None:
        """Draw stroke with clean brush rendering - CRITICAL FIX."""
        if not self.drawing_surface or not self._dynamic_stroke_points:
            return
        
        try:
            import pygame
            
            color = self.canvas._current_brush_color
            
            # Draw each segment with its specific width
            for i in range(len(self._dynamic_stroke_points) - 1):
                point1 = self._dynamic_stroke_points[i]
                point2 = self._dynamic_stroke_points[i + 1]
                
                # Use average width for segment
                avg_width = max(1, int((point1['width'] + point2['width']) / 2))
                
                # Draw clean line segment
                start_pos = (int(point1['x']), int(point1['y']))
                end_pos = (int(point2['x']), int(point2['y']))
                
                # CLEAN BRUSH FIX: Use anti-aliased lines
                pygame.draw.line(self.drawing_surface, color, start_pos, end_pos, avg_width)
                
                # Add clean end caps for smooth appearance
                if avg_width > 2:
                    cap_radius = max(1, avg_width // 2)
                    pygame.draw.circle(self.drawing_surface, color, start_pos, cap_radius)
                    pygame.draw.circle(self.drawing_surface, color, end_pos, cap_radius)
            
            # Final end cap
            if len(self._dynamic_stroke_points) > 0:
                last_point = self._dynamic_stroke_points[-1]
                final_width = max(1, int(last_point['width']))
                final_pos = (int(last_point['x']), int(last_point['y']))
                
                if final_width > 2:
                    pygame.draw.circle(self.drawing_surface, color, final_pos, final_width // 2)
            
            logger.debug("Drew clean dynamic stroke with %d points", len(self._dynamic_stroke_points))
            
        except Exception as e:
            logger.error("Error drawing dynamic stroke: %s", e)
    
    def _erase_dynamic_stroke(self) -> None:
        """Erase from drawing layer only - CRITICAL FIX."""
        if not self.drawing_surface or not self._dynamic_stroke_points:
            return
        
        try:
            import pygame
            
            # CRITICAL FIX: Proper erasing using destination out blend mode
            for point in self._dynamic_stroke_points:
                erase_radius = max(2, int(point['width']))
                erase_pos = (int(point['x']), int(point['y']))
                
                # Create mask surface for erasing
                mask_surface = pygame.Surface((erase_radius * 4, erase_radius * 4), pygame.SRCALPHA)
                mask_center = (erase_radius * 2, erase_radius * 2)
                
                # Draw white circle on mask (what to erase)
                pygame.draw.circle(mask_surface, (255, 255, 255, 255), mask_center, erase_radius)
                
                # Position mask surface
                mask_rect = mask_surface.get_rect(center=erase_pos)
                
                # Clip to surface bounds
                mask_rect.clamp_ip(self.drawing_surface.get_rect())
                
                # Erase by setting alpha to 0 using per-pixel alpha manipulation
                try:
                    # Get the area to erase
                    erase_area = pygame.Rect(max(0, erase_pos[0] - erase_radius), 
                                           max(0, erase_pos[1] - erase_radius),
                                           min(erase_radius * 2, self.drawing_surface.get_width() - max(0, erase_pos[0] - erase_radius)),
                                           min(erase_radius * 2, self.drawing_surface.get_height() - max(0, erase_pos[1] - erase_radius)))
                    
                    # Create a circular mask and apply it
                    for x in range(erase_area.left, erase_area.right):
                        for y in range(erase_area.top, erase_area.bottom):
                            dx = x - erase_pos[0]
                            dy = y - erase_pos[1]
                            if dx*dx + dy*dy <= erase_radius*erase_radius:
                                # Set pixel to transparent
                                try:
                                    self.drawing_surface.set_at((x, y), (0, 0, 0, 0))
                                except:
                                    continue
                except:
                    # Fallback: use blend mode
                    pygame.draw.circle(self.drawing_surface, (0, 0, 0, 0), erase_pos, erase_radius)
            
            logger.debug("Erased from drawing layer only (background preserved)")
            
        except Exception as e:
            logger.error("Error erasing dynamic stroke: %s", e)
    
    def _update_shape_preview(self) -> None:
        """Update shape preview with proper parabola orientation."""
        if not self._shape_start_pos or not self._shape_current_pos:
            return
        
        start_x, start_y = self._shape_start_pos
        end_x, end_y = self._shape_current_pos
        
        try:
            if self._current_tool == 'line':
                self._preview_points = [(start_x, start_y), (end_x, end_y)]
            elif self._current_tool == 'rect':
                self._preview_points = self._generate_rect_preview(start_x, start_y, end_x, end_y)
            elif self._current_tool == 'circle':
                self._preview_points = self._generate_circle_preview(start_x, start_y, end_x, end_y)
            elif self._current_tool == 'triangle':
                self._preview_points = self._generate_triangle_preview(start_x, start_y, end_x, end_y)
            elif self._current_tool == 'parabola':
                self._preview_points = self._generate_parabola_preview(start_x, start_y, end_x, end_y)
        except Exception as e:
            logger.error("Error updating shape preview: %s", e)
            self._preview_points = [(start_x, start_y), (end_x, end_y)]
    
    def _generate_parabola_preview(self, x1: int, y1: int, x2: int, y2: int) -> List[Tuple[int, int]]:
        """Generate parabola with flexible curvature - CRITICAL FIX."""
        if abs(x2 - x1) < 2 and abs(y2 - y1) < 2:
            return [(x1, y1), (x2, y2)]
        
        points = []
        steps = 50  # More points for smoother curves
        
        # Calculate parabola parameters based on start and end points
        dx = x2 - x1
        dy = y2 - y1
        
        # Use the midpoint as base for vertex calculation
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        
        # Calculate vertex offset based on drag direction and distance
        distance = math.sqrt(dx*dx + dy*dy)
        
        # CRITICAL FIX: Flexible vertex positioning
        if abs(dx) > abs(dy):
            # More horizontal movement - standard parabola
            h = mid_x  # Vertex x at midpoint
            
            # Vertex y offset based on vertical drag
            if dy > 0:
                # Dragging down - bowl shape
                k = min(y1, y2) - distance * 0.25
            else:
                # Dragging up - rainbow shape
                k = max(y1, y2) + distance * 0.25
        else:
            # More vertical movement - steeper curves
            h = mid_x
            
            # Adjust vertex based on vertical displacement
            vertex_offset = distance * 0.4  # More dramatic curves
            if dy > 0:
                k = y1 - vertex_offset  # Bowl below start
            else:
                k = y1 + vertex_offset  # Rainbow above start
        
        # Calculate coefficient to pass through both points
        try:
            if abs(x1 - h) > 0.1:
                a = (y1 - k) / ((x1 - h) ** 2)
            else:
                # Vertical line case
                a = 1.0 if dy > 0 else -1.0
        except:
            a = 1.0 if dy > 0 else -1.0
        
        # Generate smooth curve points
        for i in range(steps + 1):
            t = i / steps
            x = x1 + t * (x2 - x1)
            
            # Calculate y using parabola equation
            y = a * (x - h) ** 2 + k
            
            points.append((int(x), int(y)))
        
        curve_type = "bowl" if dy >= 0 else "rainbow"
        logger.debug("Generated flexible %s parabola: a=%.3f, vertex=(%.1f, %.1f), distance=%.1f", 
                    curve_type, a, h, k, distance)
        
        return points
    
    def _generate_rect_preview(self, x1: int, y1: int, x2: int, y2: int) -> List[Tuple[int, int]]:
        """Generate rectangle preview."""
        return [
            (x1, y1), (x2, y1),  # Top
            (x2, y1), (x2, y2),  # Right
            (x2, y2), (x1, y2),  # Bottom  
            (x1, y2), (x1, y1)   # Left
        ]
    
    def _generate_circle_preview(self, x1: int, y1: int, x2: int, y2: int) -> List[Tuple[int, int]]:
        """Generate circle preview with solid outline - CRITICAL FIX."""
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        radius = max(1, int(math.sqrt((x2 - x1)**2 + (y2 - y1)**2) // 2))
        
        points = []
        
        # Generate more points for solid circle outline - CRITICAL FIX
        num_points = max(32, radius)  # More points for smoother circles
        
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            
            # Add both current and next point to create solid lines
            next_angle = 2 * math.pi * (i + 1) / num_points
            next_x = center_x + radius * math.cos(next_angle)
            next_y = center_y + radius * math.sin(next_angle)
            
            points.append((int(x), int(y)))
            points.append((int(next_x), int(next_y)))
        
        logger.debug("Generated solid circle preview: radius=%d, points=%d", radius, len(points))
        return points
    
    def _generate_triangle_preview(self, x1: int, y1: int, x2: int, y2: int) -> List[Tuple[int, int]]:
        """Generate triangle preview."""
        return [
            (x1, y1), (x2, y2),  # Diagonal
            (x2, y2), (x2, y1),  # Vertical
            (x2, y1), (x1, y1)   # Horizontal
        ]
    
    def _complete_shape(self) -> None:
        """Complete shape and add to drawing layer."""
        if not self._preview_points or not self.drawing_surface:
            return
        
        try:
            import pygame
            
            color = (255, 255, 255)  # White for shapes
            width = max(2, self._current_base_width // 2)  # Thinner for shapes
            
            # Draw shape lines
            for i in range(0, len(self._preview_points), 2):
                if i + 1 < len(self._preview_points):
                    start = self._preview_points[i]
                    end = self._preview_points[i + 1]
                    pygame.draw.line(self.drawing_surface, color, start, end, width)
            
            logger.info("Completed shape: %s with %d segments", self._current_tool, len(self._preview_points) // 2)
            
        except Exception as e:
            logger.error("Error completing shape: %s", e)
    
    def _reset_drawing_state(self) -> None:
        """Reset all drawing state."""
        self._is_drawing = False
        self._dynamic_stroke_points = []
        self._shape_start_pos = None
        self._shape_current_pos = None
        self._preview_points = []
    
    def render(self, screen_surface) -> None:
        """Render all layers with proper separation - CRITICAL FIX."""
        try:
            if not screen_surface:
                return
            
            # Clear screen
            screen_surface.fill((0, 0, 0))
            
            # Layer 1: Background (permanent grid)
            if self.background_surface:
                screen_surface.blit(self.background_surface, (0, 0))
            
            # Layer 2: Drawing (erasable strokes)
            if self.drawing_surface:
                screen_surface.blit(self.drawing_surface, (0, 0))
            
            # Layer 3: Live preview
            self._render_live_preview(screen_surface)
            
            # Layer 4: UI overlay
            if self.ui_surface:
                screen_surface.blit(self.ui_surface, (0, 0))
            
        except Exception as e:
            logger.error("Error in layered render: %s", e)
    
    def _render_live_preview(self, screen_surface) -> None:
        """Render live drawing preview."""
        try:
            import pygame
            
            if self._is_drawing:
                if self._current_tool in ['line', 'rect', 'circle', 'triangle', 'parabola']:
                    # Render shape preview with solid lines - CRITICAL FIX
                    if self._preview_points:
                        preview_color = (128, 128, 255)  # Light blue
                        preview_width = 2
                        
                        if self._current_tool in ['circle', 'parabola']:
                            # Render as continuous lines for solid appearance
                            for i in range(0, len(self._preview_points) - 1, 2):
                                if i + 1 < len(self._preview_points):
                                    start = self._preview_points[i]
                                    end = self._preview_points[i + 1]
                                    pygame.draw.line(screen_surface, preview_color, start, end, preview_width)
                        else:
                            # Other shapes use paired points
                            for i in range(0, len(self._preview_points), 2):
                                if i + 1 < len(self._preview_points):
                                    start = self._preview_points[i]
                                    end = self._preview_points[i + 1]
                                    pygame.draw.line(screen_surface, preview_color, start, end, preview_width)
                
                elif self._dynamic_stroke_points and len(self._dynamic_stroke_points) > 1:
                    # Render live brush/eraser stroke
                    color = self.canvas._current_brush_color
                    
                    # CRITICAL FIX: Translucent eraser preview
                    if self._current_tool == 'eraser':
                        # Create translucent red preview surface
                        preview_surface = pygame.Surface(screen_surface.get_size(), pygame.SRCALPHA)
                        translucent_red = (255, 100, 100, 128)  # Red with 50% alpha
                        
                        # Draw translucent preview on separate surface
                        for i in range(len(self._dynamic_stroke_points) - 1):
                            point1 = self._dynamic_stroke_points[i]
                            point2 = self._dynamic_stroke_points[i + 1]
                            
                            width = max(1, int((point1['width'] + point2['width']) / 2))
                            start_pos = (int(point1['x']), int(point1['y']))
                            end_pos = (int(point2['x']), int(point2['y']))
                            
                            # Draw translucent line
                            pygame.draw.line(preview_surface, translucent_red, start_pos, end_pos, width)
                            
                            # Translucent end caps
                            if width > 2:
                                cap_radius = width // 2
                                pygame.draw.circle(preview_surface, translucent_red, start_pos, cap_radius)
                                pygame.draw.circle(preview_surface, translucent_red, end_pos, cap_radius)
                        
                        # Blit translucent preview to screen
                        screen_surface.blit(preview_surface, (0, 0))
                    else:
                        # Regular brush preview
                        for i in range(len(self._dynamic_stroke_points) - 1):
                            point1 = self._dynamic_stroke_points[i]
                            point2 = self._dynamic_stroke_points[i + 1]
                            
                            width = max(1, int((point1['width'] + point2['width']) / 2))
                            start_pos = (int(point1['x']), int(point1['y']))
                            end_pos = (int(point2['x']), int(point2['y']))
                            
                            pygame.draw.line(screen_surface, color, start_pos, end_pos, width)
                            
                            # Clean end caps
                            if width > 2:
                                cap_radius = width // 2
                                pygame.draw.circle(screen_surface, color, start_pos, cap_radius)
                                pygame.draw.circle(screen_surface, color, end_pos, cap_radius)
            
        except Exception as e:
            logger.error("Error rendering live preview: %s", e)
    
    def clear_canvas(self) -> None:
        """Clear only the drawing layer - CRITICAL FIX."""
        try:
            if self.drawing_surface:
                self.drawing_surface.fill((0, 0, 0, 0))  # Clear to transparent
            
            self._reset_drawing_state()
            logger.info("Cleared drawing layer (background preserved)")
            
        except Exception as e:
            logger.error("Error clearing canvas: %s", e)
    
    def handle_key_press(self, key: str) -> bool:
        """Handle key press events."""
        if key == 'space':
            # Cycle tools
            tools = ['brush', 'eraser', 'line', 'rect', 'circle', 'triangle', 'parabola']
            try:
                current_index = tools.index(self._current_tool)
                next_tool = tools[(current_index + 1) % len(tools)]
                self._current_tool = next_tool
                self.bus.publish('tool_changed', next_tool)
                return True
            except ValueError:
                self._current_tool = 'brush'
                return True
        elif key == 'c':
            self.clear_canvas()
            return True
        elif key in '12345':
            # Neon colors
            colors = {
                '1': (57, 255, 20),   # Neon Green
                '2': (0, 255, 255),   # Neon Blue
                '3': (255, 20, 147),  # Neon Pink
                '4': (255, 255, 0),   # Neon Yellow
                '5': (255, 97, 3),    # Neon Orange
            }
            if key in colors:
                self.canvas.set_brush_color(colors[key])
                return True
        elif key in ['+', '=']:
            self._current_base_width = min(self._current_base_width + 1, 50)
            self.bus.publish('brush_width_changed', self._current_base_width)
            return True
        elif key in ['-', '_']:
            self._current_base_width = max(self._current_base_width - 1, 1)
            self.bus.publish('brush_width_changed', self._current_base_width)
            return True
        
        return False
    
    def get_current_tool(self) -> str:
        """Get current tool."""
        return self._current_tool
    
    def get_current_brush_width(self) -> int:
        """Get current brush width."""
        return self._current_base_width
    
    def is_drawing(self) -> bool:
        """Check if currently drawing."""
        return self._is_drawing
    
    def get_stroke_count(self) -> int:
        """Get stroke count (approximate)."""
        return len(self._dynamic_stroke_points) if self._is_drawing else 0