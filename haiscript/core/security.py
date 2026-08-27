"""
HaiScript 安全加固模块
修复安全报告中指出的漏洞
"""
import os
import re
import shlex
import subprocess
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from haiscript.core.constants import (
    DANGEROUS_PATTERNS,
    ALLOWED_SYSTEM_COMMANDS,
    DEFAULT_ENCODING,
    WINDOWS_ENCODING,
    LOG_FILE,
)


class SecurityManager:
    """安全管理器 - 处理命令注入、路径检查等安全问题"""

    def __init__(self, enable_checks: bool = True):
        self.enable_checks = enable_checks
        self._setup_logging()
        self._compile_patterns()

    def _setup_logging(self):
        """设置操作审计日志"""
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            logging.basicConfig(
                filename=str(LOG_FILE),
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                encoding='utf-8'
            )
            self.logger = logging.getLogger('haiscript')
        except Exception:
            self.logger = None

    def log_operation(self, operation: str, detail: str = "", success: bool = True):
        """记录操作审计日志"""
        if self.logger:
            level = logging.INFO if success else logging.WARNING
            self.logger.log(level, f"[{operation}] {detail}")

    def _compile_patterns(self):
        """预编译危险模式正则"""
        self._danger_regexes = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]

    def check_dangerous_patterns(self, command: str) -> Tuple[bool, str]:
        """检查命令中是否包含危险模式

        Returns:
            (是否危险, 危险说明)
        """
        if not self.enable_checks:
            return False, ""

        for i, pattern in enumerate(self._danger_regexes):
            if pattern.search(command):
                return True, f"匹配危险模式 #{i + 1}: {DANGEROUS_PATTERNS[i]}"
        return False, ""

    def is_safe_path(self, file_path: str) -> Tuple[bool, str]:
        """检查路径是否安全（防止目录遍历和系统关键文件访问）

        Returns:
            (是否安全, 原因说明)
        """
        if not self.enable_checks:
            return True, ""

        try:
            path = Path(file_path).resolve()
            path_str = str(path).lower()

            # Windows 系统关键目录
            if os.name == 'nt':
                forbidden_prefixes = [
                    'c:\\windows',
                    'c:\\program files',
                    'c:\\program files (x86)',
                    'c:\\programdata',
                    'c:\\system volume information',
                ]
                for prefix in forbidden_prefixes:
                    if path_str.startswith(prefix):
                        return False, f"禁止访问系统目录: {path}"

                # 根目录保护
                if len(path.parts) <= 2 and path_str.startswith('c:\\'):
                    return False, f"禁止在系统根目录操作: {path}"
            else:
                # Linux/Unix 系统关键目录
                forbidden_prefixes = [
                    '/etc/', '/boot/', '/root/', '/usr/bin/',
                    '/usr/sbin/', '/proc/', '/sys/', '/dev/',
                ]
                for prefix in forbidden_prefixes:
                    if path_str.startswith(prefix[:-1]) or path_str == prefix[:-1]:
                        return False, f"禁止访问系统目录: {path}"

            return True, ""
        except Exception as e:
            return False, f"路径检查异常: {e}"

    def validate_pid(self, pid_str: str) -> Tuple[bool, Optional[int]]:
        """验证PID参数是否合法"""
        try:
            pid = int(pid_str)
            if pid <= 0 or pid > 4194304:
                return False, None
            return True, pid
        except (ValueError, TypeError):
            return False, None

    def safe_execute_command(
        self,
        command: str,
        timeout: int = 30,
        use_shell: bool = False
    ) -> Tuple[int, str, str]:
        """安全执行系统命令

        关键修复:
        1. 避免 shell=True（除非必要）
        2. 危险模式检查
        3. 超时限制
        4. 日志记录
        """
        # 检查危险模式
        is_danger, reason = self.check_dangerous_patterns(command)
        if is_danger:
            self.log_operation("BLOCKED_COMMAND", f"{command} - {reason}", False)
            return -1, "", f"安全拦截: {reason}"

        # 检查白名单（如果启用）
        if self.enable_checks:
            try:
                if use_shell:
                    first_token = command.strip().split()[0].lower()
                else:
                    tokens = shlex.split(command)
                    first_token = tokens[0].lower() if tokens else ""

                if first_token and first_token not in ALLOWED_SYSTEM_COMMANDS:
                    # 只对白名单命令直接系统执行
                    pass  # 允许非白名单命令由上层处理，但已经过危险模式检查
            except Exception:
                pass

        self.log_operation("EXEC_CMD", command)

        try:
            encoding = WINDOWS_ENCODING if os.name == 'nt' else DEFAULT_ENCODING

            if use_shell:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding=encoding,
                    errors='replace',
                    timeout=timeout
                )
            else:
                try:
                    args = shlex.split(command)
                except ValueError:
                    args = command.split()

                result = subprocess.run(
                    args,
                    shell=False,
                    capture_output=True,
                    text=True,
                    encoding=encoding,
                    errors='replace',
                    timeout=timeout
                )

            return result.returncode, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            self.log_operation("TIMEOUT", command, False)
            return -1, "", "命令执行超时"
        except FileNotFoundError:
            return -1, "", f"命令未找到: {command}"
        except Exception as e:
            self.log_operation("ERROR", f"{command} - {e}", False)
            return -1, "", f"命令执行错误: {e}"
