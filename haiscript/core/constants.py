"""
HaiScript 常量定义
"""
from pathlib import Path

# 项目信息
PROJECT_NAME = "HaiScript"
VERSION = "1.2.0"
WEBSITE = "https://haiscript.netlify.app/"
AUTHOR = "Yan_Canghai (HTPS-CDY)"
REPO_URL = "https://github.com/HTPS-CDY/HaiScript"
LIB_REPO_URL = "https://github.com/HTPS-CDY/HSLib"
LICENSE_NAME = "MIT"

# 配置文件路径
CONFIG_DIR = Path.home() / ".haiscript"
CONFIG_FILE = CONFIG_DIR / "config.json"
ALIAS_FILE = CONFIG_DIR / "aliases.json"
HISTORY_FILE = CONFIG_DIR / "history"
LOG_FILE = CONFIG_DIR / "haiscript.log"

# 脚本扩展名
SCRIPT_EXTENSION = ".hs"
COMPILED_EXTENSION = ".c"
EXECUTABLE_EXTENSION = ".exe" if __import__('os').name == 'nt' else ""

# 编码
DEFAULT_ENCODING = "utf-8"
WINDOWS_ENCODING = "gbk"

# 默认配置
DEFAULT_CONFIG = {
    "enable_safety_checks": True,
    "enable_command_whitelist": True,
    "allowed_roots": [],
    "process_history_limit": 100,
    "default_timeout": 30,
    "log_operations": True,
    "max_input_length": 4096,
}

# 危险命令黑名单（正则表达式）
DANGEROUS_PATTERNS = [
    r'rm\s+-rf\s+[/\\]',
    r'del\s+/[Ff]\s+/[Qq]\s+[A-Za-z]:\\',
    r'format\s+[A-Za-z]:',
    r'powershell\s+.*-Command',
    r'Invoke-Expression',
    r'rmdir\s+/[Ss]\s+/[Qq]',
    r'reg\s+delete',
    r'chmod\s+777\s+/',
    r'chown\s+-R\s+.*:/',
    r'dd\s+if=.*of=/dev/',
]

# 允许的系统命令白名单
ALLOWED_SYSTEM_COMMANDS = {
    'ping', 'ipconfig', 'ifconfig', 'netstat',
    'whoami', 'hostname', 'date', 'time',
    'tasklist', 'ps',
}
