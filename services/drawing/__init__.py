"""
Drawing Module Exports
Consolidates all drawing functionality into unified exports.
"""

# Unified Drawing Engine
from .engine import (
    # Core drawing engine
    DrawingEngine,
    DrawingError,
    CoordinateSystemError,
    RenderingError,
    
    # Coordinate system
    CoordinateSystem,
    WorldCoordinate,
    ScreenCoordinate,
    ViewportState,
    
    # Drawing canvas
    DrawingCanvas,
    Stroke,
    DrawingConfiguration,
    
    # Rendering backend protocol
    RenderingBackend,
    
    # Factory functions
    create_drawing_engine,
    create_pygame_backend
)

# Unified Tool Management
from .tools import (
    # Core tool system
    ToolManager,
    ToolType,
    ToolState,
    ToolError,
    ToolStateError,
    ShapeGenerationError,
    
    # Tool protocols and bases
    DrawingTool,
    BaseTool,
    
    # Standard tools
    BrushTool,
    EraserTool,
    LineTool,
    RectangleTool,
    CircleTool,
    
    # Shape generation
    ShapeGenerator,
    
    # Brush control
    BrushController,
    
    # Factory functions
    create_tool_manager,
    create_shape_generator
)

# Version information
__version__ = "1.0.0"
__author__ = "Unified Drawing System"

# Export groups for convenience
__all__ = [
    # Drawing engine
    "DrawingEngine",
    "CoordinateSystem",
    "WorldCoordinate",
    "ScreenCoordinate",
    "ViewportState",
    "DrawingCanvas",
    "Stroke",
    "DrawingConfiguration",
    "RenderingBackend",
    "create_drawing_engine",
    
    # Tool management
    "ToolManager",
    "ToolType",
    "ToolState",
    "DrawingTool",
    "BrushTool",
    "EraserTool", 
    "LineTool",
    "RectangleTool",
    "CircleTool",
    "ShapeGenerator",
    "BrushController",
    "create_tool_manager",
    "create_shape_generator"
]