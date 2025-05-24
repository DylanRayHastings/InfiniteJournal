"""
Drawing module initialization - OPTIMIZED

Provides core drawing functionality with optimized imports.
"""

from .canvas import DrawingCanvas
from .models import Point, Stroke, Page
from .stroke_generator import BasicStrokeGenerator
from .input_handler import DrawingInputHandler
from .exceptions import DrawingError, InvalidColorError, PersistenceError

__all__ = [
    "DrawingCanvas",
    "Point",
    "Stroke", 
    "Page",
    "BasicStrokeGenerator",
    "DrawingInputHandler",
    "DrawingError",
    "InvalidColorError",
    "PersistenceError"
]