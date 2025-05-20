"""
Stub for Panda3D Engine, Clock, InputAdapter.
"""
from core.interfaces import Engine, Clock, InputAdapter, Event

class PandaEngineAdapter(Engine):
    def init_window(self, w, h, title): pass
    def poll_events(self): return []
    def clear(self): pass
    def present(self): pass
    def draw_line(self, start, end, width): pass
    def draw_circle(self, center, radius): pass
    def draw_text(self, text, pos, font_size): pass

class PandaClockAdapter(Clock):
    def tick(self, fps): pass
    def get_time(self): return 0.0

class PandaInputAdapter(InputAdapter):
    def translate(self, events): return []
