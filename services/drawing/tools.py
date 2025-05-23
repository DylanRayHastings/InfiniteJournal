"""
Fixed Unified Tool Management System
Eliminates service initialization timing issues.
"""

import logging
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Protocol, Type, TypeVar
from enum import Enum

from ..core import UniversalService, ServiceConfiguration, ValidationService, EventBus

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ToolError(Exception):
    """Base exception for tool operations."""
    pass


class ToolStateError(ToolError):
    """Raised when tool state operations fail."""
    pass


class ShapeGenerationError(ToolError):
    """Raised when shape generation fails."""
    pass


class ToolType(Enum):
    """Universal tool type enumeration."""
    BRUSH = "brush"
    ERASER = "eraser" 
    LINE = "line"
    RECTANGLE = "rect"
    CIRCLE = "circle"
    TRIANGLE = "triangle"
    PARABOLA = "parabola"


@dataclass(frozen=True)
class ToolState:
    """Immutable tool state configuration."""
    tool_type: ToolType
    brush_width: int
    color: Tuple[int, int, int]
    opacity: float = 1.0
    is_active: bool = False
    
    def with_updates(self, **kwargs) -> 'ToolState':
        """Create new state with updates."""
        current_values = {
            'tool_type': self.tool_type,
            'brush_width': self.brush_width,
            'color': self.color,
            'opacity': self.opacity,
            'is_active': self.is_active
        }
        current_values.update(kwargs)
        return ToolState(**current_values)


class DrawingTool(Protocol):
    """Protocol for all drawing tools."""
    
    def get_tool_type(self) -> ToolType:
        """Get the tool type."""
        ...
    
    def start_operation(self, start_pos: Tuple[int, int], state: ToolState) -> Any:
        """Start tool operation."""
        ...
    
    def update_operation(self, current_pos: Tuple[int, int], operation_data: Any) -> Any:
        """Update ongoing operation."""
        ...
    
    def finish_operation(self, end_pos: Tuple[int, int], operation_data: Any) -> Any:
        """Finish tool operation."""
        ...
    
    def cancel_operation(self, operation_data: Any) -> None:
        """Cancel ongoing operation."""
        ...


class BaseTool(ABC):
    """Base implementation for drawing tools."""
    
    def __init__(self, tool_type: ToolType):
        self.tool_type = tool_type
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def get_tool_type(self) -> ToolType:
        """Get the tool type."""
        return self.tool_type
    
    @abstractmethod
    def start_operation(self, start_pos: Tuple[int, int], state: ToolState) -> Any:
        """Start tool operation."""
        pass
    
    @abstractmethod
    def update_operation(self, current_pos: Tuple[int, int], operation_data: Any) -> Any:
        """Update ongoing operation."""
        pass
    
    @abstractmethod
    def finish_operation(self, end_pos: Tuple[int, int], operation_data: Any) -> Any:
        """Finish tool operation."""
        pass
    
    def cancel_operation(self, operation_data: Any) -> None:
        """Cancel ongoing operation."""
        self.logger.debug(f"Cancelled {self.tool_type} operation")


class BrushTool(BaseTool):
    """Brush tool for freehand drawing."""
    
    def __init__(self):
        super().__init__(ToolType.BRUSH)
    
    def start_operation(self, start_pos: Tuple[int, int], state: ToolState) -> Dict[str, Any]:
        """Start brush stroke."""
        return {
            'type': 'brush_stroke',
            'points': [start_pos],
            'color': state.color,
            'width': state.brush_width
        }
    
    def update_operation(self, current_pos: Tuple[int, int], operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add point to brush stroke."""
        operation_data['points'].append(current_pos)
        return operation_data
    
    def finish_operation(self, end_pos: Tuple[int, int], operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Finish brush stroke."""
        if end_pos not in operation_data['points']:
            operation_data['points'].append(end_pos)
        operation_data['completed'] = True
        return operation_data


class EraserTool(BaseTool):
    """Eraser tool for removing content."""
    
    def __init__(self):
        super().__init__(ToolType.ERASER)
    
    def start_operation(self, start_pos: Tuple[int, int], state: ToolState) -> Dict[str, Any]:
        """Start eraser operation."""
        return {
            'type': 'erase_operation',
            'points': [start_pos],
            'radius': state.brush_width
        }
    
    def update_operation(self, current_pos: Tuple[int, int], operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Continue erasing."""
        operation_data['points'].append(current_pos)
        return operation_data
    
    def finish_operation(self, end_pos: Tuple[int, int], operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Finish erase operation."""
        if end_pos not in operation_data['points']:
            operation_data['points'].append(end_pos)
        operation_data['completed'] = True
        return operation_data


class LineTool(BaseTool):
    """Line tool for drawing straight lines."""
    
    def __init__(self):
        super().__init__(ToolType.LINE)
    
    def start_operation(self, start_pos: Tuple[int, int], state: ToolState) -> Dict[str, Any]:
        """Start line drawing."""
        return {
            'type': 'line',
            'start_pos': start_pos,
            'end_pos': start_pos,
            'color': state.color,
            'width': state.brush_width
        }
    
    def update_operation(self, current_pos: Tuple[int, int], operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update line end position."""
        operation_data['end_pos'] = current_pos
        return operation_data
    
    def finish_operation(self, end_pos: Tuple[int, int], operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Finish line drawing."""
        operation_data['end_pos'] = end_pos
        operation_data['completed'] = True
        return operation_data


class ShapeGenerator:
    """Universal shape generation for geometric tools."""
    
    @staticmethod
    def generate_rectangle_points(
        start: Tuple[int, int], 
        end: Tuple[int, int]
    ) -> List[Tuple[int, int]]:
        """Generate rectangle corner points."""
        x1, y1 = start
        x2, y2 = end
        return [
            (x1, y1), (x2, y1),
            (x2, y2), (x1, y2),
            (x1, y1)  # Close the rectangle
        ]
    
    @staticmethod
    def generate_circle_points(
        center: Tuple[int, int],
        radius: int,
        resolution: int = 64
    ) -> List[Tuple[int, int]]:
        """Generate circle points."""
        cx, cy = center
        points = []
        
        for i in range(resolution + 1):
            angle = 2 * math.pi * i / resolution
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            points.append((int(x), int(y)))
        
        return points


class RectangleTool(BaseTool):
    """Rectangle tool using shape generator."""
    
    def __init__(self):
        super().__init__(ToolType.RECTANGLE)
    
    def start_operation(self, start_pos: Tuple[int, int], state: ToolState) -> Dict[str, Any]:
        """Start rectangle drawing."""
        return {
            'type': 'rectangle',
            'start_pos': start_pos,
            'end_pos': start_pos,
            'color': state.color,
            'width': state.brush_width
        }
    
    def update_operation(self, current_pos: Tuple[int, int], operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update rectangle."""
        operation_data['end_pos'] = current_pos
        operation_data['points'] = ShapeGenerator.generate_rectangle_points(
            operation_data['start_pos'], current_pos
        )
        return operation_data
    
    def finish_operation(self, end_pos: Tuple[int, int], operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Finish rectangle."""
        operation_data['end_pos'] = end_pos
        operation_data['points'] = ShapeGenerator.generate_rectangle_points(
            operation_data['start_pos'], end_pos
        )
        operation_data['completed'] = True
        return operation_data


class CircleTool(BaseTool):
    """Circle tool using shape generator."""
    
    def __init__(self):
        super().__init__(ToolType.CIRCLE)
    
    def start_operation(self, start_pos: Tuple[int, int], state: ToolState) -> Dict[str, Any]:
        """Start circle drawing."""
        return {
            'type': 'circle',
            'center': start_pos,
            'radius': 0,
            'color': state.color,
            'width': state.brush_width
        }
    
    def update_operation(self, current_pos: Tuple[int, int], operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update circle radius."""
        center = operation_data['center']
        radius = int(math.sqrt(
            (current_pos[0] - center[0])**2 + 
            (current_pos[1] - center[1])**2
        ))
        operation_data['radius'] = radius
        operation_data['points'] = ShapeGenerator.generate_circle_points(center, radius)
        return operation_data
    
    def finish_operation(self, end_pos: Tuple[int, int], operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Finish circle."""
        center = operation_data['center']
        radius = int(math.sqrt(
            (end_pos[0] - center[0])**2 + 
            (end_pos[1] - center[1])**2
        ))
        operation_data['radius'] = radius
        operation_data['points'] = ShapeGenerator.generate_circle_points(center, radius)
        operation_data['completed'] = True
        return operation_data


class BrushController:
    """Controller for brush size and settings."""
    
    def __init__(self, min_size: int = 1, max_size: int = 200, step_size: int = 2):
        self.min_size = min_size
        self.max_size = max_size
        self.step_size = step_size
        self.current_size = 5
        
    def increase_size(self) -> int:
        """Increase brush size by step."""
        self.current_size = min(self.current_size + self.step_size, self.max_size)
        return self.current_size
    
    def decrease_size(self) -> int:
        """Decrease brush size by step."""
        self.current_size = max(self.current_size - self.step_size, self.min_size)
        return self.current_size
    
    def set_size(self, size: int) -> int:
        """Set specific brush size."""
        self.current_size = max(self.min_size, min(size, self.max_size))
        return self.current_size
    
    def get_size(self) -> int:
        """Get current brush size."""
        return self.current_size


class ToolManager(UniversalService):
    """
    Universal tool manager eliminating all tool service duplication.
    
    Fixed to handle service initialization timing issues.
    """
    
    def __init__(
        self,
        config: ServiceConfiguration,
        validation_service: ValidationService = None,
        event_bus: EventBus = None
    ):
        super().__init__(config, validation_service, event_bus)
        
        self.tools: Dict[ToolType, DrawingTool] = {}
        self.current_tool: Optional[DrawingTool] = None
        self.current_state = ToolState(
            tool_type=ToolType.BRUSH,
            brush_width=5,
            color=(255, 255, 255)
        )
        self.brush_controller = BrushController()
        self.active_operation: Optional[Any] = None
        
    def _initialize_service(self) -> None:
        """Initialize tool manager service - FIXED VERSION."""
        # Register all standard tools
        self._register_standard_tools()
        
        # Set default tool WITHOUT using service error handling during initialization
        self._set_default_tool_direct()
        
        # Subscribe to events
        if self.event_bus:
            self.event_bus.subscribe('tool_changed', self._handle_tool_change)
            self.event_bus.subscribe('brush_size_changed', self._handle_brush_size_change)
            self.event_bus.subscribe('color_changed', self._handle_color_change)
        
        self.logger.info("Tool manager initialized")
    
    def _cleanup_service(self) -> None:
        """Clean up tool manager resources."""
        if self.active_operation:
            self.cancel_current_operation()
        self.logger.info("Tool manager cleaned up")
    
    def _register_standard_tools(self):
        """Register all standard drawing tools."""
        standard_tools = [
            BrushTool(),
            EraserTool(),
            LineTool(),
            RectangleTool(),
            CircleTool(),
        ]
        
        for tool in standard_tools:
            self.tools[tool.get_tool_type()] = tool
            self.logger.debug(f"Registered tool: {tool.get_tool_type()}")
    
    def _set_default_tool_direct(self):
        """Set default tool directly without service state checks - FIXED."""
        try:
            # Set current tool directly without error handling wrapper
            if ToolType.BRUSH in self.tools:
                self.current_tool = self.tools[ToolType.BRUSH]
                self.current_state = self.current_state.with_updates(
                    tool_type=ToolType.BRUSH,
                    is_active=True
                )
                self.logger.info("Default tool set to BRUSH (direct)")
            else:
                self.logger.warning("BRUSH tool not found in registered tools")
                
        except Exception as error:
            self.logger.error(f"Failed to set default tool: {error}")
    
    def register_tool(self, tool: DrawingTool):
        """Register custom tool."""
        self.tools[tool.get_tool_type()] = tool
        self.logger.info(f"Registered custom tool: {tool.get_tool_type()}")
    
    def set_active_tool(self, tool_type: ToolType) -> bool:
        """Set active drawing tool."""
        def _set_tool():
            if tool_type not in self.tools:
                raise ToolError(f"Tool not found: {tool_type}")
            
            # Cancel any active operation
            if self.active_operation:
                self.cancel_current_operation()
            
            self.current_tool = self.tools[tool_type]
            self.current_state = self.current_state.with_updates(
                tool_type=tool_type,
                is_active=True
            )
            
            if self.event_bus:
                self.event_bus.publish('active_tool_changed', {
                    'tool_type': tool_type.value,
                    'state': self.current_state
                })
            
            self.logger.info(f"Active tool changed to: {tool_type}")
            return True
        
        # Only use error handling if service is running, otherwise set directly
        if self.is_ready():
            return self.execute_with_error_handling("set_active_tool", _set_tool)
        else:
            # Direct call during initialization
            return _set_tool()
    
    def start_tool_operation(self, start_pos: Tuple[int, int]) -> Any:
        """Start tool operation."""
        def _start_operation():
            if not self.current_tool:
                raise ToolStateError("No active tool")
            
            if self.active_operation:
                self.cancel_current_operation()
            
            self.active_operation = self.current_tool.start_operation(start_pos, self.current_state)
            
            if self.event_bus:
                self.event_bus.publish('tool_operation_started', {
                    'tool_type': self.current_state.tool_type.value,
                    'start_pos': start_pos,
                    'operation_data': self.active_operation
                })
            
            return self.active_operation
        
        return self.execute_with_error_handling("start_tool_operation", _start_operation)
    
    def update_tool_operation(self, current_pos: Tuple[int, int]) -> Any:
        """Update active tool operation."""
        def _update_operation():
            if not self.current_tool or not self.active_operation:
                return None
            
            self.active_operation = self.current_tool.update_operation(current_pos, self.active_operation)
            
            if self.event_bus:
                self.event_bus.publish('tool_operation_updated', {
                    'tool_type': self.current_state.tool_type.value,
                    'current_pos': current_pos,
                    'operation_data': self.active_operation
                })
            
            return self.active_operation
        
        return self.execute_with_error_handling("update_tool_operation", _update_operation)
    
    def finish_tool_operation(self, end_pos: Tuple[int, int]) -> Any:
        """Finish active tool operation."""
        def _finish_operation():
            if not self.current_tool or not self.active_operation:
                return None
            
            result = self.current_tool.finish_operation(end_pos, self.active_operation)
            
            if self.event_bus:
                self.event_bus.publish('tool_operation_finished', {
                    'tool_type': self.current_state.tool_type.value,
                    'end_pos': end_pos,
                    'operation_data': result
                })
            
            self.active_operation = None
            return result
        
        return self.execute_with_error_handling("finish_tool_operation", _finish_operation)
    
    def cancel_current_operation(self):
        """Cancel active tool operation."""
        def _cancel_operation():
            if self.current_tool and self.active_operation:
                self.current_tool.cancel_operation(self.active_operation)
                
                if self.event_bus:
                    self.event_bus.publish('tool_operation_cancelled', {
                        'tool_type': self.current_state.tool_type.value
                    })
                
                self.active_operation = None
        
        return self.execute_with_error_handling("cancel_tool_operation", _cancel_operation)
    
    def set_brush_size(self, size: int):
        """Set brush size."""
        new_size = self.brush_controller.set_size(size)
        self.current_state = self.current_state.with_updates(brush_width=new_size)
        
        if self.event_bus:
            self.event_bus.publish('brush_size_updated', {'size': new_size})
    
    def set_color(self, color: Tuple[int, int, int]):
        """Set drawing color."""
        self.current_state = self.current_state.with_updates(color=color)
        
        if self.event_bus:
            self.event_bus.publish('color_updated', {'color': color})
    
    def _handle_tool_change(self, data: Dict[str, Any]):
        """Handle tool change event."""
        tool_name = data.get('tool_type')
        if tool_name:
            try:
                tool_type = ToolType(tool_name)
                self.set_active_tool(tool_type)
            except ValueError:
                self.logger.warning(f"Unknown tool type: {tool_name}")
    
    def _handle_brush_size_change(self, data: Dict[str, Any]):
        """Handle brush size change event."""
        size = data.get('size')
        if size:
            self.set_brush_size(size)
    
    def _handle_color_change(self, data: Dict[str, Any]):
        """Handle color change event."""
        color = data.get('color')
        if color:
            self.set_color(color)


# Factory functions
def create_tool_manager(
    validation_service: ValidationService = None,
    event_bus: EventBus = None
) -> ToolManager:
    """Create tool manager with standard configuration."""
    config = ServiceConfiguration(
        service_name="tool_manager",
        debug_mode=False,
        auto_start=True
    )
    
    return ToolManager(
        config=config,
        validation_service=validation_service,
        event_bus=event_bus
    )


def create_shape_generator() -> ShapeGenerator:
    """Create shape generator."""
    return ShapeGenerator()