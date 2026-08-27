; HaiScript to NASM x86-64 自动生成汇编代码
; target: Windows PE64, NASM win64 format

; ---- extern (C runtime from msvcrt) ----
extern printf
extern ExitProcess
extern fgets
extern stdin
extern strlen
extern strcmp
extern malloc
extern memcpy
extern free

; ---- .data (initialized) ----
section .data
    str_1: db `%s`, 0
    str_2: db `优秀`, 0
    str_3: db ``, 0Ah, ``, 0
    str_4: db `良好`, 0
    str_5: db `sum =`, 0
    str_6: db ` `, 0
    str_7: db `%lld`, 0
    str_8: db `fib(5) =`, 0
    str_9: db `positive`, 0
    str_10: db `done`, 0
    g_score dq 85
    g_n dq 0
    g_sum dq 0
    g_x dq 5

; ---- .text (code) ----
section .text
hs_f_fib:
    push rbp
    mov rbp, rsp
    sub rsp, 48    ; shadow space + locals
    mov [rbp-8], rcx  ; param k
    mov rax, [rbp-8]    ; k
    push rax
    mov rax, 2    ; 2
    push rax
    pop rdx    ; right
    pop rax    ; left
    cmp rax, rdx
    setl al
    movzx rax, al
    push rax
    pop rax
    test rax, rax
    jz .else2
    mov rax, [rbp-8]    ; k
    push rax
    pop rax    ; return value
    leave
    ret
    jmp .end_if1
    .else2:
    .end_if1:
    mov rax, [rbp-8]    ; k
    push rax
    mov rax, 1    ; 1
    push rax
    pop rdx    ; right
    pop rax    ; left
    sub rax, rdx
    push rax
    pop rcx    ; arg 1
    mov rax, rsp            ; 保存 rsp（含栈上额外参数）
    and rsp, -16            ; 强制 16 字节对齐
    sub rsp, 32            ; shadow space
    call hs_f_fib
    mov rsp, rax            ; 恢复 rsp（清理 shadow space + 对齐）
    push rax    ; return value
    mov rax, [rbp-8]    ; k
    push rax
    mov rax, 2    ; 2
    push rax
    pop rdx    ; right
    pop rax    ; left
    sub rax, rdx
    push rax
    pop rcx    ; arg 1
    mov rax, rsp            ; 保存 rsp（含栈上额外参数）
    and rsp, -16            ; 强制 16 字节对齐
    sub rsp, 32            ; shadow space
    call hs_f_fib
    mov rsp, rax            ; 恢复 rsp（清理 shadow space + 对齐）
    push rax    ; return value
    pop rdx    ; right
    pop rax    ; left
    add rax, rdx
    push rax
    pop rax    ; return value
    leave
    ret
    xor rax, rax    ; return 0 (fallback)
    leave
    ret

global main
main:
    push rbp
    mov rbp, rsp
    sub rsp, 32    ; shadow space for main
    mov rax, [g_score]    ; score
    push rax
    mov rax, 90    ; 90
    push rax
    pop rdx    ; right
    pop rax    ; left
    cmp rax, rdx
    setge al
    movzx rax, al
    push rax
    pop rax
    test rax, rax
    jz .else4
    lea rcx, [str_1]
    lea rdx, [str_2]
    call printf
    lea rcx, [str_3]
    call printf
    jmp .end_if3
    .else4:
    mov rax, [g_score]    ; score
    push rax
    mov rax, 80    ; 80
    push rax
    pop rdx    ; right
    pop rax    ; left
    cmp rax, rdx
    setge al
    movzx rax, al
    push rax
    pop rax
    test rax, rax
    jz .elif_else5
    lea rcx, [str_1]
    lea rdx, [str_4]
    call printf
    lea rcx, [str_3]
    call printf
    jmp .end_if3
    .elif_else5:
    .end_if3:
    .while_start6:
    mov rax, [g_n]    ; n
    push rax
    mov rax, 10    ; 10
    push rax
    pop rdx    ; right
    pop rax    ; left
    cmp rax, rdx
    setle al
    movzx rax, al
    push rax
    pop rax
    test rax, rax
    jz .while_end7
    mov rax, [g_sum]    ; sum
    push rax
    mov rax, [g_n]    ; n
    push rax
    pop rdx    ; right
    pop rax    ; left
    add rax, rdx
    push rax
    pop rax    ; assign value
    mov [g_sum], rax  ; sum
    mov rax, [g_n]    ; n
    push rax
    mov rax, 1    ; 1
    push rax
    pop rdx    ; right
    pop rax    ; left
    add rax, rdx
    push rax
    pop rax    ; assign value
    mov [g_n], rax  ; n
    jmp .while_start6
    .while_end7:
    lea rcx, [str_1]
    lea rdx, [str_5]
    call printf
    lea rcx, [str_6]
    call printf
    mov rax, [g_sum]    ; sum
    push rax
    pop rdx    ; print value
    lea rcx, [str_7]
    call printf
    lea rcx, [str_3]
    call printf
    lea rcx, [str_1]
    lea rdx, [str_8]
    call printf
    lea rcx, [str_6]
    call printf
    mov rax, 5    ; 5
    push rax
    pop rcx    ; arg 1
    mov rax, rsp            ; 保存 rsp（含栈上额外参数）
    and rsp, -16            ; 强制 16 字节对齐
    sub rsp, 32            ; shadow space
    call hs_f_fib
    mov rsp, rax            ; 恢复 rsp（清理 shadow space + 对齐）
    push rax    ; return value
    pop rdx    ; print value
    lea rcx, [str_7]
    call printf
    lea rcx, [str_3]
    call printf
    mov rax, [g_x]    ; x
    push rax
    mov rax, 0    ; 0
    push rax
    pop rdx    ; right
    pop rax    ; left
    cmp rax, rdx
    setg al
    movzx rax, al
    push rax
    pop rax
    test rax, rax
    jz .else9
    lea rcx, [str_1]
    lea rdx, [str_9]
    call printf
    lea rcx, [str_3]
    call printf
    jmp .end_if8
    .else9:
    .end_if8:
    lea rcx, [str_1]
    lea rdx, [str_10]
    call printf
    lea rcx, [str_3]
    call printf
    add rsp, 32    ; restore shadow space
    pop rbp
    xor rcx, rcx    ; exit code 0
    call ExitProcess
    int3    ; safety net (never reached)