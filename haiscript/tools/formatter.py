"""
HaiScript 代码格式化工具（AST Pretty Printer）
用法：
    from haiscript.tools.formatter import format_source, format_file
    out = format_source(src)           # 格式化源码字符串
    ok = format_file(path, inplace=True)  # 格式化文件
"""
from __future__ import annotations

import json as _pyjson
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

from haiscript.interpreter.lexer import Lexer
from haiscript.interpreter.parser import (
    Program, NumberLiteral, StringLiteral, BoolLiteral, NilLiteral,
    ListLiteral, MapLiteral, SetLiteral, Identifier, MemberAccess,
    BinOp, UnaryOp, Assign, IndexAssign, VarDecl, IfStatement,
    WhileStatement, ForStatement, BreakStatement, ContinueStatement,
    ThrowStatement, TryCatchStatement, ExportStatement, AssertStatement,
    FuncDef, FuncCall, MethodCall, ReturnStatement, PrintStatement,
    InputCall, ImportStatement, ListIndex, RangeExpr, ParseError, Parser,
    ASTNode,
)


# 左结合二元运算符优先级（数值越大越紧）
_BINOP_PREC = {
    'or': 1, 'and': 2,
    '==': 3, '!=': 3, '<': 3, '>': 3, '<=': 3, '>=': 3,
    '+': 4, '-': 4,
    '*': 5, '/': 5, '%': 5,
    'has': 3,
}
_UNARY_PREC = 9


def _escape_string(s: str) -> str:
    """HaiScript 字符串字面量转义（使用双引号包裹）"""
    # 优先双引号，若双引号比单引号多则改用单引号（简化：统一双引号）
    out = ['"']
    for ch in s:
        if ch == '\\':
            out.append('\\\\')
        elif ch == '"':
            out.append('\\"')
        elif ch == '\n':
            out.append('\\n')
        elif ch == '\r':
            out.append('\\r')
        elif ch == '\t':
            out.append('\\t')
        elif ord(ch) < 0x20:
            out.append(f'\\x{ord(ch):02x}')
        else:
            out.append(ch)
    out.append('"')
    return ''.join(out)


@dataclass
class _FmtCtx:
    indent: int = 0
    step: int = 4  # 每级缩进 4 空格

    def push(self) -> "_FmtCtx":
        self.indent += self.step
        return self

    def pop(self) -> "_FmtCtx":
        self.indent = max(0, self.indent - self.step)
        return self

    @property
    def pad(self) -> str:
        return ' ' * self.indent


class PrettyPrinter:
    def __init__(self, step: int = 4):
        self.ctx = _FmtCtx(step=step)
        self.buf: List[str] = []

    # ---------- 入口 ----------
    def format(self, node: ASTNode) -> str:
        self.buf = []
        self._visit(node)
        return ''.join(self.buf).rstrip() + '\n'

    # ---------- 辅助 ----------
    def _w(self, s: str):
        self.buf.append(s)

    def _nl(self):
        """只换行（不写缩进），下一行内容需显式 _pad"""
        self.buf.append('\n')

    def _pad(self):
        """写入当前缩进"""
        self.buf.append(self.ctx.pad)

    # ---------- 多态分派 ----------
    def _visit(self, n: ASTNode):
        name = type(n).__name__
        fn = getattr(self, f'_n_{name}', None)
        if fn is None:
            raise ValueError(f"formatter: 未知 AST 节点: {name}")
        fn(n)

    # ---------- 顶层 & 语句列表 ----------
    def _n_Program(self, n: Program):
        self._pad()
        for i, s in enumerate(n.statements):
            if i > 0:
                # 顶层函数/if/for/while/try 之间空一行
                if isinstance(s, (FuncDef, IfStatement, ForStatement,
                                  WhileStatement, TryCatchStatement,
                                  ImportStatement, VarDecl)):
                    self._nl()
                self._nl()
                self._pad()
            self._visit(s)

    def _block(self, stmts: List[ASTNode]):
        """HS 使用 end 闭合；block 就是子语句列表（统一缩进）"""
        if not stmts:
            return
        self.ctx.push()
        for i, s in enumerate(stmts):
            if i > 0:
                self._nl()
            self._pad()
            self._visit(s)
        self.ctx.pop()

    # ---------- 字面量 ----------
    def _n_NumberLiteral(self, n: NumberLiteral):
        if isinstance(n.value, int):
            self._w(str(n.value))
        else:
            s = repr(n.value)
            if s.endswith('.0'):
                s = s[:-1]  # 3.0 → 3.
            self._w(s)

    def _n_StringLiteral(self, n: StringLiteral):
        self._w(_escape_string(n.value))

    def _n_BoolLiteral(self, n: BoolLiteral):
        self._w('true' if n.value else 'false')

    def _n_NilLiteral(self, _n: NilLiteral):
        self._w('nil')

    def _n_ListLiteral(self, n: ListLiteral):
        self._w('[')
        parts = []
        for e in n.elements:
            p = PrettyPrinter(step=self.ctx.step)
            p._visit(e)
            parts.append(''.join(p.buf))
        if len(parts) <= 4 and sum(len(x) for x in parts) < 60:
            self._w(', '.join(parts))
        else:
            self.ctx.push()
            for i, p in enumerate(parts):
                if i:
                    self._w(',')
                self._nl()
                self._pad()
                self._w(p)
            self.ctx.pop()
            self._nl()
            self._pad()
        self._w(']')

    def _n_MapLiteral(self, n: MapLiteral):
        self._w('{')
        pairs = []
        for k, v in n.pairs:
            pk = PrettyPrinter(step=self.ctx.step); pk._visit(k)
            pv = PrettyPrinter(step=self.ctx.step); pv._visit(v)
            pairs.append((''.join(pk.buf), ''.join(pv.buf)))
        if pairs and all(len(k)+len(v) < 50 for k,v in pairs) and len(pairs) <= 3:
            self._w(', '.join(f'{k}: {v}' for k,v in pairs))
        else:
            self.ctx.push()
            for i, (k, v) in enumerate(pairs):
                if i: self._w(',')
                self._nl(); self._pad()
                self._w(f'{k}: {v}')
            self.ctx.pop()
            if pairs:
                self._nl(); self._pad()
        self._w('}')

    def _n_SetLiteral(self, n: SetLiteral):
        items = []
        for e in n.elements:
            p = PrettyPrinter(step=self.ctx.step); p._visit(e)
            items.append(''.join(p.buf))
        self._w('set{')
        if len(items) <= 4 and sum(len(x) for x in items) < 60:
            self._w(', '.join(items))
        else:
            self.ctx.push()
            for i, p in enumerate(items):
                if i: self._w(',')
                self._nl(); self._pad(); self._w(p)
            self.ctx.pop()
            if items: self._nl(); self._pad()
        self._w('}')

    # ---------- 标识符 / 访问 ----------
    def _n_Identifier(self, n: Identifier):
        self._w(n.name)

    def _fmt_expr(self, n: ASTNode, prec: int = 0) -> str:
        p = PrettyPrinter(step=self.ctx.step)
        p._visit(n)
        s = ''.join(p.buf)
        # 简单判断：若是 BinOp/UnaryOp 且优先级更低，包一层括号
        need_paren = False
        if isinstance(n, BinOp):
            op_prec = _BINOP_PREC.get(n.op, 0)
            if op_prec < prec:
                need_paren = True
        elif isinstance(n, UnaryOp):
            if _UNARY_PREC < prec:
                need_paren = True
        return f'({s})' if need_paren else s

    def _n_MemberAccess(self, n: MemberAccess):
        self._w(f"{self._fmt_expr(n.object, 10)}.{n.member}")

    def _n_ListIndex(self, n: ListIndex):
        self._w(f"{self._fmt_expr(n.list_expr, 10)}[{self._fmt_expr(n.index)}]")

    def _n_BinOp(self, n: BinOp):
        op_prec = _BINOP_PREC.get(n.op, 0)
        self._w(self._fmt_expr(n.left, op_prec))
        self._w(f' {n.op} ')
        self._w(self._fmt_expr(n.right, op_prec + 1))

    def _n_UnaryOp(self, n: UnaryOp):
        self._w(f"{n.op} ")
        self._w(self._fmt_expr(n.operand, _UNARY_PREC))

    # ---------- 赋值 & 变量声明 ----------
    def _n_Assign(self, n: Assign):
        self._w(f"{n.target} = {self._fmt_expr(n.value)}")

    def _n_IndexAssign(self, n: IndexAssign):
        self._w(f"{self._fmt_expr(n.container, 10)}[{self._fmt_expr(n.index)}] = {self._fmt_expr(n.value)}")

    def _n_VarDecl(self, n: VarDecl):
        self._w(f'var {n.name}')
        if n.type_hint:
            self._w(f': {n.type_hint}')
        if n.value is not None:
            self._w(f' = {self._fmt_expr(n.value)}')

    # ---------- 控制流 ----------
    def _n_IfStatement(self, n: IfStatement):
        self._w(f'if {self._fmt_expr(n.condition)}:')
        if n.then_branch:
            self._nl()
            self._block(n.then_branch)
        for (ec, eb) in n.elif_branches:
            self._nl(); self._pad()
            self._w(f'elif {self._fmt_expr(ec)}:')
            if eb:
                self._nl()
                self._block(eb)
        if n.else_branch:
            self._nl(); self._pad()
            self._w('else:')
            self._nl()
            self._block(n.else_branch)
        self._nl(); self._pad()
        self._w('end')

    def _n_WhileStatement(self, n: WhileStatement):
        self._w(f'while {self._fmt_expr(n.condition)}:')
        if n.body:
            self._nl()
            self._block(n.body)
        self._nl(); self._pad()
        self._w('end')

    def _n_ForStatement(self, n: ForStatement):
        start_s = self._fmt_expr(n.start)
        end_s = self._fmt_expr(n.end)
        if n.step is not None:
            step_s = f', {self._fmt_expr(n.step)}'
        else:
            step_s = ''
        self._w(f'for {n.var_name} in range({start_s}, {end_s}{step_s}):')
        if n.body:
            self._nl()
            self._block(n.body)
        self._nl(); self._pad()
        self._w('end')

    def _n_BreakStatement(self, _n: BreakStatement):
        self._w('break')

    def _n_ContinueStatement(self, _n: ContinueStatement):
        self._w('continue')

    def _n_ThrowStatement(self, n: ThrowStatement):
        self._w('throw')
        if n.kind:
            self._w(f' {n.kind}')
        self._w(f' {self._fmt_expr(n.value)}')

    def _n_TryCatchStatement(self, n: TryCatchStatement):
        self._w('try:')
        if n.try_body:
            self._nl()
            self._block(n.try_body)
        if n.catch_body:
            self._nl(); self._pad()
            self._w('catch')
            if n.catch_kind:
                self._w(f' {n.catch_kind}')
            if n.catch_var:
                self._w(f'({n.catch_var})')
            self._w(':')
            self._nl()
            self._block(n.catch_body)
        if n.finally_body:
            self._nl(); self._pad()
            self._w('finally:')
            self._nl()
            self._block(n.finally_body)
        self._nl(); self._pad()
        self._w('end')

    def _n_ExportStatement(self, n: ExportStatement):
        self._w('export ')
        parts = []
        for nm in n.names:
            parts.append(nm)
        for (k, v) in n.assignments:
            parts.append(f'{k} = {self._fmt_expr(v)}')
        self._w(', '.join(parts))

    def _n_AssertStatement(self, n: AssertStatement):
        self._w(f'assert {self._fmt_expr(n.condition)}')
        if n.message:
            self._w(f', {self._fmt_expr(n.message)}')

    # ---------- 函数 ----------
    def _n_FuncDef(self, n: FuncDef):
        params = []
        for i, p in enumerate(n.params):
            t = n.param_types[i] if i < len(n.param_types) else None
            if t:
                params.append(f'{p}: {t}')
            else:
                params.append(p)
        self._w(f'func {n.name}({", ".join(params)})')
        if n.return_type:
            self._w(f' -> {n.return_type}')
        self._w(':')
        if n.body:
            self._nl()
            self._block(n.body)
        self._nl(); self._pad()
        self._w('end')

    def _n_FuncCall(self, n: FuncCall):
        args = ', '.join(self._fmt_expr(a) for a in n.args)
        self._w(f'{n.name}({args})')

    def _n_MethodCall(self, n: MethodCall):
        obj = self._fmt_expr(n.object, 10)
        args = ', '.join(self._fmt_expr(a) for a in n.args)
        self._w(f'{obj}.{n.method}({args})')

    def _n_ReturnStatement(self, n: ReturnStatement):
        self._w('return')
        if n.value is not None:
            self._w(f' {self._fmt_expr(n.value)}')

    def _n_PrintStatement(self, n: PrintStatement):
        args = ', '.join(self._fmt_expr(a) for a in n.args)
        self._w(f'print({args})')

    def _n_InputCall(self, n: InputCall):
        if n.prompt:
            self._w(f'input({self._fmt_expr(n.prompt)})')
        else:
            self._w('input()')

    def _n_ImportStatement(self, n: ImportStatement):
        self._w(f'import {_escape_string(n.module_name)}')
        if n.alias:
            self._w(f' as {n.alias}')

    def _n_RangeExpr(self, n: RangeExpr):
        parts = [self._fmt_expr(n.start), self._fmt_expr(n.end)]
        if n.step is not None:
            parts.append(self._fmt_expr(n.step))
        self._w(f"range({', '.join(parts)})")


# ==========================================================
# 对外 API
# ==========================================================
def format_source(source: str, step: int = 4, file_tag: str = "<source>") -> str:
    """格式化 HaiScript 源码字符串"""
    tokens = Lexer(source, file_tag).tokenize()
    ast = Parser(tokens).parse()
    return PrettyPrinter(step=step).format(ast)


def format_file(path: Union[str, Path], inplace: bool = False,
                check: bool = False, step: int = 4) -> Union[bool, str]:
    """格式化 .hs 文件
    - check=True:  返回是否需要格式化 (True=已格式化/不需要, False=需要格式化)
    - inplace=True: 直接写回原文件；返回是否发生修改
    - 默认: 返回格式化后的源码字符串
    """
    p = Path(path)
    src = p.read_text(encoding='utf-8')
    try:
        out = format_source(src, step=step, file_tag=str(p))
    except (ParseError, Exception) as e:
        raise ValueError(f"格式化失败（语法错误）: {e}") from e
    if check:
        return src == out
    if inplace:
        if src != out:
            p.write_text(out, encoding='utf-8')
            return True
        return False
    return out
