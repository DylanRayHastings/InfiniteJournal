"""
Immutable dataclasses for drawing primitives.
"""
from dataclasses import dataclass, field
from typing import List, Tuple

import logging
from icecream import ic
from debug import DEBUG, VERBOSE_DEBUG

if DEBUG:
    ic.configureOutput(prefix='[models] ')
    logging.getLogger().setLevel(logging.DEBUG)

@dataclass
class Point:
    x: float
    y: float
    z: float = 0.0  # NEW
    width: int = 1

@dataclass
class Stroke:
    color: Tuple[int, int, int]
    points: List[Point] = field(default_factory=list)

    def add_point(self, point: Point) -> None:
        self.points.append(point)
        if DEBUG and VERBOSE_DEBUG:
            ic(f"Point added to stroke: {point}")
        logging.debug(f"Added point to stroke (color={self.color}): {point}")


@dataclass
class Page:
    strokes: List[Stroke] = field(default_factory=list)

    def new_stroke(self, color: Tuple[int, int, int]) -> Stroke:
        stroke = Stroke(color=color)
        self.strokes.append(stroke)
        if DEBUG and VERBOSE_DEBUG:
            ic(f"New stroke started with color: {color}")
        logging.info(f"Stroke created with color: {color}")
        return stroke
