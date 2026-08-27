"""
HaiScript OS 模块头文件
提供操作系统信息查询、环境变量、进程控制等能力。
"""
from typing import List, Optional


name: str
"""操作系统名称。"""

platform: str
"""操作系统平台。"""

arch: str
"""CPU 架构。"""

argv: List[str]
"""命令行参数列表。"""


def env(name: str, default: Optional[str] = None) -> str:
    """读取环境变量，不存在则返回 default。"""
    ...


def user() -> str:
    """返回当前用户名。"""
    ...


def hostname() -> str:
    """返回主机名。"""
    ...


def exit(code: int = 0) -> None:
    """退出当前进程。"""
    ...


def cwd() -> str:
    """返回当前工作目录。"""
    ...


def chdir(d: str) -> None:
    """切换当前工作目录。"""
    ...


def time() -> float:
    """返回当前时间戳（秒）。"""
    ...


def sleep(s: float) -> None:
    """睡眠指定秒数。"""
    ...
