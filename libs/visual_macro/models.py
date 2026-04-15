from __future__ import annotations

from dataclasses import dataclass
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
    "if",
    "repeat",
    "while_alive",
    "image_exists",
    "finish",
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


@dataclass(slots=True)
class SequenceNode:
    type: Literal["sequence"]
    children: list["StatementNode"]
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
    block_id: str | None = None


@dataclass(slots=True)
class WaitUntilNotImageNode:
    type: Literal["wait_until_not_image"]
    template: str
    threshold: float
    use_gray: bool
    poll_interval: float
    timeout_seconds: float | None = None
    block_id: str | None = None


@dataclass(slots=True)
class ImageExistsNode:
    type: Literal["image_exists"]
    template: str
    threshold: float
    use_gray: bool
    block_id: str | None = None


@dataclass(slots=True)
class IfNode:
    type: Literal["if"]
    condition: "ConditionNode"
    then_body: list["StatementNode"]
    else_body: list["StatementNode"]
    block_id: str | None = None


@dataclass(slots=True)
class RepeatNode:
    type: Literal["repeat"]
    count: int
    body: list["StatementNode"]
    block_id: str | None = None


@dataclass(slots=True)
class WhileAliveNode:
    type: Literal["while_alive"]
    body: list["StatementNode"]
    block_id: str | None = None


@dataclass(slots=True)
class FinishNode:
    type: Literal["finish"]
    block_id: str | None = None


@dataclass(slots=True)
class PrintNode:
    type: Literal["print"]
    message: str
    block_id: str | None = None


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
    | IfNode
    | RepeatNode
    | WhileAliveNode
    | FinishNode
)

ConditionNode: TypeAlias = ImageExistsNode


@dataclass(slots=True)
class ProgramModel:
    version: ProgramVersion
    root: SequenceNode
