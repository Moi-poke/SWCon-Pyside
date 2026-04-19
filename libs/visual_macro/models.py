from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypeAlias

ProgramVersion = Literal["1.0"]
NodeType = Literal[
    "sequence",
    "press",
    "press_many",
    "mash",
    "hold",
    "hold_end",
    "stick_move",
    "stick_hold",
    "stick_release",
    "wait",
    "wait_until_image",
    "wait_until_not_image",
    "print",
    "print_value",
    "if",
    "repeat",
    "while_alive",
    "while_condition",
    "while_image_exists",
    "while_not_image_exists",
    "image_exists",
    "finish",
    "set_variable",
    "get_variable",
    "change_variable",
    "for_range",
    "break",
    "continue",
    "call_function",
    "call_function_value",
    "return",
    "comment",
    "number",
    "text",
    "boolean",
    "arithmetic",
    "random_int",
    "random_float",
    "compare",
    "logic_operation",
    "logic_not",
    "ternary",
    "text_join",
    "text_length",
    "text_contains",
    "text_substring",
    "to_number",
    "to_text",
    "math_single",
    "math_minmax",
    "function_param",
    "list_create_empty",
    "list_create_with",
    "list_length",
    "list_get",
    "list_set",
    "list_append",
    "list_for_each",
]

InputName = Literal[
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
]

StickName = Literal["LEFT_STICK", "RIGHT_STICK"]


# ======================================================================
# Statement nodes
# ======================================================================

@dataclass(slots=True)
class SequenceNode:
    type: Literal["sequence"]
    children: list[StatementNode]
    block_id: str | None = None


@dataclass(slots=True)
class PressNode:
    type: Literal["press"]
    button: InputName
    duration: float
    wait: float
    block_id: str | None = None


@dataclass(slots=True)
class PressManyNode:
    type: Literal["press_many"]
    buttons: list[InputName]
    duration: float
    wait: float
    block_id: str | None = None


@dataclass(slots=True)
class MashNode:
    type: Literal["mash"]
    button: InputName
    count: int
    duration: float
    interval: float
    block_id: str | None = None


@dataclass(slots=True)
class HoldNode:
    type: Literal["hold"]
    button: InputName
    duration: float
    block_id: str | None = None


@dataclass(slots=True)
class HoldEndNode:
    type: Literal["hold_end"]
    button: InputName
    block_id: str | None = None


@dataclass(slots=True)
class StickMoveNode:
    type: Literal["stick_move"]
    stick: StickName
    angle: float
    radius: float
    duration: float
    wait: float
    block_id: str | None = None


@dataclass(slots=True)
class StickHoldNode:
    type: Literal["stick_hold"]
    stick: StickName
    angle: float
    radius: float
    duration: float
    block_id: str | None = None


@dataclass(slots=True)
class StickReleaseNode:
    type: Literal["stick_release"]
    stick: StickName
    block_id: str | None = None


@dataclass(slots=True)
class WaitNode:
    type: Literal["wait"]
    seconds: float
    block_id: str | None = None


@dataclass(slots=True)
class WaitUntilImageNode:
    type: Literal["wait_until_image"]
    template: str
    threshold: float
    use_gray: bool
    poll_interval: float
    timeout_seconds: float | None = None
    trim: list[int] | None = None
    block_id: str | None = None


@dataclass(slots=True)
class WaitUntilNotImageNode:
    type: Literal["wait_until_not_image"]
    template: str
    threshold: float
    use_gray: bool
    poll_interval: float
    timeout_seconds: float | None = None
    trim: list[int] | None = None
    block_id: str | None = None


@dataclass(slots=True)
class PrintNode:
    type: Literal["print"]
    message: str
    block_id: str | None = None


@dataclass(slots=True)
class PrintValueNode:
    type: Literal["print_value"]
    value: ValueNode
    block_id: str | None = None


@dataclass(slots=True)
class IfNode:
    type: Literal["if"]
    condition: ValueNode
    then_body: list[StatementNode]
    else_body: list[StatementNode]
    block_id: str | None = None


@dataclass(slots=True)
class RepeatNode:
    type: Literal["repeat"]
    count: int
    body: list[StatementNode]
    block_id: str | None = None


@dataclass(slots=True)
class WhileAliveNode:
    type: Literal["while_alive"]
    body: list[StatementNode]
    block_id: str | None = None


@dataclass(slots=True)
class WhileConditionNode:
    type: Literal["while_condition"]
    condition: ValueNode
    body: list[StatementNode]
    block_id: str | None = None


@dataclass(slots=True)
class WhileImageExistsNode:
    type: Literal["while_image_exists"]
    body: list[StatementNode]
    template: str
    threshold: float
    use_gray: bool
    poll_interval: float
    timeout_seconds: float | None = None
    trim: list[int] | None = None
    block_id: str | None = None


@dataclass(slots=True)
class WhileNotImageExistsNode:
    type: Literal["while_not_image_exists"]
    body: list[StatementNode]
    template: str
    threshold: float
    use_gray: bool
    poll_interval: float
    timeout_seconds: float | None = None
    trim: list[int] | None = None
    block_id: str | None = None


@dataclass(slots=True)
class FinishNode:
    type: Literal["finish"]
    block_id: str | None = None


@dataclass(slots=True)
class SetVariableNode:
    type: Literal["set_variable"]
    name: str
    value: ValueNode
    block_id: str | None = None


@dataclass(slots=True)
class ChangeVariableNode:
    type: Literal["change_variable"]
    name: str
    delta: ValueNode
    block_id: str | None = None


@dataclass(slots=True)
class ForRangeNode:
    type: Literal["for_range"]
    var_name: str
    from_value: int
    to_value: int
    step: int
    body: list[StatementNode]
    block_id: str | None = None


@dataclass(slots=True)
class BreakNode:
    type: Literal["break"]
    block_id: str | None = None


@dataclass(slots=True)
class ContinueNode:
    type: Literal["continue"]
    block_id: str | None = None


@dataclass(slots=True)
class CallFunctionNode:
    type: Literal["call_function"]
    name: str
    args: dict[str, ValueNode | None]
    block_id: str | None = None


@dataclass(slots=True)
class ReturnNode:
    type: Literal["return"]
    value: ValueNode | None = None
    block_id: str | None = None


@dataclass(slots=True)
class ListSetNode:
    type: Literal["list_set"]
    var_name: str
    index: ValueNode
    value: ValueNode
    block_id: str | None = None


@dataclass(slots=True)
class ListAppendNode:
    type: Literal["list_append"]
    var_name: str
    value: ValueNode
    block_id: str | None = None


@dataclass(slots=True)
class ListForEachNode:
    type: Literal["list_for_each"]
    var_name: str
    list: ValueNode
    body: list[StatementNode]
    block_id: str | None = None


@dataclass(slots=True)
class CommentNode:
    type: Literal["comment"]
    text: str
    block_id: str | None = None


# ======================================================================
# Value nodes (expressions)
# ======================================================================

@dataclass(slots=True)
class ImageExistsNode:
    type: Literal["image_exists"]
    template: str
    threshold: float
    use_gray: bool
    trim: list[int] | None = None
    block_id: str | None = None


@dataclass(slots=True)
class NumberNode:
    type: Literal["number"]
    value: float
    block_id: str | None = None


@dataclass(slots=True)
class TextNode:
    type: Literal["text"]
    value: str
    block_id: str | None = None


@dataclass(slots=True)
class BooleanNode:
    type: Literal["boolean"]
    value: bool
    block_id: str | None = None


@dataclass(slots=True)
class GetVariableNode:
    type: Literal["get_variable"]
    name: str
    block_id: str | None = None


@dataclass(slots=True)
class ArithmeticNode:
    type: Literal["arithmetic"]
    op: str
    left: ValueNode
    right: ValueNode
    block_id: str | None = None


@dataclass(slots=True)
class RandomIntNode:
    type: Literal["random_int"]
    min: int
    max: int
    block_id: str | None = None


@dataclass(slots=True)
class RandomFloatNode:
    type: Literal["random_float"]
    min: float
    max: float
    block_id: str | None = None


@dataclass(slots=True)
class CompareNode:
    type: Literal["compare"]
    op: str
    left: ValueNode
    right: ValueNode
    block_id: str | None = None


@dataclass(slots=True)
class LogicOperationNode:
    type: Literal["logic_operation"]
    op: str
    left: ValueNode
    right: ValueNode
    block_id: str | None = None


@dataclass(slots=True)
class LogicNotNode:
    type: Literal["logic_not"]
    value: ValueNode
    block_id: str | None = None


@dataclass(slots=True)
class TernaryNode:
    type: Literal["ternary"]
    condition: ValueNode
    true_value: ValueNode
    false_value: ValueNode
    block_id: str | None = None


@dataclass(slots=True)
class TextJoinNode:
    type: Literal["text_join"]
    left: ValueNode
    right: ValueNode
    block_id: str | None = None


@dataclass(slots=True)
class TextLengthNode:
    type: Literal["text_length"]
    value: ValueNode
    block_id: str | None = None


@dataclass(slots=True)
class TextContainsNode:
    type: Literal["text_contains"]
    text: ValueNode
    search: ValueNode
    block_id: str | None = None


@dataclass(slots=True)
class TextSubstringNode:
    type: Literal["text_substring"]
    text: ValueNode
    start: ValueNode
    length: ValueNode
    block_id: str | None = None


@dataclass(slots=True)
class ToNumberNode:
    type: Literal["to_number"]
    value: ValueNode
    block_id: str | None = None


@dataclass(slots=True)
class ToTextNode:
    type: Literal["to_text"]
    value: ValueNode
    block_id: str | None = None


@dataclass(slots=True)
class MathSingleNode:
    type: Literal["math_single"]
    op: str
    value: ValueNode
    block_id: str | None = None


@dataclass(slots=True)
class MathMinMaxNode:
    type: Literal["math_minmax"]
    op: str
    left: ValueNode
    right: ValueNode
    block_id: str | None = None


@dataclass(slots=True)
class FunctionParamNode:
    type: Literal["function_param"]
    name: str
    block_id: str | None = None


@dataclass(slots=True)
class CallFunctionValueNode:
    type: Literal["call_function_value"]
    name: str
    args: dict[str, ValueNode | None]
    block_id: str | None = None


@dataclass(slots=True)
class ListCreateEmptyNode:
    type: Literal["list_create_empty"]
    block_id: str | None = None


@dataclass(slots=True)
class ListCreateWithNode:
    type: Literal["list_create_with"]
    items: list[ValueNode]
    block_id: str | None = None


@dataclass(slots=True)
class ListLengthNode:
    type: Literal["list_length"]
    list: ValueNode
    block_id: str | None = None


@dataclass(slots=True)
class ListGetNode:
    type: Literal["list_get"]
    list: ValueNode
    index: ValueNode
    block_id: str | None = None


# ======================================================================
# Type aliases
# ======================================================================

StatementNode: TypeAlias = (
    SequenceNode
    | PressNode
    | PressManyNode
    | MashNode
    | HoldNode
    | HoldEndNode
    | StickMoveNode
    | StickHoldNode
    | StickReleaseNode
    | WaitNode
    | WaitUntilImageNode
    | WaitUntilNotImageNode
    | PrintNode
    | PrintValueNode
    | IfNode
    | RepeatNode
    | WhileAliveNode
    | WhileConditionNode
    | WhileImageExistsNode
    | WhileNotImageExistsNode
    | FinishNode
    | SetVariableNode
    | ChangeVariableNode
    | ForRangeNode
    | BreakNode
    | ContinueNode
    | CallFunctionNode
    | ReturnNode
    | ListSetNode
    | ListAppendNode
    | ListForEachNode
    | CommentNode
)

ValueNode: TypeAlias = (
    ImageExistsNode
    | NumberNode
    | TextNode
    | BooleanNode
    | GetVariableNode
    | ArithmeticNode
    | RandomIntNode
    | RandomFloatNode
    | CompareNode
    | LogicOperationNode
    | LogicNotNode
    | TernaryNode
    | TextJoinNode
    | TextLengthNode
    | TextContainsNode
    | TextSubstringNode
    | ToNumberNode
    | ToTextNode
    | MathSingleNode
    | MathMinMaxNode
    | FunctionParamNode
    | CallFunctionValueNode
    | ListCreateEmptyNode
    | ListCreateWithNode
    | ListLengthNode
    | ListGetNode
)

# backward compatibility
ConditionNode: TypeAlias = ValueNode


# ======================================================================
# Function definition & Program model
# ======================================================================

@dataclass(slots=True)
class FunctionDefinition:
    name: str
    params: list[str]
    body: list[StatementNode]
    block_id: str | None = None


@dataclass(slots=True)
class ProgramModel:
    version: ProgramVersion
    root: SequenceNode
    functions: dict[str, FunctionDefinition] = field(default_factory=dict)
