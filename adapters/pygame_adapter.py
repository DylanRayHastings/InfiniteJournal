"""
PyGame Adapter: Engine, Clock, and Input Implementations for Core Interfaces.

This module provides PyGame-based concrete implementations for rendering, event
handling, timing, and input translation. Intended to be used with abstract
interfaces defined in core.interfaces.
"""

import pygame
import logging
from icecream import ic
from debug import DEBUG, VERBOSE_DEBUG

from core.interfaces import Engine, Clock, Event, InputAdapter
from core.events import EventBus

if DEBUG:
    ic.configureOutput(prefix='[pygame_adapter] ')
    logging.getLogger().setLevel(logging.DEBUG)


class PygameEngineAdapter(Engine):
    def __init__(self):
        self.screen = None
        logging.info("PygameEngineAdapter initialized")

    def init_window(self, width: int, height: int, title: str) -> None:
        pygame.init()
        pygame.font.init()
        flags = pygame.SCALED | pygame.RESIZABLE | pygame.DOUBLEBUF | pygame.HWSURFACE
        try:
            self.screen = pygame.display.set_mode((width, height), flags, vsync=1)
            pygame.display.set_caption(title)
            logging.info(f"Window initialized: {width}x{height} - '{title}' (vsync=1)")
            if DEBUG and VERBOSE_DEBUG:
                ic(width, height, title, flags)
        except TypeError:
            self.screen = pygame.display.set_mode((width, height), flags)
            pygame.display.set_caption(title)
            logging.warning("vsync not supported. Fallback used.")

    def poll_events(self):
        events = []
        raw_events = pygame.event.get()
        for e in raw_events:
            if e.type == pygame.QUIT:
                events.append(Event('QUIT', {}))
            elif e.type == pygame.MOUSEMOTION:
                events.append(Event('MOUSE_MOVE', {'pos': e.pos, 'rel': e.rel}))
            elif e.type == pygame.MOUSEBUTTONDOWN:
                if e.button == 4:
                    events.append(Event('KEY_PRESS', 'SCROLL_UP'))
                elif e.button == 5:
                    events.append(Event('KEY_PRESS', 'SCROLL_DOWN'))
                else:
                    events.append(Event('MOUSE_DOWN', {'pos': e.pos, 'button': e.button}))
            elif e.type == pygame.MOUSEBUTTONUP:
                events.append(Event('MOUSE_UP', {'pos': e.pos, 'button': e.button}))
            elif e.type == pygame.KEYDOWN:
                events.append(Event('KEY_PRESS', pygame.key.name(e.key)))
        if DEBUG and VERBOSE_DEBUG:
            ic(events)
        logging.debug(f"Polled {len(events)} events")
        return events

    def clear(self, color=(0, 0, 0)) -> None:
        self.screen.fill(color)
        if DEBUG and VERBOSE_DEBUG:
            ic(f"Screen cleared with color {color}")

    def present(self) -> None:
        pygame.display.flip()
        if DEBUG and VERBOSE_DEBUG:
            ic("Screen presented")

    def draw_line(self, start, end, width: int, color=(255, 255, 255)) -> None:
        pygame.draw.line(self.screen, color, start, end, width)
        if DEBUG and VERBOSE_DEBUG:
            ic(f"Line drawn from {start} to {end}, width={width}, color={color}")

    def draw_circle(self, center, radius: int, color=(255, 255, 255), width: int = 0) -> None:
        try:
            pygame.draw.circle(self.screen, color, center, radius, width)
            if DEBUG and VERBOSE_DEBUG:
                ic(f"Circle drawn at {center}, radius={radius}, width={width}, color={color}")
        except Exception as e:
            logging.exception(f"Failed to draw circle at {center} with color={color}")
            raise

    def draw_text(self, text: str, pos, font_size: int, color=(255, 255, 255)) -> None:
        font = pygame.font.SysFont(None, font_size)
        surf = font.render(text, True, color)
        self.screen.blit(surf, pos)
        if DEBUG and VERBOSE_DEBUG:
            ic(f"Text '{text}' drawn at {pos}, size={font_size}, color={color}")

    def draw_stroke(self, points, color=(255, 255, 255), default_width=3) -> None:
        def unpack(pt):
            if hasattr(pt, "x") and hasattr(pt, "y"):
                w = getattr(pt, "width", default_width)
                return pt.x, pt.y, w
            elif isinstance(pt, (tuple, list)):
                if len(pt) == 3:
                    return pt[0], pt[1], pt[2]
                elif len(pt) == 2:
                    return pt[0], pt[1], default_width
            logging.error(f"Invalid stroke point format: {pt}")
            raise ValueError("Unsupported point format in stroke: " + repr(pt))

        if len(points) == 0:
            return
        if len(points) == 1:
            x, y, w = unpack(points[0])
            self.draw_circle((x, y), w, color, 0)
            return
        for i in range(1, len(points)):
            x0, y0, w0 = unpack(points[i - 1])
            x1, y1, w1 = unpack(points[i])
            self.draw_line((x0, y0), (x1, y1), w0, color)
            self.draw_circle((x0, y0), w0, color, 0)
        x_end, y_end, w_end = unpack(points[-1])
        self.draw_circle((x_end, y_end), w_end, color, 0)
        if DEBUG and VERBOSE_DEBUG:
            ic(f"Stroke drawn with {len(points)} points, color={color}")

    def draw_cursor(self, pos, radius: int, color=(255, 255, 255)) -> None:
        self.draw_circle(pos, radius, color)
        if DEBUG and VERBOSE_DEBUG:
            ic(f"Cursor drawn at {pos}, radius={radius}, color={color}")

    def draw_ui(self, mode: str, timestamp: str, font_color=(255, 255, 255)) -> None:
        self.draw_text(f"Mode: {mode}", (10, 10), 16, font_color)
        height = self.screen.get_height()
        self.draw_text(timestamp, (10, height - 20), 14, font_color)
        if DEBUG and VERBOSE_DEBUG:
            ic(f"UI drawn with mode='{mode}' and timestamp='{timestamp}'")


class PygameClockAdapter(Clock):
    def __init__(self):
        super().__init__()
        self._clock = pygame.time.Clock()
        logging.info("PygameClockAdapter initialized")

    def tick(self, fps: int) -> None:
        self._clock.tick(fps)
        if DEBUG and VERBOSE_DEBUG:
            ic(f"Clock ticked at {fps} FPS")

    def get_time(self) -> float:
        time_sec = pygame.time.get_ticks() / 1000.0
        if DEBUG and VERBOSE_DEBUG:
            ic(f"Elapsed time: {time_sec} seconds")
        return time_sec


class PygameInputAdapter(InputAdapter):
    def translate(self, events):
        if DEBUG and VERBOSE_DEBUG:
            ic(f"Translating {len(events)} events")
        return events
