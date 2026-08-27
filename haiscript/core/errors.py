"""
HaiScript 错误类型分层
层级：BaseException (Python) → HSError → 各类型错误
"""
from typing import Any, Optional


class HSError(Exception):
    """HaiScript 所有错误的基类"""

    def __init__(self, message: str = "", kind: str = "Error",
                 line: int = 0, col: int = 0, payload: Any = None):
        loc = f"[{line}:{col}] " if line or col else ""
        super().__init__(f"{loc}{kind}: {message}")
        self.message = message
        self.kind = kind
        self.line = line
        self.col = col
        self.payload = payload  # 可携带自定义数据

    # 与 HaiScript 交互时的友好构造
    @classmethod
    def wrap(cls, exc: BaseException, line: int = 0, col: int = 0) -> "HSError":
        if isinstance(exc, HSError):
            if not exc.line and not exc.col:
                exc.line, exc.col = line, col
            return exc
        if isinstance(exc, (KeyError, LookupError)):
            return KeyNotFoundError(str(exc), line=line, col=col)
        if isinstance(exc, (TypeError, ValueError)):
            return TypeError(str(exc), line=line, col=col)
        if isinstance(exc, (FileNotFoundError, PermissionError, OSError)):
            return IOError(str(exc), line=line, col=col)
        if isinstance(exc, ZeroDivisionError):
            return ZeroDivisionError_("除数为零", line=line, col=col)
        return RuntimeException(str(exc), line=line, col=col)

    def to_hs_value(self):
        """转为 HaiScript 可见的错误对象（字典）"""
        return {
            "__error__": True,
            "kind": self.kind,
            "message": self.message,
            "line": self.line,
            "col": self.col,
        }


class RuntimeException(HSError):
    """运行时错误 - 通用"""
    def __init__(self, message: str = "", line: int = 0, col: int = 0):
        super().__init__(message, "RuntimeError", line, col)


class TypeError(HSError):
    """类型错误 - 类型不匹配"""
    def __init__(self, message: str = "", line: int = 0, col: int = 0):
        super().__init__(message, "TypeError", line, col)


class KeyNotFoundError(HSError):
    """键/下标不存在 - Map/List/字符串"""
    def __init__(self, message: str = "", line: int = 0, col: int = 0):
        super().__init__(message, "KeyNotFoundError", line, col)


class IndexOutOfRangeError(HSError):
    """数组下标越界"""
    def __init__(self, message: str = "", line: int = 0, col: int = 0):
        super().__init__(message, "IndexOutOfRangeError", line, col)


class ZeroDivisionError_(HSError):
    """除零错误"""
    def __init__(self, message: str = "", line: int = 0, col: int = 0):
        super().__init__(message, "ZeroDivisionError", line, col)


class IOError(HSError):
    """I/O错误 - 文件/网络等"""
    def __init__(self, message: str = "", line: int = 0, col: int = 0, path: str = ""):
        super().__init__(message, "IOError", line, col, payload={"path": path})


class ParseError_(HSError):
    """语法错误（HaiScript层可见版本）"""
    def __init__(self, message: str = "", line: int = 0, col: int = 0):
        super().__init__(message, "ParseError", line, col)


class AssertionError_(HSError):
    """断言失败（避免与 Python 内置 AssertionError 同名冲突）"""
    def __init__(self, message: str = "", line: int = 0, col: int = 0):
        super().__init__(message, "AssertionError", line, col)


class ModuleNotFoundError(HSError):
    """import 模块不存在"""
    def __init__(self, module: str, line: int = 0, col: int = 0):
        super().__init__(f"模块不存在: '{module}'", "ModuleNotFoundError", line, col)
        self.module = module
