"""Runtime executor for Visual Macro programs."""

from __future__ import annotations

import time
import traceback
from typing import TypeAlias, cast

from PySide6.QtCore import QObject, Signal, Slot

from libs.CommandBase import CommandBase, StopThread
from libs.keys import Button, Direction, Hat, Stick
from libs.visual_macro.errors import VisualMacroRuntimeError
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
    ProgramModel,
    PrintNode,
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

InputSymbol: TypeAlias = Button | Hat | Direction


class VisualMacroRuntime(CommandBase):
    """Execute a typed Visual Macro program on top of CommandBase."""

    highlight_block_requested = Signal(str)
    clear_block_highlight_requested = Signal()

    def __init__(self, program: ProgramModel, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._program: ProgramModel = program

    @Slot()
    def run(self) -> None:
        try:
            self.do()
            self.finish()
        except StopThread:
            self.stop_function.emit(True)
            self.info("Command finished successfully", force=True)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            traceback.print_exc()
            self.error(f"{exc} エラーが発生しました", force=True)
            self.stop_function.emit(True)
        finally:
            self._clear_highlight()

    def do(self) -> None:
        self._execute_sequence(self._program.root)

    def _highlight_node(self, node: object) -> None:
        block_id = getattr(node, "block_id", None)
        if isinstance(block_id, str) and block_id:
            self.highlight_block_requested.emit(block_id)

    def _clear_highlight(self) -> None:
        self.clear_block_highlight_requested.emit()

    def _execute_statement(self, node: StatementNode) -> None:
        self.check_if_alive()
        self._highlight_node(node)

        if isinstance(node, SequenceNode):
            self._execute_sequence(node)
            return
        if isinstance(node, PressNode):
            self._execute_press(node)
            return
        if isinstance(node, PressManyNode):
            self._execute_press_many(node)
            return
        if isinstance(node, MashNode):
            self._execute_mash(node)
            return
        if isinstance(node, HoldNode):
            self._execute_hold(node)
            return
        if isinstance(node, HoldEndNode):
            self._execute_hold_end(node)
            return
        if isinstance(node, StickMoveNode):
            self._execute_stick_move(node)
            return
        if isinstance(node, StickHoldNode):
            self._execute_stick_hold(node)
            return
        if isinstance(node, StickReleaseNode):
            self._execute_stick_release(node)
            return
        if isinstance(node, WaitNode):
            self._execute_wait(node)
            return
        if isinstance(node, WaitUntilImageNode):
            self._execute_wait_until_image(node)
            return
        if isinstance(node, WaitUntilNotImageNode):
            self._execute_wait_until_not_image(node)
            return
        if isinstance(node, PrintNode):
            self._execute_print(node)
            return
        if isinstance(node, IfNode):
            self._execute_if(node)
            return
        if isinstance(node, RepeatNode):
            self._execute_repeat(node)
            return
        if isinstance(node, WhileAliveNode):
            self._execute_while_alive(node)
            return
        if isinstance(node, FinishNode):
            self._execute_finish(node)
            return

        raise VisualMacroRuntimeError(
            f"Unsupported statement node: {type(node).__name__}"
        )

    def _execute_sequence(self, node: SequenceNode) -> None:
        for child in node.children:
            self.check_if_alive()
            self._execute_statement(child)

    def _execute_press(self, node: PressNode) -> None:
        button_symbol = self._resolve_input(node.button)
        self.press(button_symbol, duration=node.duration, wait=node.wait)

    def _execute_press_many(self, node: PressManyNode) -> None:
        buttons = [self._resolve_input(name) for name in node.buttons]
        self.press(buttons, duration=node.duration, wait=node.wait)

    def _execute_mash(self, node: MashNode) -> None:
        button_symbol = self._resolve_input(node.button)
        self.pressRep(
            button_symbol,
            repeat=node.count,
            duration=node.duration,
            interval=node.interval,
            wait=0.0,
        )

    def _execute_hold(self, node: HoldNode) -> None:
        button_symbol = self._resolve_input(node.button)
        self.hold(button_symbol, duration=node.duration)

    def _execute_hold_end(self, node: HoldEndNode) -> None:
        button_symbol = self._resolve_input(node.button)
        self.holdEnd(button_symbol)

    def _execute_stick_move(self, node: StickMoveNode) -> None:
        direction = self._build_direction(node.stick, node.angle, node.radius)
        self.press(direction, duration=node.duration, wait=node.wait)

    def _execute_stick_hold(self, node: StickHoldNode) -> None:
        direction = self._build_direction(node.stick, node.angle, node.radius)
        self.hold(direction, duration=node.duration)

    def _execute_stick_release(self, node: StickReleaseNode) -> None:
        direction = self._build_direction(node.stick, 0.0, 0.0)
        self.holdEnd(direction)

    def _execute_wait(self, node: WaitNode) -> None:
        self.wait(node.seconds)

    def _execute_wait_until_image(self, node: WaitUntilImageNode) -> None:
        self._wait_for_template(
            template=node.template,
            threshold=node.threshold,
            use_gray=node.use_gray,
            poll_interval=node.poll_interval,
            timeout_seconds=node.timeout_seconds,
            target_state=True,
        )

    def _execute_wait_until_not_image(self, node: WaitUntilNotImageNode) -> None:
        self._wait_for_template(
            template=node.template,
            threshold=node.threshold,
            use_gray=node.use_gray,
            poll_interval=node.poll_interval,
            timeout_seconds=node.timeout_seconds,
            target_state=False,
        )

    def _execute_print(self, node: PrintNode) -> None:
        self.info(node.message)

    def _wait_for_template(
        self,
        *,
        template: str,
        threshold: float,
        use_gray: bool,
        poll_interval: float,
        timeout_seconds: float | None,
        target_state: bool,
    ) -> None:
        start = time.perf_counter()
        while True:
            self.check_if_alive()

            found = bool(
                self.is_contain_template(
                    template_path=template,
                    threshold=threshold,
                    use_gray=use_gray,
                )
            )
            if found == target_state:
                return

            if timeout_seconds is not None:
                elapsed = time.perf_counter() - start
                if elapsed >= timeout_seconds:
                    self.warning(
                        f"Template wait timeout: template={template}, target_state={target_state}"
                    )
                    return

            self.wait(poll_interval)

    def _execute_if(self, node: IfNode) -> None:
        condition_result = self._evaluate_condition(node.condition)
        selected_body = node.then_body if condition_result else node.else_body
        for statement in selected_body:
            self.check_if_alive()
            self._execute_statement(statement)

    def _execute_repeat(self, node: RepeatNode) -> None:
        for _ in range(node.count):
            self.check_if_alive()
            for statement in node.body:
                self.check_if_alive()
                self._execute_statement(statement)

    def _execute_while_alive(self, node: WhileAliveNode) -> None:
        while True:
            self.check_if_alive()
            for statement in node.body:
                self.check_if_alive()
                self._execute_statement(statement)

    def _execute_finish(self, node: FinishNode) -> None:
        _ = node
        self.finish()

    def _evaluate_condition(self, node: ConditionNode) -> bool:
        self.check_if_alive()
        self._highlight_node(node)

        if isinstance(node, ImageExistsNode):
            return self._evaluate_image_exists(node)

        raise VisualMacroRuntimeError(
            f"Unsupported condition node: {type(node).__name__}"
        )

    def _evaluate_image_exists(self, node: ImageExistsNode) -> bool:
        return bool(
            self.is_contain_template(
                template_path=node.template,
                threshold=node.threshold,
                use_gray=node.use_gray,
            )
        )

    def _resolve_input(self, input_name: InputName) -> InputSymbol:
        if hasattr(Button, input_name):
            return cast(InputSymbol, getattr(Button, input_name))
        if hasattr(Hat, input_name):
            return cast(InputSymbol, getattr(Hat, input_name))
        raise VisualMacroRuntimeError(f"Unsupported input name: {input_name!r}")

    def _resolve_stick(self, stick_name: StickName) -> Stick:
        if stick_name == "LEFT_STICK":
            return Stick.LEFT
        if stick_name == "RIGHT_STICK":
            return Stick.RIGHT
        raise VisualMacroRuntimeError(f"Unsupported stick name: {stick_name!r}")

    def _build_direction(
        self,
        stick_name: StickName,
        angle: float,
        radius: float,
    ) -> Direction:
        stick = self._resolve_stick(stick_name)
        clamped_radius = max(0.0, min(float(radius), 1.0))
        return Direction(stick, float(angle), clamped_radius)
