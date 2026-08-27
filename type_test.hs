var n: int = 42
var pi: float = 3.14
var name: string = "HaiScript"
var flag: bool = true
var bad_int: int = "oops"
var bad_str: string = 123
var x = 999
var nums: list<int> = [1, 2, 3]
var m: map<string, int> = {"a": 1, "b": 2}
var s: set<int> = set{1, 2, 3}
func add(a: int, b: int) -> int:
    return a + b
end
func bad_ret() -> int:
    return "not an int"
end
func double(n: int) -> int:
    return n * 2
end
var r1 = add(1, 2)
print("add(1,2) = " + string(r1))
var r2 = double("abc")
