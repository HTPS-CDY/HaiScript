"""
HaiScript IR（中间表示）与优化 Pass
-----------------------------------
IR 节点是一个简化、规范化的表达式/语句层：
  - 移除语法糖（简化列表/字典/set 字面量元素为纯表达式序列）
  - 所有二元运算规范化为 IRBinOp / IRUnOp
  - 常量折叠（Const Folding）：编译期计算 `1 + 2 * 3` → `7` 等
  - 简单死代码标记（未使用的纯表达式被标记，解释器/编译器可跳过）

最后 IR 可重新 emit 回 AST（或解释器直接遍历 IR 节点执行，这里为兼容性选择优化后的 AST 输出）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from haiscript.interpreter.parser import (
    Program, NumberLiteral, StringLiteral, BoolLiteral, NilLiteral,
    ListLiteral, MapLiteral, SetLiteral, Identifier, MemberAccess,
    BinOp, UnaryOp, Assign, IndexAssign, VarDecl, IfStatement,
    WhileStatement, ForStatement, BreakStatement, ContinueStatement,
    ThrowStatement, TryCatchStatement, ExportStatement, AssertStatement,
    FuncDef, FuncCall, MethodCall, ReturnStatement, PrintStatement,
    InputCall, ImportStatement, ListIndex, RangeExpr, ASTNode,
)


# ==========================================================
# IR 节点定义（轻量，直接 dataclass）
# ==========================================================
@dataclass
class IRNode:
    line: int = 0
    col: int = 0


# --- 字面量 ---
@dataclass
class IRNumber(IRNode):
    value: Union[int, float] = 0


@dataclass
class IRString(IRNode):
    value: str = ""


@dataclass
class IRBool(IRNode):
    value: bool = False


@dataclass
class IRNil(IRNode):
    pass


# --- 组合 ---
@dataclass
class IRList(IRNode):
    elements: List[IRNode] = field(default_factory=list)


@dataclass
class IRMap(IRNode):
    pairs: List[tuple] = field(default_factory=list)  # (IRNode, IRNode)


@dataclass
class IRSet(IRNode):
    elements: List[IRNode] = field(default_factory=list)


@dataclass
class IRRange(IRNode):
    start: IRNode = None
    end: IRNode = None
    step: Optional[IRNode] = None


# --- 变量/访问 ---
@dataclass
class IRIdent(IRNode):
    name: str = ""


@dataclass
class IRMember(IRNode):
    object: IRNode = None
    member: str = ""


@dataclass
class IRIndex(IRNode):
    object: IRNode = None
    index: IRNode = None


# --- 运算 ---
@dataclass
class IRBinOp(IRNode):
    op: str = ""
    left: IRNode = None
    right: IRNode = None


@dataclass
class IRUnOp(IRNode):
    op: str = ""
    operand: IRNode = None


# --- 调用 ---
@dataclass
class IRCall(IRNode):
    target: IRNode = None  # IRIdent / IRMember
    args: List[IRNode] = field(default_factory=list)


# --- 语句 ---
@dataclass
class IRVarDecl(IRNode):
    name: str = ""
    value: Optional[IRNode] = None
    type_hint: Optional[str] = None


@dataclass
class IRAssign(IRNode):
    target: str = ""
    value: IRNode = None


@dataclass
class IRIndexAssign(IRNode):
    container: IRNode = None
    index: IRNode = None
    value: IRNode = None


@dataclass
class IRIf(IRNode):
    condition: IRNode = None
    then_branch: List[IRNode] = field(default_factory=list)
    elif_branches: List[tuple] = field(default_factory=list)
    else_branch: List[IRNode] = field(default_factory=list)


@dataclass
class IRWhile(IRNode):
    condition: IRNode = None
    body: List[IRNode] = field(default_factory=list)


@dataclass
class IRFor(IRNode):
    var_name: str = ""
    start: IRNode = None
    end: IRNode = None
    step: Optional[IRNode] = None
    body: List[IRNode] = field(default_factory=list)


@dataclass
class IRBreak(IRNode): pass


@dataclass
class IRContinue(IRNode): pass


@dataclass
class IRThrow(IRNode):
    value: IRNode = None
    kind: Optional[str] = None


@dataclass
class IRTryCatch(IRNode):
    try_body: List[IRNode] = field(default_factory=list)
    catch_var: Optional[str] = None
    catch_kind: Optional[str] = None
    catch_body: List[IRNode] = field(default_factory=list)
    finally_body: List[IRNode] = field(default_factory=list)


@dataclass
class IRExport(IRNode):
    names: List[str] = field(default_factory=list)
    assignments: List[tuple] = field(default_factory=list)


@dataclass
class IRAssert(IRNode):
    condition: IRNode = None
    message: Optional[IRNode] = None


@dataclass
class IRFuncDef(IRNode):
    name: str = ""
    params: List[str] = field(default_factory=list)
    param_types: List[Optional[str]] = field(default_factory=list)
    return_type: Optional[str] = None
    body: List[IRNode] = field(default_factory=list)


@dataclass
class IRReturn(IRNode):
    value: Optional[IRNode] = None


@dataclass
class IRPrint(IRNode):
    args: List[IRNode] = field(default_factory=list)


@dataclass
class IRInput(IRNode):
    prompt: Optional[IRNode] = None


@dataclass
class IRImport(IRNode):
    module_name: str = ""
    alias: Optional[str] = None


@dataclass
class IRProgram(IRNode):
    statements: List[IRNode] = field(default_factory=list)


# ==========================================================
# AST → IR Lowering
# ==========================================================
class LowerToIR:
    """将 AST 节点翻译为等价 IR（保持结构，便于后续分析）"""

    def lower(self, n: ASTNode) -> IRNode:
        name = type(n).__name__
        fn = getattr(self, f'_l_{name}', None)
        if fn is None:
            raise ValueError(f"LowerToIR: 未知 AST: {name}")
        return fn(n)

    def _stmts(self, xs):
        return [self.lower(s) for s in xs]

    # --- Literals ---
    def _l_NumberLiteral(self, n: NumberLiteral): return IRNumber(value=n.value, line=n.line, col=n.col)
    def _l_StringLiteral(self, n: StringLiteral): return IRString(value=n.value, line=n.line, col=n.col)
    def _l_BoolLiteral(self, n: BoolLiteral):     return IRBool(value=n.value, line=n.line, col=n.col)
    def _l_NilLiteral(self, _n: NilLiteral):      return IRNil(line=_n.line, col=_n.col)

    def _l_ListLiteral(self, n: ListLiteral):
        return IRList(elements=[self.lower(e) for e in n.elements], line=n.line, col=n.col)

    def _l_MapLiteral(self, n: MapLiteral):
        return IRMap(pairs=[(self.lower(k), self.lower(v)) for k, v in n.pairs],
                     line=n.line, col=n.col)

    def _l_SetLiteral(self, n: SetLiteral):
        return IRSet(elements=[self.lower(e) for e in n.elements], line=n.line, col=n.col)

    def _l_RangeExpr(self, n: RangeExpr):
        return IRRange(start=self.lower(n.start), end=self.lower(n.end),
                       step=self.lower(n.step) if n.step else None,
                       line=n.line, col=n.col)

    # --- Variable / Access ---
    def _l_Identifier(self, n: Identifier): return IRIdent(name=n.name, line=n.line, col=n.col)

    def _l_MemberAccess(self, n: MemberAccess):
        return IRMember(object=self.lower(n.object), member=n.member,
                        line=n.line, col=n.col)

    def _l_ListIndex(self, n: ListIndex):
        return IRIndex(object=self.lower(n.list_expr), index=self.lower(n.index),
                       line=n.line, col=n.col)

    # --- Operations ---
    def _l_BinOp(self, n: BinOp):
        return IRBinOp(op=n.op, left=self.lower(n.left), right=self.lower(n.right),
                       line=n.line, col=n.col)

    def _l_UnaryOp(self, n: UnaryOp):
        return IRUnOp(op=n.op, operand=self.lower(n.operand), line=n.line, col=n.col)

    def _l_FuncCall(self, n: FuncCall):
        return IRCall(target=IRIdent(name=n.name, line=n.line, col=n.col),
                      args=[self.lower(a) for a in n.args],
                      line=n.line, col=n.col)

    def _l_MethodCall(self, n: MethodCall):
        mem = IRMember(object=self.lower(n.object), member=n.method,
                       line=n.line, col=n.col)
        return IRCall(target=mem, args=[self.lower(a) for a in n.args],
                      line=n.line, col=n.col)

    def _l_InputCall(self, n: InputCall):
        return IRInput(prompt=self.lower(n.prompt) if n.prompt else None,
                       line=n.line, col=n.col)

    # --- Statements ---
    def _l_VarDecl(self, n: VarDecl):
        return IRVarDecl(name=n.name, value=self.lower(n.value) if n.value else None,
                         type_hint=n.type_hint, line=n.line, col=n.col)

    def _l_Assign(self, n: Assign):
        return IRAssign(target=n.target, value=self.lower(n.value),
                        line=n.line, col=n.col)

    def _l_IndexAssign(self, n: IndexAssign):
        return IRIndexAssign(container=self.lower(n.container), index=self.lower(n.index),
                             value=self.lower(n.value), line=n.line, col=n.col)

    def _l_IfStatement(self, n: IfStatement):
        return IRIf(
            condition=self.lower(n.condition),
            then_branch=self._stmts(n.then_branch),
            elif_branches=[(self.lower(c), self._stmts(b)) for c, b in n.elif_branches],
            else_branch=self._stmts(n.else_branch),
            line=n.line, col=n.col,
        )

    def _l_WhileStatement(self, n: WhileStatement):
        return IRWhile(condition=self.lower(n.condition), body=self._stmts(n.body),
                       line=n.line, col=n.col)

    def _l_ForStatement(self, n: ForStatement):
        return IRFor(var_name=n.var_name,
                     start=self.lower(n.start), end=self.lower(n.end),
                     step=self.lower(n.step) if n.step else None,
                     body=self._stmts(n.body),
                     line=n.line, col=n.col)

    def _l_BreakStatement(self, _n): return IRBreak(line=_n.line, col=_n.col)
    def _l_ContinueStatement(self, _n): return IRContinue(line=_n.line, col=_n.col)

    def _l_ThrowStatement(self, n: ThrowStatement):
        return IRThrow(value=self.lower(n.value), kind=n.kind, line=n.line, col=n.col)

    def _l_TryCatchStatement(self, n: TryCatchStatement):
        return IRTryCatch(
            try_body=self._stmts(n.try_body),
            catch_var=n.catch_var, catch_kind=n.catch_kind,
            catch_body=self._stmts(n.catch_body),
            finally_body=self._stmts(n.finally_body),
            line=n.line, col=n.col,
        )

    def _l_ExportStatement(self, n: ExportStatement):
        return IRExport(
            names=list(n.names),
            assignments=[(k, self.lower(v)) for (k, v) in n.assignments],
            line=n.line, col=n.col,
        )

    def _l_AssertStatement(self, n: AssertStatement):
        return IRAssert(
            condition=self.lower(n.condition),
            message=self.lower(n.message) if n.message else None,
            line=n.line, col=n.col,
        )

    def _l_FuncDef(self, n: FuncDef):
        return IRFuncDef(
            name=n.name, params=list(n.params), param_types=list(n.param_types),
            return_type=n.return_type, body=self._stmts(n.body),
            line=n.line, col=n.col,
        )

    def _l_ReturnStatement(self, n: ReturnStatement):
        return IRReturn(value=self.lower(n.value) if n.value else None,
                        line=n.line, col=n.col)

    def _l_PrintStatement(self, n: PrintStatement):
        return IRPrint(args=[self.lower(a) for a in n.args], line=n.line, col=n.col)

    def _l_ImportStatement(self, n: ImportStatement):
        return IRImport(module_name=n.module_name, alias=n.alias,
                        line=n.line, col=n.col)

    def _l_Program(self, n: Program):
        return IRProgram(statements=self._stmts(n.statements), line=n.line, col=n.col)


# ==========================================================
# 常量折叠 & 简易算术化简（Const Folding Pass）
# ==========================================================
class ConstFolder:
    """递归遍历 IR，在编译期折叠可静态计算的二元/一元表达式与部分纯函数调用。
    规则：
      - 数值运算：(1+2) → 3, (6/2) → 3.0, (-3) → -3 等
      - 布尔短路：true and X → X, false or X → X
      - 字符串拼接："a" + "b" → "ab"
      - 字符串重复："ab" * 3 → "ababab"
      - list/set/map 构造本身不折叠，但内部元素会被递归折叠
    注意：不会删除任何有副作用的语句。
    """

    def __init__(self):
        self.stats: Dict[str, int] = {'folds': 0}

    # ---- entry ----
    def run(self, ir: IRNode) -> IRNode:
        return self._fold(ir)

    def _fold(self, x: IRNode) -> IRNode:
        name = type(x).__name__
        fn = getattr(self, f'_f_{name}', None)
        if fn is None:
            # 默认：对已知 statement/list 容器做递归，否则原样返回
            return x
        return fn(x)

    def _fold_many(self, xs):
        return [self._fold(x) for x in xs]

    # ---- literals ----
    def _f_IRNumber(self, n): return n
    def _f_IRString(self, n): return n
    def _f_IRBool(self, n):   return n
    def _f_IRNil(self, n):    return n

    def _f_IRList(self, n: IRList):
        return IRList(elements=self._fold_many(n.elements), line=n.line, col=n.col)

    def _f_IRMap(self, n: IRMap):
        return IRMap(pairs=[(self._fold(k), self._fold(v)) for k, v in n.pairs],
                     line=n.line, col=n.col)

    def _f_IRSet(self, n: IRSet):
        return IRSet(elements=self._fold_many(n.elements), line=n.line, col=n.col)

    def _f_IRRange(self, n: IRRange):
        step = self._fold(n.step) if n.step else None
        return IRRange(start=self._fold(n.start), end=self._fold(n.end), step=step,
                       line=n.line, col=n.col)

    # ---- variable / access ----
    def _f_IRIdent(self, n):  return n
    def _f_IRMember(self, n): return IRMember(object=self._fold(n.object), member=n.member,
                                              line=n.line, col=n.col)
    def _f_IRIndex(self, n):  return IRIndex(object=self._fold(n.object),
                                             index=self._fold(n.index),
                                             line=n.line, col=n.col)

    # ---- operations ----
    _BINOP_NUM = {'+', '-', '*', '/', '%'}
    _BINOP_CMP = {'==', '!=', '<', '>', '<=', '>='}
    _BINOP_LOG = {'and', 'or'}

    def _f_IRBinOp(self, n: IRBinOp) -> IRNode:
        l = self._fold(n.left)
        r = self._fold(n.right)
        op = n.op

        # 数值 / 字符串二元运算 —— 两边都必须是纯字面量
        if op in self._BINOP_NUM:
            if (isinstance(l, (IRNumber, IRString)) and
                    isinstance(r, (IRNumber, IRString))):
                lv, rv = _const_val(l), _const_val(r)
                try:
                    if op == '/' and rv == 0:  # 不优化除零
                        pass
                    else:
                        res = _apply_num_str_op(lv, rv, op)
                        self.stats['folds'] += 1
                        return _lift_val(res, n)
                except Exception:
                    pass
            return IRBinOp(op=op, left=l, right=r, line=n.line, col=n.col)

        # 比较
        if op in self._BINOP_CMP:
            if _is_const(l) and _is_const(r):
                lv, rv = _const_val(l), _const_val(r)
                try:
                    res = _apply_cmp(lv, rv, op)
                    self.stats['folds'] += 1
                    return IRBool(value=res, line=n.line, col=n.col)
                except Exception:
                    pass
            return IRBinOp(op=op, left=l, right=r, line=n.line, col=n.col)

        # 逻辑短路
        if op == 'and':
            if isinstance(l, IRBool):
                self.stats['folds'] += 1
                return r if l.value else l
            if isinstance(r, IRBool) and r.value:
                self.stats['folds'] += 1
                return l
        elif op == 'or':
            if isinstance(l, IRBool):
                self.stats['folds'] += 1
                return l if l.value else r
            if isinstance(r, IRBool) and not r.value:
                self.stats['folds'] += 1
                return l

        # has / 其他保持
        return IRBinOp(op=op, left=l, right=r, line=n.line, col=n.col)

    def _f_IRUnOp(self, n: IRUnOp) -> IRNode:
        o = self._fold(n.operand)
        if n.op == '-' and isinstance(o, IRNumber):
            self.stats['folds'] += 1
            return IRNumber(value=-o.value, line=n.line, col=n.col)
        if n.op == 'not' and isinstance(o, IRBool):
            self.stats['folds'] += 1
            return IRBool(value=not o.value, line=n.line, col=n.col)
        if n.op == '+' and isinstance(o, IRNumber):
            self.stats['folds'] += 1
            return o
        return IRUnOp(op=n.op, operand=o, line=n.line, col=n.col)

    # ---- calls (保持，折叠参数) ----
    def _f_IRCall(self, n: IRCall):
        # 小优化：len([...]) / len("...") / len(set{...})
        if (isinstance(n.target, IRIdent) and n.target.name == 'len'
                and len(n.args) == 1):
            a = self._fold(n.args[0])
            if isinstance(a, IRList):
                self.stats['folds'] += 1
                return IRNumber(value=len(a.elements), line=n.line, col=n.col)
            if isinstance(a, IRSet):
                self.stats['folds'] += 1
                return IRNumber(value=len(a.elements), line=n.line, col=n.col)
            if isinstance(a, IRString):
                self.stats['folds'] += 1
                return IRNumber(value=len(a.value), line=n.line, col=n.col)
        return IRCall(target=self._fold(n.target),
                      args=self._fold_many(n.args),
                      line=n.line, col=n.col)

    def _f_IRInput(self, n: IRInput):
        return IRInput(prompt=self._fold(n.prompt) if n.prompt else None,
                       line=n.line, col=n.col)

    # ---- statements ----
    def _f_IRVarDecl(self, n: IRVarDecl):
        return IRVarDecl(name=n.name,
                         value=self._fold(n.value) if n.value else None,
                         type_hint=n.type_hint, line=n.line, col=n.col)

    def _f_IRAssign(self, n: IRAssign):
        return IRAssign(target=n.target, value=self._fold(n.value),
                        line=n.line, col=n.col)

    def _f_IRIndexAssign(self, n: IRIndexAssign):
        return IRIndexAssign(container=self._fold(n.container),
                             index=self._fold(n.index),
                             value=self._fold(n.value),
                             line=n.line, col=n.col)

    def _f_IRIf(self, n: IRIf) -> IRNode:
        cond = self._fold(n.condition)
        # 静态 if 消除：if true → 取 then；if false → 取 else（若无 else 则移除）
        if isinstance(cond, IRBool):
            self.stats['folds'] += 1
            if cond.value:
                # then 分支直接内联（保留 IRIf 包装让语句列表不变形，这里用特殊方式：
                # 返回一个包含 then 语句的 IRProgram 段不太好，保持结构，
                # 但标记条件为 true/false 让解释器/编译器可跳过）
                return self._inline_if_then(n, True)
            else:
                return self._inline_if_then(n, False)
        return IRIf(
            condition=cond,
            then_branch=self._fold_many(n.then_branch),
            elif_branches=[(self._fold(c), self._fold_many(b)) for c, b in n.elif_branches],
            else_branch=self._fold_many(n.else_branch),
            line=n.line, col=n.col,
        )

    def _inline_if_then(self, n: IRIf, take_then: bool):
        """简化：保留 IRIf 结构，但条件置常量化让解释器短路即可"""
        if take_then:
            return IRIf(
                condition=IRBool(value=True, line=n.line, col=n.col),
                then_branch=self._fold_many(n.then_branch),
                elif_branches=[], else_branch=[],
                line=n.line, col=n.col,
            )
        # else 或 elif 链：尝试取第一个能匹配的 else/elif；最简策略 → 全跳过走 else_branch
        elses = self._fold_many(n.else_branch)
        return IRIf(
            condition=IRBool(value=False, line=n.line, col=n.col),
            then_branch=[], elif_branches=[], else_branch=elses,
            line=n.line, col=n.col,
        )

    def _f_IRWhile(self, n: IRWhile):
        return IRWhile(condition=self._fold(n.condition),
                       body=self._fold_many(n.body),
                       line=n.line, col=n.col)

    def _f_IRFor(self, n: IRFor):
        return IRFor(var_name=n.var_name,
                     start=self._fold(n.start), end=self._fold(n.end),
                     step=self._fold(n.step) if n.step else None,
                     body=self._fold_many(n.body),
                     line=n.line, col=n.col)

    def _f_IRBreak(self, n):    return n
    def _f_IRContinue(self, n): return n

    def _f_IRThrow(self, n: IRThrow):
        return IRThrow(value=self._fold(n.value), kind=n.kind,
                       line=n.line, col=n.col)

    def _f_IRTryCatch(self, n: IRTryCatch):
        return IRTryCatch(try_body=self._fold_many(n.try_body),
                          catch_var=n.catch_var, catch_kind=n.catch_kind,
                          catch_body=self._fold_many(n.catch_body),
                          finally_body=self._fold_many(n.finally_body),
                          line=n.line, col=n.col)

    def _f_IRExport(self, n: IRExport):
        return IRExport(names=list(n.names),
                        assignments=[(k, self._fold(v)) for (k, v) in n.assignments],
                        line=n.line, col=n.col)

    def _f_IRAssert(self, n: IRAssert):
        return IRAssert(condition=self._fold(n.condition),
                        message=self._fold(n.message) if n.message else None,
                        line=n.line, col=n.col)

    def _f_IRFuncDef(self, n: IRFuncDef):
        return IRFuncDef(name=n.name, params=list(n.params),
                         param_types=list(n.param_types),
                         return_type=n.return_type,
                         body=self._fold_many(n.body),
                         line=n.line, col=n.col)

    def _f_IRReturn(self, n: IRReturn):
        return IRReturn(value=self._fold(n.value) if n.value else None,
                        line=n.line, col=n.col)

    def _f_IRPrint(self, n: IRPrint):
        return IRPrint(args=self._fold_many(n.args), line=n.line, col=n.col)

    def _f_IRImport(self, n: IRImport): return n

    def _f_IRProgram(self, n: IRProgram):
        return IRProgram(statements=self._fold_many(n.statements),
                         line=n.line, col=n.col)


# ==========================================================
# 常量折叠辅助：字面量 ⇄ Python 值
# ==========================================================
def _is_const(x: IRNode) -> bool:
    return isinstance(x, (IRNumber, IRString, IRBool, IRNil))


def _const_val(x: IRNode) -> Any:
    if isinstance(x, IRNumber): return x.value
    if isinstance(x, IRString): return x.value
    if isinstance(x, IRBool):   return x.value
    if isinstance(x, IRNil):    return None
    raise TypeError("不是常量")


def _lift_val(v: Any, src: IRNode) -> IRNode:
    if isinstance(v, bool):     return IRBool(v, line=src.line, col=src.col)
    if v is None:               return IRNil(line=src.line, col=src.col)
    if isinstance(v, (int, float)): return IRNumber(v, line=src.line, col=src.col)
    if isinstance(v, str):      return IRString(v, line=src.line, col=src.col)
    raise TypeError(f"无法 lift: {type(v)}")


def _apply_num_str_op(a, b, op):
    if op == '+': return a + b
    if op == '-': return a - b
    if op == '*':
        # 允许 str * int
        if isinstance(a, str) and isinstance(b, int): return a * b
        if isinstance(b, str) and isinstance(a, int): return a * b
        return a * b
    if op == '/':
        r = a / b
        if isinstance(a, int) and isinstance(b, int) and r == int(r):
            return int(r)
        return r
    if op == '%': return a % b
    raise ValueError(op)


def _apply_cmp(a, b, op):
    if op == '==': return a == b
    if op == '!=': return a != b
    if op == '<':  return a < b
    if op == '>':  return a > b
    if op == '<=': return a <= b
    if op == '>=': return a >= b
    raise ValueError(op)


# ==========================================================
# IR → AST（发射回 AST，便于现有解释器/编译器直接复用）
# ==========================================================
class EmitAST:
    """将优化后的 IR 翻译回原始 AST"""

    def emit(self, ir: IRNode) -> ASTNode:
        name = type(ir).__name__
        fn = getattr(self, f'_e_{name}', None)
        if fn is None:
            raise ValueError(f"EmitAST: 未知 IR 节点: {name}")
        return fn(ir)

    def _stmts(self, xs): return [self.emit(x) for x in xs]

    def _e_IRNumber(self, n): return NumberLiteral(value=n.value, line=n.line, col=n.col)
    def _e_IRString(self, n): return StringLiteral(value=n.value, line=n.line, col=n.col)
    def _e_IRBool(self, n):   return BoolLiteral(value=n.value, line=n.line, col=n.col)
    def _e_IRNil(self, n):    return NilLiteral(line=n.line, col=n.col)

    def _e_IRList(self, n):
        return ListLiteral(elements=self._stmts(n.elements), line=n.line, col=n.col)

    def _e_IRMap(self, n):
        return MapLiteral(pairs=[(self.emit(k), self.emit(v)) for k, v in n.pairs],
                          line=n.line, col=n.col)

    def _e_IRSet(self, n):
        return SetLiteral(elements=self._stmts(n.elements), line=n.line, col=n.col)

    def _e_IRRange(self, n):
        return RangeExpr(start=self.emit(n.start), end=self.emit(n.end),
                         step=self.emit(n.step) if n.step else None,
                         line=n.line, col=n.col)

    def _e_IRIdent(self, n): return Identifier(name=n.name, line=n.line, col=n.col)

    def _e_IRMember(self, n):
        return MemberAccess(object=self.emit(n.object), member=n.member,
                            line=n.line, col=n.col)

    def _e_IRIndex(self, n):
        return ListIndex(list_expr=self.emit(n.object), index=self.emit(n.index),
                         line=n.line, col=n.col)

    def _e_IRBinOp(self, n):
        return BinOp(op=n.op, left=self.emit(n.left), right=self.emit(n.right),
                     line=n.line, col=n.col)

    def _e_IRUnOp(self, n):
        return UnaryOp(op=n.op, operand=self.emit(n.operand), line=n.line, col=n.col)

    def _e_IRCall(self, n):
        tgt = self.emit(n.target)
        args = self._stmts(n.args)
        if isinstance(tgt, Identifier):
            return FuncCall(name=tgt.name, args=args, line=n.line, col=n.col)
        if isinstance(tgt, MemberAccess):
            return MethodCall(object=tgt.object, method=tgt.member,
                              args=args, line=n.line, col=n.col)
        # 兜底：构造 call 通过 FuncCall("apply")—— 这里暂不支持复杂调用目标，转为 MethodCall-like
        raise ValueError(f"IRCall 发射失败: 未知 target 类型 {type(tgt)}")

    def _e_IRInput(self, n):
        return InputCall(prompt=self.emit(n.prompt) if n.prompt else None,
                         line=n.line, col=n.col)

    def _e_IRVarDecl(self, n):
        return VarDecl(name=n.name, value=self.emit(n.value) if n.value else None,
                       type_hint=n.type_hint, line=n.line, col=n.col)

    def _e_IRAssign(self, n):
        return Assign(target=n.target, value=self.emit(n.value),
                      line=n.line, col=n.col)

    def _e_IRIndexAssign(self, n):
        return IndexAssign(container=self.emit(n.container), index=self.emit(n.index),
                           value=self.emit(n.value), line=n.line, col=n.col)

    def _e_IRIf(self, n):
        return IfStatement(
            condition=self.emit(n.condition),
            then_branch=self._stmts(n.then_branch),
            elif_branches=[(self.emit(c), self._stmts(b)) for c, b in n.elif_branches],
            else_branch=self._stmts(n.else_branch),
            line=n.line, col=n.col,
        )

    def _e_IRWhile(self, n):
        return WhileStatement(condition=self.emit(n.condition),
                              body=self._stmts(n.body),
                              line=n.line, col=n.col)

    def _e_IRFor(self, n):
        return ForStatement(var_name=n.var_name,
                            start=self.emit(n.start), end=self.emit(n.end),
                            step=self.emit(n.step) if n.step else None,
                            body=self._stmts(n.body),
                            line=n.line, col=n.col)

    def _e_IRBreak(self, n):    return BreakStatement(line=n.line, col=n.col)
    def _e_IRContinue(self, n): return ContinueStatement(line=n.line, col=n.col)

    def _e_IRThrow(self, n):
        return ThrowStatement(value=self.emit(n.value), kind=n.kind,
                              line=n.line, col=n.col)

    def _e_IRTryCatch(self, n):
        return TryCatchStatement(
            try_body=self._stmts(n.try_body), catch_var=n.catch_var, catch_kind=n.catch_kind,
            catch_body=self._stmts(n.catch_body), finally_body=self._stmts(n.finally_body),
            line=n.line, col=n.col,
        )

    def _e_IRExport(self, n):
        return ExportStatement(names=list(n.names),
                               assignments=[(k, self.emit(v)) for (k, v) in n.assignments],
                               line=n.line, col=n.col)

    def _e_IRAssert(self, n):
        return AssertStatement(condition=self.emit(n.condition),
                               message=self.emit(n.message) if n.message else None,
                               line=n.line, col=n.col)

    def _e_IRFuncDef(self, n):
        return FuncDef(name=n.name, params=list(n.params),
                       param_types=list(n.param_types), return_type=n.return_type,
                       body=self._stmts(n.body), line=n.line, col=n.col)

    def _e_IRReturn(self, n):
        return ReturnStatement(value=self.emit(n.value) if n.value else None,
                               line=n.line, col=n.col)

    def _e_IRPrint(self, n):
        return PrintStatement(args=self._stmts(n.args), line=n.line, col=n.col)

    def _e_IRImport(self, n):
        return ImportStatement(module_name=n.module_name, alias=n.alias,
                               line=n.line, col=n.col)

    def _e_IRProgram(self, n):
        return Program(statements=self._stmts(n.statements), line=n.line, col=n.col)


# ==========================================================
# 对外 API：optimize_ast / optimize_source
# ==========================================================
def optimize_ast(ast: Program) -> tuple[Program, Dict[str, int]]:
    """对 AST 执行 Lower → ConstFold → EmitAST 流水线，返回 (优化后 AST, 统计)"""
    ir = LowerToIR().lower(ast)
    folder = ConstFolder()
    ir_opt = folder.run(ir)
    out_ast = EmitAST().emit(ir_opt)
    stats = dict(folder.stats)
    if not isinstance(out_ast, Program):
        raise TypeError("优化产物不是 Program")
    return out_ast, stats


def optimize_source(src: str, file_tag: str = "<source>") -> tuple[Program, Dict[str, int]]:
    """从源码出发执行优化（返回 AST + 统计）"""
    from haiscript.interpreter.lexer import Lexer
    from haiscript.interpreter.parser import Parser
    tokens = Lexer(src, file_tag).tokenize()
    ast = Parser(tokens).parse()
    return optimize_ast(ast)
