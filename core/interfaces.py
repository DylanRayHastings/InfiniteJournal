"""
Abstract engine-agnostic interfaces for windowing, input, rendering, and timing.
"""
from abc import ABC, abstractmethod
from typing import Any, List, Tuple

import logging
from icecream import ic
from debug import DEBUG


if DEBUG:
    ic.configureOutput(prefix='[interfaces] ')
    logging.getLogger().setLevel(logging.DEBUG)

class Event:
    """
    Normalized input/event object.
    """
    def __init__(self, type: str, data: Any):
        self.type = type
        self.data = data
        if DEBUG:
            ic(f"Event created: type='{self.type}', data={self.data}")
        logging.debug(f"Event initialized: type={self.type}, data={self.data}")


class Engine(ABC):
    """
    Windowing and primitive drawing.
    """
    @abstractmethod
    def init_window(self, width: int, height: int, title: str) -> None: ...
    
    @abstractmethod
    def poll_events(self) -> List[Event]: ...
    
    @abstractmethod
    def clear(self) -> None: ...
    
    @abstractmethod
    def present(self) -> None: ...
    
    @abstractmethod
    def draw_line(self, start: Tuple[int, int], end: Tuple[int, int], width: int) -> None: ...
    
    @abstractmethod
    def draw_circle(self, center: Tuple[int, int], radius: int) -> None: ...
    
    @abstractmethod
    def draw_text(self, text: str, pos: Tuple[int, int], font_size: int) -> None: ...


class Clock(ABC):
    """
    Frame timing and elapsed time.
    """
    @abstractmethod
    def tick(self, target_fps: int) -> None: ...
    
    @abstractmethod
    def get_time(self) -> float: ...


class InputAdapter(ABC):
    """
    Translates raw Engine events → domain Events.
    """
    @abstractmethod
    def translate(self, events: List[Event]) -> List[Event]: ...


class Renderer(ABC):
    """
    High-level drawing for strokes, cursor, UI.
    """
    @abstractmethod
    def draw_stroke(self, points: List[Tuple[int, int]], width: int) -> None: ...
    
    @abstractmethod
    def draw_cursor(self, pos: Tuple[int, int], radius: int) -> None: ...
    
    @abstractmethod
    def draw_ui(self, mode: str, timestamp: str) -> None: ...
