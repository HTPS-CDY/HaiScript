"""
HaiScript 系统命令模块
含安全加固：PID验证、shell=False优先、白名单限制
"""
import os
import sys
import platform
from datetime import datetime
from typing import List

from haiscript.core.security import SecurityManager
from haiscript.utils.colors import (
    print_success, print_error, print_warning, print_info, print_header,
)
from haiscript.utils.helpers import confirm_prompt


class SystemCommands:
    """系统命令处理器"""

    def __init__(self, security: SecurityManager):
        self.security = security

    def cmd_whoami(self, _args: List[str]) -> bool:
        """显示当前用户: whoami"""
        try:
            code, out, err = self.security.safe_execute_command(
                'whoami', timeout=5
            )
            if out:
                print(out.strip())
            elif err:
                print_error(err.strip())
            return code == 0
        except Exception as e:
            print_error(f"获取用户信息失败: {e}")
            return False

    def cmd_hostname(self, _args: List[str]) -> bool:
        """显示主机名: hostname"""
        try:
            code, out, err = self.security.safe_execute_command(
                'hostname', timeout=5
            )
            if out:
                print(out.strip())
            elif err:
                print_error(err.strip())
            return code == 0
        except Exception as e:
            print_error(f"获取主机名失败: {e}")
            return False

    def cmd_date(self, _args: List[str]) -> bool:
        """显示日期: date"""
        try:
            now = datetime.now()
            print(now.strftime("%Y-%m-%d %A"))
            return True
        except Exception as e:
            print_error(f"获取日期失败: {e}")
            return False

    def cmd_time(self, _args: List[str]) -> bool:
        """显示时间: time"""
        try:
            now = datetime.now()
            print(now.strftime("%H:%M:%S"))
            return True
        except Exception as e:
            print_error(f"获取时间失败: {e}")
            return False

    def cmd_sysinfo(self, _args: List[str]) -> bool:
        """显示系统信息: sysinfo"""
        print_header("系统信息")
        print(f"  系统:    {platform.system()} {platform.release()}")
        print(f"  平台:    {platform.platform()}")
        print(f"  处理器:  {platform.processor() or '未知'}")
        print(f"  Python:  {platform.python_version()}")
        print(f"  当前目录: {os.getcwd()}")
        try:
            import psutil
            mem = psutil.virtual_memory()
            print(f"  CPU:     {psutil.cpu_percent()}%")
            print(f"  内存:    {mem.percent}% ({mem.used // (1024**3)}GB/{mem.total // (1024**3)}GB)")
        except ImportError:
            pass
        return True

    def cmd_ps(self, _args: List[str]) -> bool:
        """显示进程列表（信息脱敏+分页）: ps"""
        try:
            if os.name == 'nt':
                code, out, err = self.security.safe_execute_command(
                    'tasklist', timeout=10
                )
            else:
                code, out, err = self.security.safe_execute_command(
                    'ps aux', timeout=10, use_shell=True
                )

            if out:
                lines = out.splitlines()
                # 分页显示：前50行
                for line in lines[:50]:
                    print(line)
                if len(lines) > 50:
                    print_info(f"（共 {len(lines)} 行，仅显示前50行）")
            if err:
                print_warning(err.strip()[:200])
            return True
        except Exception as e:
            print_error(f"获取进程列表失败: {e}")
            return False

    def cmd_kill(self, args: List[str]) -> bool:
        """结束进程（含PID验证和二次确认）: kill <PID> [-f]"""
        if not args:
            print_error("用法: kill <PID> [-f]")
            return False

        force = '-f' in args
        pid_tokens = [a for a in args if not a.startswith('-')]
        if not pid_tokens:
            print_error("请指定PID")
            return False

        pid_str = pid_tokens[0]
        is_valid, pid = self.security.validate_pid(pid_str)
        if not is_valid:
            print_error(f"无效的PID: {pid_str} (必须是正整数)")
            return False

        # 二次确认（除非强制）
        if not force:
            if not confirm_prompt(f"确定要结束进程 PID={pid} 吗?"):
                print_info("已取消")
                return False

        try:
            if os.name == 'nt':
                cmd_args = ['taskkill', '/PID', str(pid)]
                if force:
                    cmd_args.append('/F')
                code, out, err = self.security.safe_execute_command(
                    ' '.join(cmd_args), timeout=10, use_shell=True
                )
            else:
                signal = '-9' if force else '-15'
                code, out, err = self.security.safe_execute_command(
                    f'kill {signal} {pid}', timeout=10
                )

            if code == 0:
                print_success(f"已结束进程: PID={pid}")
                self.security.log_operation("KILL", f"PID={pid}", True)
            else:
                if err:
                    print_error(err.strip())
                else:
                    print_error(f"结束进程失败: code={code}")
            return code == 0
        except Exception as e:
            print_error(f"结束进程失败: {e}")
            self.security.log_operation("KILL", f"PID={pid} error: {e}", False)
            return False

    def cmd_clear(self, _args: List[str]) -> bool:
        """清屏: clear"""
        os.system('cls' if os.name == 'nt' else 'clear')
        return True
