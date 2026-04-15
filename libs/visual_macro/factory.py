"""Factory helpers for wrapping Visual Macro programs as CommandBase classes."""

from __future__ import annotations

import copy
from typing import Type

from libs.CommandBase import CommandBase
from libs.visual_macro.runtime import VisualMacroRuntime
from libs.visual_macro.schema import parse_program_json


def build_visual_macro_command_class(
    program_json: str,
    display_name: str = "Visual Macro",
) -> Type:
    """Build a no-arg CommandBase-derived class from Visual Macro JSON."""
    program = parse_program_json(program_json)

    class GeneratedVisualMacroCommand(VisualMacroRuntime):
        """Generated Visual Macro command class."""

        NAME = display_name
        CAPTURE_DIR = "./ScreenShot"
        __directory__ = "./Commands/Visual"
        __tool_tip__ = "Blockly / Visual Macro generated command."

        def __init__(self) -> None:
            super().__init__(program=copy.deepcopy(program))

    return GeneratedVisualMacroCommand
