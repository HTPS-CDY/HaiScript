"""
HaiScript 静态类型检查器（基础版，仅警告不阻止运行）
----------------------------------------------------
特性：
  1. 基于类型标注的声明一致性检查：var x: int = "str" → 警告
  2. 函数返回值类型检查：函数声明 -> int 但返回字符串 → 警告
  3. 参数传递类型一致性（调用点检查实参类型是否符合形参标注）
  4. 未标注的一律视为 any，不报警

类型系统：any ⊒ int, float, bool, string, nil, list<T>, map<K,V>, set<T>, func(...) -> R

注意：不执行复杂推断，只看标注。这是"渐进式类型"的基础版本。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

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
# 类型诊断
# ==========================================================
@dataclass
class TypeWarning:
    message: str
    line: int = 0
    col: int = 0

    def __str__(self):
        if self.line and self.col:
            return f"[{self.line}:{self.col}] 类型警告: {self.message}"
        return f"类型警告: {self.message}"


# ==========================================================
# 子类型 / 赋值兼容判定
# ==========================================================
_ANY = 'any'
_NUMERIC = {'int', 'float', 'number'}


def is_assignable(target_t: str, val_t: str) -> bool:
    """val_t 的值能否赋值给 target_t 的位置（渐进式：any 兼容一切）"""
    if not target_t or target_t == _ANY or not val_t or val_t == _ANY:
        return True
    target_t = _normalize(target_t)
    val_t = _normalize(val_t)
    if target_t == val_t:
        return True
    # number > int/float
    if target_t == 'number' and val_t in _NUMERIC:
        return True
    if target_t == 'float' and val_t == 'int':
        return True
    # list<T> 兼容（仅当元素参数相同时；宽松版：空泛型视为 list<any>）
    if _strip_generic(target_t) == 'list' and _strip_generic(val_t) == 'list':
        ta = _generic_args(target_t)
        va = _generic_args(val_t)
        if not ta or not va:
            return True
        if len(ta) == len(va) == 1:
            return is_assignable(ta[0], va[0])
    # map<K,V> / set<T> 同理宽松
    if _strip_generic(target_t) == _strip_generic(val_t):
        return _strip_generic(target_t) in {'Map', 'map', 'Set', 'set'}
    return False


def _normalize(t: str) -> str:
    return t.strip()


def _strip_generic(t: str) -> str:
    i = t.find('<')
    return t if i < 0 else t[:i]


def _generic_args(t: str) -> List[str]:
    i = t.find('<')
    if i < 0 or not t.endswith('>'):
        return []
    inner = t[i + 1:-1]
    if not inner:
        return []
    # 简单逗号分割（不处理嵌套泛型内的逗号——足够当前使用）
    depth = 0
    parts, cur = [], []
    for ch in inner:
        if ch == '<':
            depth += 1
            cur.append(ch)
        elif ch == '>':
            depth -= 1
            cur.append(ch)
        elif ch == ',' and depth == 0:
            parts.append(''.join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append(''.join(cur).strip())
    return parts


# ==========================================================
# 类型推断（仅从字面量初略推断，复杂场景回退 any）
# ==========================================================
def infer_literal_type(node: ASTNode) -> Optional[str]:
    """对字面量做粗浅类型推断，非字面量返回 None"""
    if isinstance(node, NumberLiteral):
        v = node.value
        if isinstance(v, int) and not isinstance(v, bool):
            return 'int'
        return 'float'
    if isinstance(node, StringLiteral):
        return 'string'
    if isinstance(node, BoolLiteral):
        return 'bool'
    if isinstance(node, NilLiteral):
        return 'nil'
    if isinstance(node, ListLiteral):
        return 'list<any>'
    if isinstance(node, MapLiteral):
        return 'map<any,any>'
    if isinstance(node, SetLiteral):
        return 'set<any>'
    if isinstance(node, FuncCall):
        # 已知内建函数的返回类型
        name = node.name
        if name in {'len', 'abs', 'round', 'floor', 'ceil', 'int'}:
            return 'int'
        if name in {'float', 'sqrt', 'sin', 'cos', 'tan'}:
            return 'float'
        if name in {'str', 'string'}:
            return 'string'
        if name in {'bool'}:
            return 'bool'
        if name in {'readfile', 'input'}:
            return 'string'
        if name == 'list':
            return 'list<any>'
        if name == 'Map':
            return 'map<any,any>'
        if name == 'Set':
            return 'set<any>'
        return None  # any
    return None


# ==========================================================
# 类型检查器 —— 遍历 AST
# ==========================================================
class TypeChecker:
    """
    遍历 AST，对存在类型标注的位置做赋值兼容/返回值检查。
    输出警告列表；不修改 AST。
    """

    def __init__(self):
        self.warnings: List[TypeWarning] = []
        # 作用域：变量名 → 声明类型（None 表示 any/未标注）
        self._scope: Dict[str, Optional[str]] = {}
        # 当前函数信息: (name, return_type or None)
        self._current_func: Optional[Tuple[str, Optional[str]]] = None

    # --------- 入口 ---------
    def check(self, ast: Program) -> List[TypeWarning]:
        self.warnings = []
        self._scope = {}
        self._visit_program(ast)
        return self.warnings

    def check_source(self, src: str, file_tag: str = "<source>") -> List[TypeWarning]:
        from haiscript.interpreter.lexer import Lexer
        from haiscript.interpreter.parser import Parser
        tokens = Lexer(src, file_tag).tokenize()
        ast = Parser(tokens).parse()
        return self.check(ast)

    # --------- 辅助 ---------
    def _warn(self, msg: str, node: ASTNode = None):
        line = getattr(node, 'line', 0) or 0
        col = getattr(node, 'col', 0) or 0
        self.warnings.append(TypeWarning(msg, line=line, col=col))

    def _declare(self, name: str, declared_type: Optional[str]):
        self._scope[name] = declared_type

    # --------- 遍历 ---------
    def _visit_program(self, n: Program):
        for s in n.statements:
            self._visit_stmt(s)

    def _visit_stmt(self, s: ASTNode):
        name = type(s).__name__
        fn = getattr(self, f'_v_{name}', None)
        if fn is not None:
            fn(s)

    def _visit_many(self, xs):
        for s in xs:
            self._visit_stmt(s)

    # --- 声明 ---
    def _v_VarDecl(self, n: VarDecl):
        declared = n.type_hint  # 可能 None 表示 any
        self._declare(n.name, declared)
        if declared and n.value is not None:
            inferred = infer_literal_type(n.value)
            if inferred is not None and not is_assignable(declared, inferred):
                self._warn(
                    f"变量 '{n.name}' 声明为 {declared}，但初始值类型为 {inferred}",
                    n)

    def _v_FuncDef(self, n: FuncDef):
        # 注册函数本身
        # 函数签名: func(p1,p2)->r （若有参数类型和返回类型）
        param_strs = [(t or 'any') for t in n.param_types]
        sig = f"func({','.join(param_strs)})->{n.return_type or 'any'}"
        self._declare(n.name, sig)

        old_func = self._current_func
        old_scope = dict(self._scope)
        self._current_func = (n.name, n.return_type)
        # 注册参数到局部作用域
        for pname, ptype in zip(n.params, n.param_types):
            self._declare(pname, ptype)
        self._visit_many(n.body)
        self._scope = old_scope
        self._current_func = old_func

    def _v_ReturnStatement(self, n: ReturnStatement):
        if self._current_func and self._current_func[1]:
            expected = self._current_func[1]
            if n.value is not None:
                inferred = infer_literal_type(n.value)
                if inferred is not None and not is_assignable(expected, inferred):
                    self._warn(
                        f"函数 '{self._current_func[0]}' 声明返回 {expected}，"
                        f"但返回了 {inferred}",
                        n)
            elif expected != 'nil' and expected != 'any':
                # 有显式非 nil/any 返回类型但 return 无值 → nil
                if not is_assignable(expected, 'nil'):
                    self._warn(
                        f"函数 '{self._current_func[0]}' 声明返回 {expected}，"
                        f"但返回了 nil",
                        n)

    # --- 赋值 ---
    def _v_Assign(self, n: Assign):
        declared = self._scope.get(n.target)
        if declared and n.value is not None:
            inferred = infer_literal_type(n.value)
            if inferred is not None and not is_assignable(declared, inferred):
                self._warn(
                    f"变量 '{n.target}' 声明为 {declared}，但赋值类型为 {inferred}",
                    n)

    def _v_IndexAssign(self, n: IndexAssign):
        # 深入：对 list<int>[i] = "str" 暂不警告（太复杂）
        pass

    # --- 调用点（实参类型检查）---
    def _v_FuncCall(self, n: FuncCall):
        decl = self._scope.get(n.name)
        if decl and _strip_generic(decl).lower() == 'func':
            # 解析签名：func(p1,p2)->r
            args_part, _ = _split_func_sig(decl)
            if args_part is not None and len(args_part) == len(n.args):
                for i, (expected, arg) in enumerate(zip(args_part, n.args)):
                    actual = infer_literal_type(arg)
                    if actual is not None and not is_assignable(expected, actual):
                        self._warn(
                            f"调用 '{n.name}' 时第 {i + 1} 个参数期望 {expected}，"
                            f"但实参类型为 {actual}",
                            n)

    def _v_MethodCall(self, n: MethodCall):
        # 暂不深入方法签名
        pass

    # --- 控制流（进入分支时不消除警告，即不做流敏感）---
    def _v_IfStatement(self, n: IfStatement):
        self._visit_many(n.then_branch)
        for _, body in n.elif_branches:
            self._visit_many(body)
        self._visit_many(n.else_branch)

    def _v_WhileStatement(self, n: WhileStatement):
        self._visit_many(n.body)

    def _v_ForStatement(self, n: ForStatement):
        # 循环变量暂按 any 处理
        self._visit_many(n.body)

    def _v_TryCatchStatement(self, n: TryCatchStatement):
        self._visit_many(n.try_body)
        self._visit_many(n.catch_body)
        self._visit_many(n.finally_body)

    # --- 简单节点 ---
    def _v_PrintStatement(self, n: PrintStatement): pass
    def _v_BreakStatement(self, _): pass
    def _v_ContinueStatement(self, _): pass
    def _v_ThrowStatement(self, _): pass
    def _v_AssertStatement(self, _): pass
    def _v_ImportStatement(self, _): pass
    def _v_ExportStatement(self, _): pass
    def _v_InputCall(self, _): pass


def _split_func_sig(sig: str) -> Tuple[Optional[List[str]], Optional[str]]:
    """解析 func(a,b)->r → ([a,b], r)；失败返回 (None, None)"""
    try:
        if not sig.lower().startswith('func('):
            return None, None
        rest = sig[len('func'):]
        # 找到配对的 )
        if not rest.startswith('('):
            return None, None
        depth = 0
        close = -1
        for i, ch in enumerate(rest):
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    close = i
                    break
        if close < 0:
            return None, None
        args_inner = rest[1:close]
        after = rest[close + 1:]
        ret = 'any'
        if after.startswith('->'):
            ret = after[2:].strip() or 'any'
        # args 分割（考虑嵌套泛型）
        args: List[str] = []
        cur, depth = [], 0
        for ch in args_inner:
            if ch == '<':
                depth += 1
                cur.append(ch)
            elif ch == '>':
                depth -= 1
                cur.append(ch)
            elif ch == ',' and depth == 0:
                s = ''.join(cur).strip()
                if s:
                    args.append(s)
                cur = []
            else:
                cur.append(ch)
        s = ''.join(cur).strip()
        if s:
            args.append(s)
        return args, ret
    except Exception:
        return None, None


# ==========================================================
# 便捷 API
# ==========================================================
def check_source(src: str, file_tag: str = "<source>") -> List[TypeWarning]:
    return TypeChecker().check_source(src, file_tag)


def check_file(path: str) -> List[TypeWarning]:
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()
    return check_source(src, file_tag=path)
