"""Visual Macro related exception classes."""

from __future__ import annotations


class VisualMacroError(Exception):
    """Base exception for all Visual Macro errors."""


class VisualMacroParseError(VisualMacroError):
    """Raised when Visual Macro JSON cannot be parsed into a valid program."""


class VisualMacroRuntimeError(VisualMacroError):
    """Raised when a Visual Macro fails during execution."""


class VisualMacroValidationError(VisualMacroParseError):
    """Raised when parsed JSON has missing or invalid fields."""
