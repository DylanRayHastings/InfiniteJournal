"""Custom exceptions for the drawing primitives package."""


class DrawingError(Exception):
    """Base exception type for drawing-related errors."""


class InvalidColorError(DrawingError):
    """Raised when a color tuple is invalid (not three ints 0–255)."""


class PersistenceError(DrawingError):
    """Raised when an error occurs during save/load operations."""
