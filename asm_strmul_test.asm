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
    str_1: db `Hello`, 0
    str_2: db `%lld`, 0
    str_3: db ``, 0Ah, ``, 0

; ---- .text (code) ----
section .text
; char* hs_strmul(const char* s, long long n) — 字符串重复
hs_strmul:
    push rbp
    mov rbp, rsp
    sub rsp, 48
    ; rcx = s, rdx = n
    mov [rbp-8], rcx   ; s
    mov [rbp-16], rdx  ; n
    ; if n <= 0 return empty string
    test rdx, rdx
    jle .strmul_empty
    ; ls = strlen(s)
    sub rsp, 32
    call strlen
    add rsp, 32
    mov [rbp-24], rax  ; ls
    ; total = ls * n + 1
    mov r8, rax
    imul r8, [rbp-16]
    inc r8
    ; r = malloc(total)
    mov rcx, r8
    sub rsp, 32
    call malloc
    add rsp, 32
    mov [rbp-32], rax  ; r
    ; loop: copy s n times
    xor r9, r9         ; offset = 0
.strmul_loop:
    mov rcx, [rbp-32]
    add rcx, r9
    mov rdx, [rbp-8]
    mov r8, [rbp-24]
    sub rsp, 32
    call memcpy
    add rsp, 32
    mov r8, [rbp-24]
    add r9, r8
    mov rax, [rbp-16]
    dec rax
    mov [rbp-16], rax
    test rax, rax
    jg .strmul_loop
    ; null-terminate
    mov rcx, [rbp-32]
    add rcx, r9
    mov byte [rcx], 0
    mov rax, [rbp-32]
    leave
    ret
.strmul_empty:
    mov rcx, 1
    sub rsp, 32
    call malloc
    add rsp, 32
    mov byte [rax], 0
    leave
    ret

global main
main:
    push rbp
    mov rbp, rsp
    sub rsp, 32    ; shadow space for main
    mov rcx, 3    ; count
    lea rdx, [str_1]    ; str
    sub rsp, 32
    call hs_strmul
    add rsp, 32
    push rax
    pop rdx    ; print value
    lea rcx, [str_2]
    call printf
    lea rcx, [str_3]
    call printf
    add rsp, 32    ; restore shadow space
    pop rbp
    xor rcx, rcx    ; exit code 0
    call ExitProcess
    int3    ; safety net (never reached)