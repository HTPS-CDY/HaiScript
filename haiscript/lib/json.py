"""
HaiScript JSON 模块头文件
提供 JSON 字符串与对象的互相转换，以及文件读写能力。
"""
from typing import Any, Union, Optional


def parse(s: str) -> Union[dict, list]:
    """解析 JSON 字符串为对象。"""
    ...


def stringify(v: Any, indent: Optional[int] = None) -> str:
    """将值序列化为 JSON 字符串。"""
    ...


def stringify_pretty(v: Any, indent: int = 2) -> str:
    """将值美化序列化为带缩进的 JSON 字符串。"""
    ...


def load(path: str) -> Union[dict, list]:
    """从文件读取并解析 JSON。"""
    ...


def save(path: str, value: Any, indent: int = 2) -> bool:
    """将值序列化为 JSON 写入文件。"""
    ...


def load_file(path: str) -> Union[dict, list]:
    """load 的别名。"""
    ...


def save_file(path: str, value: Any) -> bool:
    """save 的别名。"""
    ...
