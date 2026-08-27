"""
HaiScript 外部程序模块头文件
提供启动外部进程、捕获输出、查找可执行文件等能力。
"""
from typing import Dict


class Process:
    """外部进程对象。"""

    pid: int
    """进程 ID。"""

    stdin: object
    """标准输入流。"""

    stdout: object
    """标准输出流。"""

    stderr: object
    """标准错误流。"""

    def wait(self) -> int:
        """等待进程结束，返回退出码。"""
        ...

    def terminate(self) -> None:
        """终止进程。"""
        ...

    def kill(self) -> None:
        """强制杀死进程。"""
        ...


def run(*args: str) -> int:
    """运行程序并等待结束，返回退出码。"""
    ...


def capture(*args: str) -> Dict[str, Any]:
    """运行程序并捕获输出 (code, stdout, stderr)。"""
    ...


def exec(*args: str) -> Dict[str, Any]:
    """capture 的别名。"""
    ...


def popen(*args: str) -> Process:
    """启动进程并返回 Process 对象。"""
    ...


def shell(cmd: str) -> Dict[str, Any]:
    """通过 shell 执行命令。"""
    ...


def which(name: str) -> str:
    """查找可执行文件路径。"""
    ...


def find(name: str) -> str:
    """which 的别名。"""
    ...
