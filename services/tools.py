"""
Provides ToolService for managing and switching drawing tools,
publishing change events, and persisting the current tool mode.
"""

import logging
import json
from pathlib import Path
from typing import Any, Dict

from core.event_bus import EventBus


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ToolService:
    """Service for managing and persisting the current tool mode."""
    TOOL_STATE_FILENAME: str = "tool_state.json"
    DEFAULT_TOOLS: Dict[str, str] = {
        "brush": "Freehand Brush",
        "line": "Line",
        "rect": "Rectangle",
        "circle": "Circle",
        "triangle": "Triangle",
        "eraser": "Eraser",
        "text": "Text",
        "pan": "Pan",
        "integral": "Integral (∫)",
        "derivative": "Derivative (dy/dx)",
        "plot": "Function Plot",
    }

    def __init__(self, settings: Any, bus: EventBus) -> None:
        """
        Initializes the ToolService.
        Validates configuration, loads persisted mode, and subscribes to key events.

        Args:
            settings: Configuration object with attributes:
                - DEFAULT_TOOL (str): The default tool key.
                - DATA_PATH (Path): Path where state is persisted.
            bus: EventBus instance for subscribing and publishing events.

        Raises:
            ConfigurationError: If configuration is invalid.
            Exception: If subscribing to events fails.
        """
        self._logger = logging.getLogger(self.__class__.__name__)
        self._validate_settings(settings)
        self.settings = settings
        self.bus = bus
        self.tools = self.DEFAULT_TOOLS.copy()

        # Load persisted mode or use default
        persisted = self._load_persisted_mode()
        self.mode = persisted or settings.DEFAULT_TOOL
        self._logger.info("ToolService initialized with mode: %s", self.mode)

        try:
            self.bus.subscribe("key_press", self._on_key)
        except Exception as e:
            self._logger.error("Failed to subscribe to key_press events: %s", e)
            raise

    def _validate_settings(self, settings: Any) -> None:
        """Validates configuration settings."""
        default_tool = getattr(settings, "DEFAULT_TOOL", None)
        data_path = getattr(settings, "DATA_PATH", None)
        if not isinstance(default_tool, str):
            raise ConfigurationError("DEFAULT_TOOL must be a string.")
        if default_tool not in self.DEFAULT_TOOLS:
            raise ConfigurationError(f"DEFAULT_TOOL '{default_tool}' not recognized.")
        if not isinstance(data_path, Path):
            raise ConfigurationError("settings.DATA_PATH must be a pathlib.Path.")

    def _load_persisted_mode(self) -> str:
        """
        Loads the last tool mode from persistent storage.

        Returns:
            The persisted tool key if valid, else an empty string.
        """
        filepath = self.settings.DATA_PATH / self.TOOL_STATE_FILENAME
        if not filepath.exists():
            return ""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            mode = data.get("current_tool", "")
            if mode in self.tools:
                return mode
            self._logger.warning("Persisted mode '%s' is invalid.", mode)
        except (json.JSONDecodeError, OSError) as e:
            self._logger.error("Error loading tool state: %s", e)
        return ""

    def _persist_mode(self) -> None:
        """
        Writes the current tool mode to persistent storage.
        Logs an error if writing fails.
        """
        filepath = self.settings.DATA_PATH / self.TOOL_STATE_FILENAME
        try:
            self.settings.DATA_PATH.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"current_tool": self.mode}, f, indent=2)
        except OSError as e:
            self._logger.error("Failed to persist tool mode: %s", e)

    def set_mode(self, tool_key: str) -> None:
        """
        Sets the current tool mode, publishes 'mode_changed' event, and persists it.

        Args:
            tool_key: Key of the tool to switch to.

        Returns:
            None
        """
        if tool_key not in self.tools:
            self._logger.warning("Attempted to set invalid tool mode: %s", tool_key)
            return
        old = self.mode
        self.mode = tool_key
        self.bus.publish("mode_changed", self.mode)
        self._logger.debug("Tool switched from %s to %s", old, self.mode)
        self._persist_mode()

    def cycle_mode(self) -> None:
        """
        Cycles forward to the next tool in the tools list.

        Returns:
            None
        """
        keys = list(self.tools)
        try:
            idx = keys.index(self.mode)
        except ValueError:
            idx = 0
        next_key = keys[(idx + 1) % len(keys)]
        self.set_mode(next_key)

    def _on_key(self, key: Any) -> None:
        """
        Handles 'key_press' events for switching tool modes.

        Args:
            key: The key pressed event payload.
        """
        if key == "space":
            self.cycle_mode()
            return
        self.set_mode(key)
        self._logger.debug("Key press handled: %s", key)

    @property
    def current_tool_mode(self) -> str:
        """
        Returns:
            The current tool key.
        """
        return self.mode
