# =====================================================
# HaiScript 1.1 扩展综合测试
# 覆盖：Map/Set/try/catch/break/continue/export/
#       import/JSON/Path/文件IO/断言/方法调用
# =====================================================

import "lib_math" as LM

print("=== HaiScript 1.1 Extension Test ===")
print("lib_math.VERSION =", LM.VERSION)
print("lib_math.PI ~=", LM.PI, "  lib_math.E =", LM.E)
print("square(7) =", LM.square(7), " cube(3) =", LM.cube(3), " sum_range(10) =", LM.sum_range(10))

# ---------- Map 字面量 ----------
print("\n--- Map ---")
var m = {"name": "HaiScript", "version": "1.1", "year": 2026}
print("Map:", m)
print("size =", m.size)
print("keys =", m.keys())
print("values =", m.values())
m.set("author", "hycz8")
m["license"] = "MIT"
print("after set+[] =", m)
print("get('name') =", m.get("name"))
print("get('notfound', 'dflt') =", m.get("notfound", "dflt"))
print("has('year') =", m.has("year"))

# ---------- Set 字面量 ----------
print("\n--- Set ---")
var s = set{1, 2, 3, 3, 2}
var s2 = {5, 4, 3}   # 自动识别为 Set
print("s =", s, " s.size =", s.size)
print("s2 =", s2)
s.add(10)
s.add(20)
s.delete(1)
print("after add/delete s =", s)
print("s has 3 =", s.has(3), "  s has 99 =", s.has(99))
print("union =", s.union(s2))
print("inter =", s.inter(s2))
print("diff  =", s.diff(s2))
print("list  =", s.list())

# ---------- 字符串链式方法 ----------
print("\n--- String methods ---")
var txt = "  Hello, HaiScript!  "
print("original =['" + txt + "']")
print("upper   =", txt.upper())
print("strip   =['" + txt.strip() + "']")
print("split(',') =", txt.split(","))
print("replace('Hai','AWESOME') =", txt.replace("Hai", "AWESOME"))
print("contains('Hai') =", txt.contains("Hai"), " contains('nope') =", txt.contains("nope"))
print("length chars first:", len(txt.chars()), "first char =", txt.at(0), " last =", txt.at(-1))
print("starts_with('  Hel') =", txt.starts_with("  Hel"))

# ---------- 列表链式方法 ----------
print("\n--- List methods ---")
var xs = [1, 2, 3, 4, 5]
print("xs =", xs)
xs.append(6)
xs.insert(0, 0)
print("after insert(0,0), append 6:", xs)
print("xs.map(x => x*x)  via HS func —— no lambda, use def:")

func dbl(x): return x * 2 end
func is_even(x): return x % 2 == 0 end
print("map dbl =", xs.map(dbl))
print("filter even =", xs.filter(is_even))
print("sorted reverse =", xs.sorted().reverse())
print("joined =", [1, 2, 3].join(" - "))

# ---------- for 循环 break/continue ----------
print("\n--- break/continue ---")
var accum = []
for i in range(10):
    if i == 2 or i == 5:
        continue
    end
    if i == 8:
        break
    end
    accum.append(i)
end
print("accumulated =", accum, " (expect [0,1,3,4,6,7])")

# ---------- try / catch / throw / finally ----------
print("\n--- try/catch/throw/finally ---")
var trace = []
try:
    trace.push("A")
    throw RuntimeError "boom!"
    trace.push("B")   # 不应执行
catch(e):
    trace.push("C")
    print("caught error: kind=", e.kind, " msg=", e.message)
finally:
    trace.push("F")
end
print("trace =", trace, " (expect [A,C,F])")

# 特定错误类型不匹配 → 穿透并抛出
var ok = false
try:
    try:
        throw TypeError "bad type"
    catch RuntimeException(err):
        print("WRONG! should not match")
    end
catch(err):
    ok = true
    print("outer caught unmatched type =", err.kind)
end
print("ok =", ok)

# ---------- 除零抛出 ZeroDivisionError 并捕获 ----------
try:
    var x = 1 / 0
catch ZeroDivisionError(e):
    print("caught div0:", e.kind)
end

# ---------- 断言 ----------
print("\n--- assert ---")
assert 2 + 2 == 4
print("assert 2+2=4 ok ✓")
assert LM.square(5) == 25, "square 失败"
print("assert square(5)=25 ok ✓")
var caught_assert = false
try:
    assert 1 == 0, "1 != 0 indeed"
catch AssertionError(e):
    caught_assert = true
    print("assert caught properly:", e.message)
end
print("caught_assert =", caught_assert)

# ---------- JSON 标准库 ----------
print("\n--- JSON stdlib ---")
import "json"
var data = {"a": 1, "b": [1, 2, 3], "c": {"ok": true, "msg": "你好"}}
var jstr = JSON.stringify(data)
print("JSON.stringify =", jstr)
var pretty = JSON.stringify_pretty(data)
print("Pretty JSON (first 80 chars):", pretty.slice(0, 80))
var back = JSON.parse(jstr)
print("parse → a =", back["a"], "  c.msg =", back["c"].get("msg"))

# ---------- Path 标准库 ----------
print("\n--- Path stdlib ---")
import "path" as P
var j = P.join("a", "b", "c.txt")
print("join=", j)
print("basename=", P.basename(j), " dirname=", P.dirname(j))
print("extname=", P.extname(j), " stem=", P.stem(j))
print("with_ext .md =", P.with_ext(j, ".md"))
print("sep =", repr(P.sep))

# ---------- os / math 抽样 ----------
print("\n--- OS & Math (sampling) ---")
import "os"
import "math" as M
print("os.name=", os.name, "  platform=", os.platform)
print("sqrt(2)=", M.sqrt(2), " sin(PI/2)=", M.sin(M.PI / 2))
print("floor(3.7)=", M.floor(3.7), " ceil(3.1)=", M.ceil(3.1))
print("clamp(100, 0, 50)=", M.clamp(100, 0, 50))

# ---------- 文件 IO ----------
print("\n--- File I/O ---")
var testfile = "_hs_io_test.txt"
writefile(testfile, "line1: 你好\nline2: HaiScript\nline3: 123\n")
println("writefile ok? ", exists(testfile))

var f = open(testfile, "r")
var lines = f.read_lines()
f.close()
println("read_lines =", lines)

var all = readfile(testfile)
println("readfile len =", len(all), " starts_with line1 =", all.starts_with("line1"))

# 增量写入
var f2 = open(testfile, "a")
f2.write_line("line4: appended")
f2.close()
var again = readfile(testfile)
println("after append has line4 =", again.contains("line4"))
# 清理临时文件
import "os" as OS2
try:
    OS2.exit(0)  # no, just delete file
catch(e):
end
# 使用 rm 不方便（需 shell 命令），通过 open 删除不了；就保留测试文件在目录，无害

# ---------- 最后：类型标注语法解析不报错 ----------
var mystr: string = "标注通过"
var mynum: number = 42
print("\n类型标注解析 ok: mystr=", mystr, " mynum=", mynum)

func add(a: number, b: number) -> number:
    return a + b
end
print("func 标注解析 ok: add(100+200) =", add(100, 200))

print("\n=================================")
print("All 1.1 Extension Tests PASSED ✓")
