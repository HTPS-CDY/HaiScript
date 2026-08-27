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
    str_1: db `HaiScript`, 0
    str_2: db `Hello`, 0
    str_3: db `%s`, 0
    str_4: db `欢迎使用 `, 0
    str_5: db ` `, 0
    str_6: db ` v`, 0
    str_7: db `%lld`, 0
    str_8: db ``, 0Ah, ``, 0
    str_9: db ` + `, 0
    str_10: db ` = `, 0
    str_11: db ` / `, 0
    str_12: db ` % `, 0
    g_name dq str_1
    g_version dq 1
    g_a dq 10
    g_b dq 3
    g_s1 dq str_2

; ---- .text (code) ----
section .text
global main
main:
    push rbp
    mov rbp, rsp
    sub rsp, 32    ; shadow space for main
    lea rcx, [str_3]
    lea rdx, [str_4]
    call printf
    lea rcx, [str_5]
    call printf
    mov rax, [g_name]    ; name
    push rax
    pop rdx    ; print value
    lea rcx, [str_3]
    call printf
    lea rcx, [str_5]
    call printf
    lea rcx, [str_3]
    lea rdx, [str_6]
    call printf
    lea rcx, [str_5]
    call printf
    mov rax, [g_version]    ; version
    push rax
    pop rdx    ; print value
    lea rcx, [str_7]
    call printf
    lea rcx, [str_8]
    call printf
    mov rax, [g_a]    ; a
    push rax
    pop rdx    ; print value
    lea rcx, [str_7]
    call printf
    lea rcx, [str_5]
    call printf
    lea rcx, [str_3]
    lea rdx, [str_9]
    call printf
    lea rcx, [str_5]
    call printf
    mov rax, [g_b]    ; b
    push rax
    pop rdx    ; print value
    lea rcx, [str_7]
    call printf
    lea rcx, [str_5]
    call printf
    lea rcx, [str_3]
    lea rdx, [str_10]
    call printf
    lea rcx, [str_5]
    call printf
    mov rax, [g_a]    ; a
    push rax
    mov rax, [g_b]    ; b
    push rax
    pop rdx    ; right
    pop rax    ; left
    add rax, rdx
    push rax
    pop rdx    ; print value
    lea rcx, [str_7]
    call printf
    lea rcx, [str_8]
    call printf
    mov rax, [g_a]    ; a
    push rax
    pop rdx    ; print value
    lea rcx, [str_7]
    call printf
    lea rcx, [str_5]
    call printf
    lea rcx, [str_3]
    lea rdx, [str_11]
    call printf
    lea rcx, [str_5]
    call printf
    mov rax, [g_b]    ; b
    push rax
    pop rdx    ; print value
    lea rcx, [str_7]
    call printf
    lea rcx, [str_5]
    call printf
    lea rcx, [str_3]
    lea rdx, [str_10]
    call printf
    lea rcx, [str_5]
    call printf
    mov rax, [g_a]    ; a
    push rax
    mov rax, [g_b]    ; b
    push rax
    pop rdx    ; right
    pop rax    ; left
    mov rcx, rdx    ; save divisor
    cqo    ; sign-extend rax into rdx:rax
    idiv rcx    ; rdx:rax / rcx → 商 rax
    push rax
    pop rdx    ; print value
    lea rcx, [str_7]
    call printf
    lea rcx, [str_8]
    call printf
    mov rax, [g_a]    ; a
    push rax
    pop rdx    ; print value
    lea rcx, [str_7]
    call printf
    lea rcx, [str_5]
    call printf
    lea rcx, [str_3]
    lea rdx, [str_12]
    call printf
    lea rcx, [str_5]
    call printf
    mov rax, [g_b]    ; b
    push rax
    pop rdx    ; print value
    lea rcx, [str_7]
    call printf
    lea rcx, [str_5]
    call printf
    lea rcx, [str_3]
    lea rdx, [str_10]
    call printf
    lea rcx, [str_5]
    call printf
    mov rax, [g_a]    ; a
    push rax
    mov rax, [g_b]    ; b
    push rax
    pop rdx    ; right
    pop rax    ; left
    mov rcx, rdx    ; save divisor
    cqo    ; sign-extend rax into rdx:rax
    idiv rcx    ; rdx:rax / rcx → 余数 rdx
    mov rax, rdx    ; remainder
    push rax
    pop rdx    ; print value
    lea rcx, [str_7]
    call printf
    lea rcx, [str_8]
    call printf
    mov rax, [g_s1]    ; s1
    push rax
    mov rax, 3    ; 3
    push rax
    pop rdx    ; right
    pop rax    ; left
    imul rax, rdx
    push rax
    pop rdx    ; print value
    lea rcx, [str_3]
    call printf
    lea rcx, [str_8]
    call printf
    add rsp, 32    ; restore shadow space
    pop rbp
    xor rcx, rcx    ; exit code 0
    call ExitProcess
    int3    ; safety net (never reached)