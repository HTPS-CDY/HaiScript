# 示例用户模块：lib_math.hs
# 演示 export

export PI, E = 2.71828

var VERSION = "1.0.0"
export VERSION

func square(x: number) -> number:
    return x * x
end
export square

func cube(x):
    return x * x * x
end
export cube

func sum_range(n):
    var s = 0
    for i in range(n + 1):
        s = s + i
    end
    return s
end
export sum_range
