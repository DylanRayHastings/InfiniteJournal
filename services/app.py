"""Legacy app compatibility."""

from .application import SimpleApp as BaseSimpleApp

class App:
    """Legacy App class."""
    
    def __init__(self, settings, engine, clock, input_adapter, **kwargs):
        self.simple_app = BaseSimpleApp(settings, engine, clock, input_adapter)
        
    def run(self):
        return self.simple_app.run()

class SimpleApp(BaseSimpleApp):
    """Simple app export."""
    pass