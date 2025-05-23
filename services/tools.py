"""
Drawing Tool Management Service.

Provides comprehensive tool management for drawing applications including
tool switching, state persistence, event publishing, and extensible
tool configuration system.

Quick start:
    tool_service = ToolManagementService(settings, event_bus)
    tool_service.set_active_tool("brush")
    current_tool = tool_service.get_active_tool()

Extension points:
    - Add new tools: Register with register_tool() method
    - Add tool properties: Extend ToolConfiguration dataclass
    - Add key bindings: Extend KEY_BINDINGS configuration
    - Add persistence backends: Implement StateProvider interface
"""

import logging
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from abc import ABC, abstractmethod


class ToolManagementError(Exception):
    """Base exception for tool management operations."""
    pass


class ToolValidationError(ToolManagementError):
    """Raised when tool validation fails."""
    pass


class ToolPersistenceError(ToolManagementError):
    """Raised when tool state persistence fails."""
    pass


class EventPublishingError(ToolManagementError):
    """Raised when event publishing fails."""
    pass


@runtime_checkable
class EventBusProtocol(Protocol):
    """Protocol for event bus interface."""
    
    def subscribe(self, event_type: str, callback: Any) -> None:
        """Subscribe to event type with callback."""
        pass
    
    def publish(self, event_type: str, data: Any) -> None:
        """Publish event with data."""
        pass


@runtime_checkable
class SettingsProtocol(Protocol):
    """Protocol for settings interface."""
    pass


@dataclass(frozen=True)
class ToolConfiguration:
    """Configuration for individual drawing tool."""
    key: str
    display_name: str
    description: str
    keyboard_shortcut: Optional[str] = None
    is_active: bool = True
    tool_properties: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate tool configuration after initialization."""
        if not self.key:
            raise ToolValidationError("Tool key must be non-empty string")
        
        if not isinstance(self.key, str):
            raise ToolValidationError("Tool key must be string type")
        
        if not self.display_name:
            raise ToolValidationError("Tool display name must be non-empty string")
        
        if not isinstance(self.display_name, str):
            raise ToolValidationError("Tool display name must be string type")
        
        if len(self.key) > 50:
            raise ToolValidationError("Tool key must be 50 characters or less")


@dataclass
class ToolState:
    """Complete tool state for persistence."""
    active_tool_key: str
    last_updated: datetime
    tool_usage_count: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool state to dictionary for serialization."""
        return {
            "active_tool_key": self.active_tool_key,
            "last_updated": self.last_updated.isoformat(),
            "tool_usage_count": self.tool_usage_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolState':
        """Create tool state from dictionary."""
        return cls(
            active_tool_key=data["active_tool_key"],
            last_updated=datetime.fromisoformat(data["last_updated"]),
            tool_usage_count=data.get("tool_usage_count", {})
        )


class StateProvider(ABC):
    """Abstract interface for tool state persistence."""
    
    @abstractmethod
    def save_tool_state(self, state: ToolState) -> None:
        """Save tool state to persistent storage."""
        pass
    
    @abstractmethod
    def load_tool_state(self) -> Optional[ToolState]:
        """Load tool state from persistent storage."""
        pass
    
    @abstractmethod
    def clear_tool_state(self) -> None:
        """Clear saved tool state."""
        pass


def create_state_directory(state_file_path: Path) -> None:
    """Create directory for state file if it does not exist."""
    state_file_path.parent.mkdir(parents=True, exist_ok=True)


def write_state_to_file(state_file_path: Path, state_data: Dict[str, Any]) -> None:
    """Write state data to JSON file."""
    with open(state_file_path, 'w', encoding='utf-8') as file:
        json.dump(state_data, file, indent=2)


def read_state_from_file(state_file_path: Path) -> Dict[str, Any]:
    """Read state data from JSON file."""
    with open(state_file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


def remove_state_file(state_file_path: Path) -> None:
    """Remove state file if it exists."""
    if state_file_path.exists():
        state_file_path.unlink()


class FileStateProvider(StateProvider):
    """File-based tool state persistence provider."""
    
    def __init__(self, state_file_path: Path):
        """Initialize with state file path."""
        self.state_file_path = state_file_path
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def save_tool_state(self, state: ToolState) -> None:
        """Save tool state to JSON file."""
        try:
            create_state_directory(self.state_file_path)
            write_state_to_file(self.state_file_path, state.to_dict())
            self.logger.debug("Tool state saved to: %s", self.state_file_path)
            return
        except OSError as error:
            self.logger.error("Failed to save tool state: %s", error)
            raise ToolPersistenceError(f"Cannot save tool state: {error}") from error
        except json.JSONEncodeError as error:
            self.logger.error("Failed to save tool state: %s", error)
            raise ToolPersistenceError(f"Cannot save tool state: {error}") from error
    
    def load_tool_state(self) -> Optional[ToolState]:
        """Load tool state from JSON file."""
        if not self.state_file_path.exists():
            self.logger.debug("Tool state file does not exist: %s", self.state_file_path)
            return None
        
        try:
            data = read_state_from_file(self.state_file_path)
            state = ToolState.from_dict(data)
            self.logger.debug("Tool state loaded from: %s", self.state_file_path)
            return state
        except OSError as error:
            self.logger.error("Failed to load tool state: %s", error)
            raise ToolPersistenceError(f"Cannot load tool state: {error}") from error
        except json.JSONDecodeError as error:
            self.logger.error("Failed to load tool state: %s", error)
            raise ToolPersistenceError(f"Cannot load tool state: {error}") from error
        except KeyError as error:
            self.logger.error("Failed to load tool state: %s", error)
            raise ToolPersistenceError(f"Cannot load tool state: {error}") from error
        except ValueError as error:
            self.logger.error("Failed to load tool state: %s", error)
            raise ToolPersistenceError(f"Cannot load tool state: {error}") from error
    
    def clear_tool_state(self) -> None:
        """Remove tool state file."""
        try:
            remove_state_file(self.state_file_path)
            self.logger.debug("Tool state file removed: %s", self.state_file_path)
        except OSError as error:
            self.logger.error("Failed to clear tool state: %s", error)
            raise ToolPersistenceError(f"Cannot clear tool state: {error}") from error


def create_brush_tool() -> ToolConfiguration:
    """Create brush tool configuration."""
    return ToolConfiguration(
        key="brush",
        display_name="Freehand Brush",
        description="Draw freehand strokes with brush",
        keyboard_shortcut="b"
    )


def create_eraser_tool() -> ToolConfiguration:
    """Create eraser tool configuration."""
    return ToolConfiguration(
        key="eraser",
        display_name="Eraser",
        description="Erase drawn content",
        keyboard_shortcut="e"
    )


def create_line_tool() -> ToolConfiguration:
    """Create line tool configuration."""
    return ToolConfiguration(
        key="line",
        display_name="Line",
        description="Draw straight lines",
        keyboard_shortcut="l"
    )


def create_rectangle_tool() -> ToolConfiguration:
    """Create rectangle tool configuration."""
    return ToolConfiguration(
        key="rect",
        display_name="Rectangle",
        description="Draw rectangular shapes",
        keyboard_shortcut="r"
    )


def create_circle_tool() -> ToolConfiguration:
    """Create circle tool configuration."""
    return ToolConfiguration(
        key="circle",
        display_name="Circle",
        description="Draw circular shapes",
        keyboard_shortcut="c"
    )


def create_triangle_tool() -> ToolConfiguration:
    """Create triangle tool configuration."""
    return ToolConfiguration(
        key="triangle",
        display_name="Triangle",
        description="Draw triangular shapes",
        keyboard_shortcut="t"
    )


def create_parabola_tool() -> ToolConfiguration:
    """Create parabola tool configuration."""
    return ToolConfiguration(
        key="parabola",
        display_name="Parabolic Curve",
        description="Draw parabolic curves",
        keyboard_shortcut="p"
    )


def create_default_tool_list() -> List[ToolConfiguration]:
    """Create list of default tool configurations."""
    return [
        create_brush_tool(),
        create_eraser_tool(),
        create_line_tool(),
        create_rectangle_tool(),
        create_circle_tool(),
        create_triangle_tool(),
        create_parabola_tool()
    ]


def create_default_tool_registry() -> Dict[str, ToolConfiguration]:
    """Create default tool registry with standard drawing tools."""
    default_tools = create_default_tool_list()
    return {tool.key: tool for tool in default_tools}


def extract_keyboard_shortcut(tool_config: ToolConfiguration) -> Optional[str]:
    """Extract keyboard shortcut from tool configuration."""
    return tool_config.keyboard_shortcut


def add_keyboard_binding(key_bindings: Dict[str, str], tool_key: str, shortcut: str) -> None:
    """Add keyboard binding to mapping dictionary."""
    key_bindings[shortcut] = tool_key


def create_keyboard_binding_map(tool_registry: Dict[str, ToolConfiguration]) -> Dict[str, str]:
    """Create keyboard shortcut to tool key mapping."""
    key_bindings = {}
    
    for tool_key, tool_config in tool_registry.items():
        shortcut = extract_keyboard_shortcut(tool_config)
        if not shortcut:
            continue
        add_keyboard_binding(key_bindings, tool_key, shortcut)
    
    return key_bindings


def validate_tool_key_not_empty(tool_key: str) -> None:
    """Validate that tool key is not empty."""
    if not tool_key:
        raise ToolValidationError("Tool key cannot be empty")


def validate_tool_key_exists_in_registry(tool_key: str, tool_registry: Dict[str, ToolConfiguration]) -> None:
    """Validate that tool key exists in registry."""
    if tool_key not in tool_registry:
        available_tools = list(tool_registry.keys())
        raise ToolValidationError(f"Tool '{tool_key}' not found. Available tools: {available_tools}")


def validate_tool_key_exists(tool_key: str, tool_registry: Dict[str, ToolConfiguration]) -> None:
    """Validate that tool key exists in registry."""
    validate_tool_key_not_empty(tool_key)
    validate_tool_key_exists_in_registry(tool_key, tool_registry)


def validate_tool_is_active(tool_key: str, tool_registry: Dict[str, ToolConfiguration]) -> None:
    """Validate that tool is active and available for use."""
    tool_config = tool_registry[tool_key]
    
    if not tool_config.is_active:
        raise ToolValidationError(f"Tool '{tool_key}' is not currently active")


def increment_tool_usage_count(tool_key: str, usage_counts: Dict[str, int]) -> None:
    """Increment usage count for specific tool."""
    current_count = usage_counts.get(tool_key, 0)
    usage_counts[tool_key] = current_count + 1


def get_active_tool_keys(tool_registry: Dict[str, ToolConfiguration]) -> List[str]:
    """Get list of active tool keys."""
    return [key for key, config in tool_registry.items() if config.is_active]


def find_current_tool_index(current_tool_key: str, active_tools: List[str]) -> int:
    """Find index of current tool in active tools list."""
    try:
        return active_tools.index(current_tool_key)
    except ValueError:
        return -1


def calculate_next_tool_index(current_index: int, total_tools: int) -> int:
    """Calculate next tool index in cycling sequence."""
    return (current_index + 1) % total_tools


def get_next_tool_in_cycle(current_tool_key: str, tool_registry: Dict[str, ToolConfiguration]) -> str:
    """Get next active tool in cycling order."""
    active_tools = get_active_tool_keys(tool_registry)
    
    if not active_tools:
        raise ToolValidationError("No active tools available for cycling")
    
    current_index = find_current_tool_index(current_tool_key, active_tools)
    next_index = calculate_next_tool_index(current_index, len(active_tools))
    
    return active_tools[next_index]


def create_tool_change_event_data(previous_tool: str, new_tool: str, tool_config: ToolConfiguration) -> Dict[str, Any]:
    """Create event data for tool change event."""
    return {
        "previous_tool": previous_tool,
        "new_tool": new_tool,
        "tool_config": tool_config,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def publish_mode_changed_event(event_bus: EventBusProtocol, new_tool: str) -> None:
    """Publish mode changed event."""
    event_bus.publish("mode_changed", new_tool)


def publish_tool_changed_event(event_bus: EventBusProtocol, event_data: Dict[str, Any]) -> None:
    """Publish tool changed event."""
    event_bus.publish("tool_changed", event_data)


def get_available_tools_excluding_key(tool_registry: Dict[str, ToolConfiguration], exclude_key: str) -> List[str]:
    """Get list of available tools excluding specific key."""
    return [key for key, config in tool_registry.items() if config.is_active and key != exclude_key]


def create_deactivated_tool_config(original_config: ToolConfiguration) -> ToolConfiguration:
    """Create deactivated version of tool configuration."""
    return ToolConfiguration(
        key=original_config.key,
        display_name=original_config.display_name,
        description=original_config.description,
        keyboard_shortcut=original_config.keyboard_shortcut,
        is_active=False,
        tool_properties=original_config.tool_properties
    )


def select_fallback_tool_from_list(available_tools: List[str]) -> str:
    """Select fallback tool when current tool becomes unavailable."""
    return available_tools[0]


def is_brush_tool_available(active_tools: List[str]) -> bool:
    """Check if brush tool is available in active tools."""
    return "brush" in active_tools


def select_initial_tool_preference(active_tools: List[str]) -> str:
    """Select initial tool with brush preference."""
    if is_brush_tool_available(active_tools):
        return "brush"
    return select_fallback_tool_from_list(active_tools)


def check_saved_tool_exists_in_registry(saved_tool_key: str, tool_registry: Dict[str, ToolConfiguration]) -> bool:
    """Check if saved tool exists in current registry."""
    return saved_tool_key in tool_registry


def check_saved_tool_is_active(saved_tool_key: str, tool_registry: Dict[str, ToolConfiguration]) -> bool:
    """Check if saved tool is currently active."""
    tool_config = tool_registry[saved_tool_key]
    return tool_config.is_active


def apply_saved_tool_state(saved_state: ToolState, service: 'ToolManagementService') -> None:
    """Apply saved tool state to service."""
    service.active_tool_key = saved_state.active_tool_key
    service.tool_usage_counts = saved_state.tool_usage_count


def log_tool_state_restoration(logger: logging.Logger, tool_key: str) -> None:
    """Log successful tool state restoration."""
    logger.info("Restored tool state: %s", tool_key)


def log_inactive_tool_warning(logger: logging.Logger, tool_key: str) -> None:
    """Log warning about inactive saved tool."""
    logger.warning("Saved tool '%s' is inactive, using default", tool_key)


def log_missing_tool_warning(logger: logging.Logger, tool_key: str) -> None:
    """Log warning about missing saved tool."""
    logger.warning("Saved tool '%s' not found, using default", tool_key)


def convert_key_to_string(key: Any) -> str:
    """Convert keyboard input to lowercase string."""
    return str(key).lower()


def is_cycling_key(key_str: str, cycling_key: str) -> bool:
    """Check if key is the cycling key."""
    return key_str == cycling_key


def is_tool_shortcut_key(key_str: str, keyboard_bindings: Dict[str, str]) -> bool:
    """Check if key is a tool shortcut."""
    return key_str in keyboard_bindings


def get_tool_for_shortcut(key_str: str, keyboard_bindings: Dict[str, str]) -> str:
    """Get tool key for keyboard shortcut."""
    return keyboard_bindings[key_str]


def log_keyboard_tool_selection(logger: logging.Logger, key_str: str, target_tool: str) -> None:
    """Log keyboard tool selection."""
    logger.debug("Keyboard tool selection: %s -> %s", key_str, target_tool)


def log_keyboard_input_warning(logger: logging.Logger, key: Any, error: Exception) -> None:
    """Log warning for keyboard input handling failure."""
    logger.warning("Failed to handle keyboard input '%s': %s", key, error)


def log_keyboard_input_error(logger: logging.Logger, key: Any, error: Exception) -> None:
    """Log error for unexpected keyboard input failure."""
    logger.error("Unexpected error handling keyboard input '%s': %s", key, error)


def is_tool_registration_conflict(tool_key: str, tool_registry: Dict[str, ToolConfiguration]) -> bool:
    """Check if tool registration would create conflict."""
    return tool_key in tool_registry


def add_keyboard_shortcut_binding(keyboard_bindings: Dict[str, str], tool_config: ToolConfiguration) -> None:
    """Add keyboard shortcut binding for tool."""
    if not tool_config.keyboard_shortcut:
        return
    keyboard_bindings[tool_config.keyboard_shortcut] = tool_config.key


class ToolManagementService:
    """
    Comprehensive drawing tool management service.
    
    Manages tool registry, handles tool switching with validation,
    publishes tool change events, persists tool state, and provides
    extensible architecture for adding new tools.
    """
    
    DEFAULT_STATE_FILENAME = "tool_state.json"
    CYCLING_KEY = "space"
    
    def __init__(
        self,
        settings: SettingsProtocol,
        event_bus: EventBusProtocol,
        state_provider: Optional[StateProvider] = None,
        tool_registry: Optional[Dict[str, ToolConfiguration]] = None
    ):
        """
        Initialize tool management service.
        
        Args:
            settings: Application settings interface
            event_bus: Event publishing system
            state_provider: Optional custom state persistence provider
            tool_registry: Optional custom tool registry
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.settings = settings
        self.event_bus = event_bus
        
        self.tool_registry = tool_registry or create_default_tool_registry()
        self.keyboard_bindings = create_keyboard_binding_map(self.tool_registry)
        
        if state_provider is None:
            state_file_path = Path(self.DEFAULT_STATE_FILENAME)
            state_provider = FileStateProvider(state_file_path)
        
        self.state_provider = state_provider
        
        self.active_tool_key = self._determine_initial_tool()
        self.tool_usage_counts: Dict[str, int] = {}
        
        self._load_persisted_state()
        self._setup_event_subscriptions()
        
        self.logger.info("ToolManagementService initialized with active tool: %s", self.active_tool_key)
    
    def set_active_tool(self, tool_key: str) -> None:
        """
        Set active drawing tool with validation and event publishing.
        
        Args:
            tool_key: Key of tool to activate
            
        Raises:
            ToolValidationError: If tool key is invalid or tool is inactive
            EventPublishingError: If event publishing fails
        """
        validate_tool_key_exists(tool_key, self.tool_registry)
        validate_tool_is_active(tool_key, self.tool_registry)
        
        previous_tool = self.active_tool_key
        self.active_tool_key = tool_key
        
        increment_tool_usage_count(tool_key, self.tool_usage_counts)
        
        self._publish_tool_change_event(previous_tool, tool_key)
        self._persist_current_state()
        
        self.logger.info("Tool changed from '%s' to '%s'", previous_tool, tool_key)
    
    def cycle_to_next_tool(self) -> None:
        """Cycle to next active tool in sequence."""
        next_tool = get_next_tool_in_cycle(self.active_tool_key, self.tool_registry)
        self.set_active_tool(next_tool)
        
        self.logger.debug("Cycled to next tool: %s", next_tool)
    
    def get_active_tool(self) -> ToolConfiguration:
        """
        Get currently active tool configuration.
        
        Returns:
            Active tool configuration
        """
        return self.tool_registry[self.active_tool_key]
    
    def get_active_tool_key(self) -> str:
        """
        Get currently active tool key.
        
        Returns:
            Active tool key string
        """
        return self.active_tool_key
    
    def get_available_tools(self) -> List[ToolConfiguration]:
        """
        Get list of all available active tools.
        
        Returns:
            List of active tool configurations
        """
        return [config for config in self.tool_registry.values() if config.is_active]
    
    def get_tool_usage_statistics(self) -> Dict[str, int]:
        """
        Get tool usage statistics.
        
        Returns:
            Dictionary mapping tool keys to usage counts
        """
        return self.tool_usage_counts.copy()
    
    def register_tool(self, tool_config: ToolConfiguration) -> None:
        """
        Register new tool in the system.
        
        Args:
            tool_config: Tool configuration to register
            
        Raises:
            ToolValidationError: If tool configuration is invalid
        """
        if is_tool_registration_conflict(tool_config.key, self.tool_registry):
            raise ToolValidationError(f"Tool '{tool_config.key}' already registered")
        
        self.tool_registry[tool_config.key] = tool_config
        add_keyboard_shortcut_binding(self.keyboard_bindings, tool_config)
        
        self.logger.info("Registered new tool: %s", tool_config.key)
    
    def deactivate_tool(self, tool_key: str) -> None:
        """
        Deactivate tool without removing it from registry.
        
        Args:
            tool_key: Key of tool to deactivate
            
        Raises:
            ToolValidationError: If tool key is invalid or is currently active
        """
        validate_tool_key_exists(tool_key, self.tool_registry)
        
        if tool_key == self.active_tool_key:
            available_tools = get_available_tools_excluding_key(self.tool_registry, tool_key)
            
            if not available_tools:
                raise ToolValidationError("Cannot deactivate the only active tool")
            
            fallback_tool = select_fallback_tool_from_list(available_tools)
            self.set_active_tool(fallback_tool)
        
        tool_config = self.tool_registry[tool_key]
        updated_config = create_deactivated_tool_config(tool_config)
        self.tool_registry[tool_key] = updated_config
        
        self.logger.info("Deactivated tool: %s", tool_key)
    
    def clear_tool_state(self) -> None:
        """Clear all persisted tool state."""
        try:
            self.state_provider.clear_tool_state()
            self.tool_usage_counts.clear()
            
            self.logger.info("Tool state cleared successfully")
            
        except ToolPersistenceError as error:
            self.logger.error("Failed to clear tool state: %s", error)
            raise
    
    def _determine_initial_tool(self) -> str:
        """Determine initial tool to activate."""
        active_tools = get_active_tool_keys(self.tool_registry)
        
        if not active_tools:
            raise ToolValidationError("No active tools available")
        
        return select_initial_tool_preference(active_tools)
    
    def _load_persisted_state(self) -> None:
        """Load tool state from persistent storage."""
        try:
            saved_state = self.state_provider.load_tool_state()
            
            if saved_state is None:
                self.logger.debug("No saved tool state found, using defaults")
                return
            
            if not check_saved_tool_exists_in_registry(saved_state.active_tool_key, self.tool_registry):
                log_missing_tool_warning(self.logger, saved_state.active_tool_key)
                return
            
            if not check_saved_tool_is_active(saved_state.active_tool_key, self.tool_registry):
                log_inactive_tool_warning(self.logger, saved_state.active_tool_key)
                return
            
            apply_saved_tool_state(saved_state, self)
            log_tool_state_restoration(self.logger, self.active_tool_key)
            
        except ToolPersistenceError as error:
            self.logger.error("Failed to load tool state: %s", error)
    
    def _persist_current_state(self) -> None:
        """Save current tool state to persistent storage."""
        try:
            current_state = ToolState(
                active_tool_key=self.active_tool_key,
                last_updated=datetime.now(timezone.utc),
                tool_usage_count=self.tool_usage_counts
            )
            
            self.state_provider.save_tool_state(current_state)
            
        except ToolPersistenceError as error:
            self.logger.error("Failed to persist tool state: %s", error)
    
    def _setup_event_subscriptions(self) -> None:
        """Subscribe to keyboard events for tool switching."""
        try:
            self.event_bus.subscribe("key_press", self._handle_keyboard_input)
            
        except Exception as error:
            self.logger.error("Failed to subscribe to key_press events: %s", error)
            raise EventPublishingError(f"Cannot setup event subscriptions: {error}") from error
    
    def _handle_keyboard_input(self, key: Any) -> None:
        """
        Handle keyboard input for tool switching.
        
        Args:
            key: Keyboard input received
        """
        try:
            key_str = convert_key_to_string(key)
            
            if is_cycling_key(key_str, self.CYCLING_KEY):
                self.cycle_to_next_tool()
                return
            
            if not is_tool_shortcut_key(key_str, self.keyboard_bindings):
                return
            
            target_tool = get_tool_for_shortcut(key_str, self.keyboard_bindings)
            self.set_active_tool(target_tool)
            log_keyboard_tool_selection(self.logger, key_str, target_tool)
            
        except ToolValidationError as error:
            log_keyboard_input_warning(self.logger, key, error)
        except EventPublishingError as error:
            log_keyboard_input_warning(self.logger, key, error)
        except Exception as error:
            log_keyboard_input_error(self.logger, key, error)
    
    def _publish_tool_change_event(self, previous_tool: str, new_tool: str) -> None:
        """
        Publish tool change event.
        
        Args:
            previous_tool: Previously active tool key
            new_tool: Newly active tool key
            
        Raises:
            EventPublishingError: If event publishing fails
        """
        try:
            tool_config = self.tool_registry[new_tool]
            event_data = create_tool_change_event_data(previous_tool, new_tool, tool_config)
            
            publish_mode_changed_event(self.event_bus, new_tool)
            publish_tool_changed_event(self.event_bus, event_data)
            
        except Exception as error:
            self.logger.error("Failed to publish tool change event: %s", error)
            raise EventPublishingError(f"Cannot publish tool change event: {error}") from error