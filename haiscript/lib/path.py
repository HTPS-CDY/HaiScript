"""
HaiScript Path 模块头文件
提供路径字符串操作与文件系统查询能力。
"""
from typing import List


sep: str
"""路径分隔符。"""


def join(*parts: str) -> str:
    """拼接多个路径片段。"""
    ...


def basename(p: str) -> str:
    """返回路径中的文件名部分。"""
    ...


def dirname(p: str) -> str:
    """返回路径中的目录部分。"""
    ...


def extname(p: str) -> str:
    """返回路径的扩展名（含点）。"""
    ...


def stem(p: str) -> str:
    """返回不含扩展名的文件名。"""
    ...


def resolve(p: str) -> str:
    """将路径解析为绝对路径。"""
    ...


def exists(p: str) -> bool:
    """判断路径是否存在。"""
    ...


def isfile(p: str) -> bool:
    """判断路径是否为文件。"""
    ...


def isdir(p: str) -> bool:
    """判断路径是否为目录。"""
    ...


def cwd() -> str:
    """返回当前工作目录。"""
    ...


def absolute(p: str) -> str:
    """返回绝对路径。"""
    ...


def with_ext(p: str, ext: str) -> str:
    """返回替换扩展名后的路径。"""
    ...


def parent(p: str) -> str:
    """返回父目录路径。"""
    ...


def split(p: str) -> List[str]:
    """将路径拆分为各组成部分。"""
    ...
