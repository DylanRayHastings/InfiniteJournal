"""
Custom type aliases for clarity.
"""
from typing import NewType, Tuple

Point2D = NewType('Point2D', Tuple[int, int])
Color   = NewType('Color', Tuple[int, int, int])