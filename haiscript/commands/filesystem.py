"""
HaiScript 文件系统命令模块
含安全加固：路径检查、操作确认等
"""
import os
import shutil
import glob
from pathlib import Path
from typing import List, Optional, Tuple

from haiscript.core.security import SecurityManager
from haiscript.utils.colors import (
    print_success, print_error, print_warning, print_info,
    Color
)
from haiscript.utils.helpers import confirm_prompt


class FileSystemCommands:
    """文件系统命令处理器"""

    def __init__(self, security: SecurityManager):
        self.security = security

    # ---------- 目录操作 ----------
    def cmd_cd(self, args: List[str]) -> bool:
        """切换目录: cd [路径]"""
        target = args[0] if args else str(Path.home())

        # 安全检查
        is_safe, reason = self.security.is_safe_path(target)
        if not is_safe:
            print_error(f"路径访问被拒绝: {reason}")
            return False

        try:
            os.chdir(target)
            print_success(f"切换到: {Path.cwd()}")
            return True
        except Exception as e:
            print_error(f"切换目录失败: {e}")
            return False

    def cmd_pwd(self, _args: List[str]) -> bool:
        """显示当前目录: pwd"""
        print_info(f"当前目录: {Path.cwd()}")
        return True

    def cmd_ls(self, args: List[str]) -> bool:
        """列出目录内容: ls [路径] [-l]"""
        target = '.'
        for arg in args:
            if not arg.startswith('-'):
                target = arg
                break

        if not os.path.exists(target):
            print_error(f"路径不存在: {target}")
            return False

        try:
            if os.path.isdir(target):
                items = sorted(os.listdir(target))
                for item in items:
                    full = os.path.join(target, item)
                    if os.path.isdir(full):
                        print(f"{Color.INFO}{item}/{Color.RESET}")
                    else:
                        size = os.path.getsize(full)
                        size_str = f"{size:>8}"
                        print(f"  {size_str}  {item}")
            else:
                print(target)
            return True
        except Exception as e:
            print_error(f"列出文件失败: {e}")
            return False

    def cmd_mkdir(self, args: List[str]) -> bool:
        """创建目录: mkdir <目录名>"""
        if not args:
            print_error("用法: mkdir <目录名>")
            return False

        dir_name = args[0]
        is_safe, reason = self.security.is_safe_path(dir_name)
        if not is_safe:
            print_error(f"路径访问被拒绝: {reason}")
            return False

        try:
            os.makedirs(dir_name, exist_ok=True)
            print_success(f"目录已创建: {dir_name}")
            self.security.log_operation("MKDIR", dir_name)
            return True
        except Exception as e:
            print_error(f"创建目录失败: {e}")
            return False

    # ---------- 文件操作 ----------
    def cmd_touch(self, args: List[str]) -> bool:
        """创建/更新文件: touch <文件1> [文件2] ..."""
        if not args:
            print_error("用法: touch <文件1> [文件2] ...")
            return False

        all_ok = True
        for fname in args:
            is_safe, reason = self.security.is_safe_path(fname)
            if not is_safe:
                print_error(f"路径访问被拒绝 [{fname}]: {reason}")
                all_ok = False
                continue

            try:
                if os.path.exists(fname):
                    os.utime(fname, None)
                    print_info(f"已更新修改时间: {fname}")
                else:
                    with open(fname, 'w', encoding='utf-8'):
                        pass
                    print_success(f"文件已创建: {fname}")
                    self.security.log_operation("TOUCH", fname)
            except Exception as e:
                print_error(f"操作失败 [{fname}]: {e}")
                all_ok = False
        return all_ok

    def cmd_rm(self, args: List[str]) -> bool:
        """删除文件: rm <文件> [-f] [-r]"""
        if not args:
            print_error("用法: rm <文件> [-f] [-r]")
            return False

        force = '-f' in args
        recursive = '-r' in args
        targets = [a for a in args if not a.startswith('-')]

        if not targets:
            print_error("请指定要删除的文件")
            return False

        all_ok = True
        for target in targets:
            is_safe, reason = self.security.is_safe_path(target)
            if not is_safe:
                print_error(f"路径访问被拒绝 [{target}]: {reason}")
                all_ok = False
                continue

            if not os.path.exists(target):
                print_error(f"文件不存在: {target}")
                all_ok = False
                continue

            if not force:
                if not confirm_prompt(f"确定要删除 '{target}' 吗?"):
                    print_info("已取消删除")
                    continue

            try:
                if os.path.isdir(target):
                    if recursive:
                        shutil.rmtree(target)
                        print_success(f"目录已删除: {target}")
                    else:
                        print_error(f"'{target}' 是目录，请使用 -r 参数")
                        all_ok = False
                        continue
                else:
                    os.remove(target)
                    print_success(f"文件已删除: {target}")
                self.security.log_operation("RM", target)
            except Exception as e:
                print_error(f"删除失败 [{target}]: {e}")
                all_ok = False
        return all_ok

    def cmd_cp(self, args: List[str]) -> bool:
        """复制文件: cp <源> <目标>"""
        targets = [a for a in args if not a.startswith('-')]
        if len(targets) < 2:
            print_error("用法: cp <源文件> <目标文件>")
            return False

        src, dst = targets[0], targets[1]

        is_safe_s, _ = self.security.is_safe_path(src)
        is_safe_d, reason_d = self.security.is_safe_path(dst)
        if not is_safe_s:
            print_error(f"源路径访问被拒绝: {src}")
            return False
        if not is_safe_d:
            print_error(f"目标路径访问被拒绝: {reason_d}")
            return False

        if not os.path.exists(src):
            print_error(f"源文件不存在: {src}")
            return False

        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
            size = os.path.getsize(src) if os.path.isfile(src) else 0
            print_success(f"已复制: {src} -> {dst} ({size:,} 字节)")
            self.security.log_operation("CP", f"{src} -> {dst}")
            return True
        except Exception as e:
            print_error(f"复制失败: {e}")
            return False

    def cmd_mv(self, args: List[str]) -> bool:
        """移动文件: mv <源> <目标>"""
        targets = [a for a in args if not a.startswith('-')]
        if len(targets) < 2:
            print_error("用法: mv <源文件> <目标文件>")
            return False

        src, dst = targets[0], targets[1]

        is_safe_s, _ = self.security.is_safe_path(src)
        is_safe_d, reason_d = self.security.is_safe_path(dst)
        if not is_safe_s:
            print_error(f"源路径访问被拒绝: {src}")
            return False
        if not is_safe_d:
            print_error(f"目标路径访问被拒绝: {reason_d}")
            return False

        if not os.path.exists(src):
            print_error(f"源文件不存在: {src}")
            return False

        try:
            shutil.move(src, dst)
            print_success(f"已移动: {src} -> {dst}")
            self.security.log_operation("MV", f"{src} -> {dst}")
            return True
        except Exception as e:
            print_error(f"移动失败: {e}")
            return False

    def cmd_find(self, args: List[str]) -> bool:
        """查找文件: find <模式> [路径]"""
        if not args:
            print_error("用法: find <模式> [起始路径]")
            return False

        pattern = args[0]
        root = args[1] if len(args) > 1 else '.'

        is_safe, reason = self.security.is_safe_path(root)
        if not is_safe:
            print_error(f"路径访问被拒绝: {reason}")
            return False

        try:
            matches: List[str] = []
            for dirpath, dirs, files in os.walk(root):
                for fname in files:
                    if pattern in fname:
                        matches.append(os.path.join(dirpath, fname))
                if len(matches) > 50:
                    break

            if matches:
                print_success(f"找到 {len(matches)} 个匹配:")
                for m in matches[:20]:
                    print(f"  {m}")
                if len(matches) > 20:
                    print_info(f"... 还有 {len(matches) - 20} 个结果已省略")
            else:
                print_warning("未找到匹配的文件")
            return True
        except Exception as e:
            print_error(f"查找失败: {e}")
            return False

    def cmd_cat(self, args: List[str]) -> bool:
        """显示文件内容: cat <文件>"""
        if not args:
            print_error("用法: cat <文件名>")
            return False

        fname = args[0]
        is_safe, reason = self.security.is_safe_path(fname)
        if not is_safe:
            print_error(f"路径访问被拒绝: {reason}")
            return False

        if not os.path.exists(fname):
            print_error(f"文件不存在: {fname}")
            return False

        try:
            with open(fname, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(65536)  # 最多读64KB，防止超大文件
                print(content)
            return True
        except Exception as e:
            print_error(f"读取文件失败: {e}")
            return False

    def cmd_echo(self, args: List[str]) -> bool:
        """输出文字: echo <文字>"""
        print(' '.join(args))
        return True
