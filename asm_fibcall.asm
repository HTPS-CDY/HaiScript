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
    str_2: db `fib(5) =`, 0
    str_3: db ` `, 0
    str_4: db `%lld`, 0
    str_5: db ``, 0Ah, ``, 0
    str_6: db `fib(`, 0
    str_7: db `) =`, 0
    str_8: db `done`, 0

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
    lea rcx, [str_1]
    lea rdx, [str_2]
    call printf
    lea rcx, [str_3]
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
    lea rcx, [str_4]
    call printf
    lea rcx, [str_5]
    call printf
    mov rax, 0    ; 0
    push rax
    pop rax    ; vardecl initial value
    mov [rbp-16], rax  ; idx
    .while_start3:
    mov rax, [rbp-16]    ; idx
    push rax
    mov rax, 5    ; 5
    push rax
    pop rdx    ; right
    pop rax    ; left
    cmp rax, rdx
    setl al
    movzx rax, al
    push rax
    pop rax
    test rax, rax
    jz .while_end4
    lea rcx, [str_1]
    lea rdx, [str_6]
    call printf
    lea rcx, [str_3]
    call printf
    mov rax, [rbp-16]    ; idx
    push rax
    pop rdx    ; print value
    lea rcx, [str_4]
    call printf
    lea rcx, [str_3]
    call printf
    lea rcx, [str_1]
    lea rdx, [str_7]
    call printf
    lea rcx, [str_3]
    call printf
    mov rax, [rbp-16]    ; idx
    push rax
    pop rcx    ; arg 1
    mov rax, rsp            ; 保存 rsp（含栈上额外参数）
    and rsp, -16            ; 强制 16 字节对齐
    sub rsp, 32            ; shadow space
    call hs_f_fib
    mov rsp, rax            ; 恢复 rsp（清理 shadow space + 对齐）
    push rax    ; return value
    pop rdx    ; print value
    lea rcx, [str_4]
    call printf
    lea rcx, [str_5]
    call printf
    mov rax, [rbp-16]    ; idx
    push rax
    mov rax, 1    ; 1
    push rax
    pop rdx    ; right
    pop rax    ; left
    add rax, rdx
    push rax
    pop rax    ; assign value
    mov [rbp-16], rax  ; idx
    lea rcx, [str_1]
    lea rdx, [str_8]
    call printf
    lea rcx, [str_5]
    call printf
    jmp .while_start3
    .while_end4:
    jmp .end_if1
    .else2:
    .end_if1:
    xor rax, rax    ; return 0 (fallback)
    leave
    ret

global main
main:
    push rbp
    mov rbp, rsp
    sub rsp, 32    ; shadow space for main
    add rsp, 32    ; restore shadow space
    pop rbp
    xor rcx, rcx    ; exit code 0
    call ExitProcess
    int3    ; safety net (never reached)