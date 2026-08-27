#!/usr/bin/env python3
"""
HaiScript 主入口文件
功能：
1. 交互式命令行（Shell 工具箱）
2. 执行 .hs HaiScript 脚本文件
3. 将 .hs 编译为 C 代码并调用 GCC 生成可执行文件
4. 安全加固的文件/系统/网络/编码命令
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Callable, Optional

# ---------- 模块导入 ----------
from haiscript import __version__, __project_name__
from haiscript.core.config import Config
from haiscript.core.security import SecurityManager
from haiscript.core.alias import AliasManager
from haiscript.core.history import HistoryManager
from haiscript.core.constants import (
    PROJECT_NAME, VERSION, WEBSITE, SCRIPT_EXTENSION,
)
from haiscript.utils.colors import (
    Color,
    print_success, print_error, print_warning, print_info, print_header,
)
from haiscript.utils.helpers import (
    get_cwd_display, confirm_prompt, is_executable_in_path,
)

from haiscript.commands.filesystem import FileSystemCommands
from haiscript.commands.system import SystemCommands
from haiscript.commands.network import NetworkCommands
from haiscript.commands.encoding import EncodingCommands

from haiscript.interpreter.interpreter import Interpreter
from haiscript.compiler_c.gcc_compile import GCCCompiler, CompileError


# ====================================================================
# HaiScript Shell 主类
# ====================================================================
class HaiScriptShell:
    """HaiScript 交互式 Shell 主类"""

    def __init__(self, config: Config):
        self.config = config
        self.running = False

        # 核心子系统
        self.security = SecurityManager(enable_checks=config.get('enable_safety_checks', True))
        self.aliases = AliasManager(self.security)
        self.history = HistoryManager(limit=config.get('process_history_limit', 100))

        # 命令处理器
        self.fs = FileSystemCommands(self.security)
        self.sys = SystemCommands(self.security)
        self.net = NetworkCommands(self.security)
        self.enc = EncodingCommands()

        # 编译器
        self.compiler = GCCCompiler()
        self.asm_compiler = None  # 延迟初始化

        # 命令路由表: 命令名 -> (处理方法, 帮助文本)
        self._commands: Dict[str, Callable] = {}
        self._build_command_table()

    # ------------------------------------------------------------------
    # 命令路由表
    # ------------------------------------------------------------------
    def _build_command_table(self):
        """构建命令路由表"""
        # 文件系统命令
        self._register('cd', self.fs.cmd_cd, "切换目录: cd [路径]")
        self._register('pwd', self.fs.cmd_pwd, "显示当前目录")
        self._register('ls', self.fs.cmd_ls, "列出目录内容: ls [路径]")
        self._register('dir', self.fs.cmd_ls, "ls 的别名")
        self._register('mkdir', self.fs.cmd_mkdir, "创建目录: mkdir <目录名>")
        self._register('touch', self.fs.cmd_touch, "创建/更新文件: touch <文件1> [文件2...]")
        self._register('rm', self.fs.cmd_rm, "删除文件: rm <文件> [-f] [-r]")
        self._register('cp', self.fs.cmd_cp, "复制文件: cp <源> <目标>")
        self._register('mv', self.fs.cmd_mv, "移动文件: mv <源> <目标>")
        self._register('find', self.fs.cmd_find, "查找文件: find <模式> [路径]")
        self._register('cat', self.fs.cmd_cat, "显示文件内容: cat <文件>")
        self._register('type', self.fs.cmd_cat, "cat 的别名")
        self._register('echo', self.fs.cmd_echo, "输出文字: echo <文字>")

        # 系统命令
        self._register('whoami', self.sys.cmd_whoami, "显示当前用户")
        self._register('hostname', self.sys.cmd_hostname, "显示主机名")
        self._register('date', self.sys.cmd_date, "显示日期")
        self._register('time', self.sys.cmd_time, "显示时间")
        self._register('sysinfo', self.sys.cmd_sysinfo, "显示系统信息")
        self._register('ps', self.sys.cmd_ps, "显示进程列表（前50行）")
        self._register('tasklist', self.sys.cmd_ps, "ps 的别名")
        self._register('kill', self.sys.cmd_kill, "结束进程: kill <PID> [-f]")
        self._register('clear', self.sys.cmd_clear, "清屏")
        self._register('cls', self.sys.cmd_clear, "clear 的别名")

        # 网络命令
        self._register('ping', self.net.cmd_ping, "Ping 测试: ping <主机>")
        self._register('ipconfig', self.net.cmd_ipconfig, "显示 IP 配置")
        self._register('ifconfig', self.net.cmd_ipconfig, "ipconfig 的别名")
        self._register('netstat', self.net.cmd_netstat, "显示网络连接（前60行）")

        # 编码命令
        self._register('base64', self.enc.cmd_base64, "Base64 编码/解码: base64 <文本>")
        self._register('hex', self.enc.cmd_hex, "十六进制 编码/解码: hex <文本>")

        # 内建特殊命令
        self._register('alias', self._cmd_alias, "别名管理: alias [name=cmd] | alias list")
        self._register('unalias', self._cmd_unalias, "删除别名: unalias <name> | unalias -a")
        self._register('history', self._cmd_history, "显示命令历史: history [N]")
        self._register('help', self._cmd_help, "显示帮助: help [命令名]")
        self._register('?', self._cmd_help, "help 的别名")
        self._register('version', self._cmd_version, "显示版本信息")
        self._register('about', self._cmd_about, "关于 HaiScript")

        # HaiScript 特有
        self._register('run', self._cmd_run, "执行 .hs 脚本: run <脚本.hs> [args...] [-O|--optimize]")
        self._register('compile', self._cmd_compile,
                       "编译 .hs 为可执行文件: compile <脚本.hs> [输出.exe] [--asm] [--keep-c] [--keep-asm] [--no-opt]")
        self._register('check', self._cmd_check, "检查 .hs 脚本语法: check <脚本.hs> [--opt]")
        self._register('typecheck', self._cmd_typecheck,
                       "静态类型检查（标注驱动，仅警告）: typecheck <脚本.hs>")
        self._register('fmt', self._cmd_fmt,
                       "格式化 .hs 源码: fmt <脚本.hs> [-i|--in-place] [--check] [--indent=2|4]")
        self._register('opt', self._cmd_opt,
                       "IR 优化预览: opt <脚本.hs> [--stats]")
        self._register('hsinser', self._cmd_hsinser,
                       "包管理器: hsinser <install|list|remove|search|info|update|versions>")

    def _register(self, name: str, handler: Callable, help_text: str = ""):
        """注册一个命令"""
        self._commands[name] = (handler, help_text)

    # ------------------------------------------------------------------
    # 特殊内建命令
    # ------------------------------------------------------------------
    def _cmd_alias(self, args: List[str]) -> bool:
        """alias 命令"""
        if not args:
            alias_list = self.aliases.list_aliases()
            if not alias_list:
                print_info("没有定义任何别名")
                return True
            print_header("已定义的别名")
            for name, cmd in sorted(alias_list.items()):
                print(f"  {name:<12} -> {cmd}")
            return True

        text = ' '.join(args)
        if text.lower() == 'list':
            return self._cmd_alias([])

        if '=' in text:
            name, cmd = text.split('=', 1)
            name = name.strip()
            cmd = cmd.strip().strip('"\'')
            if not name:
                print_error("别名名称不能为空")
                return False
            if name in ('alias', 'unalias'):
                print_error(f"不能为关键字 '{name}' 创建别名")
                return False
            ok = self.aliases.add_alias(name, cmd)
            if ok:
                print_success(f"别名已添加: {name} -> {cmd}")
            else:
                print_error(f"添加别名失败（可能包含危险模式）: {name}")
            return ok
        print_error("用法: alias name=command")
        return False

    def _cmd_unalias(self, args: List[str]) -> bool:
        """unalias 命令"""
        if not args:
            print_error("用法: unalias <别名> | unalias -a")
            return False
        name = args[0]
        if name in ('-a', '--all'):
            if confirm_prompt("确定要删除所有别名吗?"):
                self.aliases.remove_all()
                print_success("所有别名已删除")
                return True
            return False
        ok = self.aliases.remove_alias(name)
        if ok:
            print_success(f"别名已删除: {name}")
        else:
            print_warning(f"别名不存在: {name}")
        return ok

    def _cmd_history(self, args: List[str]) -> bool:
        """history 命令"""
        count = 20
        if args:
            try:
                count = max(1, int(args[0]))
            except ValueError:
                pass
        recent = self.history.get_recent(count)
        if not recent:
            print_info("没有命令历史")
            return True
        print_header(f"最近 {len(recent)} 条命令历史")
        for i, cmd in enumerate(recent, 1):
            print(f"  {i:>3d}: {cmd}")
        return True

    def _cmd_help(self, args: List[str]) -> bool:
        """help 命令"""
        if args:
            target = args[0]
            if target in self._commands:
                _, help_text = self._commands[target]
                if help_text:
                    print(f"{Color.BOLD}{target}{Color.RESET} - {help_text}")
                else:
                    print_info(f"命令 '{target}' 无帮助文本")
                return True
            print_warning(f"未知命令: {target}。使用 'help' 查看完整列表。")
            return False

        # 完整帮助
        print_header(f"{PROJECT_NAME} v{VERSION} 命令列表")
        print(f"  官网: {WEBSITE}")
        print()
        categories = [
            ("文件系统", ['cd', 'pwd', 'ls', 'mkdir', 'touch', 'rm', 'cp', 'mv', 'find', 'cat', 'echo']),
            ("系统管理", ['whoami', 'hostname', 'date', 'time', 'sysinfo', 'ps', 'kill', 'clear']),
            ("网络工具", ['ping', 'ipconfig', 'netstat']),
            ("编码工具", ['base64', 'hex']),
            ("HaiScript", ['run', 'compile', 'check', 'fmt', 'hsinser']),
            ("其它", ['alias', 'unalias', 'history', 'help', 'version', 'about']),
        ]
        for cat_name, cmds in categories:
            print(f"{Color.HEADER}{cat_name}:{Color.RESET}")
            for c in cmds:
                if c in self._commands:
                    _, ht = self._commands[c]
                    print(f"  {Color.BOLD}{c:<12}{Color.RESET} {ht}")
            print()
        print_info("提示: 输入 help <命令名> 查看详细用法")
        print_info(f"提示: HaiScript 脚本: run script.hs, 编译: compile script.hs")
        return True

    def _cmd_version(self, _args: List[str]) -> bool:
        print(f"{PROJECT_NAME} {VERSION}")
        return True

    def _cmd_about(self, _args: List[str]) -> bool:
        from haiscript.core.constants import AUTHOR, REPO_URL, LIB_REPO_URL, LICENSE_NAME
        about_text = f"""
{Color.BOLD}{PROJECT_NAME} v{VERSION}{Color.RESET}
  轻量级脚本语言与命令行工具箱

{Color.HEADER}作者:{Color.RESET}  {AUTHOR}
{Color.HEADER}许可证:{Color.RESET}  {LICENSE_NAME}
{Color.HEADER}官网:{Color.RESET}    {WEBSITE}
{Color.HEADER}主仓库:{Color.RESET}  {REPO_URL}
{Color.HEADER}包仓库:{Color.RESET}  {LIB_REPO_URL} (hsinser 扩展源)

{Color.HEADER}特性:{Color.RESET}
  - Shell 命令：文件 / 系统 / 网络 / 编码
  - 解释执行 HaiScript 脚本 (*{SCRIPT_EXTENSION})
  - 编译为原生 EXE：C 后端 (GCC) 或汇编后端 (NASM + lld-link)
  - 标准库：json / path / os / math / pic / touch / http / lan
  - 工具链：fmt 格式化、typecheck 类型检查、opt IR 优化
  - 包管理器：hsinser install/search/list/remove/update/versions
  - 多模块架构：核心/命令/解释器/编译器解耦
"""
        print(about_text)
        return True

    # ------------------------------------------------------------------
    # HaiScript 特有：脚本执行/编译/检查
    # ------------------------------------------------------------------
    def _cmd_run(self, args: List[str]) -> bool:
        """run script.hs [args...] [-O|--optimize]"""
        if not args:
            print_error(f"用法: run <脚本{SCRIPT_EXTENSION}> [参数...] [-O|--optimize]")
            return False

        opts = {a for a in args if a.startswith('-')}
        positional = [a for a in args if not a.startswith('-')]
        if not positional:
            print_error(f"用法: run <脚本{SCRIPT_EXTENSION}> [参数...] [-O|--optimize]")
            return False

        optimize = '-O' in opts or '--optimize' in opts
        script_path = positional[0]
        script_args = positional[1:]

        if not script_path.endswith(SCRIPT_EXTENSION):
            alt = script_path + SCRIPT_EXTENSION
            if Path(alt).exists():
                script_path = alt
        if not Path(script_path).exists():
            print_error(f"脚本文件不存在: {script_path}")
            return False

        print_info(f"执行 {PROJECT_NAME} 脚本: {script_path}" + (" (IR优化)" if optimize else ""))
        interp = Interpreter(script_path=script_path)

        if optimize:
            # 读源码 → AST → IR优化 → 执行优化后AST
            try:
                from haiscript.interpreter.lexer import Lexer
                from haiscript.interpreter.parser import Parser
                from haiscript.tools.ir import optimize_ast
                with open(script_path, 'r', encoding='utf-8') as f:
                    src = f.read()
                tokens = Lexer(src, filename=script_path).tokenize()
                ast = Parser(tokens).parse()
                ast_opt, stats = optimize_ast(ast)
                print_info(f"  IR 优化统计: {stats}")
                import io, sys
                buf = io.StringIO()
                old = sys.stdout
                sys.stdout = buf
                try:
                    exit_code = 0
                    interp._eval_program(ast_opt)
                except Exception as e:
                    sys.stdout = old
                    print(f"运行错误: {e}", file=sys.stderr)
                    exit_code = 1
                else:
                    sys.stdout = old
                    sys.stdout.write(buf.getvalue())
            except Exception as e:
                print_error(f"IR优化执行失败: {e}")
                return False
        else:
            exit_code = interp.execute_file(script_path)

        if exit_code == 0:
            print_success("脚本执行完成 (退出码 0)")
        else:
            print_warning(f"脚本执行完毕，退出码: {exit_code}")
        return exit_code == 0

    def _cmd_compile(self, args: List[str]) -> bool:
        """compile script.hs [output] [--asm] [--keep-c] [--keep-asm] [--no-opt]"""
        if not args:
            print_error(f"用法: compile <脚本{SCRIPT_EXTENSION}> [输出.exe] [--asm] [--keep-c] [--keep-asm] [--no-opt]")
            return False

        positional = [a for a in args if not a.startswith('--')]
        opts = {a for a in args if a.startswith('--')}

        input_file = positional[0]
        output_file = positional[1] if len(positional) > 1 else None

        use_asm = '--asm' in opts
        keep_c = '--keep-c' in opts
        keep_asm = '--keep-asm' in opts
        optimize = '--no-opt' not in opts

        if not Path(input_file).exists():
            if Path(input_file + SCRIPT_EXTENSION).exists():
                input_file += SCRIPT_EXTENSION
            else:
                print_error(f"输入文件不存在: {input_file}")
                return False

        if use_asm:
            # 汇编后端：.hs → .asm (NASM) → .obj → .exe (lld-link)
            if self.asm_compiler is None:
                from haiscript.asm import AsmCompiler
                self.asm_compiler = AsmCompiler()

            asm_output = None
            if keep_asm:
                asm_output = str(Path(input_file).with_suffix('.asm'))

            backend = "汇编(NASM+lld-link)"
            print_info(f"正在编译({backend}): {input_file} {'(保留ASM)' if keep_asm else ''}")
            ok, logs = self.asm_compiler.compile_file(
                input_file,
                output_exe=output_file,
                keep_asm=keep_asm,
                asm_output_path=asm_output,
            )
            print(logs)
            return ok
        else:
            # C 后端：.hs → .c (GCC) → .exe
            c_output = None
            if keep_c:
                c_output = str(Path(input_file).with_suffix('.c'))

            backend = "C(GCC)"
            print_info(f"正在编译({backend}): {input_file} {'(保留C代码)' if keep_c else ''} {'(无优化)' if not optimize else ''}")
            ok, logs = self.compiler.compile_file(
                input_file,
                output_exe=output_file,
                keep_c=keep_c,
                c_output_path=c_output,
                optimize=optimize,
            )
            print(logs)
            return ok

    def _cmd_check(self, args: List[str]) -> bool:
        """check script.hs — 语法检查"""
        if not args:
            print_error(f"用法: check <脚本{SCRIPT_EXTENSION}>")
            return False
        path = args[0]
        if not Path(path).exists() and Path(path + SCRIPT_EXTENSION).exists():
            path += SCRIPT_EXTENSION
        if not Path(path).exists():
            print_error(f"脚本文件不存在: {path}")
            return False
        try:
            from haiscript.interpreter.lexer import Lexer
            from haiscript.interpreter.parser import Parser
            with open(path, 'r', encoding='utf-8') as f:
                src = f.read()
            tokens = Lexer(src, filename=path).tokenize()
            Parser(tokens).parse()
            print_success(f"语法检查通过: {path} (共 {len(src)} 字符, {len(tokens)} tokens)")
            return True
        except Exception as e:
            print_error(f"语法错误: {e}")
            return False

    def _cmd_fmt(self, args: List[str]) -> bool:
        """fmt file.hs [-i|--in-place] [--check] [--indent=4]"""
        from haiscript.tools.formatter import format_file, format_source
        if not args:
            print_error(f"用法: fmt <脚本{SCRIPT_EXTENSION}> [-i|--in-place] [--check] [--indent=2|4]")
            print_info("若同时从 stdin 输入内容（如 -），则格式化 stdin 并输出到 stdout")
            return False

        positional = [a for a in args if not a.startswith('-') and not a.startswith('--indent=')]
        inplace = '-i' in args or '--in-place' in args
        check_mode = '--check' in args
        indent = 4
        for a in args:
            if a.startswith('--indent='):
                try:
                    indent = max(1, min(8, int(a.split('=', 1)[1])))
                except ValueError:
                    print_error("--indent 需要数字 (1-8)")
                    return False

        # stdin 模式
        if positional and positional[0] == '-':
            src = sys.stdin.read()
            try:
                out = format_source(src, step=indent, file_tag="<stdin>")
            except Exception as e:
                print_error(f"格式化失败: {e}")
                return False
            sys.stdout.write(out)
            return True

        if not positional:
            print_error("请指定要格式化的文件，或使用 '-' 从 stdin 读取")
            return False

        path = positional[0]
        if not Path(path).exists() and Path(path + SCRIPT_EXTENSION).exists():
            path += SCRIPT_EXTENSION
        if not Path(path).exists():
            print_error(f"脚本文件不存在: {path}")
            return False

        try:
            if check_mode:
                same = format_file(path, check=True, step=indent)
                if same:
                    print_success(f"已格式化（无需变更）: {path}")
                else:
                    print_warning(f"需要格式化: {path}")
                return same
            if inplace:
                changed = format_file(path, inplace=True, step=indent)
                if changed:
                    print_success(f"已就地格式化: {path}")
                else:
                    print_info(f"格式已是最新: {path}")
                return True
            # 默认：输出到 stdout
            out = format_file(path, step=indent)
            sys.stdout.write(out if isinstance(out, str) else str(out))
            return True
        except Exception as e:
            print_error(f"格式化失败: {e}")
            return False

    def _cmd_opt(self, args: List[str]) -> bool:
        """opt script.hs [--stats] — 显示IR优化效果"""
        if not args:
            print_error(f"用法: opt <脚本{SCRIPT_EXTENSION}> [--stats]")
            return False
        show_stats = '--stats' in args
        positional = [a for a in args if not a.startswith('--')]
        if not positional:
            print_error(f"用法: opt <脚本{SCRIPT_EXTENSION}> [--stats]")
            return False
        path = positional[0]
        if not Path(path).exists() and Path(path + SCRIPT_EXTENSION).exists():
            path += SCRIPT_EXTENSION
        if not Path(path).exists():
            print_error(f"脚本文件不存在: {path}")
            return False
        try:
            from haiscript.tools.ir import optimize_source
            from haiscript.tools.formatter import PrettyPrinter
            with open(path, 'r', encoding='utf-8') as f:
                src = f.read()
            ast, stats = optimize_source(src, file_tag=path)
            print_info(f"IR 优化统计: {stats}")
            if show_stats:
                # 显示一些折叠前后的对比（简化）
                print_info("  优化项:")
                print_info(f"    常量折叠: {stats.get('folds', 0)} 处")
            pp = PrettyPrinter(indent_width=2)
            print("=" * 60)
            print("优化后源码（AST发射）:")
            print("=" * 60)
            print(pp.format_program(ast))
            return True
        except Exception as e:
            print_error(f"IR 优化失败: {e}")
            return False

    def _cmd_typecheck(self, args: List[str]) -> bool:
        """typecheck script.hs — 静态类型检查（仅警告）"""
        if not args:
            print_error(f"用法: typecheck <脚本{SCRIPT_EXTENSION}>")
            return False
        path = args[0]
        if not Path(path).exists() and Path(path + SCRIPT_EXTENSION).exists():
            path += SCRIPT_EXTENSION
        if not Path(path).exists():
            print_error(f"脚本文件不存在: {path}")
            return False
        try:
            from haiscript.tools.type_checker import check_file
            warnings = check_file(path)
            if warnings:
                print_warning(f"发现 {len(warnings)} 处类型警告（渐进式类型，可忽略）:")
                for w in warnings:
                    print_warning(f"  {w}")
                return True
            print_success(f"类型检查通过（无标注相关警告）: {path}")
            return True
        except Exception as e:
            print_error(f"类型检查失败: {e}")
            return False

    def _cmd_hsinser(self, args: List[str]) -> bool:
        """hsinser - HaiScript 包管理器"""
        from haiscript.commands.package import Hsinser
        mgr = Hsinser()
        return mgr.run_command(args)

    # ------------------------------------------------------------------
    # 命令分发
    # ------------------------------------------------------------------
    def _split_command(self, line: str) -> tuple:
        """拆分命令行为 (命令名, 参数列表)"""
        stripped = line.strip()
        if not stripped:
            return ('', [])
        parts = stripped.split()
        cmd = parts[0].lower()
        args = parts[1:]
        return (cmd, args)

    def _execute_one(self, line: str) -> bool:
        """执行单条命令行（已处理别名展开）"""
        cmd, args = self._split_command(line)
        if not cmd:
            return True

        # 先检查别名
        expanded = self.aliases.expand_alias(line)
        if expanded != line:
            print_info(f"展开别名: {cmd} -> {expanded}")
            cmd, args = self._split_command(expanded)

        # 查找路由
        if cmd in self._commands:
            handler, _ = self._commands[cmd]
            try:
                return bool(handler(args))
            except KeyboardInterrupt:
                print_warning("\n操作被用户中断")
                return False
            except Exception as e:
                print_error(f"命令执行异常: {e}")
                self.security.log_operation("CMD_ERROR", f"{cmd}: {e}", False)
                return False

        # 未匹配：尝试作为 .hs 脚本（如命令行就是文件名）
        candidate = cmd
        for suffix in (SCRIPT_EXTENSION, ''):
            path_obj = Path(candidate + suffix)
            if path_obj.exists() and path_obj.is_file():
                if (candidate + suffix).endswith(SCRIPT_EXTENSION):
                    return self._cmd_run([candidate + suffix] + args)

        print_error(f"未知命令: '{cmd}'。输入 'help' 查看命令列表。")
        return False

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------
    def print_banner(self):
        banner = f"""
{Color.BOLD}{Color.HEADER}{'=' * 56}{Color.RESET}
{Color.BOLD}{Color.HEADER}      {PROJECT_NAME} v{VERSION}  |  轻量级脚本与工具箱      {Color.RESET}
{Color.BOLD}{Color.HEADER}{'=' * 56}{Color.RESET}
  官网: {WEBSITE}
  提示: 输入 'help' 查看命令, 'exit' 退出
  脚本:  run file{SCRIPT_EXTENSION}  |  compile file{SCRIPT_EXTENSION}
"""
        print(banner)

    def run(self):
        """运行交互式 Shell"""
        self.running = True
        self.print_banner()
        while self.running:
            try:
                cwd_str = get_cwd_display(40)
                prompt = f"{Color.PROMPT}{PROJECT_NAME.lower()}:{cwd_str}>{Color.RESET} "
                try:
                    line = input(prompt)
                except EOFError:
                    print()
                    break

                line_stripped = line.strip()
                if not line_stripped:
                    continue

                # 历史
                self.history.add(line_stripped)
                self.security.log_operation("INPUT", line_stripped)

                # 退出
                if line_stripped.lower() in ('exit', 'quit', 'q'):
                    print_info("再见！")
                    break

                # 执行
                self._execute_one(line_stripped)

            except KeyboardInterrupt:
                print()
                print_warning("使用 'exit' 退出程序")
            except Exception as e:
                print_error(f"未处理的异常: {e}")

        self.running = False


# ====================================================================
# 命令行参数入口
# ====================================================================
def _show_usage():
    print(f"""{PROJECT_NAME} v{VERSION}

用法:
  python -m haiscript.main                 进入交互式 Shell
  python -m haiscript.main help            显示帮助
  python -m haiscript.main version         显示版本

  python -m haiscript.main run <file.hs>         执行 HaiScript 脚本
  python -m haiscript.main compile <file.hs>     编译为可执行文件
      [--asm]         使用汇编后端 (NASM → lld-link)
      [--keep-c]      保留生成的 C 文件 (C 后端)
      [--keep-asm]    保留生成的 .asm 文件 (汇编后端)
      [--no-opt]      禁用优化
      [output.exe]    指定输出路径
  python -m haiscript.main check <file.hs>       语法检查脚本
  python -m haiscript.main fmt <file.hs>         格式化 HaiScript 源码（输出到 stdout）
      [-i|--in-place]  就地修改
      [--check]        只检查是否需要格式化
      [--indent=4]     缩进宽度 1-8（默认 4）
      [-]              从 stdin 读取内容并输出到 stdout
  python -m haiscript.main hsinser <命令>        包管理器
      install <包名> [版本]    安装包
      list                   列出已安装的包
      remove <包名>           卸载包
      search <关键词>         搜索可用包
      info <包名>             显示包详情
      update [包名|--all]     更新包
      versions <包名>         列出可用版本
  python -m haiscript.main gcc                   检查 GCC 编译器状态
  python -m haiscript.main asm                   检查汇编后端 (NASM/lld-link) 状态
""")


def _dispatch_cli(argv: List[str]) -> int:
    """处理命令行参数调度（非交互模式）"""
    if not argv:
        # 无参数 → 交互模式
        cfg = Config()
        HaiScriptShell(cfg).run()
        return 0

    sub = argv[0].lower()
    rest = argv[1:]

    if sub in ('-h', '--help', 'help', '?'):
        _show_usage()
        return 0

    if sub in ('-v', '--version', 'version'):
        print(f"{PROJECT_NAME} {VERSION}")
        return 0

    cfg = Config()
    shell = HaiScriptShell(cfg)

    if sub == 'run':
        return 0 if shell._cmd_run(rest) else 1
    if sub == 'compile':
        return 0 if shell._cmd_compile(rest) else 1
    if sub == 'check':
        return 0 if shell._cmd_check(rest) else 1
    if sub == 'typecheck':
        return 0 if shell._cmd_typecheck(rest) else 1
    if sub == 'fmt':
        return 0 if shell._cmd_fmt(rest) else 1
    if sub == 'opt':
        return 0 if shell._cmd_opt(rest) else 1
    if sub == 'hsinser':
        return 0 if shell._cmd_hsinser(rest) else 1
    if sub == 'gcc':
        ok, info = shell.compiler.is_gcc_available()
        if ok:
            print_success(f"GCC 可用: {info}")
            return 0
        print_error(f"GCC 不可用: {info}")
        return 1
    if sub == 'asm':
        from haiscript.asm import AsmCompiler
        ac = AsmCompiler()
        ok, info = ac.is_available()
        if ok:
            print_success(f"汇编后端可用: {info}")
            return 0
        print_error(f"汇编后端不可用: {info}")
        return 1

    # 如果参数是一个 .hs 文件，直接 run
    if Path(sub).exists() or Path(sub + SCRIPT_EXTENSION).exists():
        return 0 if shell._cmd_run([sub] + rest) else 1

    print_error(f"未知参数: {sub}。使用 --help 查看用法。")
    return 2


def main():
    """主入口"""
    try:
        return _dispatch_cli(sys.argv[1:])
    except KeyboardInterrupt:
        print()
        print_warning("用户中断")
        return 130
    except Exception as e:
        print_error(f"致命错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
