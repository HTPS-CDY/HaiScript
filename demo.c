/* HaiScript to C 自动生成代码 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <windows.h>

/* 控制台编码初始化（Windows UTF-8 CP65001） */
static void hs_setup_console_cp(void) {
  SetConsoleOutputCP(65001);
  SetConsoleCP(65001);
}

/* 字符串拼接辅助 */
static char* hs_strcat(const char* a, const char* b) {
  size_t la = strlen(a), lb = strlen(b);
  char* r = malloc(la + lb + 1);
  memcpy(r, a, la); memcpy(r + la, b, lb + 1);
  return r;
}

/* 字符串重复辅助 */
static char* hs_strmul(const char* s, long long n) {
  if (n <= 0) { char* e = malloc(1); e[0] = 0; return e; }
  size_t ls = strlen(s);
  char* r = malloc(ls * n + 1); size_t p = 0;
  for (long long i = 0; i < n; i++) { memcpy(r + p, s, ls); p += ls; }
  r[p] = 0; return r;
}

/* 比较 nil 的占位 */
#define HS_NIL (0LL)

long long hs_f_fib(long long);

static const char* g_name = "HaiScript";
static long long g_version = 1LL;
static double g_pi = 3.14159;
static long long g_is_active = 1;
static long long g_a = 10LL;
static long long g_b = 3LL;
static const char* g_s1 = "Hello";
static const char* g_s2 = "World";
static long long g_score = 85LL;
static void* g_nums = NULL;
static long long g_n = 0LL;
static long long g_sum = 0LL;
static long long g_total = 0LL;
static long long g_idx = 0LL;
static long long g_x = 5LL;
static long long g_y = 12LL;

long long hs_f_fib(long long k) {
  if ((((k) < (2LL))) != 0) {
    return (long long)(k);
  }
  return (long long)(((long long)(hs_f_fib((long long)(((long long)(k) - (long long)(1LL))))) + (long long)(hs_f_fib((long long)(((long long)(k) - (long long)(2LL)))))));
  return 0;
}

int main(void) {
  hs_setup_console_cp();
  printf("%s", ("欢迎使用 ") ? ("欢迎使用 ") : "nil");
  printf(" ");
  printf("%s", (g_name) ? (g_name) : "nil");
  printf(" ");
  printf("%s", (" v") ? (" v") : "nil");
  printf(" ");
  printf("%lld", (long long)(g_version));
  printf("\n");
  printf("%s", ("圆周率近似值: ") ? ("圆周率近似值: ") : "nil");
  printf(" ");
  printf("%.6f", (double)(g_pi));
  printf("\n");
  printf("%lld", (long long)(g_a));
  printf(" ");
  printf("%s", (" + ") ? (" + ") : "nil");
  printf(" ");
  printf("%lld", (long long)(g_b));
  printf(" ");
  printf("%s", (" = ") ? (" = ") : "nil");
  printf(" ");
  printf("%lld", (long long)(((long long)(g_a) + (long long)(g_b))));
  printf("\n");
  printf("%lld", (long long)(g_a));
  printf(" ");
  printf("%s", (" - ") ? (" - ") : "nil");
  printf(" ");
  printf("%lld", (long long)(g_b));
  printf(" ");
  printf("%s", (" = ") ? (" = ") : "nil");
  printf(" ");
  printf("%lld", (long long)(((long long)(g_a) - (long long)(g_b))));
  printf("\n");
  printf("%lld", (long long)(g_a));
  printf(" ");
  printf("%s", (" * ") ? (" * ") : "nil");
  printf(" ");
  printf("%lld", (long long)(g_b));
  printf(" ");
  printf("%s", (" = ") ? (" = ") : "nil");
  printf(" ");
  printf("%lld", (long long)(((long long)(g_a) * (long long)(g_b))));
  printf("\n");
  printf("%lld", (long long)(g_a));
  printf(" ");
  printf("%s", (" / ") ? (" / ") : "nil");
  printf(" ");
  printf("%lld", (long long)(g_b));
  printf(" ");
  printf("%s", (" = ") ? (" = ") : "nil");
  printf(" ");
  printf("%lld", (long long)(((long long)(g_a) / (long long)(g_b))));
  printf("\n");
  printf("%lld", (long long)(g_a));
  printf(" ");
  printf("%s", (" % ") ? (" % ") : "nil");
  printf(" ");
  printf("%lld", (long long)(g_b));
  printf(" ");
  printf("%s", (" = ") ? (" = ") : "nil");
  printf(" ");
  printf("%lld", (long long)(((long long)(g_a) % (long long)(g_b))));
  printf("\n");
  printf("%s", (hs_strcat((hs_strcat((hs_strcat((g_s1), (", "))), (g_s2))), ("!"))) ? (hs_strcat((hs_strcat((hs_strcat((g_s1), (", "))), (g_s2))), ("!"))) : "nil");
  printf("\n");
  printf("%s", (hs_strmul((g_s1), (long long)(3LL))) ? (hs_strmul((g_s1), (long long)(3LL))) : "nil");
  printf("\n");
  if ((((g_score) >= (90LL))) != 0) {
    printf("%s", ("等级: 优秀") ? ("等级: 优秀") : "nil");
    printf("\n");
  } else if ((((g_score) >= (80LL))) != 0) {
    printf("%s", ("等级: 良好") ? ("等级: 良好") : "nil");
    printf("\n");
  } else if ((((g_score) >= (60LL))) != 0) {
    printf("%s", ("等级: 及格") ? ("等级: 及格") : "nil");
    printf("\n");
  } else {
    printf("%s", ("等级: 不及格") ? ("等级: 不及格") : "nil");
    printf("\n");
  }
  printf("%s", ("列表: ") ? ("列表: ") : "nil");
  printf(" ");
  printf("%p", (void*)(g_nums));
  printf("\n");
  printf("%s", ("长度: ") ? ("长度: ") : "nil");
  printf(" ");
  printf("%lld", (long long)(0LL));
  printf("\n");
  printf("%s", ("nums[0]: ") ? ("nums[0]: ") : "nil");
  printf(" ");
  printf("%lld", (long long)(0LL));
  printf("\n");
  while ((((g_n) <= (10LL))) != 0) {
    g_sum = (long long)(((long long)(g_sum) + (long long)(g_n)));
    g_n = (long long)(((long long)(g_n) + (long long)(1LL)));
  }
  printf("%s", ("1 到 10 累加和 (while): ") ? ("1 到 10 累加和 (while): ") : "nil");
  printf(" ");
  printf("%lld", (long long)(g_sum));
  printf("\n");
  { long long i;
    for (i = (long long)(1LL); i < (long long)(11LL); i += (long long)(1LL)) {
    g_total = (long long)(((long long)(g_total) + (long long)(i)));
    }
  }
  printf("%s", ("1 到 10 累加和 (for): ") ? ("1 到 10 累加和 (for): ") : "nil");
  printf(" ");
  printf("%lld", (long long)(g_total));
  printf("\n");
  printf("%s", ("斐波那契前10项:") ? ("斐波那契前10项:") : "nil");
  printf("\n");
  while ((((g_idx) < (10LL))) != 0) {
    printf("%s", ("fib(") ? ("fib(") : "nil");
    printf(" ");
    printf("%lld", (long long)(g_idx));
    printf(" ");
    printf("%s", (") = ") ? (") = ") : "nil");
    printf(" ");
    printf("%lld", (long long)(hs_f_fib((long long)(g_idx))));
    printf("\n");
    g_idx = (long long)(((long long)(g_idx) + (long long)(1LL)));
  }
  if ((((((g_x) > (0LL))) && (((g_y) > (0LL))))) != 0) {
    printf("%s", ("x 和 y 都是正数") ? ("x 和 y 都是正数") : "nil");
    printf("\n");
  }
  if (((!(((g_x) > (g_y))))) != 0) {
    printf("%s", ("x 不大于 y") ? ("x 不大于 y") : "nil");
    printf("\n");
  }
  printf("%s", ("Demo 脚本执行完毕!") ? ("Demo 脚本执行完毕!") : "nil");
  printf("\n");
  return 0;
}
