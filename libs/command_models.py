"""Shared models for command execution context."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CommandTriggerSource(str, Enum):
    """Trigger source for execution requests."""

    UI_COMBO = "ui_combo"
    VISUAL_EDITOR = "visual_editor"
    UNKNOWN = "unknown"


@dataclass(slots=True, frozen=True)
class CommandExecutionContext:
    """Execution context used by CommandSessionController."""

    command_id: str
    kind: str
    display_name: str
    source_path: str
    trigger_source: str
    payload_json: str = ""
