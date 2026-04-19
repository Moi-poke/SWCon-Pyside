"JSON parsing and validation for Visual Macro programs."

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import cast

from libs.visual_macro.errors import VisualMacroValidationError
from libs.visual_macro.models import (
    ArithmeticNode,
    BooleanNode,
    BreakNode,
    CallFunctionNode,
    CallFunctionValueNode,
    ChangeVariableNode,
    CommentNode,
    CompareNode,
    ContinueNode,
    FinishNode,
    ForRangeNode,
    FunctionDefinition,
    FunctionParamNode,
    GetVariableNode,
    HoldEndNode,
    HoldNode,
    IfNode,
    ImageExistsNode,
    InputName,
    ListAppendNode,
    ListCreateEmptyNode,
    ListCreateWithNode,
    ListForEachNode,
    ListGetNode,
    ListLengthNode,
    ListSetNode,
    LogicNotNode,
    LogicOperationNode,
    MashNode,
    MathMinMaxNode,
    MathSingleNode,
    NumberNode,
    PressManyNode,
    PressNode,
    PrintNode,
    PrintValueNode,
    ProgramModel,
    RandomFloatNode,
    RandomIntNode,
    RepeatNode,
    ReturnNode,
    SequenceNode,
    SetVariableNode,
    StatementNode,
    StickHoldNode,
    StickMoveNode,
    StickName,
    StickReleaseNode,
    TernaryNode,
    TextContainsNode,
    TextJoinNode,
    TextLengthNode,
    TextNode,
    TextSubstringNode,
    ToNumberNode,
    ToTextNode,
    ValueNode,
    WaitNode,
    WaitUntilImageNode,
    WaitUntilNotImageNode,
    WhileAliveNode,
    WhileConditionNode,
    WhileImageExistsNode,
    WhileNotImageExistsNode,
)

_ALLOWED_INPUTS: frozenset[str] = frozenset(
    {
        "A", "B", "X", "Y", "L", "R", "ZL", "ZR",
        "PLUS", "MINUS", "LCLICK", "RCLICK",
        "HOME", "CAPTURE", "TOP", "BTM", "LEFT", "RIGHT",
    }
)
_ALLOWED_STICKS: frozenset[str] = frozenset({"LEFT_STICK", "RIGHT_STICK"})
_ALLOWED_VERSIONS: frozenset[str] = frozenset({"1.0"})
_ALLOWED_ARITHMETIC_OPS: frozenset[str] = frozenset({"ADD", "SUB", "MUL", "DIV", "MOD"})
_ALLOWED_COMPARE_OPS: frozenset[str] = frozenset({"EQ", "NEQ", "LT", "GT", "LTE", "GTE"})
_ALLOWED_LOGIC_OPS: frozenset[str] = frozenset({"AND", "OR"})
_ALLOWED_MATH_SINGLE_OPS: frozenset[str] = frozenset({"ABS", "ROUND", "FLOOR", "CEIL"})
_ALLOWED_MATH_MINMAX_OPS: frozenset[str] = frozenset({"MIN", "MAX"})


# ======================================================================
# Public API
# ======================================================================

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

    # --- functions (optional) ---
    functions: dict[str, FunctionDefinition] = {}
    functions_raw = data.get("functions")
    if functions_raw is not None:
        functions_mapping = _as_mapping(functions_raw, "root.functions")
        for func_name, func_raw in functions_mapping.items():
            func_data = _as_mapping(func_raw, f"root.functions.{func_name}")
            functions[func_name] = _parse_function_definition(
                func_data, f"root.functions.{func_name}"
            )

    return ProgramModel(
        version=cast("str", version_value),
        root=root_node,
        functions=functions,
    )


# ======================================================================
# Function definition
# ======================================================================

def _parse_function_definition(
    data: Mapping[str, object], path: str
) -> FunctionDefinition:
    name = _require_str(data, "name", path)
    params_raw = _require_sequence(data, "params", path)
    params: list[str] = []
    for i, p in enumerate(params_raw):
        if not isinstance(p, str):
            raise VisualMacroValidationError(f"{path}.params[{i}] must be a string")
        params.append(p)

    body_raw = _require_sequence(data, "body", path)
    body = _parse_statement_list(body_raw, f"{path}.body")

    return FunctionDefinition(
        name=name,
        params=params,
        body=body,
        block_id=_optional_str(data, "block_id"),
    )


# ======================================================================
# Statement node dispatcher
# ======================================================================

def _parse_statement_node(data: Mapping[str, object], path: str) -> StatementNode:
    node_type: str = _require_str(data, "type", path)

    # --- original nodes ---
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
    if node_type == "while_image_exists":
        return _parse_while_image_exists_node(data, path)
    if node_type == "while_not_image_exists":
        return _parse_while_not_image_exists_node(data, path)
    if node_type == "finish":
        return _parse_finish_node(data, path)

    # --- new nodes ---
    if node_type == "print_value":
        return _parse_print_value_node(data, path)
    if node_type == "set_variable":
        return _parse_set_variable_node(data, path)
    if node_type == "change_variable":
        return _parse_change_variable_node(data, path)
    if node_type == "while_condition":
        return _parse_while_condition_node(data, path)
    if node_type == "for_range":
        return _parse_for_range_node(data, path)
    if node_type == "break":
        return _parse_break_node(data, path)
    if node_type == "continue":
        return _parse_continue_node(data, path)
    if node_type == "call_function":
        return _parse_call_function_node(data, path)
    if node_type == "return":
        return _parse_return_node(data, path)
    if node_type == "list_set":
        return _parse_list_set_node(data, path)
    if node_type == "list_append":
        return _parse_list_append_node(data, path)
    if node_type == "list_for_each":
        return _parse_list_for_each_node(data, path)
    if node_type == "comment":
        return _parse_comment_node(data, path)

    raise VisualMacroValidationError(
        f"{path}.type has unsupported statement type: {node_type!r}"
    )


# ======================================================================
# Value node dispatcher
# ======================================================================

def _parse_value_node(data: Mapping[str, object], path: str) -> ValueNode:
    node_type: str = _require_str(data, "type", path)

    if node_type == "image_exists":
        return _parse_image_exists_node(data, path)
    if node_type == "number":
        return _parse_number_node(data, path)
    if node_type == "text":
        return _parse_text_node(data, path)
    if node_type == "boolean":
        return _parse_boolean_node(data, path)
    if node_type == "get_variable":
        return _parse_get_variable_node(data, path)
    if node_type == "arithmetic":
        return _parse_arithmetic_node(data, path)
    if node_type == "random_int":
        return _parse_random_int_node(data, path)
    if node_type == "random_float":
        return _parse_random_float_node(data, path)
    if node_type == "compare":
        return _parse_compare_node(data, path)
    if node_type == "logic_operation":
        return _parse_logic_operation_node(data, path)
    if node_type == "logic_not":
        return _parse_logic_not_node(data, path)
    if node_type == "ternary":
        return _parse_ternary_node(data, path)
    if node_type == "text_join":
        return _parse_text_join_node(data, path)
    if node_type == "text_length":
        return _parse_text_length_node(data, path)
    if node_type == "text_contains":
        return _parse_text_contains_node(data, path)
    if node_type == "text_substring":
        return _parse_text_substring_node(data, path)
    if node_type == "to_number":
        return _parse_to_number_node(data, path)
    if node_type == "to_text":
        return _parse_to_text_node(data, path)
    if node_type == "math_single":
        return _parse_math_single_node(data, path)
    if node_type == "math_minmax":
        return _parse_math_minmax_node(data, path)
    if node_type == "function_param":
        return _parse_function_param_node(data, path)
    if node_type == "call_function_value":
        return _parse_call_function_value_node(data, path)
    if node_type == "list_create_empty":
        return _parse_list_create_empty_node(data, path)
    if node_type == "list_create_with":
        return _parse_list_create_with_node(data, path)
    if node_type == "list_length":
        return _parse_list_length_node(data, path)
    if node_type == "list_get":
        return _parse_list_get_node(data, path)

    raise VisualMacroValidationError(
        f"{path}.type has unsupported value type: {node_type!r}"
    )


def _parse_optional_value_node(
    data: Mapping[str, object], key: str, path: str
) -> ValueNode | None:
    value = data.get(key)
    if value is None:
        return None
    return _parse_value_node(_as_mapping(value, f"{path}.{key}"), f"{path}.{key}")


def _parse_required_value_node(
    data: Mapping[str, object], key: str, path: str
) -> ValueNode:
    raw = _require_mapping(data, key, path)
    return _parse_value_node(raw, f"{path}.{key}")


# backward compatibility
def _parse_condition_node(data: Mapping[str, object], path: str) -> ValueNode:
    return _parse_value_node(data, path)


# ======================================================================
# trim (ROI) helper
# ======================================================================

def _parse_optional_trim(data: Mapping[str, object], path: str) -> list[int] | None:
    raw = data.get("trim")
    if raw is None:
        return None
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise VisualMacroValidationError(f"{path}.trim must be an array of 4 ints")
    if len(raw) != 4:
        raise VisualMacroValidationError(f"{path}.trim must have exactly 4 elements")
    result: list[int] = []
    for i, v in enumerate(raw):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise VisualMacroValidationError(f"{path}.trim[{i}] must be a number")
        result.append(int(v))
    # all zeros → None (full image)
    if all(v == 0 for v in result):
        return None
    return result


# ======================================================================
# Original statement node parsers (with trim support added)
# ======================================================================

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
        trim=_parse_optional_trim(data, path),
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
        trim=_parse_optional_trim(data, path),
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

    condition = _parse_value_node(condition_raw, f"{path}.condition")
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


def _parse_while_image_exists_node(
    data: Mapping[str, object], path: str
) -> WhileImageExistsNode:
    template_value = _require_str(data, "template", path)
    threshold_value = _require_float(data, "threshold", path)
    use_gray_value = _require_bool(data, "use_gray", path)
    poll_interval_value = _require_float(data, "poll_interval", path)
    timeout_value = _optional_float(data, "timeout_seconds")
    body_raw = _require_sequence(data, "body", path)
    body = _parse_statement_list(body_raw, f"{path}.body")
    return WhileImageExistsNode(
        type="while_image_exists",
        template=template_value,
        threshold=threshold_value,
        use_gray=use_gray_value,
        poll_interval=poll_interval_value,
        timeout_seconds=timeout_value,
        body=body,
        trim=_parse_optional_trim(data, path),
        block_id=_optional_str(data, "block_id"),
    )


def _parse_while_not_image_exists_node(
    data: Mapping[str, object], path: str
) -> WhileNotImageExistsNode:
    template_value = _require_str(data, "template", path)
    threshold_value = _require_float(data, "threshold", path)
    use_gray_value = _require_bool(data, "use_gray", path)
    poll_interval_value = _require_float(data, "poll_interval", path)
    timeout_value = _optional_float(data, "timeout_seconds")
    body_raw = _require_sequence(data, "body", path)
    body = _parse_statement_list(body_raw, f"{path}.body")
    return WhileNotImageExistsNode(
        type="while_not_image_exists",
        template=template_value,
        threshold=threshold_value,
        use_gray=use_gray_value,
        poll_interval=poll_interval_value,
        timeout_seconds=timeout_value,
        body=body,
        trim=_parse_optional_trim(data, path),
        block_id=_optional_str(data, "block_id"),
    )


def _parse_finish_node(data: Mapping[str, object], path: str) -> FinishNode:
    _ = path
    return FinishNode(
        type="finish",
        block_id=_optional_str(data, "block_id"),
    )


# ======================================================================
# New statement node parsers
# ======================================================================

def _parse_print_value_node(data: Mapping[str, object], path: str) -> PrintValueNode:
    value = _parse_required_value_node(data, "value", path)
    return PrintValueNode(
        type="print_value",
        value=value,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_set_variable_node(
    data: Mapping[str, object], path: str
) -> SetVariableNode:
    name = _require_str(data, "name", path)
    value = _parse_required_value_node(data, "value", path)
    return SetVariableNode(
        type="set_variable",
        name=name,
        value=value,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_change_variable_node(
    data: Mapping[str, object], path: str
) -> ChangeVariableNode:
    name = _require_str(data, "name", path)
    delta = _parse_required_value_node(data, "delta", path)
    return ChangeVariableNode(
        type="change_variable",
        name=name,
        delta=delta,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_while_condition_node(
    data: Mapping[str, object], path: str
) -> WhileConditionNode:
    condition = _parse_required_value_node(data, "condition", path)
    body_raw = _require_sequence(data, "body", path)
    body = _parse_statement_list(body_raw, f"{path}.body")
    return WhileConditionNode(
        type="while_condition",
        condition=condition,
        body=body,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_for_range_node(data: Mapping[str, object], path: str) -> ForRangeNode:
    var_name = _require_str(data, "var_name", path)
    from_value = _require_int(data, "from_value", path)
    to_value = _require_int(data, "to_value", path)
    step = _require_int(data, "step", path)
    body_raw = _require_sequence(data, "body", path)
    body = _parse_statement_list(body_raw, f"{path}.body")
    return ForRangeNode(
        type="for_range",
        var_name=var_name,
        from_value=from_value,
        to_value=to_value,
        step=step,
        body=body,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_break_node(data: Mapping[str, object], path: str) -> BreakNode:
    _ = path
    return BreakNode(
        type="break",
        block_id=_optional_str(data, "block_id"),
    )


def _parse_continue_node(data: Mapping[str, object], path: str) -> ContinueNode:
    _ = path
    return ContinueNode(
        type="continue",
        block_id=_optional_str(data, "block_id"),
    )


def _parse_call_function_args(
    data: Mapping[str, object], path: str
) -> dict[str, ValueNode | None]:
    raw = data.get("args")
    if raw is None:
        return {}
    args_mapping = _as_mapping(raw, f"{path}.args")
    result: dict[str, ValueNode | None] = {}
    for key, val in args_mapping.items():
        if val is None:
            result[key] = None
        else:
            val_mapping = _as_mapping(val, f"{path}.args.{key}")
            result[key] = _parse_value_node(val_mapping, f"{path}.args.{key}")
    return result


def _parse_call_function_node(
    data: Mapping[str, object], path: str
) -> CallFunctionNode:
    name = _require_str(data, "name", path)
    args = _parse_call_function_args(data, path)
    return CallFunctionNode(
        type="call_function",
        name=name,
        args=args,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_return_node(data: Mapping[str, object], path: str) -> ReturnNode:
    value = _parse_optional_value_node(data, "value", path)
    return ReturnNode(
        type="return",
        value=value,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_list_set_node(data: Mapping[str, object], path: str) -> ListSetNode:
    var_name = _require_str(data, "var_name", path)
    index = _parse_required_value_node(data, "index", path)
    value = _parse_required_value_node(data, "value", path)
    return ListSetNode(
        type="list_set",
        var_name=var_name,
        index=index,
        value=value,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_list_append_node(data: Mapping[str, object], path: str) -> ListAppendNode:
    var_name = _require_str(data, "var_name", path)
    value = _parse_required_value_node(data, "value", path)
    return ListAppendNode(
        type="list_append",
        var_name=var_name,
        value=value,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_list_for_each_node(
    data: Mapping[str, object], path: str
) -> ListForEachNode:
    var_name = _require_str(data, "var_name", path)
    list_value = _parse_required_value_node(data, "list", path)
    body_raw = _require_sequence(data, "body", path)
    body = _parse_statement_list(body_raw, f"{path}.body")
    return ListForEachNode(
        type="list_for_each",
        var_name=var_name,
        list=list_value,
        body=body,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_comment_node(data: Mapping[str, object], path: str) -> CommentNode:
    text = _require_str(data, "text", path)
    return CommentNode(
        type="comment",
        text=text,
        block_id=_optional_str(data, "block_id"),
    )


# ======================================================================
# Value node parsers
# ======================================================================

def _parse_image_exists_node(
    data: Mapping[str, object], path: str
) -> ImageExistsNode:
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
        trim=_parse_optional_trim(data, path),
        block_id=_optional_str(data, "block_id"),
    )


def _parse_number_node(data: Mapping[str, object], path: str) -> NumberNode:
    value = _require_float(data, "value", path)
    return NumberNode(type="number", value=value, block_id=_optional_str(data, "block_id"))


def _parse_text_node(data: Mapping[str, object], path: str) -> TextNode:
    value = _require_str(data, "value", path)
    return TextNode(type="text", value=value, block_id=_optional_str(data, "block_id"))


def _parse_boolean_node(data: Mapping[str, object], path: str) -> BooleanNode:
    value = _require_bool(data, "value", path)
    return BooleanNode(type="boolean", value=value, block_id=_optional_str(data, "block_id"))


def _parse_get_variable_node(
    data: Mapping[str, object], path: str
) -> GetVariableNode:
    name = _require_str(data, "name", path)
    return GetVariableNode(
        type="get_variable", name=name, block_id=_optional_str(data, "block_id")
    )


def _parse_arithmetic_node(data: Mapping[str, object], path: str) -> ArithmeticNode:
    op = _require_str(data, "op", path)
    if op not in _ALLOWED_ARITHMETIC_OPS:
        raise VisualMacroValidationError(
            f"{path}.op must be one of {sorted(_ALLOWED_ARITHMETIC_OPS)}, got {op!r}"
        )
    left = _parse_required_value_node(data, "left", path)
    right = _parse_required_value_node(data, "right", path)
    return ArithmeticNode(
        type="arithmetic", op=op, left=left, right=right,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_random_int_node(data: Mapping[str, object], path: str) -> RandomIntNode:
    min_val = _require_int(data, "min", path)
    max_val = _require_int(data, "max", path)
    return RandomIntNode(
        type="random_int", min=min_val, max=max_val,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_random_float_node(
    data: Mapping[str, object], path: str
) -> RandomFloatNode:
    min_val = _require_float(data, "min", path)
    max_val = _require_float(data, "max", path)
    return RandomFloatNode(
        type="random_float", min=min_val, max=max_val,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_compare_node(data: Mapping[str, object], path: str) -> CompareNode:
    op = _require_str(data, "op", path)
    if op not in _ALLOWED_COMPARE_OPS:
        raise VisualMacroValidationError(
            f"{path}.op must be one of {sorted(_ALLOWED_COMPARE_OPS)}, got {op!r}"
        )
    left = _parse_required_value_node(data, "left", path)
    right = _parse_required_value_node(data, "right", path)
    return CompareNode(
        type="compare", op=op, left=left, right=right,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_logic_operation_node(
    data: Mapping[str, object], path: str
) -> LogicOperationNode:
    op = _require_str(data, "op", path)
    if op not in _ALLOWED_LOGIC_OPS:
        raise VisualMacroValidationError(
            f"{path}.op must be one of {sorted(_ALLOWED_LOGIC_OPS)}, got {op!r}"
        )
    left = _parse_required_value_node(data, "left", path)
    right = _parse_required_value_node(data, "right", path)
    return LogicOperationNode(
        type="logic_operation", op=op, left=left, right=right,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_logic_not_node(data: Mapping[str, object], path: str) -> LogicNotNode:
    value = _parse_required_value_node(data, "value", path)
    return LogicNotNode(
        type="logic_not", value=value, block_id=_optional_str(data, "block_id")
    )


def _parse_ternary_node(data: Mapping[str, object], path: str) -> TernaryNode:
    condition = _parse_required_value_node(data, "condition", path)
    true_value = _parse_required_value_node(data, "true_value", path)
    false_value = _parse_required_value_node(data, "false_value", path)
    return TernaryNode(
        type="ternary",
        condition=condition,
        true_value=true_value,
        false_value=false_value,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_text_join_node(data: Mapping[str, object], path: str) -> TextJoinNode:
    left = _parse_required_value_node(data, "left", path)
    right = _parse_required_value_node(data, "right", path)
    return TextJoinNode(
        type="text_join", left=left, right=right,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_text_length_node(data: Mapping[str, object], path: str) -> TextLengthNode:
    value = _parse_required_value_node(data, "value", path)
    return TextLengthNode(
        type="text_length", value=value, block_id=_optional_str(data, "block_id")
    )


def _parse_text_contains_node(
    data: Mapping[str, object], path: str
) -> TextContainsNode:
    text = _parse_required_value_node(data, "text", path)
    search = _parse_required_value_node(data, "search", path)
    return TextContainsNode(
        type="text_contains", text=text, search=search,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_text_substring_node(
    data: Mapping[str, object], path: str
) -> TextSubstringNode:
    text = _parse_required_value_node(data, "text", path)
    start = _parse_required_value_node(data, "start", path)
    length = _parse_required_value_node(data, "length", path)
    return TextSubstringNode(
        type="text_substring", text=text, start=start, length=length,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_to_number_node(data: Mapping[str, object], path: str) -> ToNumberNode:
    value = _parse_required_value_node(data, "value", path)
    return ToNumberNode(
        type="to_number", value=value, block_id=_optional_str(data, "block_id")
    )


def _parse_to_text_node(data: Mapping[str, object], path: str) -> ToTextNode:
    value = _parse_required_value_node(data, "value", path)
    return ToTextNode(
        type="to_text", value=value, block_id=_optional_str(data, "block_id")
    )


def _parse_math_single_node(data: Mapping[str, object], path: str) -> MathSingleNode:
    op = _require_str(data, "op", path)
    if op not in _ALLOWED_MATH_SINGLE_OPS:
        raise VisualMacroValidationError(
            f"{path}.op must be one of {sorted(_ALLOWED_MATH_SINGLE_OPS)}, got {op!r}"
        )
    value = _parse_required_value_node(data, "value", path)
    return MathSingleNode(
        type="math_single", op=op, value=value,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_math_minmax_node(data: Mapping[str, object], path: str) -> MathMinMaxNode:
    op = _require_str(data, "op", path)
    if op not in _ALLOWED_MATH_MINMAX_OPS:
        raise VisualMacroValidationError(
            f"{path}.op must be one of {sorted(_ALLOWED_MATH_MINMAX_OPS)}, got {op!r}"
        )
    left = _parse_required_value_node(data, "left", path)
    right = _parse_required_value_node(data, "right", path)
    return MathMinMaxNode(
        type="math_minmax", op=op, left=left, right=right,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_function_param_node(
    data: Mapping[str, object], path: str
) -> FunctionParamNode:
    name = _require_str(data, "name", path)
    return FunctionParamNode(
        type="function_param", name=name, block_id=_optional_str(data, "block_id")
    )


def _parse_call_function_value_node(
    data: Mapping[str, object], path: str
) -> CallFunctionValueNode:
    name = _require_str(data, "name", path)
    args = _parse_call_function_args(data, path)
    return CallFunctionValueNode(
        type="call_function_value",
        name=name,
        args=args,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_list_create_empty_node(
    data: Mapping[str, object], path: str
) -> ListCreateEmptyNode:
    _ = path
    return ListCreateEmptyNode(
        type="list_create_empty", block_id=_optional_str(data, "block_id")
    )


def _parse_list_create_with_node(
    data: Mapping[str, object], path: str
) -> ListCreateWithNode:
    items_raw = _require_sequence(data, "items", path)
    items: list[ValueNode] = []
    for i, item_raw in enumerate(items_raw):
        item_mapping = _as_mapping(item_raw, f"{path}.items[{i}]")
        items.append(_parse_value_node(item_mapping, f"{path}.items[{i}]"))
    return ListCreateWithNode(
        type="list_create_with", items=items,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_list_length_node(data: Mapping[str, object], path: str) -> ListLengthNode:
    list_value = _parse_required_value_node(data, "list", path)
    return ListLengthNode(
        type="list_length", list=list_value,
        block_id=_optional_str(data, "block_id"),
    )


def _parse_list_get_node(data: Mapping[str, object], path: str) -> ListGetNode:
    list_value = _parse_required_value_node(data, "list", path)
    index = _parse_required_value_node(data, "index", path)
    return ListGetNode(
        type="list_get", list=list_value, index=index,
        block_id=_optional_str(data, "block_id"),
    )


# ======================================================================
# Statement list helper
# ======================================================================

def _parse_statement_list(items: Sequence[object], path: str) -> list[StatementNode]:
    statements: list[StatementNode] = []
    for index, item in enumerate(items):
        item_mapping = _as_mapping(item, f"{path}[{index}]")
        statements.append(_parse_statement_node(item_mapping, f"{path}[{index}]"))
    return statements


# ======================================================================
# Primitive helpers & validators
# ======================================================================

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
