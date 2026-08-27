"""
HaiScript 词法分析器 (Lexer)
将源代码文本转换为 Token 序列
"""
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional


class TokenType(Enum):
    # 字面量
    NUMBER = auto()
    STRING = auto()
    IDENTIFIER = auto()

    # 关键字
    VAR = auto()
    IF = auto()
    ELIF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    IN = auto()
    RANGE = auto()
    FUNC = auto()
    RETURN = auto()
    END = auto()
    PRINT = auto()
    INPUT = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    TRUE = auto()
    FALSE = auto()
    NIL = auto()
    IMPORT = auto()
    # —— 1.1 扩展关键字 ——
    TRY = auto()
    CATCH = auto()
    FINALLY = auto()
    THROW = auto()
    BREAK = auto()
    CONTINUE = auto()
    EXPORT = auto()
    MAP = auto()          # 类型提示
    SET = auto()          # 类型提示
    BOOL = auto()         # 类型提示
    NUMBER_KW = auto()    # 'number' 类型提示
    STRING_KW = auto()    # 'string' 类型提示
    LIST_KW = auto()      # 'list' 类型提示
    ANY_KW = auto()       # 'any' 类型提示
    ASSERT = auto()
    AS = auto()

    # 运算符
    PLUS = auto()        # +
    MINUS = auto()       # -
    STAR = auto()        # *
    SLASH = auto()       # /
    PERCENT = auto()     # %
    EQ = auto()          # =
    EQEQ = auto()        # ==
    NEQ = auto()         # !=
    LT = auto()          # <
    GT = auto()          # >
    LEQ = auto()         # <=
    GEQ = auto()         # >=
    PIPE = auto()        # |> 管道（为未来保留）
    FAT_ARROW = auto()   # => 箭头
    ARROW = auto()       # -> 类型标注返回箭头

    # 分隔符
    LPAREN = auto()      # (
    RPAREN = auto()      # )
    LBRACKET = auto()    # [
    RBRACKET = auto()    # ]
    LBRACE = auto()      # {
    RBRACE = auto()      # }
    COMMA = auto()       # ,
    COLON = auto()       # :
    SEMICOLON = auto()   # ;
    DOT = auto()         # .
    NEWLINE = auto()     # 换行
    EOF = auto()         # 文件结束


KEYWORDS = {
    'var': TokenType.VAR,
    'if': TokenType.IF,
    'elif': TokenType.ELIF,
    'else': TokenType.ELSE,
    'while': TokenType.WHILE,
    'for': TokenType.FOR,
    'in': TokenType.IN,
    'range': TokenType.RANGE,
    'func': TokenType.FUNC,
    'return': TokenType.RETURN,
    'end': TokenType.END,
    'print': TokenType.PRINT,
    'input': TokenType.INPUT,
    'and': TokenType.AND,
    'or': TokenType.OR,
    'not': TokenType.NOT,
    'true': TokenType.TRUE,
    'false': TokenType.FALSE,
    'nil': TokenType.NIL,
    'import': TokenType.IMPORT,
    # 1.1 扩展
    'try': TokenType.TRY,
    'catch': TokenType.CATCH,
    'finally': TokenType.FINALLY,
    'throw': TokenType.THROW,
    'break': TokenType.BREAK,
    'continue': TokenType.CONTINUE,
    'export': TokenType.EXPORT,
    'Map': TokenType.MAP,
    'Set': TokenType.SET,
    'bool': TokenType.BOOL,
    'number': TokenType.NUMBER_KW,
    'string': TokenType.STRING_KW,
    'list': TokenType.LIST_KW,
    'any': TokenType.ANY_KW,
    'assert': TokenType.ASSERT,
    'as': TokenType.AS,
}


@dataclass
class Token:
    type: TokenType
    value: any
    line: int
    col: int


class LexError(Exception):
    def __init__(self, msg: str, line: int, col: int):
        super().__init__(f"[{line}:{col}] 词法错误: {msg}")
        self.line = line
        self.col = col


class Lexer:
    """HaiScript 词法分析器"""

    def __init__(self, source: str, filename: str = "<string>"):
        self.src = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []

    # ---------- 辅助 ----------
    def _peek(self, offset: int = 0) -> Optional[str]:
        idx = self.pos + offset
        return self.src[idx] if idx < len(self.src) else None

    def _advance(self) -> str:
        ch = self.src[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _skip_whitespace_and_comments(self):
        while self.pos < len(self.src):
            ch = self._peek()
            if ch in (' ', '\t', '\r'):
                self._advance()
            elif ch == '#':
                # 行注释直到换行
                while self.pos < len(self.src) and self._peek() != '\n':
                    self._advance()
            elif ch == '\\' and self._peek(1) == '\n':
                # 行连接符
                self._advance()  # \
                self._advance()  # \n
            else:
                break

    def _make_token(self, type_: TokenType, value=None) -> Token:
        return Token(type=type_, value=value, line=self.line, col=self.col)

    # ---------- 扫描各种元素 ----------
    def _scan_number(self) -> Token:
        start_col = self.col
        start_pos = self.pos
        is_float = False

        while self.pos < len(self.src):
            ch = self._peek()
            if ch.isdigit():
                self._advance()
            elif ch == '.' and not is_float and self._peek(1) and self._peek(1).isdigit():
                is_float = True
                self._advance()
            else:
                break

        text = self.src[start_pos:self.pos]
        value = float(text) if is_float else int(text)
        return Token(TokenType.NUMBER, value, self.line, start_col)

    def _scan_string(self, quote: str) -> Token:
        start_col = self.col
        self._advance()  # 跳过开始引号
        chars = []
        while self.pos < len(self.src):
            ch = self._peek()
            if ch == quote:
                self._advance()
                return Token(TokenType.STRING, ''.join(chars), self.line, start_col)
            elif ch == '\\':
                self._advance()
                esc = self._peek()
                if esc is None:
                    raise LexError("字符串未闭合", self.line, start_col)
                escape_map = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\', '"': '"', "'": "'", '0': '\0'}
                chars.append(escape_map.get(esc, esc))
                self._advance()
            elif ch == '\n':
                raise LexError("字符串跨行未闭合", self.line, start_col)
            else:
                chars.append(self._advance())
        raise LexError(f"字符串未闭合 (缺少 {quote})", self.line, start_col)

    def _scan_identifier(self) -> Token:
        start_col = self.col
        start_pos = self.pos
        while self.pos < len(self.src):
            ch = self._peek()
            if ch and (ch.isalnum() or ch == '_'):
                self._advance()
            else:
                break
        text = self.src[start_pos:self.pos]
        tok_type = KEYWORDS.get(text, TokenType.IDENTIFIER)
        if tok_type == TokenType.TRUE:
            return Token(tok_type, True, self.line, start_col)
        if tok_type == TokenType.FALSE:
            return Token(tok_type, False, self.line, start_col)
        if tok_type == TokenType.NIL:
            return Token(tok_type, None, self.line, start_col)
        return Token(tok_type, text, self.line, start_col)

    # ---------- 主扫描 ----------
    def tokenize(self) -> List[Token]:
        """执行词法分析，返回Token列表"""
        while self.pos < len(self.src):
            self._skip_whitespace_and_comments()
            if self.pos >= len(self.src):
                break

            ch = self._peek()
            start_line, start_col = self.line, self.col

            # 换行
            if ch == '\n':
                self._advance()
                self.tokens.append(Token(TokenType.NEWLINE, '\n', start_line, start_col))
                continue

            # 数字
            if ch.isdigit():
                self.tokens.append(self._scan_number())
                continue

            # 字符串
            if ch in ('"', "'"):
                self.tokens.append(self._scan_string(ch))
                continue

            # 标识符/关键字
            if ch.isalpha() or ch == '_':
                self.tokens.append(self._scan_identifier())
                continue

            # 运算符和分隔符
            advance_two = False
            if ch == '+':
                ttype = TokenType.PLUS
            elif ch == '-':
                if self._peek(1) == '>':
                    ttype = TokenType.ARROW  # -> 返回类型箭头
                    advance_two = True
                else:
                    ttype = TokenType.MINUS
            elif ch == '*':
                ttype = TokenType.STAR
            elif ch == '/':
                ttype = TokenType.SLASH
            elif ch == '%':
                ttype = TokenType.PERCENT
            elif ch == '!':
                if self._peek(1) == '=':
                    ttype = TokenType.NEQ
                    advance_two = True
                else:
                    raise LexError(f"意外字符: '!', 是否想写 '!='?", start_line, start_col)
            elif ch == '<':
                if self._peek(1) == '=':
                    ttype = TokenType.LEQ
                    advance_two = True
                else:
                    ttype = TokenType.LT
            elif ch == '>':
                if self._peek(1) == '=':
                    ttype = TokenType.GEQ
                    advance_two = True
                else:
                    ttype = TokenType.GT
            elif ch == '(':
                ttype = TokenType.LPAREN
            elif ch == ')':
                ttype = TokenType.RPAREN
            elif ch == '[':
                ttype = TokenType.LBRACKET
            elif ch == ']':
                ttype = TokenType.RBRACKET
            elif ch == '{':
                ttype = TokenType.LBRACE
            elif ch == '}':
                ttype = TokenType.RBRACE
            elif ch == ',':
                ttype = TokenType.COMMA
            elif ch == ';':
                ttype = TokenType.SEMICOLON
            elif ch == '.':
                # 如果前后都是数字，可能是点；但我们的数字解析只允许 x.y
                ttype = TokenType.DOT
            elif ch == ':':
                if self._peek(1) == '>':
                    ttype = TokenType.FAT_ARROW  # :>（留作未来使用）
                    advance_two = True
                else:
                    ttype = TokenType.COLON
            elif ch == '|':
                if self._peek(1) == '>':
                    ttype = TokenType.PIPE  # |> 管道
                    advance_two = True
                else:
                    raise LexError(f"意外字符: '|', 是否想写 '|>' 管道?", start_line, start_col)
            elif ch == '=':
                if self._peek(1) == '=':
                    ttype = TokenType.EQEQ
                    advance_two = True
                elif self._peek(1) == '>':
                    ttype = TokenType.FAT_ARROW  # =>
                    advance_two = True
                else:
                    ttype = TokenType.EQ
            else:
                raise LexError(f"未知字符: '{ch}'", start_line, start_col)

            if advance_two:
                self._advance()
                self._advance()
            else:
                self._advance()
            self.tokens.append(Token(ttype, None, start_line, start_col))

        # 末尾换行 + EOF
        if self.tokens and self.tokens[-1].type != TokenType.NEWLINE:
            self.tokens.append(Token(TokenType.NEWLINE, '\n', self.line, self.col))
        self.tokens.append(Token(TokenType.EOF, None, self.line, self.col))
        return self.tokens
