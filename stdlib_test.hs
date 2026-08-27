# HaiScript 1.2 新标准库测试

# --- json 文件处理 ---
import "json"

var data = {"name": "HaiScript", "version": 1.2, "tags": ["lang", "tool", "asm"]}
var json_str = json.stringify(data)
print("JSON.stringify:", json_str)

# 写入 JSON 文件
json.save("_test_data.json", data)
print("json.save 完成")

# 读取 JSON 文件
var loaded = json.load("_test_data.json")
print("json.load name:", loaded.name)
print("json.load version:", loaded.version)
print("json.load tags:", loaded.tags)

# --- touch (外部程序) ---
import "touch"

var result = touch.capture("cmd", "/c", "echo HelloFromTouch")
print("touch.capture stdout:", result.stdout)
print("touch.capture code:", result.code)

var found = touch.which("cmd")
print("touch.which cmd:", found)

# --- lan (局域网) ---
import "lan"

var my_ip = lan.ip()
print("lan.ip:", my_ip)

var my_host = lan.hostname()
print("lan.hostname:", my_host)

# 测试端口扫描（本地）
var port_open = lan.scan_port("127.0.0.1", 80, 1)
print("lan.scan_port 127.0.0.1:80:", port_open)

# --- os ---
import "os"

print("os.name:", os.name)
print("os.platform:", os.platform)
print("os.user:", os.user())

# --- math ---
import "math"

print("math.sqrt(16):", math.sqrt(16))
print("math.floor(3.7):", math.floor(3.7))
print("math.ceil(3.2):", math.ceil(3.2))

print("=== HaiScript 1.2 Stdlib Test PASSED ===")
