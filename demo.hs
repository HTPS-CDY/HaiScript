# HaiScript 示例脚本: demo.hs
# 测试基本语法、变量、条件、循环、函数、输入输出

# 1. 变量
var name = "HaiScript"
var version = 1
var pi = 3.14159
var is_active = true

print("欢迎使用 ", name, " v", version)
print("圆周率近似值: ", pi)

# 2. 算术
var a = 10
var b = 3
print(a, " + ", b, " = ", a + b)
print(a, " - ", b, " = ", a - b)
print(a, " * ", b, " = ", a * b)
print(a, " / ", b, " = ", a / b)
print(a, " % ", b, " = ", a % b)

# 3. 字符串
var s1 = "Hello"
var s2 = "World"
print(s1 + ", " + s2 + "!")
print(s1 * 3)

# 4. 条件判断
var score = 85
if score >= 90:
    print("等级: 优秀")
elif score >= 80:
    print("等级: 良好")
elif score >= 60:
    print("等级: 及格")
else:
    print("等级: 不及格")
end

# 5. 列表
var nums = [1, 2, 3, 4, 5]
print("列表: ", nums)
print("长度: ", len(nums))
print("nums[0]: ", nums[0])

# 6. while 循环
var n = 0
var sum = 0
while n <= 10:
    sum = sum + n
    n = n + 1
end
print("1 到 10 累加和 (while): ", sum)

# 7. for 循环
var total = 0
for i in range(1, 11):
    total = total + i
end
print("1 到 10 累加和 (for): ", total)

# 8. 函数
func fib(k):
    if k < 2:
        return k
    end
    return fib(k - 1) + fib(k - 2)
end

print("斐波那契前10项:")
var idx = 0
while idx < 10:
    print("fib(", idx, ") = ", fib(idx))
    idx = idx + 1
end

# 9. 逻辑运算
var x = 5
var y = 12
if x > 0 and y > 0:
    print("x 和 y 都是正数")
end
if not (x > y):
    print("x 不大于 y")
end

# 10. 完成
print("Demo 脚本执行完毕!")
