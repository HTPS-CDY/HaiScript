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
    str_2: db `add(3,4) =`, 0
    str_3: db ` `, 0
    str_4: db `%lld`, 0
    str_5: db ``, 0Ah, ``, 0

; ---- .text (code) ----
section .text
hs_f_add:
    push rbp
    mov rbp, rsp
    sub rsp, 48    ; shadow space + locals
    mov [rbp-8], rcx  ; param a
    mov [rbp-16], rdx  ; param b
    mov rax, [rbp-8]    ; a
    push rax
    mov rax, [rbp-16]    ; b
    push rax
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
    lea rcx, [str_1]
    lea rdx, [str_2]
    call printf
    lea rcx, [str_3]
    call printf
    mov rax, 3    ; 3
    push rax
    pop rcx    ; arg 1
    mov rax, 4    ; 4
    push rax
    pop rdx    ; arg 2
    mov rax, rsp            ; 保存 rsp（含栈上额外参数）
    and rsp, -16            ; 强制 16 字节对齐
    sub rsp, 32            ; shadow space
    call hs_f_add
    mov rsp, rax            ; 恢复 rsp（清理 shadow space + 对齐）
    push rax    ; return value
    pop rdx    ; print value
    lea rcx, [str_4]
    call printf
    lea rcx, [str_5]
    call printf
    add rsp, 32    ; restore shadow space
    pop rbp
    xor rcx, rcx    ; exit code 0
    call ExitProcess
    int3    ; safety net (never reached)