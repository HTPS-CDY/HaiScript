"""
HaiScript GCC 编译封装
将生成的 C 代码写入文件并调用 GCC 编译成可执行文件
"""
import os
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from haiscript.compiler_c.codegen import CCodeGenerator, CodegenError
from haiscript.interpreter.parser import ParseError
from haiscript.core.constants import DEFAULT_ENCODING, WINDOWS_ENCODING


class CompileError(Exception):
    def __init__(self, msg: str, detail: str = ""):
        super().__init__(msg + (f"\n{detail}" if detail else ""))
        self.detail = detail


class GCCCompiler:
    """HaiScript -> C -> GCC 编译器"""

    def __init__(self, gcc_path: Optional[str] = None):
        self.gcc = gcc_path or self._find_gcc()

    @staticmethod
    def _find_gcc() -> str:
        """查找可用的 GCC 编译器"""
        candidates = ['gcc', 'cc', 'mingw32-gcc', 'x86_64-w64-mingw32-gcc',
                      'clang', 'zig cc']
        for c in candidates:
            if shutil.which(c):
                return c
        return 'gcc'  # 找不到也返回默认名，调用时会报错

    def is_gcc_available(self) -> Tuple[bool, str]:
        """检查 GCC 是否可用"""
        try:
            result = subprocess.run(
                [self.gcc, '--version'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.splitlines()[0] if result.stdout else "OK"
                return True, version
            return False, result.stderr.strip() or f"返回码 {result.returncode}"
        except FileNotFoundError:
            return False, f"未找到编译器: {self.gcc}。请安装 GCC/MinGW 并加入 PATH。"
        except Exception as e:
            return False, str(e)

    def compile_source(
        self,
        haiscript_src: str,
        output_exe: str,
        keep_c: bool = False,
        c_output_path: Optional[str] = None,
        optimize: bool = True,
    ) -> Tuple[bool, str]:
        """
        编译 HaiScript 源码为可执行文件

        Args:
            haiscript_src: HaiScript 源代码字符串
            output_exe: 输出可执行文件路径
            keep_c: 是否保留生成的 C 文件
            c_output_path: 指定 C 文件输出路径（保留时有效）
            optimize: 是否启用优化 (-O2)

        Returns:
            (是否成功, 日志信息)
        """
        # 1. 检查 GCC
        ok, info = self.is_gcc_available()
        if not ok:
            return False, f"编译器不可用: {info}\n请安装 GCC（Windows 推荐 MinGW-w64）并加入环境变量 PATH。"

        logs = [f"使用编译器: {info}"]

        # 2. 生成 C 代码
        try:
            c_code = CCodeGenerator().generate(haiscript_src)
        except CodegenError as e:
            return False, f"代码生成失败: {e}"
        except ParseError as e:
            return False, f"语法错误: {e}"
        except Exception as e:
            return False, f"生成 C 代码异常: {e}"

        # 3. 写文件并编译
        tmpdir = None
        try:
            if keep_c and c_output_path:
                c_path = Path(c_output_path)
                c_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                tmpdir = tempfile.mkdtemp(prefix='haiscript_cc_')
                c_path = Path(tmpdir) / "haiscript_out.c"

            with open(c_path, 'w', encoding=DEFAULT_ENCODING) as f:
                f.write(c_code)
            logs.append(f"已生成 C 代码: {c_path} ({len(c_code)} 字节)")

            # 4. 调用 GCC
            cmd = [self.gcc, str(c_path), '-o', output_exe, '-std=c11', '-Wall']
            if optimize:
                cmd.append('-O2')
            if os.name != 'nt':
                cmd.append('-lm')
            else:
                # Windows：明确指定源/执行字符集为 UTF-8，与控制台 CP65001 初始化配套
                # -finput-charset=  C 源文件本身的编码（我们写文件时用 UTF-8）
                # -fexec-charset=   编译后 exe 中字符串字面量的存储编码
                # 两者一致（UTF-8），再配合运行时 SetConsoleOutputCP(65001) 就不乱码
                cmd += ['-finput-charset=UTF-8', '-fexec-charset=UTF-8']

            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=120,
                    encoding=WINDOWS_ENCODING if os.name == 'nt' else DEFAULT_ENCODING,
                    errors='replace',
                )
            except subprocess.TimeoutExpired:
                return False, "编译超时（120秒）"
            except Exception as e:
                return False, f"调用编译器失败: {e}"

            if result.returncode != 0:
                err = (result.stderr or result.stdout or f"返回码 {result.returncode}").strip()
                logs.append("编译器输出:")
                logs.append(err)
                return False, '\n'.join(logs)

            logs.append(f"编译成功! 可执行文件: {Path(output_exe).resolve()}")
            size = Path(output_exe).stat().st_size if Path(output_exe).exists() else 0
            logs.append(f"文件大小: {size:,} 字节")
            return True, '\n'.join(logs)

        finally:
            if tmpdir and not keep_c:
                try:
                    shutil.rmtree(tmpdir, ignore_errors=True)
                except Exception:
                    pass

    def compile_file(
        self,
        input_hs: str,
        output_exe: Optional[str] = None,
        **kwargs
    ) -> Tuple[bool, str]:
        """编译 .hs 脚本文件为可执行文件"""
        path = Path(input_hs)
        if not path.exists():
            return False, f"输入文件不存在: {input_hs}"
        try:
            with open(path, 'r', encoding=DEFAULT_ENCODING) as f:
                src = f.read()
        except Exception as e:
            return False, f"读取输入文件失败: {e}"

        if output_exe is None:
            exe_suffix = '.exe' if os.name == 'nt' else ''
            output_exe = str(path.with_suffix(exe_suffix))

        return self.compile_source(src, output_exe, **kwargs)
