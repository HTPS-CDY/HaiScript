"""
HaiScript C 代码生成器
将 AST 转换为 C 源代码
"""
import os
from typing import List, Dict, Set, Tuple

from haiscript.interpreter.lexer import Lexer
from haiscript.interpreter.parser import (
    Parser, ParseError,
    Program, NumberLiteral, StringLiteral, BoolLiteral, NilLiteral, ListLiteral,
    Identifier, BinOp, UnaryOp, Assign, VarDecl,
    IfStatement, WhileStatement, ForStatement,
    FuncDef, FuncCall, ReturnStatement,
    PrintStatement, InputCall, ImportStatement,
    ListIndex, RangeExpr,
)


class CodegenError(Exception):
    def __init__(self, msg: str, line: int = 0):
        loc = f"[行{line}] " if line else ""
        super().__init__(f"{loc}代码生成错误: {msg}")


class CCodeGenerator:
    """将 HaiScript AST 转换为 C 源代码"""

    def __init__(self):
        self.output: List[str] = []
        self.indent = 0
        self.var_types: Dict[str, str] = {}  # 变量名 -> C类型
        self.func_sigs: List[str] = []      # 函数声明
        self.used_functions: Set[str] = set()  # 需要的标准库函数
        self.temp_counter = 0
        self.current_func: str = ""
        self._in_function = False

    # ---------- 辅助 ----------
    def _emit(self, line: str = ""):
        if line:
            self.output.append("  " * self.indent + line)
        else:
            self.output.append("")

    def _push_indent(self):
        self.indent += 1

    def _pop_indent(self):
        self.indent = max(0, self.indent - 1)

    def _new_temp(self, prefix: str = "tmp") -> str:
        self.temp_counter += 1
        return f"{prefix}_{self.temp_counter}"

    def _c_type_for(self, value) -> str:
        """根据Python值推断C类型"""
        if isinstance(value, bool):
            return 'int'
        if isinstance(value, int):
            return 'long long'
        if isinstance(value, float):
            return 'double'
        if isinstance(value, str):
            return 'const char*'
        if isinstance(value, list):
            return 'void*'
        return 'long long'

    def _require_function(self, func_name: str):
        self.used_functions.add(func_name)

    # ---------- 头部 ----------
    def _emit_header(self):
        self._emit("/* HaiScript to C 自动生成代码 */")
        self._emit("#include <stdio.h>")
        self._emit("#include <stdlib.h>")
        self._emit("#include <string.h>")
        self._emit("#include <stdbool.h>")
        if os.name == 'nt':
            # Windows 控制台编码：先尝试把控制台切到 UTF-8（CP65001）
            # 现代 Windows 10/11 支持良好；若失败则退回系统默认代码页。
            # 同时 GCC 必须用 -finput-charset=UTF-8 -fexec-charset=UTF-8 编译，
            # 保证字符串字面量在 .exe 中以 UTF-8 存储，与 CP65001 一致。
            self._emit("#include <windows.h>")
            self._emit("")
            self._emit("/* 控制台编码初始化（Windows UTF-8 CP65001） */")
            self._emit("static void hs_setup_console_cp(void) {")
            self._emit("  SetConsoleOutputCP(65001);")
            self._emit("  SetConsoleCP(65001);")
            self._emit("}")
        self._emit("")
        self._emit("/* 字符串拼接辅助 */")
        self._emit("static char* hs_strcat(const char* a, const char* b) {")
        self._emit("  size_t la = strlen(a), lb = strlen(b);")
        self._emit("  char* r = malloc(la + lb + 1);")
        self._emit("  memcpy(r, a, la); memcpy(r + la, b, lb + 1);")
        self._emit("  return r;")
        self._emit("}")
        self._emit("")
        self._emit("/* 字符串重复辅助 */")
        self._emit("static char* hs_strmul(const char* s, long long n) {")
        self._emit("  if (n <= 0) { char* e = malloc(1); e[0] = 0; return e; }")
        self._emit("  size_t ls = strlen(s);")
        self._emit("  char* r = malloc(ls * n + 1); size_t p = 0;")
        self._emit("  for (long long i = 0; i < n; i++) { memcpy(r + p, s, ls); p += ls; }")
        self._emit("  r[p] = 0; return r;")
        self._emit("}")
        self._emit("")
        self._emit("/* 比较 nil 的占位 */")
        self._emit("#define HS_NIL (0LL)")
        self._emit("")

    def _emit_footer(self):
        self._emit("")

    # ---------- 主入口 ----------
    def generate(self, source: str) -> str:
        """从 HaiScript 源码生成 C 代码字符串"""
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()

        self.output = []
        self.var_types = {}
        self.func_sigs = []
        self.used_functions = set()
        self.temp_counter = 0
        self.current_func = ""
        self._in_function = False

        self._emit_header()

        # 第一遍：收集全局变量声明
        global_vars_code: List[str] = []
        for stmt in ast.statements:
            if isinstance(stmt, FuncDef):
                # 收集函数签名
                param_types = ', '.join('long long' for _ in stmt.params) if stmt.params else 'void'
                sig = f"long long hs_f_{stmt.name}({param_types});"
                self.func_sigs.append(sig)
            elif isinstance(stmt, VarDecl):
                # 全局变量
                t = 'long long'
                initial = '0'
                if stmt.value is not None:
                    if isinstance(stmt.value, NumberLiteral):
                        if isinstance(stmt.value.value, float):
                            t = 'double'
                            initial = repr(stmt.value.value)
                        else:
                            initial = repr(stmt.value.value) + 'LL'
                    elif isinstance(stmt.value, BoolLiteral):
                        initial = '1' if stmt.value.value else '0'
                    elif isinstance(stmt.value, StringLiteral):
                        t = 'const char*'
                        initial = self._c_string(stmt.value.value)
                    elif isinstance(stmt.value, ListLiteral):
                        t = 'void*'
                        initial = 'NULL'
                self.var_types[f"g_{stmt.name}"] = t
                global_vars_code.append(f"static {t} g_{stmt.name} = {initial};")

        # 输出函数声明
        for sig in self.func_sigs:
            self._emit(sig)
        self._emit("")
        # 输出全局变量
        for gv in global_vars_code:
            self._emit(gv)
        if global_vars_code:
            self._emit("")

        # 第二遍：生成所有用户函数
        user_funcs = [s for s in ast.statements if isinstance(s, FuncDef)]
        for fd in user_funcs:
            self._gen_function(fd)

        # 主函数：执行非函数、非全局声明的顶层语句
        self._emit("int main(void) {")
        self._push_indent()
        if os.name == 'nt':
            # 先切换控制台到 UTF-8 代码页（CP65001），保证中文输出不乱码
            self._emit("hs_setup_console_cp();")
        for stmt in ast.statements:
            if not isinstance(stmt, (FuncDef, VarDecl)):
                self._gen_top_statement(stmt)
        self._emit("return 0;")
        self._pop_indent()
        self._emit("}")
        self._emit_footer()

        return '\n'.join(self.output)

    # ---------- 函数生成 ----------
    def _gen_function(self, fd: FuncDef):
        self.current_func = fd.name
        self._in_function = True
        
        # 使用带参数名的完整签名
        params_named = ', '.join(f'long long {p}' for p in fd.params) if fd.params else 'void'
        self._emit(f"long long hs_f_{fd.name}({params_named}) {{")
        self._push_indent()

        # 将参数注册到变量表
        for p in fd.params:
            self.var_types[p] = 'long long'

        for s in fd.body:
            self._gen_statement(s)
        
        # 确保函数有返回值（保底）；即使函数中已有 return，也只是 C 的 unreachable 警告
        self._emit("return 0;")
        self._pop_indent()
        self._emit("}")
        self._emit("")
        
        # 清理当前函数的局部变量
        for p in fd.params:
            if p in self.var_types:
                del self.var_types[p]
        self.current_func = ""
        self._in_function = False

    # ---------- 语句生成 ----------
    def _gen_statement(self, stmt):
        if isinstance(stmt, VarDecl):
            self._gen_vardecl(stmt)
        elif isinstance(stmt, Assign):
            self._gen_assign(stmt)
        elif isinstance(stmt, IfStatement):
            self._gen_if(stmt)
        elif isinstance(stmt, WhileStatement):
            self._gen_while(stmt)
        elif isinstance(stmt, ForStatement):
            self._gen_for(stmt)
        elif isinstance(stmt, ReturnStatement):
            self._gen_return(stmt)
        elif isinstance(stmt, PrintStatement):
            self._gen_print(stmt)
        elif isinstance(stmt, ImportStatement):
            raise CodegenError("编译模式暂不支持 import 语句", stmt.line)
        else:
            # 表达式语句
            self._gen_expr(stmt)
            self._emit(";")

    def _gen_top_statement(self, stmt):
        """顶层 main 中的语句"""
        self._gen_statement(stmt)

    def _gen_vardecl(self, node: VarDecl):
        if self._in_function:
            # 局部变量
            t = 'long long'
            initial = '0'
            if node.value is not None:
                expr_code, expr_type = self._gen_rvalue(node.value)
                t = expr_type
                initial = expr_code
            self.var_types[node.name] = t
            self._emit(f"{t} {node.name} = {initial};")
        else:
            # 全局变量在 header 里已处理
            pass

    def _gen_assign(self, node: Assign):
        expr_code, expr_type = self._gen_rvalue(node.value)
        # 确定目标位置
        vname, is_global = self._resolve_var(node.target)
        if vname is None:
            # 新变量，默认为局部 long long
            if self._in_function:
                self.var_types[node.target] = expr_type
                self._emit(f"{expr_type} {node.target} = {expr_code};")
            else:
                raise CodegenError(f"赋值未声明的全局变量: {node.target}", node.line)
        else:
            self._emit(f"{vname} = ({expr_type})({expr_code});")

    def _resolve_var(self, name: str):
        """解析变量为 C 表达式；返回 (cname, is_global)"""
        # 局部变量
        if name in self.var_types:
            return (name, False)
        # 全局变量
        gname = f"g_{name}"
        if gname in self.var_types:
            return (gname, True)
        return (None, False)

    def _gen_if(self, node: IfStatement):
        cond, _ = self._gen_rvalue(node.condition)
        self._emit(f"if (({cond}) != 0) {{")
        self._push_indent()
        for s in node.then_branch:
            self._gen_statement(s)
        self._pop_indent()
        
        for cond_e, body in node.elif_branches:
            ce, _ = self._gen_rvalue(cond_e)
            self._emit(f"}} else if (({ce}) != 0) {{")
            self._push_indent()
            for s in body:
                self._gen_statement(s)
            self._pop_indent()
            
        if node.else_branch:
            self._emit("} else {")
            self._push_indent()
            for s in node.else_branch:
                self._gen_statement(s)
            self._pop_indent()
        self._emit("}")

    def _gen_while(self, node: WhileStatement):
        cond, _ = self._gen_rvalue(node.condition)
        self._emit(f"while (({cond}) != 0) {{")
        self._push_indent()
        for s in node.body:
            self._gen_statement(s)
        self._pop_indent()
        self._emit("}")

    def _gen_for(self, node: ForStatement):
        start, _ = self._gen_rvalue(node.start)
        end, _ = self._gen_rvalue(node.end)
        if node.step:
            step, _ = self._gen_rvalue(node.step)
        else:
            step = "1LL"
        ivar = node.var_name
        self._emit(f"{{ long long {ivar};")
        self._emit(f"  for ({ivar} = (long long)({start}); {ivar} < (long long)({end}); {ivar} += (long long)({step})) {{")
        self._push_indent()
        self.var_types[ivar] = 'long long'
        for s in node.body:
            self._gen_statement(s)
        self._pop_indent()
        self._emit("  }")
        self._emit("}")

    def _gen_return(self, node: ReturnStatement):
        if node.value:
            expr, _ = self._gen_rvalue(node.value)
            self._emit(f"return (long long)({expr});")
        else:
            self._emit("return 0;")
        # NOTE: 不再 raise ReturnValueGen —— 异常会穿透嵌套 if/while/for，
        # 导致未执行 _pop_indent 和未 emit 闭合 }，进而大括号匹配错误、
        # indent 不平衡、后续语句/main 函数错误嵌套到当前函数中。
        # 函数末尾统一 emit 保底 return 0;，C 编译器的 unreachable code 警告不影响正确性。

    def _gen_print(self, node: PrintStatement):
        args = []
        for a in node.args:
            ec, et = self._gen_rvalue(a)
            args.append((ec, et))
        
        for i, (ec, et) in enumerate(args):
            if i > 0:
                self._emit('printf(" ");')
            fmt_map = {
                'long long': '%lld',
                'int': '%d',
                'double': '%.6f',
                'const char*': '%s',
                'char*': '%s',
                'void*': '%p',
            }
            fmt = fmt_map.get(et, '%lld')
            if et in ('const char*', 'char*'):
                self._emit(f'printf("{fmt}", ({ec}) ? ({ec}) : "nil");')
            else:
                self._emit(f'printf("{fmt}", ({et})({ec}));')
        self._emit('printf("\\n");')

    # ---------- 右值表达式：返回 (c_code, c_type) ----------
    def _gen_rvalue(self, expr) -> Tuple[str, str]:
        tname = type(expr).__name__
        m = getattr(self, f'_rv_{tname}', None)
        if m:
            return m(expr)
        raise CodegenError(f"不支持的表达式类型: {tname}", getattr(expr, 'line', 0))

    def _rv_NumberLiteral(self, n: NumberLiteral):
        if isinstance(n.value, float):
            return (repr(n.value), 'double')
        return (repr(n.value) + 'LL', 'long long')

    def _rv_StringLiteral(self, s: StringLiteral):
        return (self._c_string(s.value), 'const char*')

    def _rv_BoolLiteral(self, b: BoolLiteral):
        return ('1' if b.value else '0', 'int')

    def _rv_NilLiteral(self, _n):
        return ('0LL', 'long long')

    def _rv_ListLiteral(self, lst: ListLiteral):
        return ('NULL', 'void*')

    def _rv_Identifier(self, i: Identifier):
        cname, is_global = self._resolve_var(i.name)
        if cname is None:
            raise CodegenError(f"未定义的变量: '{i.name}'", i.line)
        vtype = self.var_types.get(cname, 'long long')
        return (cname, vtype)

    def _rv_UnaryOp(self, u: UnaryOp):
        ec, et = self._gen_rvalue(u.operand)
        if u.op == '-':
            return (f"(-({ec}))", et)
        if u.op == '+':
            return (f"(+({ec}))", et)
        if u.op == 'not':
            return (f"(!({ec}))", 'int')
        raise CodegenError(f"未知一元运算符: {u.op}", u.line)

    def _rv_BinOp(self, b: BinOp):
        lc, lt = self._gen_rvalue(b.left)
        rc, rt = self._gen_rvalue(b.right)
        
        # 字符串拼接
        if b.op == '+' and (lt in ('const char*', 'char*') or rt in ('const char*', 'char*')):
            self._require_function('hs_strcat')
            return (f"hs_strcat(({lc}), ({rc}))", 'char*')
        
        # 字符串重复
        if b.op == '*' and lt in ('const char*', 'char*') and rt in ('long long', 'int'):
            self._require_function('hs_strmul')
            return (f"hs_strmul(({lc}), (long long)({rc}))", 'char*')
        if b.op == '*' and rt in ('const char*', 'char*') and lt in ('long long', 'int'):
            self._require_function('hs_strmul')
            return (f"hs_strmul(({rc}), (long long)({lc}))", 'char*')

        result_type = 'long long'
        if lt == 'double' or rt == 'double':
            result_type = 'double'

        op = b.op
        if op in ('+', '-', '*', '/', '%'):
            if op == '%':
                return (f"((long long)({lc}) % (long long)({rc}))", 'long long')
            if op == '/':
                if result_type == 'double':
                    return (f"((double)({lc}) / (double)({rc}))", 'double')
                return (f"((long long)({lc}) / (long long)({rc}))", 'long long')
            return (f"(({result_type})({lc}) {op} ({result_type})({rc}))", result_type)

        if op in ('==', '!=', '<', '>', '<=', '>='):
            if lt in ('const char*', 'char*') and rt in ('const char*', 'char*'):
                cmp_map = {
                    '==': '== 0', '!=': '!= 0',
                    '<': '< 0', '>': '> 0',
                    '<=': '<= 0', '>=': '>= 0'
                }
                return (f"(strcmp({lc}, {rc}) {cmp_map[op]})", 'int')
            return (f"(({lc}) {op} ({rc}))", 'int')

        if op == 'and':
            return (f"(({lc}) && ({rc}))", 'int')
        if op == 'or':
            return (f"(({lc}) || ({rc}))", 'int')

        raise CodegenError(f"未知二元运算符: {op}", b.line)

    def _rv_FuncCall(self, fc: FuncCall):
        # 内置函数处理
        if fc.name == 'len':
            if fc.args:
                ac, at = self._gen_rvalue(fc.args[0])
                if at in ('const char*', 'char*'):
                    return (f"(long long)strlen({ac})", 'long long')
                if at == 'void*':
                    return ('0LL', 'long long')
            return ('0LL', 'long long')
        if fc.name == 'abs':
            if fc.args:
                ac, at = self._gen_rvalue(fc.args[0])
                if at == 'double':
                    return (f"fabs({ac})", 'double')
                return (f"llabs((long long)({ac}))", 'long long')
            return ('0LL', 'long long')
        if fc.name == 'min' and len(fc.args) >= 2:
            a, ta = self._gen_rvalue(fc.args[0])
            b, tb = self._gen_rvalue(fc.args[1])
            return (f"(({a}) < ({b}) ? ({a}) : ({b}))", ta)
        if fc.name == 'max' and len(fc.args) >= 2:
            a, ta = self._gen_rvalue(fc.args[0])
            b, tb = self._gen_rvalue(fc.args[1])
            return (f"(({a}) > ({b}) ? ({a}) : ({b}))", ta)
        # 用户函数调用
        arg_codes = []
        for a in fc.args:
            ac, _ = self._gen_rvalue(a)
            arg_codes.append(f"(long long)({ac})")
        return (f"hs_f_{fc.name}({', '.join(arg_codes)})", 'long long')

    def _rv_InputCall(self, ic: InputCall):
        tmp = self._new_temp('buf')
        if ic.prompt:
            pc, pt = self._gen_rvalue(ic.prompt)
            self._emit(f'printf("%s", ({pc}) ? ({pc}) : "");')
        self._emit(f'char {tmp}[4096];')
        self._emit(f'if (!fgets({tmp}, sizeof({tmp}), stdin)) {{ {tmp}[0] = 0; }}')
        self._emit(f'{{ size_t _l = strlen({tmp}); if (_l > 0 && {tmp}[_l-1] == \'\\n\') {tmp}[_l-1] = 0; }}')
        tmp2 = self._new_temp('inp')
        self._emit(f'char* {tmp2} = strdup({tmp});')
        return (f"{tmp2}", 'char*')

    def _rv_ListIndex(self, li: ListIndex):
        lc, lt = self._gen_rvalue(li.list_expr)
        ic, _ = self._gen_rvalue(li.index)
        if lt in ('const char*', 'char*'):
            tmp = self._new_temp('ch')
            self._emit(f'char {tmp}[2] = {{ (({lc})[(long long)({ic})]), 0 }};')
            return (f"{tmp}", 'char*')
        return ('0LL', 'long long')

    # ---------- 表达式语句（无返回） ----------
    def _gen_expr(self, expr):
        if isinstance(expr, FuncCall):
            ec, _ = self._rv_FuncCall(expr)
            self._emit(f"(void)({ec})")
        else:
            ec, _ = self._gen_rvalue(expr)
            self._emit(f"(void)({ec})")

    # ---------- 字符串 ----------
    @staticmethod
    def _c_string(s: str) -> str:
        escaped = (s.replace('\\', '\\\\')
                    .replace('\n', '\\n')
                    .replace('\r', '\\r')
                    .replace('\t', '\\t')
                    .replace('"', '\\"')
                    .replace('\0', '\\0'))
        return f'"{escaped}"'


class ReturnValueGen(Exception):
    """生成 return 后提前结束 block"""
    pass
