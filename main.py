"""
Main Entry Point: Application Composition and Startup

Sets up configuration, adapters, services, and UI widgets, then launches the app.
"""

from backup import *
from config import Settings
from core.events import EventBus
from core.services import (
    JournalService,
    ToolService,
    UndoRedoService,
    App
)
from adapters.pygame_adapter import (
    PygameEngineAdapter,
    PygameClockAdapter,
    PygameInputAdapter
)
from adapters.fs_adapter import (
    FileSystemJournalRepository,
    ScreenshotExporter
)
from ui.canvas_widget import CanvasWidget
from ui.toolbar import Toolbar
from ui.status_bar import StatusBar
from ui.popup_manager import PopupManager

def compose_app() -> App:
    """
    Composes the main application object with all configuration,
    adapters, domain services, and widgets.
    
    Returns:
        App: Fully initialized application instance.
    """
    # Load user/system settings
    settings = Settings.load()
    # Set up the event bus for message passing between modules
    bus = EventBus()

    # Instantiate platform adapters
    engine = PygameEngineAdapter()
    clock  = PygameClockAdapter()
    inp    = PygameInputAdapter()

    # Set up domain services and IO
    repo      = FileSystemJournalRepository()
    exporter  = ScreenshotExporter()
    journal   = JournalService(bus)
    undo      = UndoRedoService(bus)
    tools     = ToolService(settings, bus)

    # Initialize all UI widgets/components
    canvas = CanvasWidget(journal, engine, bus)
    toolbar = Toolbar(tools, engine, bus)
    status = StatusBar(clock, engine, settings)
    popup = PopupManager(bus, engine, clock)

    # Compose everything into a single App object
    return App(
        settings=settings,
        engine=engine,
        clock=clock,
        input_adapter=inp,
        journal_service=journal,
        tool_service=tools,
        undo_service=undo,
        repository=repo,
        exporter=exporter,
        widgets=[canvas, toolbar, status, popup],
    )

def main():
    """
    Entry point for launching the application.
    """
    app = compose_app()
    app.run()

if __name__ == '__main__':
    main()
