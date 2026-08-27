# 简化编译测试脚本，仅使用目前支持的特性
var a = 3
var b = 7
print("a + b = ", a + b)
print("a * b = ", a * b)

var i = 0
var s = 0
while i <= 10:
    s = s + i
    i = i + 1
end
print("sum 1..10 = ", s)

func square(x):
    return x * x
end

print("square(9) = ", square(9))

# 条件
var score = 88
if score >= 90:
    print("Excellent")
elif score >= 80:
    print("Good")
else:
    print("Pass")
end

print("Compile test PASSED!")
