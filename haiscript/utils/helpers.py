"""
HaiScript 通用辅助函数
"""
import os
import sys
from pathlib import Path
from typing import Optional


def is_running_as_exe() -> bool:
    """检测是否作为打包EXE运行"""
    return hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS')


def get_cwd_display(max_len: int = 40) -> str:
    """获取显示用的当前路径（过长时截断）"""
    cwd = str(Path.cwd())
    if len(cwd) > max_len:
        return "..." + cwd[-(max_len - 3):]
    return cwd


def clear_screen():
    """清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')


def confirm_prompt(message: str, default_no: bool = True) -> bool:
    """二次确认提示

    Args:
        message: 提示信息
        default_no: 默认是否为No

    Returns:
        用户是否确认
    """
    suffix = " (y/N): " if default_no else " (Y/n): "
    try:
        answer = input(message + suffix).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False

    if not answer:
        return not default_no
    return answer in ('y', 'yes')


def is_executable_in_path(command: str) -> bool:
    """检查命令是否在PATH中存在"""
    if os.path.exists(command):
        return True

    path_dirs = os.environ.get('PATH', '').split(os.pathsep)
    for dir_path in path_dirs:
        full_path = os.path.join(dir_path, command)
        if os.path.exists(full_path):
            return True

    # Windows 检查 .exe/.bat/.cmd 后缀
    if os.name == 'nt':
        for ext in ('.exe', '.bat', '.cmd', '.py'):
            ext_path = command + ext
            if os.path.exists(ext_path):
                return True
            for dir_path in path_dirs:
                full_path = os.path.join(dir_path, ext_path)
                if os.path.exists(full_path):
                    return True

    return False


def safe_join_path(*parts) -> Optional[str]:
    """安全拼接路径并解析为绝对路径"""
    try:
        return str(Path(*parts).resolve())
    except Exception:
        return None
