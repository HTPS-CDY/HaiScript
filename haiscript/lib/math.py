"""
HaiScript Math 模块头文件
提供数学常量与常用数学函数。
"""
from typing import Optional


PI: float
"""圆周率 π。"""

E: float
"""自然常数 e。"""

TAU: float
"""2π。"""

INF: float
"""正无穷。"""

NAN: float
"""非数。"""


def sqrt(x: float) -> float:
    """平方根。"""
    ...


def cbrt(x: float) -> float:
    """立方根。"""
    ...


def sin(x: float) -> float:
    """正弦。"""
    ...


def cos(x: float) -> float:
    """余弦。"""
    ...


def tan(x: float) -> float:
    """正切。"""
    ...


def asin(x: float) -> float:
    """反正弦。"""
    ...


def acos(x: float) -> float:
    """反余弦。"""
    ...


def atan(x: float) -> float:
    """反正切。"""
    ...


def atan2(y: float, x: float) -> float:
    """双参数反正切。"""
    ...


def log(x: float, base: Optional[float] = None) -> float:
    """对数，默认自然对数。"""
    ...


def log2(x: float) -> float:
    """以 2 为底的对数。"""
    ...


def log10(x: float) -> float:
    """以 10 为底的对数。"""
    ...


def exp(x: float) -> float:
    """e 的 x 次方。"""
    ...


def pow(x: float, y: float) -> float:
    """x 的 y 次方。"""
    ...


def floor(x: float) -> float:
    """向下取整。"""
    ...


def ceil(x: float) -> float:
    """向上取整。"""
    ...


def round(x: float, ndigits: Optional[int] = None) -> float:
    """四舍五入。"""
    ...


def mod(x: float, y: float) -> float:
    """取模。"""
    ...


def sign(x: float) -> float:
    """符号函数。"""
    ...


def clamp(x: float, lo: float, hi: float) -> float:
    """将 x 限制在 [lo, hi] 区间。"""
    ...


def degrees(x: float) -> float:
    """弧度转角度。"""
    ...


def radians(x: float) -> float:
    """角度转弧度。"""
    ...


def abs(x: float) -> float:
    """绝对值。"""
    ...
