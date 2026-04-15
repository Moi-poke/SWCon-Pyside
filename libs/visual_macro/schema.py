"""JSON parsing and validation for Visual Macro programs."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import cast

from libs.visual_macro.errors import VisualMacroValidationError
from libs.visual_macro.models import (
    ConditionNode,
    FinishNode,
    HoldEndNode,
    HoldNode,
    IfNode,
    ImageExistsNode,
    InputName,
    MashNode,
    PressManyNode,
    PressNode,
    PrintNode,
    ProgramModel,
    RepeatNode,
    SequenceNode,
    StatementNode,
    StickHoldNode,
    StickMoveNode,
    StickName,
    StickReleaseNode,
    WaitNode,
    WaitUntilImageNode,
    WaitUntilNotImageNode,
    WhileAliveNode,
)

_ALLOWED_INPUTS: frozenset[str] = frozenset(
    {
        "A",
        "B",
        "X",
        "Y",
        "L",
        "R",
        "ZL",
        "ZR",
        "PLUS",
        "MINUS",
        "LCLICK",
        "RCLICK",
        "HOME",
        "CAPTURE",
        "TOP",
        "BTM",
        "LEFT",
        "RIGHT",
    }
)
_ALLOWED_STICKS: frozenset[str] = frozenset({"LEFT_STICK", "RIGHT_STICK"})
_ALLOWED_VERSIONS: frozenset[str] = frozenset({"1.0"})


def parse_program_json(text: str) -> ProgramModel:
    try:
        raw_value: object = json.loads(text)
    except json.JSONDecodeError as exc:
        raise VisualMacroValidationError(f"Invalid JSON: {exc}") from exc

    return parse_program_dict(_as_mapping(raw_value, path="root"))


def parse_program_dict(data: Mapping[str, object]) -> ProgramModel:
    version_value: str = _require_str(data, "version", "root")
    if version_value not in _ALLOWED_VERSIONS:
        raise VisualMacroValidationError(
            f"root.version must be one of {sorted(_ALLOWED_VERSIONS)}, got {version_value!r}"
        )

    root_value: Mapping[str, object] = _require_mapping(data, "root", "root")
    root_node: StatementNode = _parse_statement_node(root_value, path="root.root")
    if not isinstance(root_node, SequenceNode):
        raise VisualMacroValidationError("root.root must be a 'sequence' node")

    return ProgramModel(version=cast("str", version_value), root=root_node)


def _optional_str(data: Mapping[str, object], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise VisualMacroValidationError(f"Optional field {key!r} must be a string")
    return value


def _optional_float(data: Mapping[str, object], key: str) -> float | None:
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VisualMacroValidationError(f"Optional field {key!r} must be a number")
    return float(value)


def _validate_input_name(value: str, path: str) -> InputName:
    if value not in _ALLOWED_INPUTS:
        raise VisualMacroValidationError(
            f"{path} must be one of {sorted(_ALLOWED_INPUTS)}, got {value!r}"
        )
    return cast(InputName, value)


def _validate_stick_name(value: str, path: str) -> StickName:
    if value not in _ALLOWED_STICKS:
        raise VisualMacroValidationError(
            f"{path} must be one of {sorted(_ALLOWED_STICKS)}, got {value!r}"
        )
    return cast(StickName, value)


def _parse_statement_node(data: Mapping[str, object], path: str) -> StatementNode:
    node_type: str = _require_str(data, "type", path)

    if node_type == "sequence":
        return _parse_sequence_node(data, path)
    if node_type == "press":
        return _parse_press_node(data, path)
    if node_type == "press_many":
        return _parse_press_many_node(data, path)
    if node_type == "mash":
        return _parse_mash_node(data, path)
    if node_type == "hold":
        return _parse_hold_node(data, path)
    if node_type == "hold_end":
        return _parse_hold_end_node(data, path)
    if node_type == "stick_move":
        return _parse_stick_move_node(data, path)
    if node_type == "stick_hold":
        return _parse_stick_hold_node(data, path)
    if node_type == "stick_release":
        return _parse_stick_release_node(data, path)
    if node_type == "wait":
        return _parse_wait_node(data, path)
    if node_type == "wait_until_image":
        return _parse_wait_until_image_node(data, path)
    if node_type == "wait_until_not_image":
        return _parse_wait_until_not_image_node(data, path)
    if node_type == "print":
        return _parse_print_node(data, path)
    if node_type == "if":
        return _parse_if_node(data, path)
    if node_type == "repeat":
        return _parse_repeat_node(data, path)
    if node_type == "while_alive":
        return _parse_while_alive_node(data, path)
    if node_type == "finish":
        return _parse_finish_node(data, path)

    raise VisualMacroValidationError(
        f"{path}.type has unsupported statement type: {node_type!r}"
    )


def _parse_condition_node(data: Mapping[str, object], path: str) -> ConditionNode:
    node_type: str = _require_str(data, "type", path)
    if node_type == "image_exists":
        return _parse_image_exists_node(data, path)

    raise VisualMacroValidationError(
        f"{path}.type has unsupported condition type: {node_type!r}"
    )


def _parse_sequence_node(data: Mapping[str, object], path: str) -> SequenceNode:
    children_raw: Sequence[object] = _require_sequence(data, "children", path)
    children: list[StatementNode] = []
    for index, child_raw in enumerate(children_raw):
        child_mapping = _as_mapping(child_raw, f"{path}.children[{index}]")
        children.append(
            _parse_statement_node(child_mapping, f"{path}.children[{index}]")
        )
    return SequenceNode(
        type="sequence",
        children=children,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_press_node(data: Mapping[str, object], path: str) -> PressNode:
    button_value = _validate_input_name(
        _require_str(data, "button", path), f"{path}.button"
    )
    duration_value = _require_float(data, "duration", path)
    wait_value = _require_float(data, "wait", path)
    if duration_value < 0.0:
        raise VisualMacroValidationError(f"{path}.duration must be >= 0.0")
    if wait_value < 0.0:
        raise VisualMacroValidationError(f"{path}.wait must be >= 0.0")
    return PressNode(
        type="press",
        button=button_value,
        duration=duration_value,
        wait=wait_value,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_press_many_node(data: Mapping[str, object], path: str) -> PressManyNode:
    buttons_raw = _require_sequence(data, "buttons", path)
    buttons: list[InputName] = []
    for index, value in enumerate(buttons_raw):
        if not isinstance(value, str):
            raise VisualMacroValidationError(
                f"{path}.buttons[{index}] must be a string"
            )
        buttons.append(_validate_input_name(value, f"{path}.buttons[{index}]"))

    if not buttons:
        raise VisualMacroValidationError(f"{path}.buttons must not be empty")

    duration_value = _require_float(data, "duration", path)
    wait_value = _require_float(data, "wait", path)
    if duration_value < 0.0:
        raise VisualMacroValidationError(f"{path}.duration must be >= 0.0")
    if wait_value < 0.0:
        raise VisualMacroValidationError(f"{path}.wait must be >= 0.0")

    return PressManyNode(
        type="press_many",
        buttons=buttons,
        duration=duration_value,
        wait=wait_value,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_mash_node(data: Mapping[str, object], path: str) -> MashNode:
    button_value = _validate_input_name(
        _require_str(data, "button", path), f"{path}.button"
    )
    count_value = _require_int(data, "count", path)
    duration_value = _require_float(data, "duration", path)
    interval_value = _require_float(data, "interval", path)

    if count_value < 0:
        raise VisualMacroValidationError(f"{path}.count must be >= 0")
    if duration_value < 0.0:
        raise VisualMacroValidationError(f"{path}.duration must be >= 0.0")
    if interval_value < 0.0:
        raise VisualMacroValidationError(f"{path}.interval must be >= 0.0")

    return MashNode(
        type="mash",
        button=button_value,
        count=count_value,
        duration=duration_value,
        interval=interval_value,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_hold_node(data: Mapping[str, object], path: str) -> HoldNode:
    button_value = _validate_input_name(
        _require_str(data, "button", path), f"{path}.button"
    )
    duration_value = _require_float(data, "duration", path)
    if duration_value < 0.0:
        raise VisualMacroValidationError(f"{path}.duration must be >= 0.0")
    return HoldNode(
        type="hold",
        button=button_value,
        duration=duration_value,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_hold_end_node(data: Mapping[str, object], path: str) -> HoldEndNode:
    button_value = _validate_input_name(
        _require_str(data, "button", path), f"{path}.button"
    )
    return HoldEndNode(
        type="hold_end",
        button=button_value,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_stick_move_node(data: Mapping[str, object], path: str) -> StickMoveNode:
    stick_value = _validate_stick_name(
        _require_str(data, "stick", path), f"{path}.stick"
    )
    angle_value = _require_float(data, "angle", path)
    radius_value = _require_float(data, "radius", path)
    duration_value = _require_float(data, "duration", path)
    wait_value = _require_float(data, "wait", path)

    if radius_value < 0.0 or radius_value > 1.0:
        raise VisualMacroValidationError(f"{path}.radius must be between 0.0 and 1.0")
    if duration_value < 0.0:
        raise VisualMacroValidationError(f"{path}.duration must be >= 0.0")
    if wait_value < 0.0:
        raise VisualMacroValidationError(f"{path}.wait must be >= 0.0")

    return StickMoveNode(
        type="stick_move",
        stick=stick_value,
        angle=angle_value,
        radius=radius_value,
        duration=duration_value,
        wait=wait_value,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_stick_hold_node(data: Mapping[str, object], path: str) -> StickHoldNode:
    stick_value = _validate_stick_name(
        _require_str(data, "stick", path), f"{path}.stick"
    )
    angle_value = _require_float(data, "angle", path)
    radius_value = _require_float(data, "radius", path)
    duration_value = _require_float(data, "duration", path)

    if radius_value < 0.0 or radius_value > 1.0:
        raise VisualMacroValidationError(f"{path}.radius must be between 0.0 and 1.0")
    if duration_value < 0.0:
        raise VisualMacroValidationError(f"{path}.duration must be >= 0.0")

    return StickHoldNode(
        type="stick_hold",
        stick=stick_value,
        angle=angle_value,
        radius=radius_value,
        duration=duration_value,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_stick_release_node(
    data: Mapping[str, object], path: str
) -> StickReleaseNode:
    stick_value = _validate_stick_name(
        _require_str(data, "stick", path), f"{path}.stick"
    )
    return StickReleaseNode(
        type="stick_release",
        stick=stick_value,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_wait_node(data: Mapping[str, object], path: str) -> WaitNode:
    seconds_value = _require_float(data, "seconds", path)
    if seconds_value < 0.0:
        raise VisualMacroValidationError(f"{path}.seconds must be >= 0.0")
    return WaitNode(
        type="wait",
        seconds=seconds_value,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_wait_until_image_node(
    data: Mapping[str, object], path: str
) -> WaitUntilImageNode:
    template_value = _require_str(data, "template", path)
    threshold_value = _require_float(data, "threshold", path)
    use_gray_value = _require_bool(data, "use_gray", path)
    poll_interval_value = _require_float(data, "poll_interval", path)
    timeout_value = _optional_float(data, "timeout_seconds")

    if not template_value:
        raise VisualMacroValidationError(f"{path}.template must not be empty")
    if threshold_value < 0.0 or threshold_value > 1.0:
        raise VisualMacroValidationError(
            f"{path}.threshold must be between 0.0 and 1.0"
        )
    if poll_interval_value <= 0.0:
        raise VisualMacroValidationError(f"{path}.poll_interval must be > 0.0")
    if timeout_value is not None and timeout_value <= 0.0:
        raise VisualMacroValidationError(
            f"{path}.timeout_seconds must be > 0.0 when specified"
        )

    return WaitUntilImageNode(
        type="wait_until_image",
        template=template_value,
        threshold=threshold_value,
        use_gray=use_gray_value,
        poll_interval=poll_interval_value,
        timeout_seconds=timeout_value,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_wait_until_not_image_node(
    data: Mapping[str, object], path: str
) -> WaitUntilNotImageNode:
    template_value = _require_str(data, "template", path)
    threshold_value = _require_float(data, "threshold", path)
    use_gray_value = _require_bool(data, "use_gray", path)
    poll_interval_value = _require_float(data, "poll_interval", path)
    timeout_value = _optional_float(data, "timeout_seconds")

    if not template_value:
        raise VisualMacroValidationError(f"{path}.template must not be empty")
    if threshold_value < 0.0 or threshold_value > 1.0:
        raise VisualMacroValidationError(
            f"{path}.threshold must be between 0.0 and 1.0"
        )
    if poll_interval_value <= 0.0:
        raise VisualMacroValidationError(f"{path}.poll_interval must be > 0.0")
    if timeout_value is not None and timeout_value <= 0.0:
        raise VisualMacroValidationError(
            f"{path}.timeout_seconds must be > 0.0 when specified"
        )

    return WaitUntilNotImageNode(
        type="wait_until_not_image",
        template=template_value,
        threshold=threshold_value,
        use_gray=use_gray_value,
        poll_interval=poll_interval_value,
        timeout_seconds=timeout_value,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_print_node(data: Mapping[str, object], path: str) -> PrintNode:
    message_value = _require_str(data, "message", path)
    return PrintNode(
        type="print",
        message=message_value,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_if_node(data: Mapping[str, object], path: str) -> IfNode:
    condition_raw = _require_mapping(data, "condition", path)
    then_raw = _require_sequence(data, "then", path)
    else_raw = _require_sequence(data, "else", path)

    condition = _parse_condition_node(condition_raw, f"{path}.condition")
    then_body = _parse_statement_list(then_raw, f"{path}.then")
    else_body = _parse_statement_list(else_raw, f"{path}.else")

    return IfNode(
        type="if",
        condition=condition,
        then_body=then_body,
        else_body=else_body,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_repeat_node(data: Mapping[str, object], path: str) -> RepeatNode:
    count_value = _require_int(data, "count", path)
    if count_value < 0:
        raise VisualMacroValidationError(f"{path}.count must be >= 0")

    body_raw = _require_sequence(data, "body", path)
    body = _parse_statement_list(body_raw, f"{path}.body")

    return RepeatNode(
        type="repeat",
        count=count_value,
        body=body,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_while_alive_node(data: Mapping[str, object], path: str) -> WhileAliveNode:
    body_raw = _require_sequence(data, "body", path)
    body = _parse_statement_list(body_raw, f"{path}.body")
    return WhileAliveNode(
        type="while_alive",
        body=body,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_finish_node(data: Mapping[str, object], path: str) -> FinishNode:
    _ = path
    return FinishNode(
        type="finish",
        block_id=_optional_str(data, "block_id"),
    )


def _parse_image_exists_node(data: Mapping[str, object], path: str) -> ImageExistsNode:
    template_value = _require_str(data, "template", path)
    threshold_value = _require_float(data, "threshold", path)
    use_gray_value = _require_bool(data, "use_gray", path)

    if not template_value:
        raise VisualMacroValidationError(f"{path}.template must not be empty")
    if threshold_value < 0.0 or threshold_value > 1.0:
        raise VisualMacroValidationError(
            f"{path}.threshold must be between 0.0 and 1.0"
        )

    return ImageExistsNode(
        type="image_exists",
        template=template_value,
        threshold=threshold_value,
        use_gray=use_gray_value,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_statement_list(items: Sequence[object], path: str) -> list[StatementNode]:
    statements: list[StatementNode] = []
    for index, item in enumerate(items):
        item_mapping = _as_mapping(item, f"{path}[{index}]")
        statements.append(_parse_statement_node(item_mapping, f"{path}[{index}]"))
    return statements


def _require_mapping(
    data: Mapping[str, object], key: str, path: str
) -> Mapping[str, object]:
    value = _require_key(data, key, path)
    return _as_mapping(value, f"{path}.{key}")


def _require_sequence(data: Mapping[str, object], key: str, path: str) -> Sequence:
    value = _require_key(data, key, path)
    if isinstance(value, (str, bytes, bytearray)):
        raise VisualMacroValidationError(
            f"{path}.{key} must be an array, got string-like value"
        )
    if not isinstance(value, Sequence):
        raise VisualMacroValidationError(f"{path}.{key} must be an array")
    return cast(Sequence[object], value)


def _require_str(data: Mapping[str, object], key: str, path: str) -> str:
    value = _require_key(data, key, path)
    if not isinstance(value, str):
        raise VisualMacroValidationError(f"{path}.{key} must be a string")
    return value


def _require_bool(data: Mapping[str, object], key: str, path: str) -> bool:
    value = _require_key(data, key, path)
    if not isinstance(value, bool):
        raise VisualMacroValidationError(f"{path}.{key} must be a boolean")
    return value


def _require_int(data: Mapping[str, object], key: str, path: str) -> int:
    value = _require_key(data, key, path)
    if isinstance(value, bool) or not isinstance(value, int):
        raise VisualMacroValidationError(f"{path}.{key} must be an integer")
    return value


def _require_float(data: Mapping[str, object], key: str, path: str) -> float:
    value = _require_key(data, key, path)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VisualMacroValidationError(f"{path}.{key} must be a number")
    return float(value)


def _require_key(data: Mapping[str, object], key: str, path: str) -> object:
    if key not in data:
        raise VisualMacroValidationError(f"Missing required field: {path}.{key}")
    return data[key]


def _as_mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise VisualMacroValidationError(f"{path} must be an object")
    return cast(Mapping[str, object], value)
