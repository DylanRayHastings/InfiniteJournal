"""
Enhanced UndoRedo Management Service.

Provides comprehensive undo/redo functionality with state management,
memory optimization, and extensible action handling for production applications.

Quick start:
    service = UndoRedoService(event_bus)
    service.record_action(action_data)
    service.undo()
    service.redo()

Extension points:
    - Add new action types: Extend ActionType enum and handlers
    - Add validation rules: Implement custom action validators
    - Add persistence: Extend with state serialization capabilities
    - Add compression: Implement state compression for large datasets
"""

from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from abc import ABC, abstractmethod
import logging
import json
import weakref

logger = logging.getLogger(__name__)

class ActionType(Enum):
    """Supported action types for undo/redo operations."""
    STROKE_ADDED = "stroke_added"
    STROKE_REMOVED = "stroke_removed"
    STROKE_MODIFIED = "stroke_modified"
    CANVAS_CLEARED = "canvas_cleared"
    LAYER_ADDED = "layer_added"
    LAYER_REMOVED = "layer_removed"
    PROPERTY_CHANGED = "property_changed"

class UndoRedoError(Exception):
    """Base exception for undo/redo operations."""
    pass

class InvalidActionError(UndoRedoError):
    """Raised when action data is invalid."""
    pass

class StackEmptyError(UndoRedoError):
    """Raised when attempting to undo/redo from empty stack."""
    pass

@dataclass(frozen=True)
class ActionState:
    """Immutable action state for undo/redo operations."""
    action_type: ActionType
    timestamp: datetime
    state_data: Dict[str, Any]
    description: str
    
    def __post_init__(self):
        """Validate action state after initialization."""
        if not isinstance(self.state_data, dict):
            raise InvalidActionError("State data must be a dictionary")
        
        if not self.description or not self.description.strip():
            raise InvalidActionError("Description cannot be empty")

@dataclass
class StackStatistics:
    """Statistics about undo/redo stack usage."""
    undo_count: int = 0
    redo_count: int = 0
    total_actions_recorded: int = 0
    memory_usage_bytes: int = 0
    oldest_action_timestamp: Optional[datetime] = None
    newest_action_timestamp: Optional[datetime] = None

class ActionValidator(ABC):
    """Abstract base for action validation."""
    
    @abstractmethod
    def validate_action_data(self, action_type: ActionType, state_data: Dict[str, Any]) -> bool:
        """Validate action data before recording."""
        pass

class DefaultActionValidator(ActionValidator):
    """Default validation for common action types."""
    
    def validate_action_data(self, action_type: ActionType, state_data: Dict[str, Any]) -> bool:
        """Validate action data with basic rules."""
        if not isinstance(state_data, dict):
            return False
        
        if action_type == ActionType.STROKE_ADDED and 'stroke_id' not in state_data:
            return False
        
        if action_type == ActionType.PROPERTY_CHANGED and 'property_name' not in state_data:
            return False
        
        return True

class ActionStateFactory:
    """Factory for creating validated action states."""
    
    def __init__(self, validator: ActionValidator):
        self.validator = validator
    
    def create_action_state(
        self, 
        action_type: ActionType, 
        state_data: Dict[str, Any], 
        description: str
    ) -> ActionState:
        """Create validated action state."""
        if not self.validator.validate_action_data(action_type, state_data):
            raise InvalidActionError(f"Invalid action data for type: {action_type.value}")
        
        return ActionState(
            action_type=action_type,
            timestamp=datetime.now(timezone.utc),
            state_data=state_data.copy(),
            description=description.strip()
        )

class MemoryManager:
    """Manages memory usage for undo/redo stacks."""
    
    def __init__(self, max_memory_bytes: int = 50 * 1024 * 1024):
        self.max_memory_bytes = max_memory_bytes
    
    def estimate_action_size(self, action_state: ActionState) -> int:
        """Estimate memory usage of action state."""
        try:
            serialized = json.dumps(action_state.state_data, default=str)
            return len(serialized.encode('utf-8')) + len(action_state.description.encode('utf-8'))
        except (TypeError, ValueError):
            return 1024
    
    def should_trim_stack(self, current_memory: int) -> bool:
        """Determine if stack should be trimmed for memory management."""
        return current_memory > self.max_memory_bytes
    
    def calculate_trim_amount(self, current_memory: int) -> int:
        """Calculate how many items to remove from stack."""
        excess_memory = current_memory - self.max_memory_bytes
        return max(1, excess_memory // 1024)

class EventBusInterface(ABC):
    """Interface for event bus integration."""
    
    @abstractmethod
    def subscribe(self, event_name: str, callback: Callable) -> None:
        """Subscribe to event bus events."""
        pass
    
    @abstractmethod
    def publish(self, event_name: str, data: Any) -> None:
        """Publish events to event bus."""
        pass

class UndoRedoService:
    """
    Comprehensive undo/redo service for state management.
    
    Provides robust undo/redo functionality with memory management,
    validation, statistics tracking, and extensible action handling.
    
    Features:
        - Memory-aware stack management
        - Action validation and type safety
        - Comprehensive statistics tracking
        - Event bus integration
        - Extensible action types
        - Production-ready error handling
    """
    
    def __init__(
        self,
        event_bus: EventBusInterface,
        max_stack_size: int = 100,
        max_memory_bytes: int = 50 * 1024 * 1024,
        validator: Optional[ActionValidator] = None
    ):
        """
        Initialize undo/redo service.
        
        Args:
            event_bus: Event bus for integration
            max_stack_size: Maximum number of actions in each stack
            max_memory_bytes: Maximum memory usage for stacks
            validator: Custom action validator (uses default if None)
        """
        self.undo_stack: List[ActionState] = []
        self.redo_stack: List[ActionState] = []
        self.max_stack_size = max_stack_size
        self.statistics = StackStatistics()
        
        self.memory_manager = MemoryManager(max_memory_bytes)
        self.action_factory = ActionStateFactory(validator or DefaultActionValidator())
        self.event_bus_ref = weakref.ref(event_bus)
        
        self.subscription_handlers: Dict[str, Callable] = {
            'stroke_added': self._handle_stroke_added,
            'stroke_removed': self._handle_stroke_removed,
            'stroke_modified': self._handle_stroke_modified,
            'canvas_cleared': self._handle_canvas_cleared
        }
        
        self._register_event_handlers(event_bus)
        self._current_memory_usage = 0
        
        logger.info(
            "UndoRedoService initialized - max_stack: %d, max_memory: %d bytes",
            max_stack_size, max_memory_bytes
        )
    
    def record_action(
        self, 
        action_type: ActionType, 
        state_data: Dict[str, Any], 
        description: str
    ) -> None:
        """
        Record new action for undo/redo.
        
        Args:
            action_type: Type of action being recorded
            state_data: State information for the action
            description: Human-readable description of action
            
        Raises:
            InvalidActionError: If action data is invalid
        """
        try:
            action_state = self.action_factory.create_action_state(
                action_type, state_data, description
            )
            
            self._add_to_undo_stack(action_state)
            self._clear_redo_stack()
            self._update_statistics_for_new_action(action_state)
            self._publish_action_recorded_event(action_state)
            
            logger.debug(
                "Action recorded: %s - %s (stack size: %d)",
                action_type.value, description, len(self.undo_stack)
            )
            
        except Exception as error:
            logger.error("Failed to record action: %s", error)
            raise
    
    def undo(self) -> Optional[ActionState]:
        """
        Undo the last recorded action.
        
        Returns:
            The action that was undone, or None if stack is empty
            
        Raises:
            StackEmptyError: If undo stack is empty
        """
        if not self.can_undo():
            raise StackEmptyError("Cannot undo: stack is empty")
        
        action_state = self.undo_stack.pop()
        self.redo_stack.append(action_state)
        
        self._update_memory_usage()
        self.statistics.undo_count += 1
        
        self._publish_action_undone_event(action_state)
        
        logger.debug(
            "Action undone: %s - %s",
            action_state.action_type.value, action_state.description
        )
        
        return action_state
    
    def redo(self) -> Optional[ActionState]:
        """
        Redo the last undone action.
        
        Returns:
            The action that was redone, or None if stack is empty
            
        Raises:
            StackEmptyError: If redo stack is empty
        """
        if not self.can_redo():
            raise StackEmptyError("Cannot redo: stack is empty")
        
        action_state = self.redo_stack.pop()
        self.undo_stack.append(action_state)
        
        self._update_memory_usage()
        self.statistics.redo_count += 1
        
        self._publish_action_redone_event(action_state)
        
        logger.debug(
            "Action redone: %s - %s",
            action_state.action_type.value, action_state.description
        )
        
        return action_state
    
    def can_undo(self) -> bool:
        """Check if undo operation is possible."""
        return len(self.undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Check if redo operation is possible."""
        return len(self.redo_stack) > 0
    
    def clear_all_stacks(self) -> None:
        """Clear both undo and redo stacks."""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._current_memory_usage = 0
        
        logger.info("All undo/redo stacks cleared")
    
    def get_undo_stack_preview(self, max_items: int = 10) -> List[str]:
        """Get preview of undo stack descriptions."""
        return [
            action.description 
            for action in reversed(self.undo_stack[-max_items:])
        ]
    
    def get_redo_stack_preview(self, max_items: int = 10) -> List[str]:
        """Get preview of redo stack descriptions."""
        return [
            action.description 
            for action in reversed(self.redo_stack[-max_items:])
        ]
    
    def get_statistics(self) -> StackStatistics:
        """Get current statistics about stack usage."""
        return StackStatistics(
            undo_count=self.statistics.undo_count,
            redo_count=self.statistics.redo_count,
            total_actions_recorded=self.statistics.total_actions_recorded,
            memory_usage_bytes=self._current_memory_usage,
            oldest_action_timestamp=self._get_oldest_action_timestamp(),
            newest_action_timestamp=self._get_newest_action_timestamp()
        )
    
    def _register_event_handlers(self, event_bus: EventBusInterface) -> None:
        """Register event handlers with event bus."""
        for event_name, handler in self.subscription_handlers.items():
            event_bus.subscribe(event_name, handler)
    
    def _handle_stroke_added(self, event_data: Dict[str, Any]) -> None:
        """Handle stroke added event."""
        self.record_action(
            ActionType.STROKE_ADDED,
            event_data,
            f"Added stroke: {event_data.get('stroke_id', 'unknown')}"
        )
    
    def _handle_stroke_removed(self, event_data: Dict[str, Any]) -> None:
        """Handle stroke removed event."""
        self.record_action(
            ActionType.STROKE_REMOVED,
            event_data,
            f"Removed stroke: {event_data.get('stroke_id', 'unknown')}"
        )
    
    def _handle_stroke_modified(self, event_data: Dict[str, Any]) -> None:
        """Handle stroke modified event."""
        self.record_action(
            ActionType.STROKE_MODIFIED,
            event_data,
            f"Modified stroke: {event_data.get('stroke_id', 'unknown')}"
        )
    
    def _handle_canvas_cleared(self, event_data: Dict[str, Any]) -> None:
        """Handle canvas cleared event."""
        self.record_action(
            ActionType.CANVAS_CLEARED,
            event_data,
            "Canvas cleared"
        )
    
    def _add_to_undo_stack(self, action_state: ActionState) -> None:
        """Add action to undo stack with size and memory management."""
        self.undo_stack.append(action_state)
        
        action_size = self.memory_manager.estimate_action_size(action_state)
        self._current_memory_usage += action_size
        
        self._enforce_stack_limits()
    
    def _clear_redo_stack(self) -> None:
        """Clear redo stack when new action is recorded."""
        if self.redo_stack:
            for action in self.redo_stack:
                action_size = self.memory_manager.estimate_action_size(action)
                self._current_memory_usage -= action_size
            
            self.redo_stack.clear()
    
    def _enforce_stack_limits(self) -> None:
        """Enforce maximum stack size and memory limits."""
        while len(self.undo_stack) > self.max_stack_size:
            removed_action = self.undo_stack.pop(0)
            action_size = self.memory_manager.estimate_action_size(removed_action)
            self._current_memory_usage -= action_size
        
        if self.memory_manager.should_trim_stack(self._current_memory_usage):
            trim_count = self.memory_manager.calculate_trim_amount(self._current_memory_usage)
            
            for _ in range(min(trim_count, len(self.undo_stack))):
                removed_action = self.undo_stack.pop(0)
                action_size = self.memory_manager.estimate_action_size(removed_action)
                self._current_memory_usage -= action_size
    
    def _update_memory_usage(self) -> None:
        """Recalculate current memory usage."""
        total_memory = 0
        
        for action in self.undo_stack:
            total_memory += self.memory_manager.estimate_action_size(action)
        
        for action in self.redo_stack:
            total_memory += self.memory_manager.estimate_action_size(action)
        
        self._current_memory_usage = total_memory
    
    def _update_statistics_for_new_action(self, action_state: ActionState) -> None:
        """Update statistics when new action is recorded."""
        self.statistics.total_actions_recorded += 1
    
    def _get_oldest_action_timestamp(self) -> Optional[datetime]:
        """Get timestamp of oldest action in stacks."""
        all_actions = self.undo_stack + self.redo_stack
        
        if not all_actions:
            return None
        
        return min(action.timestamp for action in all_actions)
    
    def _get_newest_action_timestamp(self) -> Optional[datetime]:
        """Get timestamp of newest action in stacks."""
        all_actions = self.undo_stack + self.redo_stack
        
        if not all_actions:
            return None
        
        return max(action.timestamp for action in all_actions)
    
    def _publish_action_recorded_event(self, action_state: ActionState) -> None:
        """Publish action recorded event."""
        event_bus = self.event_bus_ref()
        if event_bus:
            event_bus.publish('action_recorded', {
                'action_type': action_state.action_type.value,
                'description': action_state.description,
                'timestamp': action_state.timestamp.isoformat()
            })
    
    def _publish_action_undone_event(self, action_state: ActionState) -> None:
        """Publish action undone event."""
        event_bus = self.event_bus_ref()
        if event_bus:
            event_bus.publish('action_undone', {
                'action_type': action_state.action_type.value,
                'description': action_state.description,
                'timestamp': action_state.timestamp.isoformat()
            })
    
    def _publish_action_redone_event(self, action_state: ActionState) -> None:
        """Publish action redone event."""
        event_bus = self.event_bus_ref()
        if event_bus:
            event_bus.publish('action_redone', {
                'action_type': action_state.action_type.value,
                'description': action_state.description,
                'timestamp': action_state.timestamp.isoformat()
            })


class AdvancedUndoRedoService(UndoRedoService):
    """
    Advanced undo/redo service with additional features.
    
    Extends base service with features like action grouping,
    state compression, and persistence capabilities.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize advanced service with additional capabilities."""
        super().__init__(*args, **kwargs)
        self.action_groups: Dict[str, List[ActionState]] = {}
        self.compression_enabled = kwargs.get('compression_enabled', False)
    
    def begin_action_group(self, group_name: str) -> None:
        """Begin grouping actions under a common name."""
        if group_name in self.action_groups:
            raise InvalidActionError(f"Action group already exists: {group_name}")
        
        self.action_groups[group_name] = []
        logger.debug("Action group started: %s", group_name)
    
    def end_action_group(self, group_name: str) -> None:
        """End action grouping and record as single undoable action."""
        if group_name not in self.action_groups:
            raise InvalidActionError(f"Action group not found: {group_name}")
        
        grouped_actions = self.action_groups.pop(group_name)
        
        if grouped_actions:
            self.record_action(
                ActionType.PROPERTY_CHANGED,
                {'grouped_actions': [action.state_data for action in grouped_actions]},
                f"Group: {group_name} ({len(grouped_actions)} actions)"
            )
        
        logger.debug("Action group completed: %s (%d actions)", group_name, len(grouped_actions))
    
    def export_stack_state(self) -> Dict[str, Any]:
        """Export current stack state for persistence."""
        return {
            'undo_stack': [
                {
                    'action_type': action.action_type.value,
                    'timestamp': action.timestamp.isoformat(),
                    'state_data': action.state_data,
                    'description': action.description
                }
                for action in self.undo_stack
            ],
            'redo_stack': [
                {
                    'action_type': action.action_type.value,
                    'timestamp': action.timestamp.isoformat(),
                    'state_data': action.state_data,
                    'description': action.description
                }
                for action in self.redo_stack
            ],
            'statistics': {
                'undo_count': self.statistics.undo_count,
                'redo_count': self.statistics.redo_count,
                'total_actions_recorded': self.statistics.total_actions_recorded
            }
        }
    
    def import_stack_state(self, state_data: Dict[str, Any]) -> None:
        """Import previously exported stack state."""
        self.clear_all_stacks()
        
        for action_data in state_data.get('undo_stack', []):
            action_state = ActionState(
                action_type=ActionType(action_data['action_type']),
                timestamp=datetime.fromisoformat(action_data['timestamp']),
                state_data=action_data['state_data'],
                description=action_data['description']
            )
            self.undo_stack.append(action_state)
        
        for action_data in state_data.get('redo_stack', []):
            action_state = ActionState(
                action_type=ActionType(action_data['action_type']),
                timestamp=datetime.fromisoformat(action_data['timestamp']),
                state_data=action_data['state_data'],
                description=action_data['description']
            )
            self.redo_stack.append(action_state)
        
        stats_data = state_data.get('statistics', {})
        self.statistics.undo_count = stats_data.get('undo_count', 0)
        self.statistics.redo_count = stats_data.get('redo_count', 0)
        self.statistics.total_actions_recorded = stats_data.get('total_actions_recorded', 0)
        
        self._update_memory_usage()
        logger.info("Stack state imported successfully")