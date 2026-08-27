"""
HaiScript 局域网模块头文件
提供本机网络信息、主机名解析、端口扫描、TCP 连接等能力。
"""
from typing import Any, Callable, Dict, List, Optional


def ip() -> str:
    """获取本机内网 IP。"""
    ...


def hostname() -> str:
    """获取本机主机名。"""
    ...


def resolve(hostname: str) -> str:
    """解析主机名到 IP。"""
    ...


def ping(host: str, timeout: float = 2) -> bool:
    """TCP ping，返回是否可达。"""
    ...


def scan_port(host: str, port: int, timeout: float = 1) -> bool:
    """扫描指定端口是否开放。"""
    ...


def scan(ip_base: str, port: Optional[int] = None, timeout: float = 0.5) -> List[str]:
    """扫描局域网内活动主机/端口。"""
    ...


def connect(host: str, port: int, data: Optional[Any] = None, timeout: float = 10) -> Any:
    """建立 TCP 连接并发送数据。"""
    ...


def listen(port: int, handler: Optional[Callable] = None, timeout: float = 30) -> Dict[str, Any]:
    """TCP 监听，返回连接信息。"""
    ...


def send(host: str, port: int, data: Optional[Any] = None, timeout: float = 10) -> Any:
    """connect 的别名。"""
    ...
