"""
HaiScript HTTP 模块头文件
提供 HTTP 请求、文件下载、HTTP 服务器等能力。
"""
from typing import Any, Callable, Dict, Optional


def get(url: str, timeout: int = 10) -> Dict[str, Any]:
    """发起 HTTP GET 请求，返回 (status, body, headers)。"""
    ...


def post(url: str, data: Any, timeout: int = 10) -> Dict[str, Any]:
    """发起 HTTP POST 请求。"""
    ...


def download(url: str, path: str, timeout: int = 30) -> bool:
    """下载文件到本地路径。"""
    ...


def serve(port: int, handler: Optional[Callable] = None, static_dir: Optional[str] = None) -> None:
    """启动 HTTP 服务器（阻塞）。"""
    ...


def serve_bg(port: int, handler: Optional[Callable] = None) -> str:
    """后台启动 HTTP 服务器，返回服务器标识。"""
    ...


def start(port: int, handler: Optional[Callable] = None) -> str:
    """serve_bg 的别名。"""
    ...


def stop() -> bool:
    """停止后台 HTTP 服务器。"""
    ...
