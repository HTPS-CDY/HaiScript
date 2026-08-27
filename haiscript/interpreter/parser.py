"""
HaiScript 语法分析器 (Parser)
将 Token 序列转换为抽象语法树 (AST)
"""
from dataclasses import dataclass, field
from typing import List, Optional, Union

from haiscript.interpreter.lexer import Token, TokenType, Lexer, LexError


# ---------- AST 节点定义 ----------
@dataclass
class ASTNode:
    line: int = 0
    col: int = 0


@dataclass
class Program(ASTNode):
    statements: List[ASTNode] = field(default_factory=list)


@dataclass
class NumberLiteral(ASTNode):
    value: Union[int, float] = 0


@dataclass
class StringLiteral(ASTNode):
    value: str = ""


@dataclass
class BoolLiteral(ASTNode):
    value: bool = False


@dataclass
class NilLiteral(ASTNode):
    pass


@dataclass
class ListLiteral(ASTNode):
    elements: List[ASTNode] = field(default_factory=list)


@dataclass
class MapLiteral(ASTNode):
    """{k1: v1, k2: v2}"""
    pairs: List[tuple] = field(default_factory=list)  # [(key_node, val_node), ...]


@dataclass
class SetLiteral(ASTNode):
    """set{1,2,3} 或 {1,2,3}(非键值对)"""
    elements: List[ASTNode] = field(default_factory=list)


@dataclass
class Identifier(ASTNode):
    name: str = ""


@dataclass
class MemberAccess(ASTNode):
    """expr.member —— 点属性访问"""
    object: ASTNode = None
    member: str = ""


@dataclass
class BinOp(ASTNode):
    op: str = ""
    left: ASTNode = None
    right: ASTNode = None


@dataclass
class UnaryOp(ASTNode):
    op: str = ""
    operand: ASTNode = None


@dataclass
class Assign(ASTNode):
    """var = val 赋值"""
    target: str = ""
    value: ASTNode = None


@dataclass
class IndexAssign(ASTNode):
    """容器[索引] = 值"""
    container: ASTNode = None
    index: ASTNode = None
    value: ASTNode = None


@dataclass
class VarDecl(ASTNode):
    name: str = ""
    value: Optional[ASTNode] = None
    type_hint: Optional[str] = None  # 类型标注（可选）


@dataclass
class IfStatement(ASTNode):
    condition: ASTNode = None
    then_branch: List[ASTNode] = field(default_factory=list)
    elif_branches: List[tuple] = field(default_factory=list)  # [(cond, stmts), ...]
    else_branch: List[ASTNode] = field(default_factory=list)


@dataclass
class WhileStatement(ASTNode):
    condition: ASTNode = None
    body: List[ASTNode] = field(default_factory=list)


@dataclass
class ForStatement(ASTNode):
    var_name: str = ""
    start: ASTNode = None
    end: ASTNode = None
    step: Optional[ASTNode] = None
    body: List[ASTNode] = field(default_factory=list)


@dataclass
class BreakStatement(ASTNode):
    pass


@dataclass
class ContinueStatement(ASTNode):
    pass


@dataclass
class ThrowStatement(ASTNode):
    value: ASTNode = None
    kind: Optional[str] = None  # "RuntimeError" 等类型名


@dataclass
class TryCatchStatement(ASTNode):
    try_body: List[ASTNode] = field(default_factory=list)
    catch_var: Optional[str] = None  # catch(e) 的 e
    catch_kind: Optional[str] = None  # catch Type(e) 指定类型
    catch_body: List[ASTNode] = field(default_factory=list)
    finally_body: List[ASTNode] = field(default_factory=list)


@dataclass
class ExportStatement(ASTNode):
    """export name1, name2 或 export name = expr"""
    names: List[str] = field(default_factory=list)
    assignments: List[tuple] = field(default_factory=list)  # [(name, value_node), ...]


@dataclass
class AssertStatement(ASTNode):
    condition: ASTNode = None
    message: Optional[ASTNode] = None


@dataclass
class FuncDef(ASTNode):
    name: str = ""
    params: List[str] = field(default_factory=list)
    param_types: List[Optional[str]] = field(default_factory=list)
    return_type: Optional[str] = None
    body: List[ASTNode] = field(default_factory=list)


@dataclass
class FuncCall(ASTNode):
    name: str = ""
    args: List[ASTNode] = field(default_factory=list)


@dataclass
class MethodCall(ASTNode):
    """expr.method(args) —— 运行时解析"""
    object: ASTNode = None
    method: str = ""
    args: List[ASTNode] = field(default_factory=list)


@dataclass
class ReturnStatement(ASTNode):
    value: Optional[ASTNode] = None


@dataclass
class PrintStatement(ASTNode):
    args: List[ASTNode] = field(default_factory=list)


@dataclass
class InputCall(ASTNode):
    prompt: Optional[ASTNode] = None


@dataclass
class ImportStatement(ASTNode):
    module_name: str = ""
    alias: Optional[str] = None  # import "foo" as F


@dataclass
class ListIndex(ASTNode):
    list_expr: ASTNode = None
    index: ASTNode = None


@dataclass
class RangeExpr(ASTNode):
    start: ASTNode = None
    end: ASTNode = None
    step: Optional[ASTNode] = None


# 控制流标签 (内部使用)
class _ControlFlow(BaseException):
    pass


class BreakSignal(_ControlFlow):
    pass


class ContinueSignal(_ControlFlow):
    pass


# ---------- 解析错误 ----------
class ParseError(Exception):
    def __init__(self, msg: str, line: int = 0, col: int = 0):
        super().__init__(f"[{line}:{col}] 语法错误: {msg}")
        self.line = line
        self.col = col


# ---------- 语法分析器 ----------
class Parser:
    """HaiScript 语法分析器"""

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    # ---------- 辅助 ----------
    def _peek(self, offset: int = 0) -> Token:
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else self.tokens[-1]

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.type != TokenType.EOF:
            self.pos += 1
        return tok

    def _check(self, *types: TokenType) -> bool:
        return self._peek().type in types

    def _match(self, *types: TokenType) -> Optional[Token]:
        if self._check(*types):
            return self._advance()
        return None

    def _expect(self, type_: TokenType, msg: str = "") -> Token:
        tok = self._advance()
        if tok.type != type_:
            expected = msg or type_.name
            raise ParseError(
                f"期望 {expected}，实际得到 {tok.type.name}" +
                (f" ('{tok.value}')" if tok.value is not None else ""),
                tok.line, tok.col
            )
        return tok

    def _skip_newlines(self):
        while self._check(TokenType.NEWLINE):
            self._advance()

    # ---------- 顶层 ----------
    def parse(self) -> Program:
        """解析整个程序"""
        program = Program()
        self._skip_newlines()
        while not self._check(TokenType.EOF):
            stmt = self._parse_statement()
            if stmt is not None:
                program.statements.append(stmt)
            self._skip_newlines()
        return program

    # ---------- 语句 ----------
    def _parse_statement(self) -> Optional[ASTNode]:
        tok = self._peek()
        line, col = tok.line, tok.col

        if tok.type == TokenType.VAR:
            return self._parse_var_decl()
        elif tok.type == TokenType.IF:
            return self._parse_if()
        elif tok.type == TokenType.WHILE:
            return self._parse_while()
        elif tok.type == TokenType.FOR:
            return self._parse_for()
        elif tok.type == TokenType.FUNC:
            return self._parse_func_def()
        elif tok.type == TokenType.RETURN:
            return self._parse_return()
        elif tok.type == TokenType.PRINT:
            return self._parse_print()
        elif tok.type == TokenType.IMPORT:
            return self._parse_import()
        elif tok.type == TokenType.TRY:
            return self._parse_try()
        elif tok.type == TokenType.THROW:
            return self._parse_throw()
        elif tok.type == TokenType.BREAK:
            t = self._advance()
            self._expect_newline_or_eof()
            return BreakStatement(line=t.line, col=t.col)
        elif tok.type == TokenType.CONTINUE:
            t = self._advance()
            self._expect_newline_or_eof()
            return ContinueStatement(line=t.line, col=t.col)
        elif tok.type == TokenType.EXPORT:
            return self._parse_export()
        elif tok.type == TokenType.ASSERT:
            return self._parse_assert()
        elif tok.type in (TokenType.NEWLINE, TokenType.EOF,
                          TokenType.CATCH, TokenType.FINALLY, TokenType.END):
            return None
        else:
            # 可能是赋值或表达式语句
            return self._parse_assign_or_expr()

    def _parse_type_signature(self) -> str:
        """解析类型标注语法：
        基础类型:  int, float, bool, string, nil, any
        容器类型:  list, map, set, func
        泛型:      list<int>, map<string, int>, func(int, string) -> bool
        返回: 规范化的类型字符串（如 "list<int>", "map<string,int>", "func(int,string)->bool"）
        """
        # 第一个 token: IDENTIFIER 或 类型关键字
        tok = self._advance()
        valid_simple = {
            TokenType.IDENTIFIER, TokenType.STRING_KW, TokenType.NUMBER_KW,
            TokenType.BOOL, TokenType.LIST_KW, TokenType.MAP, TokenType.SET,
            TokenType.ANY_KW, TokenType.NIL,
        }
        if tok.type not in valid_simple:
            raise ParseError(f"期望类型名，得到 {tok.type.name}" +
                             (f" ('{tok.value}')" if tok.value else ""),
                             tok.line, tok.col)
        base = tok.value if tok.value else {
            TokenType.STRING_KW: "string",
            TokenType.NUMBER_KW: "number",
            TokenType.BOOL: "bool",
            TokenType.LIST_KW: "list",
            TokenType.MAP: "Map",
            TokenType.SET: "Set",
            TokenType.ANY_KW: "any",
            TokenType.NIL: "nil",
        }.get(tok.type, tok.type.name)

        # 泛型参数: Type<T1, T2, ...>
        if self._match(TokenType.LT):
            args: List[str] = []
            # 允许 > 前换行
            self._skip_newlines()
            if not self._check(TokenType.GT):
                while True:
                    self._skip_newlines()
                    args.append(self._parse_type_signature())
                    self._skip_newlines()
                    if not self._match(TokenType.COMMA):
                        break
            self._skip_newlines()
            self._expect(TokenType.GT, "泛型闭合 '>'")
            return f"{base}<{','.join(args)}>"

        # 函数类型简写: func(int, string) -> bool  —— 先处理括号参数
        # (这里 base 若是 IDENTIFIER 'func'，且紧跟 LPAREN)
        if base.lower() == 'func' and self._check(TokenType.LPAREN):
            self._advance()
            arg_types: List[str] = []
            if not self._check(TokenType.RPAREN):
                while True:
                    arg_types.append(self._parse_type_signature())
                    if not self._match(TokenType.COMMA):
                        break
            self._expect(TokenType.RPAREN)
            ret_type = 'nil'
            if self._match(TokenType.ARROW):
                ret_type = self._parse_type_signature()
            return f"func({','.join(arg_types)})->{ret_type}"

        return base

    def _parse_var_decl(self) -> VarDecl:
        tok = self._expect(TokenType.VAR)
        name_tok = self._expect(TokenType.IDENTIFIER, "变量名")
        node = VarDecl(line=tok.line, col=tok.col, name=name_tok.value)
        # 类型标注: name : Type
        if self._match(TokenType.COLON):
            node.type_hint = self._parse_type_signature()
        if self._match(TokenType.EQ):
            node.value = self._parse_expression()
        self._expect_newline_or_eof()
        return node

    def _parse_assert(self) -> AssertStatement:
        tok = self._expect(TokenType.ASSERT)
        node = AssertStatement(line=tok.line, col=tok.col)
        node.condition = self._parse_expression()
        if self._match(TokenType.COMMA):
            node.message = self._parse_expression()
        self._expect_newline_or_eof()
        return node

    def _parse_throw(self) -> ThrowStatement:
        tok = self._expect(TokenType.THROW)
        node = ThrowStatement(line=tok.line, col=tok.col)
        # throw "msg" | throw Type "msg" | throw(err_object)
        first = self._parse_expression()
        # 模式 1：throw TypeError "msg"  —— 第一个是类型标识符 + 第二个是字符串
        # 模式 2：throw "msg"
        # 简化：只看其后是否有第二个表达式；若 first 是标识符且是已知错误名，且下一个 token 是表达式开头，则为 (kind, msg)
        kind_set = {'RuntimeError', 'RuntimeException', 'TypeError', 'IOError',
                    'KeyNotFoundError', 'IndexOutOfRangeError', 'ZeroDivisionError',
                    'AssertionError', 'AssertionError_', 'Error', 'ParseError',
                    'ModuleNotFoundError', 'HSError'}
        if isinstance(first, Identifier) and first.name in kind_set:
            if not self._check(TokenType.NEWLINE, TokenType.EOF, TokenType.END, TokenType.CATCH, TokenType.FINALLY,
                               TokenType.SEMICOLON):
                node.kind = first.name
                node.value = self._parse_expression()
                self._expect_newline_or_eof()
                return node
        node.value = first
        self._expect_newline_or_eof()
        return node

    def _parse_try(self) -> TryCatchStatement:
        tok = self._expect(TokenType.TRY)
        node = TryCatchStatement(line=tok.line, col=tok.col)
        self._expect(TokenType.COLON)
        self._skip_newlines()
        node.try_body = self._parse_block(end_keywords=(TokenType.CATCH, TokenType.FINALLY, TokenType.END))

        # catch [Kind](var):
        if self._match(TokenType.CATCH):
            # 形式: catch: | catch(var): | catch Kind: | catch Kind(var):
            if self._check(TokenType.IDENTIFIER):
                first_tok = self._advance()
                if self._check(TokenType.LPAREN):
                    # catch Kind(var): — 后跟括号，first_tok 必为类型名
                    node.catch_kind = first_tok.value
                    self._advance()
                    node.catch_var = self._expect(TokenType.IDENTIFIER, "catch变量").value
                    self._expect(TokenType.RPAREN)
                else:
                    # catch Kind: 或 catch var: 根据常见约定判定
                    kind_set = {'RuntimeError', 'RuntimeException', 'TypeError', 'IOError',
                                'KeyNotFoundError', 'IndexOutOfRangeError', 'ZeroDivisionError',
                                'AssertionError', 'AssertionError_', 'Error', 'ParseError',
                                'ModuleNotFoundError', 'HSError'}
                    if first_tok.value in kind_set:
                        node.catch_kind = first_tok.value
                    else:
                        node.catch_var = first_tok.value
            elif self._check(TokenType.LPAREN):
                # catch(var):
                self._advance()
                node.catch_var = self._expect(TokenType.IDENTIFIER, "catch变量").value
                self._expect(TokenType.RPAREN)
            self._expect(TokenType.COLON)
            self._skip_newlines()
            node.catch_body = self._parse_block(end_keywords=(TokenType.FINALLY, TokenType.END))

        if self._match(TokenType.FINALLY):
            self._expect(TokenType.COLON)
            self._skip_newlines()
            node.finally_body = self._parse_block(end_keywords=(TokenType.END,))

        # 消费 END（如存在）
        if self._check(TokenType.END):
            self._advance()
            self._expect_newline_or_eof()
        return node

    def _parse_export(self) -> ExportStatement:
        tok = self._expect(TokenType.EXPORT)
        node = ExportStatement(line=tok.line, col=tok.col)
        # 模式 A: export x, y, z
        # 模式 B: export x = expr, y = expr2
        # 模式 C: export func foo() ...  —— 后续由 func def 自己处理，这里不做
        while True:
            name_tok = self._expect(TokenType.IDENTIFIER, "导出的名称")
            if self._match(TokenType.EQ):
                value = self._parse_expression()
                node.assignments.append((name_tok.value, value))
            else:
                node.names.append(name_tok.value)
            if not self._match(TokenType.COMMA):
                break
        self._expect_newline_or_eof()
        return node

    def _parse_if(self) -> IfStatement:
        tok = self._expect(TokenType.IF)
        node = IfStatement(line=tok.line, col=tok.col)
        node.condition = self._parse_expression()
        self._expect(TokenType.COLON)
        self._skip_newlines()
        node.then_branch = self._parse_block()

        # elif
        while self._check(TokenType.ELIF):
            self._advance()
            elif_cond = self._parse_expression()
            self._expect(TokenType.COLON)
            self._skip_newlines()
            elif_body = self._parse_block()
            node.elif_branches.append((elif_cond, elif_body))

        # else
        if self._check(TokenType.ELSE):
            self._advance()
            self._expect(TokenType.COLON)
            self._skip_newlines()
            node.else_branch = self._parse_block()

        return node

    def _parse_while(self) -> WhileStatement:
        tok = self._expect(TokenType.WHILE)
        node = WhileStatement(line=tok.line, col=tok.col)
        node.condition = self._parse_expression()
        self._expect(TokenType.COLON)
        self._skip_newlines()
        node.body = self._parse_block()
        return node

    def _parse_for(self) -> ForStatement:
        tok = self._expect(TokenType.FOR)
        node = ForStatement(line=tok.line, col=tok.col)
        var_tok = self._expect(TokenType.IDENTIFIER, "循环变量名")
        node.var_name = var_tok.value
        self._expect(TokenType.IN)
        if self._check(TokenType.RANGE):
            self._advance()
            self._expect(TokenType.LPAREN)
            args = self._parse_expr_list(TokenType.RPAREN)
            if len(args) == 1:
                node.start = NumberLiteral(value=0, line=tok.line, col=tok.col)
                node.end = args[0]
            elif len(args) >= 2:
                node.start = args[0]
                node.end = args[1]
            if len(args) >= 3:
                node.step = args[2]
            self._expect(TokenType.RPAREN)
        else:
            # 简单形式: for i = start to end [step s]:
            raise ParseError("目前仅支持 for <var> in range(n) 形式", tok.line, tok.col)
        self._expect(TokenType.COLON)
        self._skip_newlines()
        node.body = self._parse_block()
        return node

    def _parse_func_def(self) -> FuncDef:
        tok = self._expect(TokenType.FUNC)
        node = FuncDef(line=tok.line, col=tok.col)
        name_tok = self._expect(TokenType.IDENTIFIER, "函数名")
        node.name = name_tok.value
        self._expect(TokenType.LPAREN)
        node.params = []
        node.param_types = []
        if not self._check(TokenType.RPAREN):
            while True:
                p = self._expect(TokenType.IDENTIFIER, "参数名")
                node.params.append(p.value)
                ptype: Optional[str] = None
                # 参数类型: param : Type
                if self._match(TokenType.COLON):
                    ptype = self._parse_type_signature()
                node.param_types.append(ptype)
                if not self._match(TokenType.COMMA):
                    break
        self._expect(TokenType.RPAREN)
        # 返回类型: -> Type
        if self._match(TokenType.ARROW):
            node.return_type = self._parse_type_signature()
        self._expect(TokenType.COLON)
        self._skip_newlines()
        node.body = self._parse_block()
        return node

    def _parse_block(self, end_keywords=None) -> List[ASTNode]:
        """解析语句块；默认以 END 结尾，可通过 end_keywords 指定其他结束词"""
        if end_keywords is None:
            end_keywords = (TokenType.END, TokenType.ELIF, TokenType.ELSE)
        always_end = tuple(set(end_keywords) | {TokenType.EOF})
        stmts: List[ASTNode] = []
        while not self._check(*always_end):
            self._skip_newlines()
            if self._check(*always_end):
                break
            stmt = self._parse_statement()
            if stmt is not None:
                stmts.append(stmt)
        # END 由外层消费
        if TokenType.END in end_keywords and self._check(TokenType.END):
            # 只有 if/func/for/while 的 END 由这里自动消费；try/catch/finally 的 END 交给上层
            self._advance()
            self._expect_newline_or_eof()
        return stmts

    def _expect_newline_or_eof(self):
        if not self._check(TokenType.NEWLINE, TokenType.EOF, TokenType.END, TokenType.ELIF, TokenType.ELSE):
            tok = self._peek()
            raise ParseError(
                f"语句末尾期望换行，得到 {tok.type.name}" +
                (f" ('{tok.value}')" if tok.value is not None else ""),
                tok.line, tok.col
            )
        self._skip_newlines()

    def _parse_return(self) -> ReturnStatement:
        tok = self._expect(TokenType.RETURN)
        node = ReturnStatement(line=tok.line, col=tok.col)
        if not self._check(TokenType.NEWLINE, TokenType.EOF, TokenType.END):
            node.value = self._parse_expression()
        self._expect_newline_or_eof()
        return node

    def _parse_print(self) -> PrintStatement:
        tok = self._expect(TokenType.PRINT)
        node = PrintStatement(line=tok.line, col=tok.col)
        self._expect(TokenType.LPAREN)
        node.args = self._parse_expr_list(TokenType.RPAREN)
        self._expect(TokenType.RPAREN)
        self._expect_newline_or_eof()
        return node

    def _parse_import(self) -> ImportStatement:
        tok = self._expect(TokenType.IMPORT)
        name_tok = self._expect(TokenType.STRING, "模块名（字符串）")
        node = ImportStatement(line=tok.line, col=tok.col, module_name=name_tok.value)
        if self._match(TokenType.AS):
            alias_tok = self._expect(TokenType.IDENTIFIER, "别名")
            node.alias = alias_tok.value
        self._expect_newline_or_eof()
        return node

    def _parse_assign_or_expr(self) -> ASTNode:
        # 尝试解析为表达式，然后看是否有 =
        expr = self._parse_expression()

        if self._check(TokenType.EQ):
            if isinstance(expr, Identifier):
                eq_tok = self._advance()
                value = self._parse_expression()
                self._expect_newline_or_eof()
                return Assign(line=eq_tok.line, col=eq_tok.col, target=expr.name, value=value)
            if isinstance(expr, ListIndex):
                # list[index] = value / map[k] = v
                eq_tok = self._advance()
                value = self._parse_expression()
                self._expect_newline_or_eof()
                return IndexAssign(line=eq_tok.line, col=eq_tok.col,
                                   container=expr.list_expr, index=expr.index, value=value)
            if isinstance(expr, MemberAccess):
                # obj.member = value —— 转为方法调用 "set"；在解释器端处理
                eq_tok = self._advance()
                value = self._parse_expression()
                self._expect_newline_or_eof()
                # 建模成 IndexAssign(container=obj, index=StringLiteral(member), value=value)
                from haiscript.interpreter.parser import StringLiteral as _SL
                idx = _SL(value=expr.member, line=expr.line, col=expr.col)
                return IndexAssign(line=eq_tok.line, col=eq_tok.col,
                                   container=expr.object, index=idx, value=value)

        # 表达式语句
        self._expect_newline_or_eof()
        return expr

    # ---------- 表达式（按优先级） ----------
    def _parse_expression(self):
        return self._parse_or()

    def _parse_or(self):
        left = self._parse_and()
        while self._check(TokenType.OR):
            tok = self._advance()
            right = self._parse_and()
            left = BinOp(op='or', left=left, right=right, line=tok.line, col=tok.col)
        return left

    def _parse_and(self):
        left = self._parse_not()
        while self._check(TokenType.AND):
            tok = self._advance()
            right = self._parse_not()
            left = BinOp(op='and', left=left, right=right, line=tok.line, col=tok.col)
        return left

    def _parse_not(self):
        if self._check(TokenType.NOT):
            tok = self._advance()
            operand = self._parse_not()
            return UnaryOp(op='not', operand=operand, line=tok.line, col=tok.col)
        return self._parse_compare()

    def _parse_compare(self):
        left = self._parse_additive()
        while self._check(TokenType.EQEQ, TokenType.NEQ, TokenType.LT, TokenType.GT, TokenType.LEQ, TokenType.GEQ):
            tok = self._advance()
            op_map = {
                TokenType.EQEQ: '==', TokenType.NEQ: '!=',
                TokenType.LT: '<', TokenType.GT: '>',
                TokenType.LEQ: '<=', TokenType.GEQ: '>=',
            }
            right = self._parse_additive()
            left = BinOp(op=op_map[tok.type], left=left, right=right, line=tok.line, col=tok.col)
        return left

    def _parse_additive(self):
        left = self._parse_multiplicative()
        while self._check(TokenType.PLUS, TokenType.MINUS):
            tok = self._advance()
            right = self._parse_multiplicative()
            left = BinOp(op='+' if tok.type == TokenType.PLUS else '-',
                        left=left, right=right, line=tok.line, col=tok.col)
        return left

    def _parse_multiplicative(self):
        left = self._parse_unary()
        while self._check(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            tok = self._advance()
            right = self._parse_unary()
            op = {TokenType.STAR: '*', TokenType.SLASH: '/', TokenType.PERCENT: '%'}[tok.type]
            left = BinOp(op=op, left=left, right=right, line=tok.line, col=tok.col)
        return left

    def _parse_unary(self):
        if self._check(TokenType.MINUS, TokenType.PLUS):
            tok = self._advance()
            operand = self._parse_unary()
            return UnaryOp(op='-' if tok.type == TokenType.MINUS else '+',
                          operand=operand, line=tok.line, col=tok.col)
        return self._parse_postfix()

    def _parse_postfix(self):
        expr = self._parse_primary()
        while True:
            if self._check(TokenType.LBRACKET):
                lb = self._advance()
                idx = self._parse_expression()
                rb = self._expect(TokenType.RBRACKET, "']'")
                expr = ListIndex(list_expr=expr, index=idx, line=lb.line, col=lb.col)
            elif self._check(TokenType.DOT):
                dot = self._advance()  # .
                # .member
                mem_tok = self._peek()
                member_name = None
                if mem_tok.type == TokenType.IDENTIFIER:
                    member_name = mem_tok.value
                    self._advance()
                elif mem_tok.type in (TokenType.STRING_KW, TokenType.NUMBER_KW,
                                      TokenType.BOOL, TokenType.LIST_KW, TokenType.MAP, TokenType.SET,
                                      TokenType.ANY_KW, TokenType.RANGE, TokenType.MAP, TokenType.SET,
                                      TokenType.IN):
                    # 允许用关键字做属性名（少见但兼容）
                    member_name = mem_tok.value if mem_tok.value else mem_tok.type.name
                    self._advance()
                else:
                    raise ParseError(f"'.' 后期望标识符，实际 {mem_tok.type.name}", mem_tok.line, mem_tok.col)
                expr = MemberAccess(object=expr, member=member_name, line=dot.line, col=dot.col)
            elif self._check(TokenType.LPAREN):
                lp = self._advance()
                args = self._parse_expr_list(TokenType.RPAREN)
                rp = self._expect(TokenType.RPAREN, "')'")
                if isinstance(expr, Identifier):
                    expr = FuncCall(name=expr.name, args=args, line=lp.line, col=lp.col)
                elif isinstance(expr, MemberAccess):
                    # obj.method(args) → MethodCall
                    expr = MethodCall(object=expr.object, method=expr.member,
                                      args=args, line=lp.line, col=lp.col)
                else:
                    # expr(a,b) Callable: 转为 MethodCall(object=expr, method="__call__")
                    expr = MethodCall(object=expr, method="__call__",
                                      args=args, line=lp.line, col=lp.col)
            elif self._check(TokenType.MINUS):
                # 防止把 a->b 的 ">" 误认为方法调用
                break
            else:
                break
        return expr

    def _parse_primary(self):
        tok = self._peek()

        if tok.type == TokenType.NUMBER:
            self._advance()
            return NumberLiteral(value=tok.value, line=tok.line, col=tok.col)
        if tok.type == TokenType.STRING:
            self._advance()
            return StringLiteral(value=tok.value, line=tok.line, col=tok.col)
        if tok.type == TokenType.TRUE or tok.type == TokenType.FALSE:
            self._advance()
            return BoolLiteral(value=tok.value, line=tok.line, col=tok.col)
        if tok.type == TokenType.NIL:
            self._advance()
            return NilLiteral(line=tok.line, col=tok.col)

        # 标识符或"类型关键字"（string/int/bool/list/map/set/any 等）作为表达式
        keyword_ids = {
            TokenType.STRING_KW, TokenType.NUMBER_KW,
            TokenType.BOOL, TokenType.LIST_KW, TokenType.MAP, TokenType.SET,
            TokenType.ANY_KW,
        }
        if tok.type == TokenType.IDENTIFIER or tok.type in keyword_ids:
            name = tok.value if tok.value else {
                TokenType.STRING_KW: "string",
                TokenType.NUMBER_KW: "number",
                TokenType.BOOL: "bool",
                TokenType.LIST_KW: "list",
                TokenType.MAP: "Map",
                TokenType.SET: "Set",
                TokenType.ANY_KW: "any",
            }.get(tok.type, tok.type.name)
            # set{1,2,3} | map{k:v} 构造字面量
            if name == 'set' and self._peek(1).type == TokenType.LBRACE:
                self._advance()  # 'set'
                return self._parse_set_literal(tok.line, tok.col)
            if name == 'map' and self._peek(1).type == TokenType.LBRACE:
                self._advance()  # 'map'
                return self._parse_map_literal(tok.line, tok.col)
            # 特殊处理 input()
            if name == 'input' and self._peek(1).type == TokenType.LPAREN:
                self._advance()  # 跳过 input
                self._advance()  # 跳过 (
                prompt = None
                if not self._check(TokenType.RPAREN):
                    prompt = self._parse_expression()
                self._expect(TokenType.RPAREN, "')'")
                return InputCall(prompt=prompt, line=tok.line, col=tok.col)
            ident = Identifier(name=name, line=tok.line, col=tok.col)
            self._advance()
            return ident

        if tok.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_expression()
            self._expect(TokenType.RPAREN, "')'")
            return expr
        if tok.type == TokenType.LBRACKET:
            lb = self._advance()
            elements = self._parse_expr_list(TokenType.RBRACKET)
            self._expect(TokenType.RBRACKET, "']'")
            lit = ListLiteral(elements=elements, line=lb.line, col=lb.col)
            return self._try_dot_chain(lit)
        if tok.type == TokenType.LBRACE:
            # { ... } —— 可能是 map 或 set，空则为 map
            line, col = tok.line, tok.col
            self._advance()  # {
            self._skip_newlines()
            # 空: {} => MapLiteral
            if self._check(TokenType.RBRACE):
                self._advance()
                return self._try_dot_chain(MapLiteral(line=line, col=col))
            # 预读：若第一个元素后紧跟 : => Map
            save = self.pos
            first_expr = self._parse_expression()
            is_map = False
            self._skip_newlines()
            if self._check(TokenType.COLON):
                is_map = True
            self.pos = save
            if is_map:
                return self._try_dot_chain(self._parse_map_literal(line, col, already_open=True))
            else:
                return self._try_dot_chain(self._parse_set_literal(line, col, already_open=True))

        # 点成员访问从 postfix 处理 —— 但数字和字符串也可能 .member，我们在 postfix 前单独扫一次
        raise ParseError(
            f"意外的 token: {tok.type.name}" +
            (f" ('{tok.value}')" if tok.value is not None else ""),
            tok.line, tok.col
        )

    def _try_dot_chain(self, expr: ASTNode) -> ASTNode:
        """在一个 primary 之后尝试消费若干个 `.member` / `.member(args)` 访问"""
        # 由外层的 _parse_postfix 在 while 循环中统一处理 —— 这里直接返回即可
        # 但为了支持 x["k"].m 的链式访问，_parse_postfix 的 while 会继续运行。
        return expr

    def _parse_map_literal(self, line: int, col: int, already_open: bool = False) -> MapLiteral:
        """解析 { k1: v1, k2: v2 }"""
        if not already_open:
            self._expect(TokenType.LBRACE, "'{'")
        node = MapLiteral(line=line, col=col)
        self._skip_newlines()
        if self._check(TokenType.RBRACE):
            self._advance()
            return node
        while True:
            self._skip_newlines()
            k = self._parse_expression()
            self._expect(TokenType.COLON, "':'")
            self._skip_newlines()
            v = self._parse_expression()
            node.pairs.append((k, v))
            self._skip_newlines()
            if not self._match(TokenType.COMMA):
                break
            self._skip_newlines()
        self._skip_newlines()
        self._expect(TokenType.RBRACE, "'}'")
        return node

    def _parse_set_literal(self, line: int, col: int, already_open: bool = False) -> SetLiteral:
        """解析 {1,2,3} 或 set{1,2,3}"""
        if not already_open:
            self._expect(TokenType.LBRACE, "'{'")
        node = SetLiteral(line=line, col=col)
        self._skip_newlines()
        if self._check(TokenType.RBRACE):
            self._advance()
            return node
        while True:
            self._skip_newlines()
            node.elements.append(self._parse_expression())
            self._skip_newlines()
            if not self._match(TokenType.COMMA):
                break
            self._skip_newlines()
        self._skip_newlines()
        self._expect(TokenType.RBRACE, "'}'")
        return node

    def _parse_expr_list(self, end_token: TokenType) -> List[ASTNode]:
        exprs: List[ASTNode] = []
        self._skip_newlines()
        if not self._check(end_token):
            exprs.append(self._parse_expression())
            while self._match(TokenType.COMMA):
                self._skip_newlines()
                if self._check(end_token):
                    break
                exprs.append(self._parse_expression())
            self._skip_newlines()
        return exprs
