"""
Immutable dataclasses for drawing primitives.
"""
from dataclasses import dataclass, field
from typing import List, Tuple

import logging
from icecream import ic
from debug import DEBUG

if DEBUG:
    ic.configureOutput(prefix='[models] ')
    logging.getLogger().setLevel(logging.DEBUG)

@dataclass
class Point:
    x: int
    y: int
    width: int

    def __post_init__(self):
        if DEBUG:
            ic(f"Point created: ({self.x}, {self.y}, width={self.width})")
        logging.debug(f"Point initialized: x={self.x}, y={self.y}, width={self.width}")


@dataclass
class Stroke:
    color: Tuple[int, int, int]
    points: List[Point] = field(default_factory=list)

    def add_point(self, point: Point) -> None:
        self.points.append(point)
        if DEBUG:
            ic(f"Point added to stroke: {point}")
        logging.debug(f"Added point to stroke (color={self.color}): {point}")


@dataclass
class Page:
    strokes: List[Stroke] = field(default_factory=list)

    def new_stroke(self, color: Tuple[int, int, int]) -> Stroke:
        stroke = Stroke(color=color)
        self.strokes.append(stroke)
        if DEBUG:
            ic(f"New stroke started with color: {color}")
        logging.info(f"Stroke created with color: {color}")
        return stroke
