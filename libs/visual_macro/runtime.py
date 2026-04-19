"""Runtime executor for Visual Macro programs."""

from __future__ import annotations

import math
import operator
import random
import time
import traceback
from typing import TypeAlias, cast

from PySide6.QtCore import QObject, Signal, Slot

from libs.CommandBase import CommandBase, StopThread
from libs.keys import Button, Direction, Hat, Stick
from libs.visual_macro.errors import VisualMacroRuntimeError
from libs.visual_macro.models import (
    ArithmeticNode, BooleanNode, BreakNode, CallFunctionNode,
    CallFunctionValueNode, ChangeVariableNode, CommentNode, CompareNode,
    ConditionNode, ContinueNode, FinishNode, ForRangeNode, FunctionParamNode,
    GetVariableNode, HoldEndNode, HoldNode, IfNode, ImageExistsNode,
    InputName, ListAppendNode, ListCreateEmptyNode,
    ListCreateWithNode, ListForEachNode, ListGetNode, ListLengthNode,
    ListSetNode, LogicNotNode, LogicOperationNode, MashNode, MathMinMaxNode,
    MathSingleNode, NumberNode, PressManyNode, PressNode, PrintNode,
    PrintValueNode, ProgramModel, RandomFloatNode, RandomIntNode, RepeatNode,
    ReturnNode, SequenceNode, SetVariableNode, StatementNode, StickHoldNode,
    StickMoveNode, StickName, StickReleaseNode, TernaryNode,
    TextContainsNode, TextJoinNode, TextLengthNode, TextNode,
    TextSubstringNode, ToNumberNode, ToTextNode, ValueNode, WaitNode,
    WaitUntilImageNode, WaitUntilNotImageNode, WhileAliveNode,
    WhileConditionNode, WhileNotImageExistsNode, WhileImageExistsNode,
)

InputSymbol: TypeAlias = Button | Hat | Direction

_ARITHMETIC_OPERATORS = {
    "ADD": operator.add, "SUB": operator.sub, "MUL": operator.mul,
    "DIV": operator.truediv, "MOD": operator.mod,
}
_COMPARE_OPERATORS = {
    "EQ": operator.eq, "NEQ": operator.ne, "LT": operator.lt,
    "GT": operator.gt, "LTE": operator.le, "GTE": operator.ge,
}
_MATH_SINGLE_FUNCS = {
    "ABS": abs, "ROUND": round, "FLOOR": math.floor, "CEIL": math.ceil,
}
_MAX_CALL_DEPTH = 64


class _LoopBreak(Exception):
    """Raised by a break node to exit the innermost loop."""

class _LoopContinue(Exception):
    """Raised by a continue node to skip to the next loop iteration."""

class _FunctionReturn(Exception):
    """Raised by a return node to exit the current function with a value."""
    def __init__(self, value: object = None) -> None:
        super().__init__()
        self.value = value


class VisualMacroRuntime(CommandBase):
    """Execute a typed Visual Macro program on top of CommandBase."""

    highlight_block_requested = Signal(str)
    clear_block_highlight_requested = Signal()

    def __init__(self, program: ProgramModel, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._program: ProgramModel = program
        self._variables: dict[str, object] = {}
        self._call_stack: list[dict[str, object]] = []

    @Slot()
    def run(self) -> None:
        try:
            self.do()
            self.finish()
        except StopThread:
            self.stop_function.emit(True)
            self.info("Command finished successfully", force=True)
        except Exception as exc:
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

    # ── 文の実行 ──

    def _execute_statement(self, node: StatementNode) -> None:
        self.check_if_alive()
        self._highlight_node(node)
        if isinstance(node, SequenceNode): self._execute_sequence(node); return
        if isinstance(node, PressNode): self._execute_press(node); return
        if isinstance(node, PressManyNode): self._execute_press_many(node); return
        if isinstance(node, MashNode): self._execute_mash(node); return
        if isinstance(node, HoldNode): self._execute_hold(node); return
        if isinstance(node, HoldEndNode): self._execute_hold_end(node); return
        if isinstance(node, StickMoveNode): self._execute_stick_move(node); return
        if isinstance(node, StickHoldNode): self._execute_stick_hold(node); return
        if isinstance(node, StickReleaseNode): self._execute_stick_release(node); return
        if isinstance(node, WaitNode): self._execute_wait(node); return
        if isinstance(node, WaitUntilImageNode): self._execute_wait_until_image(node); return
        if isinstance(node, WaitUntilNotImageNode): self._execute_wait_until_not_image(node); return
        if isinstance(node, PrintNode): self._execute_print(node); return
        if isinstance(node, IfNode): self._execute_if(node); return
        if isinstance(node, RepeatNode): self._execute_repeat(node); return
        if isinstance(node, WhileAliveNode): self._execute_while_alive(node); return
        if isinstance(node, WhileImageExistsNode): self._execute_while_image_exists(node); return
        if isinstance(node, WhileNotImageExistsNode): self._execute_while_not_image_exists(node); return
        if isinstance(node, FinishNode): self._execute_finish(node); return
        if isinstance(node, SetVariableNode): self._execute_set_variable(node); return
        if isinstance(node, ChangeVariableNode): self._execute_change_variable(node); return
        if isinstance(node, WhileConditionNode): self._execute_while_condition(node); return
        if isinstance(node, PrintValueNode): self._execute_print_value(node); return
        if isinstance(node, ForRangeNode): self._execute_for_range(node); return
        if isinstance(node, BreakNode): self._execute_break(node); return
        if isinstance(node, ContinueNode): self._execute_continue(node); return
        if isinstance(node, CallFunctionNode): self._execute_call_function(node); return
        if isinstance(node, ReturnNode): self._execute_return(node); return
        if isinstance(node, ListSetNode): self._execute_list_set(node); return
        if isinstance(node, ListAppendNode): self._execute_list_append(node); return
        if isinstance(node, ListForEachNode): self._execute_list_for_each(node); return
        if isinstance(node, CommentNode): return  # no-op
        raise VisualMacroRuntimeError(f"Unsupported statement node: {type(node).__name__}")

    def _execute_sequence(self, node: SequenceNode) -> None:
        for child in node.children:
            self.check_if_alive()
            self._execute_statement(child)

    def _execute_press(self, node: PressNode) -> None:
        self.press(self._resolve_input(node.button), duration=node.duration, wait=node.wait)

    def _execute_press_many(self, node: PressManyNode) -> None:
        self.press([self._resolve_input(n) for n in node.buttons], duration=node.duration, wait=node.wait)

    def _execute_mash(self, node: MashNode) -> None:
        self.pressRep(self._resolve_input(node.button), repeat=node.count, duration=node.duration, interval=node.interval, wait=0.0)

    def _execute_hold(self, node: HoldNode) -> None:
        self.hold(self._resolve_input(node.button), duration=node.duration)

    def _execute_hold_end(self, node: HoldEndNode) -> None:
        self.holdEnd(self._resolve_input(node.button))

    def _execute_stick_move(self, node: StickMoveNode) -> None:
        self.press(self._build_direction(node.stick, node.angle, node.radius), duration=node.duration, wait=node.wait)

    def _execute_stick_hold(self, node: StickHoldNode) -> None:
        self.hold(self._build_direction(node.stick, node.angle, node.radius), duration=node.duration)

    def _execute_stick_release(self, node: StickReleaseNode) -> None:
        self.holdEnd(self._build_direction(node.stick, 0.0, 0.0))

    def _execute_wait(self, node: WaitNode) -> None:
        self.wait(node.seconds)

    def _execute_wait_until_image(self, node: WaitUntilImageNode) -> None:
        self._wait_for_template(template=node.template, threshold=node.threshold, use_gray=node.use_gray, trim=node.trim, poll_interval=node.poll_interval, timeout_seconds=node.timeout_seconds, target_state=True)

    def _execute_wait_until_not_image(self, node: WaitUntilNotImageNode) -> None:
        self._wait_for_template(template=node.template, threshold=node.threshold, use_gray=node.use_gray, trim=node.trim, poll_interval=node.poll_interval, timeout_seconds=node.timeout_seconds, target_state=False)

    def _execute_print(self, node: PrintNode) -> None:
        self.info(node.message)

    def _wait_for_template(self, *, template: str, threshold: float, use_gray: bool, trim: list[int] | None = None, poll_interval: float, timeout_seconds: float | None, target_state: bool) -> None:
        start = time.perf_counter()
        while True:
            self.check_if_alive()
            found = bool(self.is_contain_template(template_path=template, threshold=threshold, use_gray=use_gray, trim=trim))
            if found == target_state: return
            if timeout_seconds is not None and (time.perf_counter() - start) >= timeout_seconds:
                self.warning(f"Template wait timeout: template={template}, target_state={target_state}"); return
            self.wait(poll_interval)

    def _execute_if(self, node: IfNode) -> None:
        body = node.then_body if bool(self._evaluate_value(node.condition)) else node.else_body
        for s in body: self.check_if_alive(); self._execute_statement(s)

    def _execute_repeat(self, node: RepeatNode) -> None:
        for _ in range(node.count):
            self.check_if_alive()
            try:
                for s in node.body: self.check_if_alive(); self._execute_statement(s)
            except _LoopContinue: continue
            except _LoopBreak: break

    def _execute_while_alive(self, node: WhileAliveNode) -> None:
        while True:
            self.check_if_alive()
            try:
                for s in node.body: self.check_if_alive(); self._execute_statement(s)
            except _LoopContinue: continue
            except _LoopBreak: break

    def _execute_while_image_exists(self, node: WhileImageExistsNode) -> None:
        start = time.perf_counter()
        while True:
            self.check_if_alive()
            if not bool(self.is_contain_template(template_path=node.template, threshold=node.threshold, use_gray=node.use_gray, trim=node.trim)): return
            if node.timeout_seconds is not None and (time.perf_counter() - start) >= node.timeout_seconds:
                self.warning(f"while_image_exists timeout: template={node.template}"); return
            try:
                for s in node.body: self.check_if_alive(); self._execute_statement(s)
                self.wait(node.poll_interval)
            except _LoopContinue: self.wait(node.poll_interval); continue
            except _LoopBreak: break

    def _execute_while_not_image_exists(self, node: WhileNotImageExistsNode) -> None:
        start = time.perf_counter()
        while True:
            self.check_if_alive()
            if bool(self.is_contain_template(template_path=node.template, threshold=node.threshold, use_gray=node.use_gray, trim=node.trim)): return
            if node.timeout_seconds is not None and (time.perf_counter() - start) >= node.timeout_seconds:
                self.warning(f"while_not_image_exists timeout: template={node.template}"); return
            try:
                for s in node.body: self.check_if_alive(); self._execute_statement(s)
                self.wait(node.poll_interval)
            except _LoopContinue: self.wait(node.poll_interval); continue
            except _LoopBreak: break

    def _execute_finish(self, node: FinishNode) -> None:
        _ = node; self.finish()

    # ── 変数操作 ──

    def _execute_set_variable(self, node: SetVariableNode) -> None:
        self._variables[node.name] = self._evaluate_value(node.value)

    def _execute_change_variable(self, node: ChangeVariableNode) -> None:
        cur = self._variables.get(node.name, 0); delta = self._evaluate_value(node.delta)
        if not isinstance(cur, (int, float)): cur = 0
        if not isinstance(delta, (int, float)): delta = 0
        self._variables[node.name] = cur + delta

    def _execute_while_condition(self, node: WhileConditionNode) -> None:
        while True:
            self.check_if_alive()
            if not self._evaluate_value(node.condition): return
            try:
                for s in node.body: self.check_if_alive(); self._execute_statement(s)
            except _LoopContinue: continue
            except _LoopBreak: break

    def _execute_print_value(self, node: PrintValueNode) -> None:
        self.info(str(self._evaluate_value(node.value)))

    def _execute_for_range(self, node: ForRangeNode) -> None:
        if node.step == 0: self.warning("for_range: step が 0 のためスキップします"); return
        i = node.from_value
        while (node.step > 0 and i <= node.to_value) or (node.step < 0 and i >= node.to_value):
            self.check_if_alive(); self._variables[node.var_name] = i
            try:
                for s in node.body: self.check_if_alive(); self._execute_statement(s)
            except _LoopContinue: pass
            except _LoopBreak: break
            i += node.step

    def _execute_break(self, node: BreakNode) -> None:
        _ = node; raise _LoopBreak()

    def _execute_continue(self, node: ContinueNode) -> None:
        _ = node; raise _LoopContinue()

    # ── 関数呼び出し ──

    def _execute_call_function(self, node: CallFunctionNode) -> None:
        func_def = self._program.functions.get(node.name)
        if func_def is None: raise VisualMacroRuntimeError(f"未定義の関数です: {node.name!r}")
        if len(self._call_stack) >= _MAX_CALL_DEPTH: raise VisualMacroRuntimeError(f"関数呼び出しの深さが上限 ({_MAX_CALL_DEPTH}) を超えました")
        local_scope = {p: self._evaluate_value(node.args.get(p)) for p in func_def.params}
        self._call_stack.append(local_scope)
        try:
            self._highlight_node(func_def)
            for s in func_def.body: self.check_if_alive(); self._execute_statement(s)
        except _FunctionReturn:
            pass  # statement版は戻り値を捨てる
        finally:
            self._call_stack.pop()

    def _execute_return(self, node: ReturnNode) -> None:
        raise _FunctionReturn(self._evaluate_value(node.value))

    # ── リスト操作 ──

    def _execute_list_set(self, node: ListSetNode) -> None:
        lst = self._variables.get(node.var_name)
        if not isinstance(lst, list): self.warning(f"list_set: 変数 {node.var_name!r} はリストではありません"); return
        idx_val = self._evaluate_value(node.index); val = self._evaluate_value(node.value)
        idx = int(idx_val) if isinstance(idx_val, (int, float)) else 0
        if 0 <= idx < len(lst): lst[idx] = val
        else: self.warning(f"list_set: インデックス {idx} は範囲外です (リスト長: {len(lst)})")

    def _execute_list_append(self, node: ListAppendNode) -> None:
        lst = self._variables.get(node.var_name)
        if not isinstance(lst, list):
            lst = []; self._variables[node.var_name] = lst
        lst.append(self._evaluate_value(node.value))

    def _execute_list_for_each(self, node: ListForEachNode) -> None:
        lst_val = self._evaluate_value(node.list)
        if not isinstance(lst_val, list): self.warning("list_for_each: 対象がリストではありません"); return
        for item in lst_val:
            self.check_if_alive(); self._variables[node.var_name] = item
            try:
                for s in node.body: self.check_if_alive(); self._execute_statement(s)
            except _LoopContinue: continue
            except _LoopBreak: break

    # ── 値の評価 ──

    def _evaluate_value(self, node: ValueNode | None) -> object:
        if node is None: return None
        self.check_if_alive(); self._highlight_node(node)
        if isinstance(node, ImageExistsNode): return self._evaluate_image_exists(node)
        if isinstance(node, NumberNode): return node.value
        if isinstance(node, TextNode): return node.value
        if isinstance(node, BooleanNode): return node.value
        if isinstance(node, GetVariableNode): return self._variables.get(node.name)
        if isinstance(node, ArithmeticNode): return self._evaluate_arithmetic(node)
        if isinstance(node, RandomIntNode): return random.randint(node.min, node.max)
        if isinstance(node, RandomFloatNode): return random.uniform(node.min, node.max)
        if isinstance(node, CompareNode): return self._evaluate_compare(node)
        if isinstance(node, LogicOperationNode): return self._evaluate_logic_operation(node)
        if isinstance(node, LogicNotNode): return not bool(self._evaluate_value(node.value))
        if isinstance(node, TernaryNode):
            return self._evaluate_value(node.true_value) if bool(self._evaluate_value(node.condition)) else self._evaluate_value(node.false_value)
        if isinstance(node, TextJoinNode):
            l = self._evaluate_value(node.left); r = self._evaluate_value(node.right)
            return str(l if l is not None else "") + str(r if r is not None else "")
        if isinstance(node, TextLengthNode):
            v = self._evaluate_value(node.value); return len(str(v)) if v is not None else 0
        if isinstance(node, TextContainsNode):
            txt = self._evaluate_value(node.text); srch = self._evaluate_value(node.search)
            return str(srch or "") in str(txt or "")
        if isinstance(node, TextSubstringNode): return self._evaluate_text_substring(node)
        if isinstance(node, FunctionParamNode): return self._evaluate_function_param(node)
        if isinstance(node, CallFunctionValueNode): return self._evaluate_call_function_value(node)
        if isinstance(node, ListCreateEmptyNode): return []
        if isinstance(node, ListCreateWithNode): return [self._evaluate_value(item) for item in node.items]
        if isinstance(node, ListLengthNode):
            v = self._evaluate_value(node.list); return len(v) if isinstance(v, list) else 0
        if isinstance(node, ListGetNode): return self._evaluate_list_get(node)
        if isinstance(node, ToNumberNode): return self._evaluate_to_number(node)
        if isinstance(node, ToTextNode): return str(self._evaluate_value(node.value) or "")
        if isinstance(node, MathSingleNode): return self._evaluate_math_single(node)
        if isinstance(node, MathMinMaxNode): return self._evaluate_math_minmax(node)
        raise VisualMacroRuntimeError(f"Unsupported value node: {type(node).__name__}")

    # backward compatibility
    def _evaluate_condition(self, node: ConditionNode) -> bool:
        return bool(self._evaluate_value(node))

    def _evaluate_image_exists(self, node: ImageExistsNode) -> bool:
        return bool(self.is_contain_template(template_path=node.template, threshold=node.threshold, use_gray=node.use_gray, trim=node.trim))

    def _evaluate_arithmetic(self, node: ArithmeticNode) -> float:
        lv = self._evaluate_value(node.left); rv = self._evaluate_value(node.right)
        ln = float(lv) if isinstance(lv, (int, float)) else 0.0
        rn = float(rv) if isinstance(rv, (int, float)) else 0.0
        op_func = _ARITHMETIC_OPERATORS.get(node.op)
        if op_func is None: raise VisualMacroRuntimeError(f"Unsupported arithmetic op: {node.op!r}")
        if node.op in ("DIV", "MOD") and rn == 0.0: self.warning(f"Division by zero: {node.op}"); return 0.0
        return float(op_func(ln, rn))

    def _evaluate_compare(self, node: CompareNode) -> bool:
        lv = self._evaluate_value(node.left); rv = self._evaluate_value(node.right)
        op_func = _COMPARE_OPERATORS.get(node.op)
        if op_func is None: raise VisualMacroRuntimeError(f"Unsupported compare op: {node.op!r}")
        try: return bool(op_func(lv, rv))
        except TypeError: return False

    def _evaluate_logic_operation(self, node: LogicOperationNode) -> bool:
        lv = bool(self._evaluate_value(node.left)); rv = bool(self._evaluate_value(node.right))
        if node.op == "AND": return lv and rv
        if node.op == "OR": return lv or rv
        raise VisualMacroRuntimeError(f"Unsupported logic op: {node.op!r}")

    def _evaluate_function_param(self, node: FunctionParamNode) -> object:
        for scope in reversed(self._call_stack):
            if node.name in scope: return scope[node.name]
        self.warning(f"引数 {node.name!r} が見つかりません（関数外で使用されています）"); return None

    def _evaluate_call_function_value(self, node: CallFunctionValueNode) -> object:
        func_def = self._program.functions.get(node.name)
        if func_def is None: raise VisualMacroRuntimeError(f"未定義の関数です: {node.name!r}")
        if len(self._call_stack) >= _MAX_CALL_DEPTH: raise VisualMacroRuntimeError(f"関数呼び出しの深さが上限 ({_MAX_CALL_DEPTH}) を超えました")
        local_scope = {p: self._evaluate_value(node.args.get(p)) for p in func_def.params}
        self._call_stack.append(local_scope)
        try:
            self._highlight_node(func_def)
            for s in func_def.body: self.check_if_alive(); self._execute_statement(s)
        except _FunctionReturn as ret:
            return ret.value
        finally:
            self._call_stack.pop()
        return None  # no return statement encountered

    def _evaluate_list_get(self, node: ListGetNode) -> object:
        lst = self._evaluate_value(node.list); idx_val = self._evaluate_value(node.index)
        if not isinstance(lst, list): self.warning("list_get: 対象がリストではありません"); return None
        idx = int(idx_val) if isinstance(idx_val, (int, float)) else 0
        if 0 <= idx < len(lst): return lst[idx]
        self.warning(f"list_get: インデックス {idx} は範囲外です (リスト長: {len(lst)})"); return None

    def _evaluate_to_number(self, node: ToNumberNode) -> float:
        v = self._evaluate_value(node.value)
        if isinstance(v, (int, float)): return float(v)
        if isinstance(v, str):
            try: return float(v)
            except ValueError: pass
        if isinstance(v, bool): return 1.0 if v else 0.0
        return 0.0

    def _evaluate_math_single(self, node: MathSingleNode) -> float:
        v = self._evaluate_value(node.value)
        num = float(v) if isinstance(v, (int, float)) else 0.0
        func = _MATH_SINGLE_FUNCS.get(node.op)
        if func is None: raise VisualMacroRuntimeError(f"Unsupported math_single op: {node.op!r}")
        return float(func(num))

    def _evaluate_math_minmax(self, node: MathMinMaxNode) -> float:
        lv = self._evaluate_value(node.left); rv = self._evaluate_value(node.right)
        ln = float(lv) if isinstance(lv, (int, float)) else 0.0
        rn = float(rv) if isinstance(rv, (int, float)) else 0.0
        if node.op == "MIN": return min(ln, rn)
        if node.op == "MAX": return max(ln, rn)
        raise VisualMacroRuntimeError(f"Unsupported math_minmax op: {node.op!r}")

    def _evaluate_text_substring(self, node: TextSubstringNode) -> str:
        txt = str(self._evaluate_value(node.text) or "")
        start_val = self._evaluate_value(node.start)
        length_val = self._evaluate_value(node.length)
        start = int(start_val) if isinstance(start_val, (int, float)) else 0
        length = int(length_val) if isinstance(length_val, (int, float)) else len(txt)
        start = max(0, start)
        return txt[start:start + length]

    # ── 入力解決 ──

    def _resolve_input(self, input_name: InputName) -> InputSymbol:
        if hasattr(Button, input_name): return cast(InputSymbol, getattr(Button, input_name))
        if hasattr(Hat, input_name): return cast(InputSymbol, getattr(Hat, input_name))
        raise VisualMacroRuntimeError(f"Unsupported input name: {input_name!r}")

    def _resolve_stick(self, stick_name: StickName) -> Stick:
        if stick_name == "LEFT_STICK": return Stick.LEFT
        if stick_name == "RIGHT_STICK": return Stick.RIGHT
        raise VisualMacroRuntimeError(f"Unsupported stick name: {stick_name!r}")

    def _build_direction(self, stick_name: StickName, angle: float, radius: float) -> Direction:
        return Direction(self._resolve_stick(stick_name), float(angle), max(0.0, min(float(radius), 1.0)))
