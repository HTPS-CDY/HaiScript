# HaiScript v1.2.0

轻量级脚本语言与命令行工具箱。

> **作者**: Yan_Canghai (HTPS-CDY) | **协议**: MIT | **官网**: https://haiscript.netlify.app/

> 直接获取的可执行文件显示的官网无效，此外，推荐自行打包项目，确保功能完整

---

## 🔗 链接

| 项目 | 地址 |
|---|---|
| 官网 | https://haiscript.netlify.app/ |
| 主仓库 | https://github.com/HTPS-CDY/HaiScript |
| 包管理器仓库 (HSLib) | https://github.com/HTPS-CDY/HSLib |

---

## ✨ 特性

- **交互式 Shell 工具箱**：文件、系统、网络、编码命令
- **HaiScript 脚本语言 (.hs)**：类 Python 语法，变量、函数、递归、字符串、列表、Map/Set、异常捕获
- **双后端编译**：C 后端 (GCC) 或 汇编后端 (NASM + lld-link，完全自包含，零外部依赖)
- **标准库**：json / path / os / math / pic（图片）/ touch（外部程序）/ http（内网服务）/ lan（局域网）
- **包管理器 hsinser**：`hsinser install <包名>` 一键安装扩展包（从 HSLib 仓库下载 tar.gz 解压到 lib/）
- **开发工具**：fmt 格式化、typecheck 渐进式类型检查、IR 中间表示 + 常量折叠优化

---

## 🚀 快速开始

### 方式一：直接运行（推荐，无需任何环境）

下载 [haiscript.tar](https://github.com/HTPS-CDY/HaiScript/releases/download/v1.2.0/haiscript.tar)，解压后双击 `haiscript.exe` 即可进入交互式 Shell。
汇编后端（NASM + lld-link + 全部依赖 DLL）已完整嵌入，不需要安装 Python、GCC 或任何其它工具。

> 所有 Releases：https://github.com/HTPS-CDY/HaiScript/releases

### 方式二：源码运行

### 环境要求

- Python 3.10+
- GCC（仅 C 后端需要；汇编后端内置 NASM + lld-link，无需额外安装）

### 安装

```bash
# 克隆仓库
git clone https://github.com/HTPS-CDY/HaiScript.git
cd HaiScript
```

无第三方依赖，纯标准库可运行。

### 进入交互式 Shell

```bash
python -m haiscript.main
```

### 命令行用法

```bash
# 查看帮助
python -m haiscript.main --help

# 执行 HaiScript 脚本 (.hs)
python -m haiscript.main run demo.hs

# IR 优化执行
python -m haiscript.main run demo.hs -O

# 检查脚本语法
python -m haiscript.main check demo.hs

# 静态类型检查（仅警告）
python -m haiscript.main typecheck demo.hs

# 格式化源码
python -m haiscript.main fmt demo.hs -i

# 编译为原生 EXE（C 后端 + GCC）
python -m haiscript.main compile demo.hs output.exe

# 编译为原生 EXE（汇编后端 NASM + lld-link，零外部依赖）
python -m haiscript.main compile demo.hs output.exe --asm --keep-asm

# 检查汇编后端可用性
python -m haiscript.main asm

# 包管理器（HSLib 仓库）
python -m haiscript.main hsinser search mypackage
python -m haiscript.main hsinser install mypackage
python -m haiscript.main hsinser list
python -m haiscript.main hsinser update --all
```

---

## 📄 HaiScript 语法速览 (.hs)

```
# 变量
var name = "HaiScript"
age = 30

# 类型注解（渐进式，仅 typecheck 时警告）
var x: int = 42
func add(a: int, b: int) -> int:
    return a + b
end

# 打印
print("Hello, ", name, " age=", age)

# 条件 + 异常捕获
try:
    if age < 0:
        throw ValueError("年龄不能为负")
    end
catch e:
    print("错误:", e)
end

# 循环：while
var i = 0
var sum = 0
while i <= 100:
    sum = sum + i
    i = i + 1
end

# 循环：for ... in range
for j in range(1, 101):
    sum = sum + j
end

# 递归函数
func fib(n):
    if n < 2:
        return n
    end
    return fib(n-1) + fib(n-2)
end
print("fib(10) =", fib(10))

# 字符串
var s = "Hello"
print(s * 3)                    # HelloHelloHello
print(s + ", World!")
print("长度:", len(s))
print("转字符串:", string(123))  # "123"

# 列表 / Map / Set
var arr = [1, 1, 2, 3, 5, 8]
print(arr[0])

var m = Map({"a": 1, "b": 2})
var s2 = Set([1, 2, 3])

# 模块化
import json
import path
import math
```

---

## 🏗️ 项目结构

```
HaiScript/
├── LICENSE                       # MIT 协议
├── README.md                     # 本文档
├── index.html                    # 官网（可直接部署 Netlify）
├── haiscript/
│   ├── __init__.py               # 版本号
│   ├── main.py                   # 主入口（Shell + CLI 调度）
│   │
│   ├── core/                     # 核心模块
│   │   ├── constants.py          # 项目名、版本、官网、作者、链接
│   │   ├── config.py             # ~/.haiscript/config.json
│   │   ├── security.py           # 运行权限与路径管理
│   │   ├── alias.py              # 别名管理
│   │   └── history.py            # 命令历史
│   │
│   ├── commands/                 # Shell 命令实现
│   │   ├── filesystem.py         # cd/ls/mkdir/touch/rm/cp/mv/find/cat/echo
│   │   ├── system.py             # whoami/hostname/date/time/sysinfo/ps/kill/clear
│   │   ├── network.py            # ping/ipconfig/netstat
│   │   ├── encoding.py           # base64/hex
│   │   └── package.py            # hsinser 包管理器
│   │
│   ├── interpreter/              # HaiScript 解释器（run .hs）
│   │   ├── lexer.py              # 词法分析
│   │   ├── parser.py             # 语法分析 → AST
│   │   └── interpreter.py        # 解释执行 + 标准库加载
│   │
│   ├── compiler_c/               # C 后端
│   │   ├── codegen.py            # AST → C11 源码
│   │   └── gcc_compile.py        # 调用 GCC 编译 EXE（含 UTF-8 编码修复）
│   │
│   ├── asm/                      # 汇编后端（NASM x86-64 → lld-link）
│   │   ├── __init__.py
│   │   ├── asm_codegen.py        # AST → NASM 汇编
│   │   ├── asm_compiler.py       # 调用内部 nasm.exe + lld-link.exe
│   │   ├── nasm.exe              # ✅ 内置汇编器（NASM 2.x）
│   │   ├── lld-link.exe          # ✅ 内置链接器（LLVM lld-link）
│   │   ├── libLLVM-22.dll        # 链接器依赖
│   │   ├── libwinpthread-1.dll
│   │   ├── libstdc++-6.dll
│   │   ├── libgcc_s_seh-1.dll
│   │   ├── libffi-8.dll
│   │   ├── libiconv-2.dll
│   │   ├── libxml2-16.dll
│   │   ├── libzstd.dll
│   │   ├── zlib1.dll
│   │   └── lib/lib{kernel32,msvcrt,user32}.a   # 内部导入库
│   │
│   ├── lib/                      # 标准库头文件 + hsinser 安装目录
│   │   ├── __init__.py
│   │   ├── json.py               # JSON 处理
│   │   ├── path.py               # 路径操作
│   │   ├── os.py                 # 系统操作
│   │   ├── math.py               # 数学函数
│   │   ├── pic.py                # 图片处理
│   │   ├── touch.py              # 外部程序调用
│   │   ├── http.py               # 内网 HTTP 服务
│   │   └── lan.py                # 局域网功能
│   │
│   ├── tools/                    # 开发工具
│   │   ├── formatter.py          # 源码格式化
│   │   ├── type_checker.py       # 渐进式静态类型检查
│   │   └── ir.py                 # IR 中间表示 + 常量折叠优化
│   │
│   └── utils/
│       ├── colors.py             # 极简语义色（6 种）
│       └── helpers.py            # 通用辅助
│
└── ~/.haiscript/                 # 用户数据目录
    ├── config.json               # 用户配置
    ├── aliases.json              # 别名
    ├── history                   # 命令历史
    ├── haiscript.log             # 运行日志
    └── packages.json             # hsinser 已安装包元数据
```

---

## 📦 包管理器 (hsinser)

从 [HSLib 仓库](https://github.com/HTPS-CDY/HSLib) 的 `packages/<包名>/<版本>.tar.gz` 下载扩展包，解压到 `haiscript/lib/<包名>/`。

```
  hsinser install <包名> [版本]    安装包（默认最新版本）
  hsinser list                     列出已安装的包
  hsinser remove <包名>            卸载包
  hsinser search <关键词>          搜索可用包
  hsinser info <包名>              显示包详情
  hsinser update [包名|--all]      更新包
  hsinser versions <包名>          列出可用版本
```

---

## 📝 许可证

MIT © Yan_Canghai (HTPS-CDY) — 详见 [LICENSE](LICENSE)
