"""
HaiScript 1.2 解释执行器 (Interpreter)
扩展：Map/Set 容器、try/catch/throw、break/continue、export、
      文件 IO、JSON/Path/os/math 标准库、点成员方法调用、断言、
      分层错误类型、import 别名、
      新增标准库：json(文件处理)/pic(图片)/touch(外部程序)/http(服务器)/lan(局域网)。
"""
import os
import sys
import json as _pyjson
from pathlib import Path as PyPath
from typing import Any, Dict, List, Optional, Set as PySet

from haiscript.interpreter.lexer import Lexer
from haiscript.core.errors import (
    HSError, RuntimeException, TypeError, KeyNotFoundError,
    IndexOutOfRangeError, ZeroDivisionError_, IOError, AssertionError_,
    ModuleNotFoundError, ParseError_,
)
from haiscript.interpreter.parser import (
    Parser, ParseError,
    Program, NumberLiteral, StringLiteral, BoolLiteral, NilLiteral,
    ListLiteral, MapLiteral, SetLiteral,
    Identifier, MemberAccess, BinOp, UnaryOp, Assign, IndexAssign, VarDecl,
    IfStatement, WhileStatement, ForStatement,
    BreakStatement, ContinueStatement,
    ThrowStatement, TryCatchStatement,
    ExportStatement, AssertStatement,
    FuncDef, FuncCall, MethodCall, ReturnStatement,
    PrintStatement, InputCall, ImportStatement,
    ListIndex, RangeExpr, BreakSignal, ContinueSignal,
)


# ==========================================================
# 控制流与返回信号
# ==========================================================
class ReturnValue(Exception):
    def __init__(self, value: Any):
        super().__init__()
        self.value = value


# ==========================================================
# HaiScript 运行时值标记
#   dict  → 普通字典 或 HS_Map (__hstype__="map")
#   set   → 普通集合 或 HS_Set (__hstype__="set")
#   dict  → 模块     (__hstype__="module")
# ==========================================================
HS_Map = Dict   # 实际为 dict 加 __hstype__ 标记
HS_Set = PySet  # 实际为 set 加 __hstype__ 标记


def _hs_map(*pairs):
    m = dict(pairs) if pairs else {}
    m['__hstype__'] = 'map'
    return m


def _hs_set(*elems):
    s = set(elems) if elems else set()
    # set 不能放自定义属性，用包装
    return _HSSet(s)


class _HSSet:
    """HaiScript Set 值包装（set 无法挂属性，显式包装）"""
    __slots__ = ('data', '__hstype__')

    def __init__(self, data=None):
        self.data = set(data) if data is not None else set()
        self.__hstype__ = 'set'

    def __repr__(self):
        return "set{" + ", ".join(_to_str_static(e) for e in self.data) + "}"

    def __eq__(self, other):
        return isinstance(other, _HSSet) and self.data == other.data

    def __hash__(self):  # 不可hash，仅为了兼容
        return id(self)


# ==========================================================
# 类型检查 / 字符串化
# ==========================================================
def _hs_type_name(v: Any) -> str:
    if v is None:
        return 'nil'
    if isinstance(v, bool):
        return 'bool'
    if isinstance(v, (int, float)):
        return 'number'
    if isinstance(v, str):
        return 'string'
    if isinstance(v, list):
        return 'list'
    if isinstance(v, dict):
        return v.get('__hstype__', 'map' if '__hstype__' not in v else v.get('__hstype__', 'map')) if False else (
            v.get('__hstype__', 'module') if v.get('__hstype__') in ('module',) else 'map'
        )
    if isinstance(v, _HSSet):
        return 'set'
    t = type(v).__name__
    return {'int': 'number', 'float': 'number', 'str': 'string',
            'list': 'list', 'bool': 'bool', 'NoneType': 'nil',
            'dict': 'map', 'set': 'set'}.get(t, t)


def _to_str_static(value: Any) -> str:
    """无状态的字符串化（用于 _HSSet 表示）"""
    if value is None:
        return 'nil'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        if isinstance(value, float) and value == int(value) and abs(value) < 1e100:
            return str(value)
        return str(value)
    if isinstance(value, str):
        # 调试用简洁版 —— 不带引号（print 用的是 _to_str）
        return value
    if isinstance(value, list):
        return "[" + ", ".join(_to_str_static(e) for e in value) + "]"
    if isinstance(value, dict):
        if value.get('__hstype__') == 'module':
            return f"<module {value.get('__name__', '?')}>"
        items = []
        for k, v in value.items():
            if k == '__hstype__':
                continue
            if isinstance(k, str):
                ks = '"' + k + '"'
            else:
                ks = _to_str_static(k)
            items.append(f"{ks}: {_to_str_static(v)}")
        return "{" + ", ".join(items) + "}"
    if isinstance(value, _HSSet):
        return repr(value)
    return str(value)


# ==========================================================
# 解释器主类
# ==========================================================
class Interpreter:
    """HaiScript 解释执行器 v1.1"""

    def __init__(self, script_path: Optional[str] = None,
                 export_map: Optional[Dict[str, Any]] = None,
                 parent_dirs: Optional[List[PyPath]] = None):
        self.globals: Dict[str, Any] = {}
        self.scopes: List[Dict[str, Any]] = []
        # 导出表 —— 当执行 import/run 时由调用方取走
        self.exports: Dict[str, Any] = export_map if export_map is not None else {}
        # 搜索路径
        self.script_dir = PyPath(script_path).parent.resolve() if script_path else PyPath.cwd()
        self.extra_search: List[PyPath] = list(parent_dirs) if parent_dirs else []
        # 加载的模块缓存
        self._loaded_modules: Dict[str, Any] = {}
        self._init_builtins()

    # ==========================================================
    # 内置函数 & 标准库
    # ==========================================================
    def _init_builtins(self):
        g = self.globals
        # 基础类型 & 算术
        g['len'] = self._bi_len
        g['type'] = self._bi_type
        g['int'] = self._bi_int
        g['float'] = self._bi_float
        g['str'] = self._bi_str
        g['string'] = self._bi_str  # string 作为 str 的别名
        g['bool'] = self._bi_bool
        g['list'] = self._bi_list
        g['map'] = self._bi_map
        g['set'] = self._bi_set
        g['Map'] = self._bi_map   # Map 别名（对应类型关键字）
        g['Set'] = self._bi_set   # Set 别名
        g['number'] = self._bi_float  # number → float（最通用数值类型）
        g['append'] = self._bi_append
        g['abs'] = abs
        g['min'] = min
        g['max'] = max
        g['sum'] = sum
        g['range'] = self._bi_range
        g['assert'] = self._bi_assert
        # 文件 IO
        g['open'] = self._bi_open
        g['readfile'] = self._bi_readfile
        g['writefile'] = self._bi_writefile
        g['exists'] = lambda p: PyPath(p).exists()
        g['isfile'] = lambda p: PyPath(p).is_file()
        g['isdir'] = lambda p: PyPath(p).is_dir()
        g['mkdir'] = self._bi_mkdir
        g['listdir'] = self._bi_listdir
        # 打印 & 输入
        g['println'] = self._bi_println
        g['eprintln'] = self._bi_eprintln
        g['repr'] = lambda v: _to_str_static(v)
        # 错误构造
        g['RuntimeError'] = lambda msg, **kw: RuntimeException(str(msg))
        g['TypeError'] = lambda msg, **kw: TypeError(str(msg))
        g['IOError'] = lambda msg, **kw: IOError(str(msg))
        g['KeyNotFoundError'] = lambda msg, **kw: KeyNotFoundError(str(msg))
        g['IndexOutOfRangeError'] = lambda msg, **kw: IndexOutOfRangeError(str(msg))
        g['ZeroDivisionError'] = lambda: ZeroDivisionError_()
        g['AssertionError'] = lambda msg="", **kw: AssertionError_(str(msg))
        # 数学常数
        g['PI'] = 3.141592653589793
        g['E'] = 2.718281828459045
        # 标准库（懒加载模块 —— HaiScript 里也可 import）
        self._stdlib_json = None
        self._stdlib_path = None

    # ------- 内置函数实现 -------
    def _bi_len(self, obj):
        try:
            if isinstance(obj, _HSSet):
                return len(obj.data)
            if isinstance(obj, dict):
                # 排除 __hstype__
                if obj.get('__hstype__') == 'map':
                    return len(obj) - 1
                return len(obj)
            return len(obj)
        except Exception as e:
            raise RuntimeException(f"len() 错误: {e}")

    def _bi_type(self, obj):
        return _hs_type_name(obj)

    def _bi_int(self, x):
        try:
            if isinstance(x, bool):
                return 1 if x else 0
            return int(x)
        except Exception:
            raise RuntimeException(f"无法转为整数: {x}")

    def _bi_float(self, x):
        try:
            return float(x)
        except Exception:
            raise RuntimeException(f"无法转为浮点数: {x}")

    def _bi_str(self, x):
        return self._to_str(x)

    def _bi_bool(self, x):
        return self._is_truthy(x)

    def _bi_list(self, *args):
        if len(args) == 0:
            return []
        if len(args) == 1:
            src = args[0]
            if isinstance(src, list):
                return list(src)
            if isinstance(src, str):
                return list(src)
            if isinstance(src, _HSSet):
                return list(src.data)
            if isinstance(src, dict):
                return [k for k in src.keys() if k != '__hstype__']
            return list(src)
        raise RuntimeException("list() 参数过多")

    def _bi_map(self, *args):
        """map() 或 map(iter_of_pairs)"""
        m = _hs_map()
        if len(args) == 0:
            return m
        if len(args) == 1:
            src = args[0]
            if isinstance(src, dict):
                for k, v in src.items():
                    if k != '__hstype__':
                        m[k] = v
                return m
            if isinstance(src, (list, tuple)):
                for item in src:
                    if isinstance(item, (list, tuple)) and len(item) == 2:
                        m[item[0]] = item[1]
                    else:
                        raise RuntimeException("map() 需要元素为长度 2 的列表")
                return m
            raise RuntimeException("map() 参数无法转换为映射")
        # map([k1, v1, k2, v2...]) ? 不支持
        raise RuntimeException("map() 参数过多")

    def _bi_set(self, *args):
        if len(args) == 0:
            return _hs_set()
        if len(args) == 1:
            src = args[0]
            if isinstance(src, _HSSet):
                return _hs_set(*list(src.data))
            if isinstance(src, (list, str, tuple)):
                return _hs_set(*list(src))
            if isinstance(src, dict):
                return _hs_set(*[k for k in src.keys() if k != '__hstype__'])
            return _hs_set(src)
        return _hs_set(*args)

    def _bi_append(self, lst, item):
        if not isinstance(lst, list):
            raise RuntimeException("append() 第一个参数必须是列表")
        lst.append(item)
        return lst

    def _bi_range(self, *args):
        if len(args) == 1:
            return list(range(int(args[0])))
        if len(args) == 2:
            return list(range(int(args[0]), int(args[1])))
        if len(args) == 3:
            return list(range(int(args[0]), int(args[1]), int(args[2])))
        raise RuntimeException("range() 参数 1-3 个")

    def _bi_assert(self, cond, msg: str = ""):
        if not self._is_truthy(cond):
            raise AssertionError_(str(msg) or "断言失败")
        return True

    def _bi_println(self, *args):
        print(' '.join(self._to_str(a) for a in args))
        return None

    def _bi_eprintln(self, *args):
        print(' '.join(self._to_str(a) for a in args), file=sys.stderr)
        return None

    def _bi_open(self, path: str, mode: str = "r"):
        """open(path, mode) → 文件对象（dict 伪装）"""
        try:
            real_mode = mode
            mapping = {'r': 'r', 'w': 'w', 'a': 'a', 'rw': 'r+', 'rb': 'rb', 'wb': 'wb'}
            f = open(path, mapping.get(mode, mode), encoding='utf-8' if 'b' not in mode else None)
        except Exception as e:
            raise IOError(f"打开文件失败: {e}", path=path)
        # 用 dict 模拟 HS 对象，便于 MethodCall
        return _HSFile(f, path)

    def _bi_readfile(self, path: str) -> str:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise IOError(f"readfile 错误: {e}", path=path)

    def _bi_writefile(self, path: str, content: str) -> bool:
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self._to_str(content) if not isinstance(content, str) else content)
            return True
        except Exception as e:
            raise IOError(f"writefile 错误: {e}", path=path)

    def _bi_mkdir(self, path: str, parents: bool = True):
        try:
            PyPath(path).mkdir(parents=parents, exist_ok=True)
            return True
        except Exception as e:
            raise IOError(f"mkdir 错误: {e}", path=path)

    def _bi_listdir(self, path: str):
        try:
            return sorted(os.listdir(path))
        except Exception as e:
            raise IOError(f"listdir 错误: {e}", path=path)

    # ==========================================================
    # 作用域
    # ==========================================================
    def _push_scope(self):
        self.scopes.append({})

    def _pop_scope(self):
        if self.scopes:
            self.scopes.pop()

    def _get(self, name: str, default=None) -> Any:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        if name in self.globals:
            return self.globals[name]
        return default

    def _has(self, name: str) -> bool:
        if name in self.globals:
            return True
        return any(name in s for s in self.scopes)

    def _set(self, name: str, value: Any, local: bool = False):
        if local and self.scopes:
            self.scopes[-1][name] = value
            return
        for scope in reversed(self.scopes):
            if name in scope:
                scope[name] = value
                return
        self.globals[name] = value

    # ==========================================================
    # 辅助：类型/字符串/真假
    # ==========================================================
    def _to_str(self, value: Any) -> str:
        return _to_str_static(value)

    def _is_truthy(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return len(value) > 0
        if isinstance(value, list):
            return len(value) > 0
        if isinstance(value, _HSSet):
            return len(value.data) > 0
        if isinstance(value, dict):
            # map: len > 0（减去 __hstype__）
            if value.get('__hstype__') == 'map':
                return (len(value) - 1) > 0
            return len(value) > 0
        if isinstance(value, HSError):
            return True
        return True

    # ==========================================================
    # 执行入口
    # ==========================================================
    def execute(self, source: str, filename: str = "<string>") -> int:
        try:
            tokens = Lexer(source, filename).tokenize()
            ast = Parser(tokens).parse()
            self._eval_program(ast)
            return 0
        except ReturnValue as rv:
            code = rv.value if isinstance(rv.value, int) else 0
            return code
        except HSError as e:
            print(f"运行错误: {e}", file=sys.stderr)
            return 1
        except ParseError as e:
            print(f"语法错误: {e}", file=sys.stderr)
            return 1
        except BreakSignal:
            print("警告: break 在循环外", file=sys.stderr)
            return 1
        except ContinueSignal:
            print("警告: continue 在循环外", file=sys.stderr)
            return 1
        except Exception as e:
            # 包装未处理异常
            he = HSError.wrap(e)
            print(f"运行错误: {he}", file=sys.stderr)
            return 1

    def execute_file(self, file_path: str) -> int:
        path = PyPath(file_path)
        if not path.exists():
            print(f"错误: 脚本文件不存在: {file_path}", file=sys.stderr)
            return 1
        self.script_dir = path.parent.resolve()
        try:
            with open(path, 'r', encoding='utf-8') as f:
                source = f.read()
        except Exception as e:
            print(f"错误: 读取脚本失败: {e}", file=sys.stderr)
            return 1
        return self.execute(source, filename=str(path))

    # ==========================================================
    # 程序与语句求值
    # ==========================================================
    def _eval_program(self, node: Program):
        for stmt in node.statements:
            self._eval_stmt(stmt)

    def _eval_stmt(self, stmt):
        cls = type(stmt).__name__
        m = getattr(self, f'_eval_{cls}', None)
        if m:
            try:
                m(stmt)
            except HSError:
                raise
            except (BreakSignal, ContinueSignal, ReturnValue):
                raise
            except Exception as e:
                he = HSError.wrap(e, getattr(stmt, 'line', 0), getattr(stmt, 'col', 0))
                raise he
        else:
            # 表达式语句
            self._eval_expr(stmt)

    # --- 声明/赋值 ---
    def _eval_VarDecl(self, node: VarDecl):
        value = self._eval_expr(node.value) if node.value else None
        self._set(node.name, value, local=True)

    def _eval_Assign(self, node: Assign):
        value = self._eval_expr(node.value)
        self._set(node.target, value)

    def _eval_IndexAssign(self, node: IndexAssign):
        container = self._eval_expr(node.container)
        index = self._eval_expr(node.index)
        value = self._eval_expr(node.value)
        try:
            if isinstance(container, list):
                if not isinstance(index, int):
                    raise TypeError("列表下标必须是整数")
                if not (-len(container) <= index < len(container)):
                    raise IndexOutOfRangeError(f"列表下标越界: {index} (长度 {len(container)})")
                container[index] = value
                return
            if isinstance(container, str):
                raise TypeError("字符串不可变，不能下标赋值")
            if isinstance(container, dict):
                # Map
                container[index] = value
                return
            if isinstance(container, _HSSet):
                raise TypeError("Set 不支持下标赋值（用 add/delete）")
            raise TypeError(f"类型 {_hs_type_name(container)} 不支持下标赋值")
        except HSError:
            raise
        except IndexError:
            raise IndexOutOfRangeError(f"下标越界: {index}")

    # --- 控制流 ---
    def _eval_IfStatement(self, node: IfStatement):
        if self._is_truthy(self._eval_expr(node.condition)):
            for s in node.then_branch:
                self._eval_stmt(s)
            return
        for cond, body in node.elif_branches:
            if self._is_truthy(self._eval_expr(cond)):
                for s in body:
                    self._eval_stmt(s)
                return
        for s in node.else_branch:
            self._eval_stmt(s)

    def _eval_WhileStatement(self, node: WhileStatement):
        while self._is_truthy(self._eval_expr(node.condition)):
            try:
                for s in node.body:
                    self._eval_stmt(s)
            except BreakSignal:
                return
            except ContinueSignal:
                continue
            except ReturnValue:
                raise

    def _eval_ForStatement(self, node: ForStatement):
        start = int(self._to_num(self._eval_expr(node.start)))
        end = int(self._to_num(self._eval_expr(node.end)))
        step = int(self._to_num(self._eval_expr(node.step))) if node.step else 1
        if step == 0:
            raise RuntimeException("for 循环 step 不能为 0", node.line, node.col)

        self._push_scope()
        try:
            if step > 0:
                i = start
                while i < end:
                    self._set(node.var_name, i, local=True)
                    try:
                        for s in node.body:
                            self._eval_stmt(s)
                    except BreakSignal:
                        return
                    except ContinueSignal:
                        pass
                    i += step
            else:
                i = start
                while i > end:
                    self._set(node.var_name, i, local=True)
                    try:
                        for s in node.body:
                            self._eval_stmt(s)
                    except BreakSignal:
                        return
                    except ContinueSignal:
                        pass
                    i += step
        finally:
            self._pop_scope()

    def _eval_BreakStatement(self, _n):
        raise BreakSignal()

    def _eval_ContinueStatement(self, _n):
        raise ContinueSignal()

    # --- try/catch/throw ---
    def _eval_TryCatchStatement(self, node: TryCatchStatement):
        exc_val = None
        raised_kind = None
        try:
            for s in node.try_body:
                self._eval_stmt(s)
        except (BreakSignal, ContinueSignal, ReturnValue):
            raise  # 控制流不捕获
        except HSError as e:
            exc_val = e
            raised_kind = e.kind
        except Exception as e:
            exc_val = HSError.wrap(e, 0, 0)
            raised_kind = exc_val.kind

        # catch
        caught = False
        if exc_val is not None and node.catch_body:
            if node.catch_kind is None or raised_kind == node.catch_kind or node.catch_kind in ('Error', 'HSError'):
                caught = True
                self._push_scope()
                try:
                    if node.catch_var:
                        self._set(node.catch_var, exc_val.to_hs_value() if isinstance(exc_val, HSError) else exc_val,
                                  local=True)
                    for s in node.catch_body:
                        self._eval_stmt(s)
                finally:
                    self._pop_scope()
        # finally
        try:
            for s in node.finally_body:
                self._eval_stmt(s)
        finally:
            pass
        # 未捕获的错误继续抛出
        if exc_val is not None and not caught:
            raise exc_val

    def _eval_ThrowStatement(self, node: ThrowStatement):
        val = self._eval_expr(node.value) if node.value else None
        kind = node.kind
        if isinstance(val, HSError):
            raise val
        if isinstance(val, Exception) and not isinstance(val, (ReturnValue, BreakSignal, ContinueSignal)):
            raise HSError.wrap(val)
        msg = str(val) if val is not None else ""
        if kind == 'RuntimeError' or not kind:
            raise RuntimeException(msg, node.line, node.col)
        if kind == 'TypeError':
            raise TypeError(msg, node.line, node.col)
        if kind == 'IOError':
            raise IOError(msg, node.line, node.col)
        if kind == 'KeyNotFoundError':
            raise KeyNotFoundError(msg, node.line, node.col)
        if kind == 'IndexOutOfRangeError':
            raise IndexOutOfRangeError(msg, node.line, node.col)
        if kind == 'ZeroDivisionError':
            raise ZeroDivisionError_(msg or "除零", node.line, node.col)
        if kind == 'AssertionError':
            raise AssertionError_(msg, node.line, node.col)
        if kind == 'ParseError':
            raise ParseError_(msg, node.line, node.col)
        # 默认
        raise RuntimeException(msg, node.line, node.col)

    # --- assert/export ---
    def _eval_AssertStatement(self, node: AssertStatement):
        cond = self._eval_expr(node.condition)
        if not self._is_truthy(cond):
            msg = ""
            if node.message:
                msg = self._to_str(self._eval_expr(node.message))
            raise AssertionError_(msg or "断言失败", node.line, node.col)

    def _eval_ExportStatement(self, node: ExportStatement):
        for name in node.names:
            if not self._has(name):
                raise RuntimeException(f"export 未定义的标识符: '{name}'", node.line, node.col)
            self.exports[name] = self._get(name)
            # 同时让全局可见（保持 import 时可见）
            self.globals[name] = self.exports[name]
        for (name, val_node) in node.assignments:
            v = self._eval_expr(val_node)
            self.exports[name] = v
            self.globals[name] = v

    # --- func/return/print ---
    def _eval_FuncDef(self, node: FuncDef):
        self.globals[node.name] = node

    def _eval_ReturnStatement(self, node: ReturnStatement):
        value = self._eval_expr(node.value) if node.value else None
        raise ReturnValue(value)

    def _eval_PrintStatement(self, node: PrintStatement):
        parts = [self._to_str(self._eval_expr(a)) for a in node.args]
        print(' '.join(parts))

    # --- import ---
    def _eval_ImportStatement(self, node: ImportStatement):
        module_name = node.module_name
        # 内置标准库
        builtin = {
            'json': self._load_std_json,
            'path': self._load_std_path,
            'os': self._load_std_os,
            'math': self._load_std_math,
            'pic': self._load_std_pic,
            'touch': self._load_std_touch,
            'http': self._load_std_http,
            'lan': self._load_std_lan,
        }
        handler = builtin.get(module_name)
        if handler:
            handler(node)
            return
        # 从文件加载
        module_path = self._resolve_module_path(module_name, node)
        cache_key = str(module_path.resolve())
        if cache_key in self._loaded_modules:
            mod = self._loaded_modules[cache_key]
            self._install_module(mod, node.alias, module_name)
            return
        with open(module_path, 'r', encoding='utf-8') as f:
            src = f.read()
        sub_exports: Dict[str, Any] = {}
        sub = Interpreter(script_path=str(module_path), export_map=sub_exports,
                          parent_dirs=[self.script_dir] + self.extra_search)
        # 复制缓存
        sub._loaded_modules = self._loaded_modules
        saved_dir = self.script_dir
        try:
            self.script_dir = module_path.parent.resolve()
            tokens = Lexer(src, str(module_path)).tokenize()
            ast = Parser(tokens).parse()
            sub._eval_program(ast)
        finally:
            self.script_dir = saved_dir
        # 模块对象
        mod = {'__hstype__': 'module',
               '__name__': module_name,
               '__file__': str(module_path.resolve())}
        for k, v in sub_exports.items():
            mod[k] = v
        if not sub_exports:
            # 没显式 export → 把顶层非下划线全局变量都带上
            for k, v in sub.globals.items():
                if not k.startswith('_') and k not in mod:
                    mod[k] = v
        self._loaded_modules[cache_key] = mod
        self._install_module(mod, node.alias, module_name)

    def _install_module(self, mod: Dict, alias: Optional[str], orig_name: str):
        if alias:
            self.globals[alias] = mod
            self._set(alias, mod)
            # 也提供一个全大写别名（如 LM → LM 不变），方便无别名 import 时 JSON.stringify 这种写法
            self.globals[alias.upper()] = mod
        else:
            # 默认：短名（去扩展名）作为模块对象名；并把导出物放入作用域
            short = PyPath(orig_name).stem if not orig_name.startswith('std:') else orig_name
            self.globals[short] = mod
            # 兼容大小写：同时注册全大写别名（json → JSON / path → PATH / os → OS / math → MATH）
            self.globals[short.upper()] = mod
            # 顶层 globals 展开（export 列表优先）
            for k, v in mod.items():
                if k.startswith('__'):
                    continue
                if not self._has(k):
                    self.globals[k] = v

    def _resolve_module_path(self, module_name: str, node: ImportStatement) -> PyPath:
        if not module_name.endswith('.hs'):
            module_name += '.hs'
        search = [self.script_dir, PyPath.cwd()] + self.extra_search
        for d in search:
            p = d / module_name
            if p.exists() and p.is_file():
                return p
        raise ModuleNotFoundError(node.module_name, node.line, node.col)

    # ==========================================================
    # 标准库模块（Python 实现）
    # ==========================================================
    def _load_std_json(self, node: ImportStatement):
        mod = {
            '__hstype__': 'module',
            '__name__': 'json',
            'parse': self._stdlib_json_parse,
            'stringify': self._stdlib_json_stringify,
            'stringify_pretty': lambda v, indent=2: self._stdlib_json_stringify(v, indent=indent),
        }
        self._loaded_modules['std:json'] = mod
        self._install_module(mod, node.alias, 'json')

    def _stdlib_json_parse(self, s: str):
        try:
            data = _pyjson.loads(s)
        except Exception as e:
            raise RuntimeException(f"JSON.parse 错误: {e}")
        return self._from_py_to_hs(data)

    def _stdlib_json_stringify(self, v, indent: Optional[int] = None):
        py = self._from_hs_to_py(v)
        try:
            return _pyjson.dumps(py, ensure_ascii=False, indent=indent,
                                 default=lambda x: None)
        except Exception as e:
            raise RuntimeException(f"JSON.stringify 错误: {e}")

    def _from_py_to_hs(self, v):
        if isinstance(v, dict):
            m = _hs_map()
            for k, val in v.items():
                m[k] = self._from_py_to_hs(val)
            return m
        if isinstance(v, list):
            return [self._from_py_to_hs(x) for x in v]
        if isinstance(v, tuple):
            return [self._from_py_to_hs(x) for x in v]
        if isinstance(v, set):
            return _hs_set(*[self._from_py_to_hs(x) for x in v])
        return v

    def _from_hs_to_py(self, v):
        if isinstance(v, _HSSet):
            return [self._from_hs_to_py(x) for x in v.data]
        if isinstance(v, dict):
            if v.get('__hstype__') == 'map':
                return {k: self._from_hs_to_py(val) for k, val in v.items() if k != '__hstype__'}
            if v.get('__hstype__') == 'module':
                return v.get('__name__', '<module>')
            return {str(k): self._from_hs_to_py(val) for k, val in v.items()}
        if isinstance(v, list):
            return [self._from_hs_to_py(x) for x in v]
        return v

    def _load_std_path(self, node: ImportStatement):
        mod = {
            '__hstype__': 'module', '__name__': 'path',
            'join': lambda *parts: str(PyPath(parts[0]).joinpath(*parts[1:])) if parts else "",
            'basename': lambda p: PyPath(p).name,
            'dirname': lambda p: str(PyPath(p).parent),
            'extname': lambda p: PyPath(p).suffix,
            'stem': lambda p: PyPath(p).stem,
            'resolve': lambda p: str(PyPath(p).resolve()),
            'exists': lambda p: PyPath(p).exists(),
            'isfile': lambda p: PyPath(p).is_file(),
            'isdir': lambda p: PyPath(p).is_dir(),
            'sep': os.sep,
            'cwd': lambda: str(PyPath.cwd()),
            'absolute': lambda p: str(PyPath(p).absolute()),
            'with_ext': lambda p, e: str(PyPath(p).with_suffix(e if e.startswith('.') else '.' + e)),
            'parent': lambda p: str(PyPath(p).parent),
            'split': lambda p: [PyPath(p).parent.as_posix(), PyPath(p).name],
        }
        self._loaded_modules['std:path'] = mod
        self._install_module(mod, node.alias, 'path')

    def _load_std_os(self, node: ImportStatement):
        import getpass
        import platform
        mod = {
            '__hstype__': 'module', '__name__': 'os',
            'name': os.name,
            'platform': sys.platform,
            'arch': platform.machine(),
            'python_version': platform.python_version(),
            'env': lambda name, default=None: os.environ.get(name, default),
            'user': getpass.getuser,
            'hostname': platform.node,
            'exit': sys.exit,
            'cwd': lambda: str(PyPath.cwd()),
            'chdir': lambda d: os.chdir(d),
            'argv': list(sys.argv),
            'time': lambda: __import__('time').time(),
            'sleep': lambda s: __import__('time').sleep(float(s)),
        }
        self._loaded_modules['std:os'] = mod
        self._install_module(mod, node.alias, 'os')

    def _load_std_math(self, node: ImportStatement):
        import math as m
        mod = {
            '__hstype__': 'module', '__name__': 'math',
            'PI': m.pi, 'E': m.e, 'TAU': m.tau, 'INF': m.inf, 'NAN': m.nan,
            'sqrt': m.sqrt, 'cbrt': lambda x: x ** (1/3),
            'sin': m.sin, 'cos': m.cos, 'tan': m.tan,
            'asin': m.asin, 'acos': m.acos, 'atan': m.atan, 'atan2': m.atan2,
            'log': m.log, 'log2': m.log2, 'log10': m.log10,
            'exp': m.exp, 'pow': m.pow,
            'floor': m.floor, 'ceil': m.ceil, 'round': round,
            'mod': lambda a, b: int(a) % int(b),
            'sign': lambda x: -1 if x < 0 else (1 if x > 0 else 0),
            'clamp': lambda x, lo, hi: max(lo, min(hi, x)),
            'degrees': m.degrees, 'radians': m.radians,
            'abs': abs,
        }
        self._loaded_modules['std:math'] = mod
        self._install_module(mod, node.alias, 'math')

    # ==========================================================
    # 标准库 — json (JSON 文件处理)
    # ==========================================================
    def _load_std_json(self, node: ImportStatement):
        """json 标准库：解析/序列化 + 文件读写"""
        mod = {
            '__hstype__': 'module', '__name__': 'json',
            'parse': self._stdlib_json_parse,
            'stringify': self._stdlib_json_stringify,
            'stringify_pretty': lambda v, indent=2: self._stdlib_json_stringify(v, indent=indent),
            # 新增：JSON 文件处理
            'load': self._stdlib_json_load,
            'save': self._stdlib_json_save,
            'load_file': self._stdlib_json_load,  # 别名
            'save_file': self._stdlib_json_save,  # 别名
        }
        self._loaded_modules['std:json'] = mod
        self._install_module(mod, node.alias, 'json')

    def _stdlib_json_load(self, path: str):
        """从文件读取并解析 JSON"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = _pyjson.load(f)
        except FileNotFoundError:
            raise IOError(f"JSON 文件不存在: {path}")
        except _pyjson.JSONDecodeError as e:
            raise RuntimeException(f"JSON 解析错误: {e}")
        except Exception as e:
            raise IOError(f"读取 JSON 文件失败: {e}")
        return self._from_py_to_hs(data)

    def _stdlib_json_save(self, path: str, value, indent: Optional[int] = 2):
        """将值序列化为 JSON 并写入文件"""
        py = self._from_hs_to_py(value)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                _pyjson.dump(py, f, ensure_ascii=False, indent=indent,
                             default=lambda x: None)
        except Exception as e:
            raise IOError(f"写入 JSON 文件失败: {e}")
        return True

    # ==========================================================
    # 标准库 — pic (图片处理)
    # ==========================================================
    def _load_std_pic(self, node: ImportStatement):
        """pic 标准库：图片处理（基于 Pillow，可选）"""
        def _require_pil():
            try:
                from PIL import Image as _Img
                return _Img
            except ImportError:
                raise RuntimeException("pic 模块需要 Pillow 库: pip install Pillow")

        def pic_load(path):
            Img = _require_pil()
            try:
                return _HSImage(Img.open(path))
            except Exception as e:
                raise IOError(f"打开图片失败: {e}")

        def pic_create(width, height, color=(255, 255, 255)):
            Img = _require_pil()
            return _HSImage(Img.new('RGB', (int(width), int(height)), tuple(color)))

        def pic_info(path):
            Img = _require_pil()
            try:
                im = Img.open(path)
                return _hs_map(
                    ('width', im.width),
                    ('height', im.height),
                    ('mode', im.mode),
                    ('format', im.format or 'unknown'),
                )
            except Exception as e:
                raise IOError(f"读取图片信息失败: {e}")

        def pic_save(hs_img, path, fmt=None):
            if not isinstance(hs_img, _HSImage):
                raise TypeError("参数必须是 pic.load/create 返回的图片对象")
            try:
                if fmt:
                    hs_img.img.save(path, format=fmt)
                else:
                    hs_img.img.save(path)
            except Exception as e:
                raise IOError(f"保存图片失败: {e}")
            return True

        def pic_resize(hs_img, w, h):
            if not isinstance(hs_img, _HSImage):
                raise TypeError("参数必须是 pic 图片对象")
            return _HSImage(hs_img.img.resize((int(w), int(h))))

        def pic_thumbnail(hs_img, w, h):
            if not isinstance(hs_img, _HSImage):
                raise TypeError("参数必须是 pic 图片对象")
            hs_img.img.thumbnail((int(w), int(h)))
            return hs_img

        def pic_rotate(hs_img, angle):
            if not isinstance(hs_img, _HSImage):
                raise TypeError("参数必须是 pic 图片对象")
            return _HSImage(hs_img.img.rotate(float(angle)))

        def pic_crop(hs_img, x, y, w, h):
            if not isinstance(hs_img, _HSImage):
                raise TypeError("参数必须是 pic 图片对象")
            return _HSImage(hs_img.img.crop((int(x), int(y), int(x+w), int(y+h))))

        def pic_get_pixel(hs_img, x, y):
            if not isinstance(hs_img, _HSImage):
                raise TypeError("参数必须是 pic 图片对象")
            return list(hs_img.img.getpixel((int(x), int(y))))

        def pic_set_pixel(hs_img, x, y, color):
            if not isinstance(hs_img, _HSImage):
                raise TypeError("参数必须是 pic 图片对象")
            hs_img.img.putpixel((int(x), int(y)), tuple(color))
            return hs_img

        def pic_to_gray(hs_img):
            if not isinstance(hs_img, _HSImage):
                raise TypeError("参数必须是 pic 图片对象")
            return _HSImage(hs_img.img.convert('L'))

        mod = {
            '__hstype__': 'module', '__name__': 'pic',
            'load': pic_load,
            'create': pic_create,
            'info': pic_info,
            'save': pic_save,
            'resize': pic_resize,
            'thumbnail': pic_thumbnail,
            'rotate': pic_rotate,
            'crop': pic_crop,
            'get_pixel': pic_get_pixel,
            'set_pixel': pic_set_pixel,
            'to_gray': pic_to_gray,
            'to_grayscale': pic_to_gray,
            'formats': ['PNG', 'JPEG', 'BMP', 'GIF', 'TIFF', 'WEBP'],
        }
        self._loaded_modules['std:pic'] = mod
        self._install_module(mod, node.alias, 'pic')

    # ==========================================================
    # 标准库 — touch (调用外部程序)
    # ==========================================================
    def _load_std_touch(self, node: ImportStatement):
        """touch 标准库：调用外部程序"""
        import subprocess as _sp

        def touch_run(*args):
            """运行外部程序，返回退出码"""
            if not args:
                raise RuntimeException("touch.run 需要至少一个参数")
            cmd = [str(a) for a in args]
            try:
                result = _sp.run(cmd, timeout=60)
                return result.returncode
            except FileNotFoundError:
                raise RuntimeException(f"程序不存在: {cmd[0]}")
            except _sp.TimeoutExpired:
                raise RuntimeException(f"程序超时: {cmd[0]}")

        def touch_capture(*args):
            """运行外部程序，捕获输出"""
            if not args:
                raise RuntimeException("touch.capture 需要至少一个参数")
            cmd = [str(a) for a in args]
            try:
                result = _sp.run(cmd, capture_output=True, text=True,
                                timeout=60, encoding='utf-8', errors='replace')
                return _hs_map(
                    ('code', result.returncode),
                    ('stdout', result.stdout),
                    ('stderr', result.stderr),
                )
            except FileNotFoundError:
                raise RuntimeException(f"程序不存在: {cmd[0]}")
            except _sp.TimeoutExpired:
                raise RuntimeException(f"程序超时: {cmd[0]}")

        def touch_popen(*args):
            """启动外部程序，返回进程对象"""
            if not args:
                raise RuntimeException("touch.popen 需要至少一个参数")
            cmd = [str(a) for a in args]
            try:
                return _sp.Popen(cmd, stdout=_sp.PIPE, stderr=_sp.PIPE,
                                 text=True, encoding='utf-8', errors='replace')
            except Exception as e:
                raise RuntimeException(f"启动程序失败: {e}")

        def touch_shell(cmd_str):
            """通过 shell 执行命令字符串"""
            try:
                result = _sp.run(cmd_str, shell=True, capture_output=True,
                                 text=True, timeout=60, encoding='utf-8', errors='replace')
                return _hs_map(
                    ('code', result.returncode),
                    ('stdout', result.stdout),
                    ('stderr', result.stderr),
                )
            except Exception as e:
                raise RuntimeException(f"shell 执行失败: {e}")

        def touch_which(name):
            """查找可执行文件路径"""
            import shutil as _sh
            p = _sh.which(str(name))
            return p if p else ""

        mod = {
            '__hstype__': 'module', '__name__': 'touch',
            'run': touch_run,
            'capture': touch_capture,
            'exec': touch_capture,  # 别名
            'popen': touch_popen,
            'shell': touch_shell,
            'which': touch_which,
            'find': touch_which,  # 别名
        }
        self._loaded_modules['std:touch'] = mod
        self._install_module(mod, node.alias, 'touch')

    # ==========================================================
    # 标准库 — http (内网服务器 / HTTP 客户端)
    # ==========================================================
    def _load_std_http(self, node: ImportStatement):
        """http 标准库：简单 HTTP 客户端 + 内网服务器"""
        import urllib.request as _ureq
        import urllib.error as _uerr
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import threading

        def http_get(url, timeout=10):
            """HTTP GET 请求"""
            try:
                req = _ureq.Request(str(url), headers={'User-Agent': 'HaiScript/1.2'})
                with _ureq.urlopen(req, timeout=int(timeout)) as resp:
                    body = resp.read().decode('utf-8', errors='replace')
                    return _hs_map(
                        ('status', resp.status),
                        ('body', body),
                        ('headers', dict(resp.headers)),
                    )
            except _uerr.URLError as e:
                raise RuntimeException(f"HTTP 请求失败: {e}")
            except Exception as e:
                raise RuntimeException(f"HTTP 请求异常: {e}")

        def http_post(url, data, timeout=10):
            """HTTP POST 请求"""
            try:
                payload = str(data).encode('utf-8')
                req = _ureq.Request(str(url), data=payload, method='POST',
                                    headers={'User-Agent': 'HaiScript/1.2',
                                             'Content-Type': 'application/x-www-form-urlencoded'})
                with _ureq.urlopen(req, timeout=int(timeout)) as resp:
                    body = resp.read().decode('utf-8', errors='replace')
                    return _hs_map(
                        ('status', resp.status),
                        ('body', body),
                    )
            except Exception as e:
                raise RuntimeException(f"HTTP POST 失败: {e}")

        def http_download(url, path, timeout=30):
            """下载文件到本地"""
            try:
                _ureq.urlretrieve(str(url), str(path))
                return True
            except Exception as e:
                raise RuntimeException(f"下载失败: {e}")

        _server_instances = []

        def http_serve(port, handler_fn=None, static_dir=None):
            """启动内网 HTTP 服务器（阻塞）"""
            port = int(port)

            class _Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if handler_fn and callable(handler_fn):
                        try:
                            result = handler_fn(self.path)
                            body = str(result).encode('utf-8')
                        except Exception as e:
                            body = f"Error: {e}".encode('utf-8')
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/html; charset=utf-8')
                        self.end_headers()
                        self.wfile.write(body)
                    elif static_dir:
                        import os.path as _op
                        path = self.path.split('?')[0]
                        if path == '/':
                            path = '/index.html'
                        filepath = _op.join(str(static_dir), path.lstrip('/').replace('/', os.sep))
                        try:
                            with open(filepath, 'rb') as f:
                                content = f.read()
                            self.send_response(200)
                            self.send_header('Content-Type', 'text/html; charset=utf-8')
                            self.end_headers()
                            self.wfile.write(content)
                        except FileNotFoundError:
                            self.send_response(404)
                            self.end_headers()
                            self.wfile.write(b'404 Not Found')
                    else:
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/plain; charset=utf-8')
                        self.end_headers()
                        self.wfile.write('HaiScript HTTP Server'.encode('utf-8'))

                def log_message(self, fmt, *args):
                    pass  # 静默

            try:
                server = HTTPServer(('0.0.0.0', port), _Handler)
                _server_instances.append(server)
                print(f"HaiScript HTTP 服务器启动: http://localhost:{port}")
                server.serve_forever()
            except Exception as e:
                raise RuntimeException(f"HTTP 服务器启动失败: {e}")

        def http_serve_bg(port, handler_fn=None):
            """后台启动 HTTP 服务器（非阻塞）"""
            port = int(port)
            import threading as _th

            class _Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if handler_fn and callable(handler_fn):
                        try:
                            result = handler_fn(self.path)
                            body = str(result).encode('utf-8')
                        except Exception as e:
                            body = f"Error: {e}".encode('utf-8')
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/html; charset=utf-8')
                        self.end_headers()
                        self.wfile.write(body)
                    else:
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/plain; charset=utf-8')
                        self.end_headers()
                        self.wfile.write('HaiScript HTTP Server'.encode('utf-8'))

                def log_message(self, fmt, *args):
                    pass

            try:
                server = HTTPServer(('0.0.0.0', port), _Handler)
                _server_instances.append(server)
                t = _th.Thread(target=server.serve_forever, daemon=True)
                t.start()
                return f"http://localhost:{port}"
            except Exception as e:
                raise RuntimeException(f"HTTP 服务器启动失败: {e}")

        def http_stop():
            """停止后台 HTTP 服务器"""
            for s in _server_instances:
                try:
                    s.shutdown()
                except Exception:
                    pass
            _server_instances.clear()
            return True

        mod = {
            '__hstype__': 'module', '__name__': 'http',
            'get': http_get,
            'post': http_post,
            'download': http_download,
            'serve': http_serve,
            'serve_bg': http_serve_bg,
            'start': http_serve_bg,  # 别名
            'stop': http_stop,
        }
        self._loaded_modules['std:http'] = mod
        self._install_module(mod, node.alias, 'http')

    # ==========================================================
    # 标准库 — lan (局域网)
    # ==========================================================
    def _load_std_lan(self, node: ImportStatement):
        """lan 标准库：局域网工具"""
        import socket as _sock
        import subprocess as _sp

        def lan_ip():
            """获取本机内网 IP"""
            try:
                s = _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM)
                s.connect(('8.8.8.8', 80))
                ip = s.getsockname()[0]
                s.close()
                return ip
            except Exception:
                return '127.0.0.1'

        def lan_hostname():
            """获取本机主机名"""
            return _sock.gethostname()

        def lan_resolve(hostname):
            """解析主机名到 IP"""
            try:
                return _sock.gethostbyname(str(hostname))
            except Exception as e:
                raise RuntimeException(f"解析失败: {e}")

        def lan_ping(host, timeout=2):
            """简单 ping（TCP 连接测试）"""
            host = str(host)
            try:
                s = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
                s.settimeout(float(timeout))
                result = s.connect_ex((host, 80))
                s.close()
                return result == 0
            except Exception:
                return False

        def lan_scan_port(host, port, timeout=1):
            """扫描指定端口"""
            host, port = str(host), int(port)
            try:
                s = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
                s.settimeout(float(timeout))
                result = s.connect_ex((host, port))
                s.close()
                return result == 0
            except Exception:
                return False

        def lan_scan(ip_base, port=None, timeout=0.5):
            """扫描局域网：ping 或端口扫描

            ip_base: 如 "192.168.1" → 扫描 192.168.1.1~254
            port: 如果指定，扫描该端口；否则做 ICMP-like TCP ping
            """
            ip_base = str(ip_base)
            results = []
            for i in range(1, 255):
                ip = f"{ip_base}.{i}"
                if port:
                    if lan_scan_port(ip, int(port), timeout):
                        results.append(ip)
                else:
                    if lan_ping(ip, timeout):
                        results.append(ip)
                # 每扫 10 个打印进度
            return results

        def lan_connect(host, port, data=None, timeout=10):
            """TCP 连接并发送/接收数据"""
            host, port = str(host), int(port)
            try:
                s = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
                s.settimeout(float(timeout))
                s.connect((host, port))
                if data:
                    s.sendall(str(data).encode('utf-8'))
                    response = s.recv(4096).decode('utf-8', errors='replace')
                    s.close()
                    return response
                s.close()
                return True
            except Exception as e:
                raise RuntimeException(f"连接失败: {e}")

        def lan_listen(port, handler=None, timeout=30):
            """TCP 监听（单次连接）"""
            port = int(port)
            try:
                srv = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
                srv.setsockopt(_sock.SOL_SOCKET, _sock.SO_REUSEADDR, 1)
                srv.bind(('0.0.0.0', port))
                srv.listen(1)
                srv.settimeout(float(timeout))
                conn, addr = srv.accept()
                data = conn.recv(4096).decode('utf-8', errors='replace')
                if handler and callable(handler):
                    response = str(handler(data, addr[0]))
                    conn.sendall(response.encode('utf-8'))
                conn.close()
                srv.close()
                return _hs_map(('ip', addr[0]), ('port', addr[1]), ('data', data))
            except _sock.timeout:
                raise RuntimeException("监听超时")
            except Exception as e:
                raise RuntimeException(f"监听失败: {e}")

        mod = {
            '__hstype__': 'module', '__name__': 'lan',
            'ip': lan_ip,
            'hostname': lan_hostname,
            'resolve': lan_resolve,
            'ping': lan_ping,
            'scan_port': lan_scan_port,
            'scan': lan_scan,
            'connect': lan_connect,
            'listen': lan_listen,
            'send': lan_connect,  # 别名
        }
        self._loaded_modules['std:lan'] = mod
        self._install_module(mod, node.alias, 'lan')

    # ==========================================================
    # 表达式求值
    # ==========================================================
    def _eval_expr(self, expr):
        tname = type(expr).__name__
        m = getattr(self, f'_eval_e_{tname}', None)
        if m:
            try:
                return m(expr)
            except HSError:
                raise
            except (BreakSignal, ContinueSignal, ReturnValue):
                raise
            except Exception as e:
                raise HSError.wrap(e, getattr(expr, 'line', 0), getattr(expr, 'col', 0))
        raise RuntimeException(f"未知表达式类型: {tname}",
                               getattr(expr, 'line', 0), getattr(expr, 'col', 0))

    def _eval_e_NumberLiteral(self, n: NumberLiteral):
        return n.value

    def _eval_e_StringLiteral(self, s: StringLiteral):
        return s.value

    def _eval_e_BoolLiteral(self, b: BoolLiteral):
        return b.value

    def _eval_e_NilLiteral(self, _n):
        return None

    def _eval_e_ListLiteral(self, lst: ListLiteral):
        return [self._eval_expr(e) for e in lst.elements]

    def _eval_e_MapLiteral(self, m: MapLiteral):
        mm = _hs_map()
        for (kn, vn) in m.pairs:
            kv = self._eval_expr(kn)
            vv = self._eval_expr(vn)
            if not isinstance(kv, (str, int, float, bool, type(None))):
                raise TypeError(f"Map 键必须是可哈希基础类型，实际 {_hs_type_name(kv)}",
                                m.line, m.col)
            mm[kv] = vv
        return mm

    def _eval_e_SetLiteral(self, s: SetLiteral):
        items = []
        for en in s.elements:
            v = self._eval_expr(en)
            if not isinstance(v, (str, int, float, bool, type(None))):
                raise TypeError(f"Set 元素必须是可哈希基础类型，实际 {_hs_type_name(v)}",
                                s.line, s.col)
            items.append(v)
        return _hs_set(*items)

    def _eval_e_Identifier(self, i: Identifier):
        if not self._has(i.name):
            raise RuntimeException(f"未定义的标识符: '{i.name}'", i.line, i.col)
        return self._get(i.name)

    def _eval_e_MemberAccess(self, ma: MemberAccess):
        obj = self._eval_expr(ma.object)
        member = ma.member
        # 特殊属性：size, length
        if member in ('size', 'length', 'len'):
            try:
                return self._bi_len(obj)
            except HSError:
                pass
        # 字典对象：先按键查（用户数据键），再按类型分派方法表
        if isinstance(obj, dict):
            hst = obj.get('__hstype__')
            # module 类型：只允许显式写入的成员
            if hst == 'module':
                if member in obj:
                    return obj[member]
                raise KeyNotFoundError(f"模块 '{obj.get('__name__')}' 中无成员 '{member}'",
                                       ma.line, ma.col)
            # 普通字典 / map  / 错误字典：优先访问用户数据键（排除 __ 开头的内部标记）
            if not (member.startswith('__') and member.endswith('__')) and member in obj:
                return obj[member]
            # 最后才分派方法表
            return _HSMapMethods(self, obj, member)
        # string 属性方法
        if isinstance(obj, str):
            return _HSStringMethods(self, obj, member)
        if isinstance(obj, list):
            return _HSListMethods(self, obj, member)
        if isinstance(obj, _HSSet):
            return _HSSetMethods(self, obj, member)
        if isinstance(obj, _HSFile):
            return _HSFileMethods(self, obj, member)
        if isinstance(obj, FuncDef):
            raise RuntimeException(f"函数对象没有成员 '{member}'", ma.line, ma.col)
        # Python 对象作为通用 fallback（仅在明确可调用时返回）
        if hasattr(obj, member):
            attr = getattr(obj, member)
            if callable(attr):
                def _wrapper(*args, **kwargs):
                    return attr(*args, **kwargs)
                return _wrapper
            return attr
        raise KeyNotFoundError(f"类型 {_hs_type_name(obj)} 没有成员 '{member}'",
                               ma.line, ma.col)

    def _eval_e_UnaryOp(self, u: UnaryOp):
        val = self._eval_expr(u.operand)
        if u.op == '-':
            return -self._to_num(val)
        if u.op == '+':
            return self._to_num(val)
        if u.op == 'not':
            return not self._is_truthy(val)
        raise RuntimeException(f"未知一元运算符: {u.op}", u.line, u.col)

    def _eval_e_BinOp(self, b: BinOp):
        if b.op == 'and':
            l = self._eval_expr(b.left)
            if not self._is_truthy(l):
                return False
            return self._is_truthy(self._eval_expr(b.right))
        if b.op == 'or':
            l = self._eval_expr(b.left)
            if self._is_truthy(l):
                return True
            return self._is_truthy(self._eval_expr(b.right))

        l = self._eval_expr(b.left)
        r = self._eval_expr(b.right)

        if b.op == '+' and (isinstance(l, str) or isinstance(r, str)):
            return self._to_str(l) + self._to_str(r)
        if b.op == '+' and isinstance(l, list) and isinstance(r, list):
            return l + r
        if b.op == '+' and isinstance(l, _HSSet) and isinstance(r, _HSSet):
            return _hs_set(*(l.data | r.data))
        if b.op == '*' and isinstance(l, str) and isinstance(r, int):
            return l * r
        if b.op == '*' and isinstance(r, str) and isinstance(l, int):
            return r * l
        if b.op == '*' and isinstance(l, list) and isinstance(r, int):
            return l * r
        if b.op == '*' and isinstance(r, list) and isinstance(l, int):
            return r * l

        op = b.op
        if op in ('+', '-', '*', '/', '%', '**'):
            ln, rn = self._to_num(l), self._to_num(r)
            if op == '+': return ln + rn
            if op == '-': return ln - rn
            if op == '*': return ln * rn
            if op == '/':
                if rn == 0:
                    raise ZeroDivisionError_("除数不能为 0", b.line, b.col)
                return ln / rn
            if op == '%':
                if rn == 0:
                    raise ZeroDivisionError_("取模除数不能为 0", b.line, b.col)
                return int(ln) % int(rn)
            if op == '**':
                try:
                    return ln ** rn
                except Exception as e:
                    raise RuntimeException(f"幂运算错误: {e}")

        if op in ('==', '!=', '<', '>', '<=', '>='):
            lh = l.data if isinstance(l, _HSSet) else l
            rh = r.data if isinstance(r, _HSSet) else r
            try:
                if op == '==': return lh == rh
                if op == '!=': return lh != rh
                if op == '<': return lh < rh
                if op == '>': return lh > rh
                if op == '<=': return lh <= rh
                if op == '>=': return lh >= rh
            except TypeError:
                raise TypeError(f"无法比较 {_hs_type_name(l)} 和 {_hs_type_name(r)}",
                                b.line, b.col)

        raise RuntimeException(f"未知运算符: {b.op}", b.line, b.col)

    def _eval_e_FuncCall(self, fc: FuncCall):
        callee = self._get(fc.name)
        if callee is None and not self._has(fc.name):
            raise RuntimeException(f"调用未定义的函数: '{fc.name}'", fc.line, fc.col)
        args = [self._eval_expr(a) for a in fc.args]
        return self._call_any(fc.name, callee, args, fc.line, fc.col)

    def _eval_e_MethodCall(self, mc: MethodCall):
        obj = self._eval_expr(mc.object)
        method = mc.method
        args = [self._eval_expr(a) for a in mc.args]
        return self._call_method(obj, method, args, mc.line, mc.col)

    def _eval_e_InputCall(self, ic: InputCall):
        prompt = ""
        if ic.prompt:
            prompt = self._to_str(self._eval_expr(ic.prompt))
        try:
            return input(prompt)
        except EOFError:
            return ""

    def _eval_e_ListIndex(self, li: ListIndex):
        container = self._eval_expr(li.list_expr)
        idx = self._eval_expr(li.index)
        try:
            if isinstance(container, (list, str)):
                if not isinstance(idx, int):
                    raise TypeError("下标必须是整数", li.line, li.col)
                if not (-len(container) <= idx < len(container)):
                    raise IndexOutOfRangeError(
                        f"下标越界: {idx} (长度={len(container)})", li.line, li.col)
                return container[idx]
            if isinstance(container, dict):
                # Map
                if idx in container:
                    return container[idx]
                raise KeyNotFoundError(f"Map 没有键 '{idx}'", li.line, li.col)
            if isinstance(container, _HSSet):
                raise TypeError("Set 不支持下标访问（用 has()）", li.line, li.col)
            raise TypeError(f"类型 {_hs_type_name(container)} 不支持下标访问", li.line, li.col)
        except HSError:
            raise
        except IndexError:
            raise IndexOutOfRangeError(f"下标越界: {idx}", li.line, li.col)
        except KeyError:
            raise KeyNotFoundError(f"Map 没有键 '{idx}'", li.line, li.col)

    # ==========================================================
    # 调用分派（普通函数 + 方法）
    # ==========================================================
    def _call_any(self, name: str, callee, args, line: int, col: int):
        if callable(callee):
            try:
                return callee(*args)
            except HSError:
                raise
            except TypeError as e:
                raise RuntimeException(f"调用 {name} 错误: {e}", line, col)
            except (ReturnValue, BreakSignal, ContinueSignal):
                raise
            except Exception as e:
                raise HSError.wrap(e, line, col)
        if isinstance(callee, FuncDef):
            return self._call_user_func(name, callee, args, line, col)
        # 尝试作为 __call__ 方法
        if hasattr(callee, '__call__'):
            try:
                return callee(*args)
            except Exception as e:
                raise HSError.wrap(e, line, col)
        raise RuntimeException(f"'{name}' 不是函数/可调用对象", line, col)

    def _call_user_func(self, name: str, fd: FuncDef, args, line: int, col: int):
        if len(args) != len(fd.params):
            raise RuntimeException(
                f"函数 {name} 需要 {len(fd.params)} 个参数，实际 {len(args)}",
                line, col
            )
        self._push_scope()
        try:
            for nm, val in zip(fd.params, args):
                self._set(nm, val, local=True)
            for s in fd.body:
                self._eval_stmt(s)
            return None
        except ReturnValue as rv:
            return rv.value
        finally:
            self._pop_scope()

    # ==========================================================
    # 方法分派
    # ==========================================================
    def _call_method(self, obj, method: str, args, line: int, col: int):
        # 1) string
        if isinstance(obj, str):
            return _HSStringMethods.call(self, obj, method, args, line, col)
        # 2) list
        if isinstance(obj, list):
            return _HSListMethods.call(self, obj, method, args, line, col)
        # 3) map
        if isinstance(obj, dict) and obj.get('__hstype__') != 'module':
            return _HSMapMethods.call(self, obj, method, args, line, col)
        # 4) set
        if isinstance(obj, _HSSet):
            return _HSSetMethods.call(self, obj, method, args, line, col)
        # 5) file
        if isinstance(obj, _HSFile):
            return _HSFileMethods.call(self, obj, method, args, line, col)
        # 6) 模块
        if isinstance(obj, dict) and obj.get('__hstype__') == 'module':
            fn = obj.get(method)
            if fn is not None and (callable(fn) or isinstance(fn, FuncDef)):
                return self._call_any(f"{obj.get('__name__','?')}.{method}", fn, args, line, col)
            raise KeyNotFoundError(f"模块 '{obj.get('__name__')}' 中无方法 '{method}'", line, col)
        # 7) Python 对象的 fallback
        if hasattr(obj, method):
            fn = getattr(obj, method)
            if callable(fn):
                try:
                    return fn(*args)
                except Exception as e:
                    raise HSError.wrap(e, line, col)
            return fn
        raise KeyNotFoundError(f"类型 {_hs_type_name(obj)} 没有方法 '{method}'", line, col)

    # ==========================================================
    # 数值转换
    # ==========================================================
    def _to_num(self, x) -> float:
        if isinstance(x, bool):
            return 1.0 if x else 0.0
        if isinstance(x, (int, float)):
            return x
        if isinstance(x, str):
            try:
                if '.' in x:
                    return float(x)
                return int(x)
            except ValueError:
                raise TypeError(f"无法将字符串转为数字: '{x}'")
        raise TypeError(f"无法转为数字: {_hs_type_name(x)}")


# ==========================================================
# 方法表：string / list / map / set / file
#   通过 "_call" 直接避免闭包构造开销
# ==========================================================
class _HSStringMethods:
    """字符串方法表"""
    @staticmethod
    def call(ip: Interpreter, s: str, m: str, args, line, col):
        if m == 'upper': return s.upper()
        if m == 'lower': return s.lower()
        if m == 'strip': return s.strip()
        if m == 'lstrip': return s.lstrip()
        if m == 'rstrip': return s.rstrip()
        if m == 'capitalize': return s.capitalize()
        if m == 'title': return s.title()
        if m == 'reverse': return s[::-1]
        if m == 'len' or m == 'size' or m == 'length': return len(s)
        if m == 'chars': return list(s)
        if m == 'bytes': return [ord(c) for c in s]
        if m == 'to_int':
            try:
                return int(s)
            except Exception:
                raise RuntimeException(f"字符串无法转 int: {s}", line, col)
        if m == 'to_num':
            try:
                return float(s) if '.' in s else int(s)
            except Exception:
                raise RuntimeException(f"字符串无法转 number: {s}", line, col)
        if m == 'split':
            sep = args[0] if args else None
            maxsplit = int(args[1]) if len(args) > 1 else -1
            return s.split(sep, maxsplit)
        if m == 'lines':
            return s.splitlines()
        if m == 'replace':
            if len(args) < 2:
                raise RuntimeException("string.replace(old, new[, count])", line, col)
            old, new = args[0], args[1]
            count = int(args[2]) if len(args) > 2 else -1
            return s.replace(str(old), str(new), count)
        if m == 'find':
            sub = str(args[0])
            start = int(args[1]) if len(args) > 1 else 0
            return s.find(sub, start)
        if m == 'contains' or m == 'has':
            return str(args[0]) in s
        if m == 'index':
            sub = str(args[0])
            start = int(args[1]) if len(args) > 1 else 0
            idx = s.find(sub, start)
            if idx < 0:
                raise KeyNotFoundError(f"子串不存在: {sub}", line, col)
            return idx
        if m == 'starts_with': return s.startswith(str(args[0]))
        if m == 'ends_with': return s.endswith(str(args[0]))
        if m == 'at':
            i = int(args[0])
            if -len(s) <= i < len(s):
                return s[i]
            raise IndexOutOfRangeError(f"string.at({i}) 越界 (长度 {len(s)})", line, col)
        if m == 'slice':
            start = int(args[0]) if args else 0
            end = int(args[1]) if len(args) > 1 else len(s)
            step = int(args[2]) if len(args) > 2 else 1
            return s[start:end:step]
        if m == 'format':
            try:
                return s.format(*args)
            except Exception as e:
                raise RuntimeException(f"string.format 错误: {e}", line, col)
        if m == 'is_empty': return len(s) == 0
        if m == 'repeat':
            n = int(args[0]) if args else 0
            return s * n
        if m == 'trim': return s.strip()
        raise KeyNotFoundError(f"string 没有方法 '{m}'", line, col)

    def __init__(self, ip, s, method):  # 用于 MemberAccess 访问方法对象
        self._ip = ip
        self._s = s
        self._m = method

    def __call__(self, *args):
        return _HSStringMethods.call(self._ip, self._s, self._m, list(args), 0, 0)


class _HSListMethods:
    @staticmethod
    def call(ip: Interpreter, lst: list, m: str, args, line, col):
        if m == 'len' or m == 'size' or m == 'length': return len(lst)
        if m == 'is_empty': return len(lst) == 0
        if m == 'push' or m == 'append':
            for a in args:
                lst.append(a)
            return lst
        if m == 'pop':
            if not lst:
                raise IndexOutOfRangeError("list.pop: 空列表", line, col)
            return lst.pop(int(args[0])) if args else lst.pop()
        if m == 'first': return lst[0] if lst else None
        if m == 'last': return lst[-1] if lst else None
        if m == 'insert':
            i = int(args[0]); v = args[1]
            lst.insert(i, v)
            return lst
        if m == 'remove':
            if len(args) == 1 and isinstance(args[0], int):
                del lst[int(args[0])]
            else:
                # 删除等于给定值的第一个元素
                target = args[0]
                for i, e in enumerate(lst):
                    if e == target:
                        del lst[i]
                        return lst
                raise KeyNotFoundError(f"list.remove: 未找到值 {ip._to_str(target)}", line, col)
            return lst
        if m == 'contains' or m == 'has':
            return args[0] in lst
        if m == 'index':
            v = args[0]
            try:
                return lst.index(v)
            except ValueError:
                raise KeyNotFoundError(f"list.index: 未找到值", line, col)
        if m == 'slice':
            s = int(args[0]) if args else 0
            e = int(args[1]) if len(args) > 1 else len(lst)
            step = int(args[2]) if len(args) > 2 else 1
            return lst[s:e:step]
        if m == 'reverse':
            lst.reverse()
            return lst
        if m == 'reversed': return list(reversed(lst))
        if m == 'sort':
            keyfn = args[0] if args and callable(args[0]) else None
            try:
                if keyfn:
                    lst.sort(key=lambda x: ip._call_any('<lambda>', keyfn, [x], line, col))
                else:
                    lst.sort()
            except Exception as ex:
                raise RuntimeException(f"list.sort 错误: {ex}", line, col)
            return lst
        if m == 'sorted':
            cp = list(lst)
            _HSListMethods.call(ip, cp, 'sort', args, line, col)
            return cp
        if m == 'copy': return list(lst)
        if m == 'clear':
            lst.clear()
            return lst
        if m == 'join':
            sep = str(args[0]) if args else ""
            return sep.join(ip._to_str(x) for x in lst)
        if m == 'map':
            fn = args[0]
            out = []
            for x in lst:
                out.append(ip._call_any('<fn>', fn, [x], line, col))
            return out
        if m == 'filter':
            fn = args[0]
            out = []
            for x in lst:
                if ip._is_truthy(ip._call_any('<fn>', fn, [x], line, col)):
                    out.append(x)
            return out
        if m == 'reduce':
            fn = args[0]
            acc = args[1] if len(args) > 1 else (lst[0] if lst else None)
            xs = lst if len(args) > 1 else lst[1:]
            for x in xs:
                acc = ip._call_any('<fn>', fn, [acc, x], line, col)
            return acc
        if m == 'each' or m == 'for_each':
            fn = args[0]
            for x in lst:
                ip._call_any('<fn>', fn, [x], line, col)
            return None
        if m == 'sum':
            try:
                return sum(lst)
            except Exception as ex:
                raise RuntimeException(f"list.sum 错误: {ex}", line, col)
        if m == 'min':
            try:
                return min(lst)
            except Exception as ex:
                raise RuntimeException(f"list.min 错误: {ex}", line, col)
        if m == 'max':
            try:
                return max(lst)
            except Exception as ex:
                raise RuntimeException(f"list.max 错误: {ex}", line, col)
        if m == 'find':
            fn = args[0]
            for x in lst:
                if ip._is_truthy(ip._call_any('<fn>', fn, [x], line, col)):
                    return x
            return None
        if m == 'find_index':
            fn = args[0]
            for i, x in enumerate(lst):
                if ip._is_truthy(ip._call_any('<fn>', fn, [x], line, col)):
                    return i
            return -1
        if m == 'all':
            fn = args[0]
            return all(ip._is_truthy(ip._call_any('<fn>', fn, [x], line, col)) for x in lst)
        if m == 'any':
            fn = args[0]
            return any(ip._is_truthy(ip._call_any('<fn>', fn, [x], line, col)) for x in lst)
        if m == 'extend':
            other = args[0]
            if isinstance(other, list):
                lst.extend(other)
            elif isinstance(other, _HSSet):
                lst.extend(other.data)
            elif isinstance(other, str):
                lst.extend(list(other))
            return lst
        raise KeyNotFoundError(f"list 没有方法 '{m}'", line, col)

    def __init__(self, ip, lst, method):
        self._ip = ip
        self._lst = lst
        self._m = method

    def __call__(self, *args):
        return _HSListMethods.call(self._ip, self._lst, self._m, list(args), 0, 0)


class _HSMapMethods:
    @staticmethod
    def call(ip: Interpreter, mp: dict, m: str, args, line, col):
        # helper：排除 __hstype__
        if m == 'len' or m == 'size' or m == 'length':
            return len(mp) - 1  # 不含 __hstype__
        if m == 'is_empty':
            return (len(mp) - 1) == 0
        if m == 'get':
            k = args[0]
            default = args[1] if len(args) > 1 else None
            return mp.get(k, default)
        if m == 'set':
            k, v = args[0], args[1]
            mp[k] = v
            return mp
        if m == 'delete' or m == 'remove':
            k = args[0]
            if k in mp:
                val = mp.pop(k)
                return val
            if len(args) > 1:
                return args[1]
            return None
        if m == 'has' or m == 'contains':
            return args[0] in mp
        if m == 'keys':
            return [k for k in mp.keys() if k != '__hstype__']
        if m == 'values':
            return [v for k, v in mp.items() if k != '__hstype__']
        if m == 'items':
            return [[k, v] for k, v in mp.items() if k != '__hstype__']
        if m == 'clear':
            keep = mp.get('__hstype__', 'map')
            mp.clear()
            mp['__hstype__'] = keep
            return mp
        if m == 'copy':
            new = _hs_map()
            for k, v in mp.items():
                if k != '__hstype__':
                    new[k] = v
            return new
        if m == 'update':
            other = args[0]
            if isinstance(other, dict):
                for k, v in other.items():
                    if k != '__hstype__':
                        mp[k] = v
            return mp
        if m == 'each' or m == 'for_each':
            fn = args[0]
            for k, v in mp.items():
                if k == '__hstype__':
                    continue
                ip._call_any('<fn>', fn, [k, v], line, col)
            return None
        if m == 'map':
            fn = args[0]
            new = _hs_map()
            for k, v in mp.items():
                if k == '__hstype__':
                    continue
                res = ip._call_any('<fn>', fn, [k, v], line, col)
                if isinstance(res, (list, tuple)) and len(res) == 2:
                    new[res[0]] = res[1]
            return new
        if m == 'filter':
            fn = args[0]
            new = _hs_map()
            for k, v in mp.items():
                if k == '__hstype__':
                    continue
                if ip._is_truthy(ip._call_any('<fn>', fn, [k, v], line, col)):
                    new[k] = v
            return new
        if m == 'find':
            fn = args[0]
            for k, v in mp.items():
                if k == '__hstype__':
                    continue
                if ip._is_truthy(ip._call_any('<fn>', fn, [k, v], line, col)):
                    return [k, v]
            return None
        if m == 'to_list':
            return [[k, v] for k, v in mp.items() if k != '__hstype__']
        raise KeyNotFoundError(f"map 没有方法 '{m}'", line, col)

    def __init__(self, ip, mp, method):
        self._ip = ip
        self._mp = mp
        self._m = method

    def __call__(self, *args):
        return _HSMapMethods.call(self._ip, self._mp, self._m, list(args), 0, 0)


class _HSSetMethods:
    @staticmethod
    def call(ip: Interpreter, s: '_HSSet', m: str, args, line, col):
        data = s.data
        if m == 'len' or m == 'size' or m == 'length': return len(data)
        if m == 'is_empty': return len(data) == 0
        if m == 'add':
            for a in args:
                data.add(a)
            return s
        if m == 'delete' or m == 'remove':
            a = args[0]
            if a in data:
                data.remove(a)
                return True
            return False
        if m == 'has' or m == 'contains':
            return args[0] in data
        if m == 'clear':
            data.clear()
            return s
        if m == 'list':
            return list(data)
        if m == 'copy':
            return _hs_set(*list(data))
        if m == 'union' or m == 'merge':
            other = args[0]
            o = other.data if isinstance(other, _HSSet) else set(other)
            return _hs_set(*(data | o))
        if m == 'inter' or m == 'intersect':
            other = args[0]
            o = other.data if isinstance(other, _HSSet) else set(other)
            return _hs_set(*(data & o))
        if m == 'diff' or m == 'difference':
            other = args[0]
            o = other.data if isinstance(other, _HSSet) else set(other)
            return _hs_set(*(data - o))
        if m == 'symdiff':
            other = args[0]
            o = other.data if isinstance(other, _HSSet) else set(other)
            return _hs_set(*(data ^ o))
        if m == 'subset':
            other = args[0]
            o = other.data if isinstance(other, _HSSet) else set(other)
            return data <= o
        if m == 'superset':
            other = args[0]
            o = other.data if isinstance(other, _HSSet) else set(other)
            return data >= o
        if m == 'each' or m == 'for_each':
            fn = args[0]
            for x in data:
                ip._call_any('<fn>', fn, [x], line, col)
            return None
        if m == 'map':
            fn = args[0]
            return [ip._call_any('<fn>', fn, [x], line, col) for x in data]
        if m == 'filter':
            fn = args[0]
            return _hs_set(*[x for x in data if ip._is_truthy(
                ip._call_any('<fn>', fn, [x], line, col))])
        raise KeyNotFoundError(f"set 没有方法 '{m}'", line, col)

    def __init__(self, ip, s, method):
        self._ip = ip
        self._s = s
        self._m = method

    def __call__(self, *args):
        return _HSSetMethods.call(self._ip, self._s, self._m, list(args), 0, 0)


# ==========================================================
# 文件对象
# ==========================================================
class _HSFile:
    __slots__ = ('f', 'path', '__hstype__')

    def __init__(self, f, path):
        self.f = f
        self.path = path
        self.__hstype__ = 'file'


class _HSFileMethods:
    @staticmethod
    def call(ip: Interpreter, fh: '_HSFile', m: str, args, line, col):
        f = fh.f
        if m == 'read':
            size = int(args[0]) if args else -1
            try:
                return f.read(size if size > 0 else None)
            except Exception as e:
                raise IOError(f"文件读取错误: {e}", path=fh.path, line=line, col=col)
        if m == 'read_line':
            try:
                ln = f.readline()
                return ln.rstrip('\n').rstrip('\r') if ln else None
            except Exception as e:
                raise IOError(f"文件读取错误: {e}", path=fh.path, line=line, col=col)
        if m == 'read_lines':
            try:
                return [ln.rstrip('\n').rstrip('\r') for ln in f.readlines()]
            except Exception as e:
                raise IOError(f"文件读取错误: {e}", path=fh.path, line=line, col=col)
        if m == 'write':
            content = ip._to_str(args[0]) if args else ''
            try:
                return f.write(content)
            except Exception as e:
                raise IOError(f"文件写入错误: {e}", path=fh.path, line=line, col=col)
        if m == 'write_line' or m == 'writeln':
            content = ip._to_str(args[0]) if args else ''
            try:
                return f.write(content + '\n')
            except Exception as e:
                raise IOError(f"文件写入错误: {e}", path=fh.path, line=line, col=col)
        if m == 'write_lines':
            lines = args[0]
            try:
                for ln in lines:
                    f.write(ip._to_str(ln) + '\n')
                return len(lines)
            except Exception as e:
                raise IOError(f"文件写入错误: {e}", path=fh.path, line=line, col=col)
        if m == 'close':
            try:
                f.close()
                return True
            except Exception as e:
                raise IOError(f"文件关闭错误: {e}", path=fh.path, line=line, col=col)
        if m == 'flush':
            f.flush()
            return True
        if m == 'seek':
            pos = int(args[0])
            whence = int(args[1]) if len(args) > 1 else 0
            f.seek(pos, whence)
            return True
        if m == 'tell':
            return f.tell()
        if m == 'path':
            return fh.path
        if m == 'closed':
            return f.closed
        if m == 'mode':
            return f.mode
        raise KeyNotFoundError(f"file 没有方法 '{m}'", line, col)

    def __init__(self, ip, fh, method):
        self._ip = ip
        self._fh = fh
        self._m = method

    def __call__(self, *args):
        return _HSFileMethods.call(self._ip, self._fh, self._m, list(args), 0, 0)


class _HSImage:
    """HaiScript 图片对象包装（pic 标准库）"""
    __slots__ = ('img', '__hstype__')

    def __init__(self, img):
        self.img = img
        self.__hstype__ = 'image'

    @property
    def width(self):
        return self.img.width

    @property
    def height(self):
        return self.img.height
