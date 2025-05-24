"""Custom exceptions for the drawing primitives package - OPTIMIZED."""

class DrawingError(Exception):
    """Base exception type for drawing-related errors."""
    __slots__ = ()

class InvalidColorError(DrawingError):
    """Raised when a color tuple is invalid (not three ints 0–255)."""
    __slots__ = ()

class PersistenceError(DrawingError):
    """Raised when an error occurs during save/load operations."""
    __slots__ = ()