"""
Immutable dataclasses for drawing primitives.
"""
from dataclasses import dataclass, field
from typing import List

@dataclass(frozen=True)
class Point:
    x: int
    y: int
    width: int

@dataclass
class Stroke:
    points: List[Point] = field(default_factory=list)

    def add_point(self, point: Point) -> None:
        self.points.append(point)

@dataclass
class Page:
    strokes: List[Stroke] = field(default_factory=list)

    def new_stroke(self) -> Stroke:
        stroke = Stroke()
        self.strokes.append(stroke)
        return stroke
