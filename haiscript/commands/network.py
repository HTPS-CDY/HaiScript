"""
HaiScript 网络命令模块
"""
import os
import sys
from typing import List

from haiscript.core.security import SecurityManager
from haiscript.utils.colors import (
    print_success, print_error, print_warning, print_info, print_header,
)


class NetworkCommands:
    """网络命令处理器"""

    def __init__(self, security: SecurityManager):
        self.security = security

    def cmd_ping(self, args: List[str]) -> bool:
        """Ping测试: ping <主机>"""
        if not args:
            print_info("用法: ping <主机名或IP地址>")
            print("  示例: ping google.com")
            print("  示例: ping 8.8.8.8")
            return False

        host = args[0].strip()
        # 简单主机名校验，防止注入
        import re
        if not re.match(r'^[a-zA-Z0-9.\-_:]+$', host):
            print_error(f"无效的主机名: {host}")
            return False

        print_info(f"Ping测试: {host}")
        try:
            if os.name == 'nt':
                cmd = f'ping -n 4 {host}'
            else:
                cmd = f'ping -c 4 {host}'

            code, out, err = self.security.safe_execute_command(
                cmd, timeout=20
            )

            if out:
                lines = out.splitlines()
                # 提取关键字行
                found_stats = False
                for line in lines:
                    line_s = line.strip()
                    if any(k in line_s for k in ('平均', 'Average', 'avg', 'ms', '丢失', 'loss')):
                        if any(k in line_s.lower() for k in ('平均', 'average', 'avg')):
                            print_success(f"统计: {line_s}")
                            found_stats = True
                        elif any(k in line_s.lower() for k in ('丢失', 'loss', 'received')):
                            if "0%" in line_s or "0.0%" in line_s:
                                print_success(f"丢包: {line_s}")
                            else:
                                print_warning(f"丢包: {line_s}")
                            found_stats = True

                if not found_stats:
                    # 显示输出摘要
                    for line in lines[:12]:
                        if line.strip():
                            print(f"  {line}")

            if err:
                err_s = err.strip()
                if err_s:
                    if "找不到主机" in err_s or "Unknown host" in err_s:
                        print_error(f"无法解析主机: {host}")
                    elif "请求超时" in err_s or "timed out" in err_s.lower():
                        print_warning("请求超时，主机可能不可达")
                    else:
                        print_warning(err_s[:300])
            return True
        except Exception as e:
            print_error(f"Ping测试失败: {e}")
            return False

    def cmd_ipconfig(self, _args: List[str]) -> bool:
        """显示IP配置: ipconfig / ifconfig"""
        try:
            if os.name == 'nt':
                cmd = 'ipconfig'
            else:
                cmd = 'ifconfig'
            code, out, err = self.security.safe_execute_command(
                cmd, timeout=10
            )
            if out:
                # 显示关键信息
                lines = out.splitlines()
                interesting = []
                keywords = ('IP', 'IPv4', 'IPv6', 'Subnet', '子网', 'Gateway', '网关',
                           'Mask', '掩码', 'MAC', 'DNS', 'ether', 'inet', 'scope')
                for line in lines:
                    if any(k.lower() in line.lower() for k in keywords):
                        interesting.append(line)
                if interesting:
                    print('\n'.join(interesting))
                else:
                    print('\n'.join(lines[:40]))
            if err:
                print_warning(err.strip()[:200])
            return True
        except Exception as e:
            print_error(f"获取网络配置失败: {e}")
            return False

    def cmd_netstat(self, _args: List[str]) -> bool:
        """显示网络连接（限制行数）: netstat"""
        try:
            if os.name == 'nt':
                cmd = 'netstat -an'
            else:
                cmd = 'netstat -tulpn'
            code, out, err = self.security.safe_execute_command(
                cmd, timeout=15
            )
            if out:
                lines = out.splitlines()
                for line in lines[:60]:
                    print(line)
                if len(lines) > 60:
                    print_info(f"（共 {len(lines)} 行，仅显示前60行）")
            if err:
                print_warning(err.strip()[:200])
            return True
        except Exception as e:
            print_error(f"获取网络连接失败: {e}")
            return False
