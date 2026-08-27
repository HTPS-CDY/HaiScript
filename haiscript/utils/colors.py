"""
HaiScript 简化版颜色工具
砍掉不必要的色彩功能，保留基本输出标识
"""
import sys
import os

# 颜色常量 - 极简版，只用几个关键颜色
class Color:
    """极简颜色类 - 砍掉ColorManager全局染色等不必要功能"""
    RESET = ''
    SUCCESS = ''  # 绿色
    ERROR = ''    # 红色
    WARNING = ''  # 黄色
    INFO = ''     # 蓝色
    HEADER = ''   # 青色
    PROMPT = ''   # 蓝色高亮
    BOLD = ''

    _initialized = False

    @classmethod
    def init(cls):
        """初始化颜色支持（仅支持简单ANSI，砍掉colorama复杂依赖）"""
        if cls._initialized:
            return
        cls._initialized = True

        try:
            # 尝试启用ANSI支持（Windows 10+）
            if os.name == 'nt':
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

            cls.RESET = '\033[0m'
            cls.SUCCESS = '\033[92m'
            cls.ERROR = '\033[91m'
            cls.WARNING = '\033[93m'
            cls.INFO = '\033[94m'
            cls.HEADER = '\033[96m'
            cls.PROMPT = '\033[94m\033[1m'
            cls.BOLD = '\033[1m'
        except Exception:
            # 不支持颜色就使用空字符串
            pass

    @staticmethod
    def disable():
        """禁用所有颜色"""
        Color.RESET = ''
        Color.SUCCESS = ''
        Color.ERROR = ''
        Color.WARNING = ''
        Color.INFO = ''
        Color.HEADER = ''
        Color.PROMPT = ''
        Color.BOLD = ''


# 自动初始化
Color.init()


def print_success(msg: str):
    """打印成功信息"""
    print(f"{Color.SUCCESS}[OK] {msg}{Color.RESET}")


def print_error(msg: str):
    """打印错误信息"""
    print(f"{Color.ERROR}[ERR] {msg}{Color.RESET}", file=sys.stderr)


def print_warning(msg: str):
    """打印警告信息"""
    print(f"{Color.WARNING}[WARN] {msg}{Color.RESET}")


def print_info(msg: str):
    """打印信息"""
    print(f"{Color.INFO}[INFO] {msg}{Color.RESET}")


def print_header(msg: str):
    """打印标题"""
    print(f"{Color.HEADER}{Color.BOLD}{msg}{Color.RESET}")
