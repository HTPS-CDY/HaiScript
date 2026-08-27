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
    str_2: db `World`, 0
    str_3: db `, `, 0
    str_4: db `!`, 0
    str_5: db `%s`, 0
    str_6: db ``, 0Ah, ``, 0
    g_s1 dq str_1
    g_s2 dq str_2

; ---- .text (code) ----
section .text
; char* hs_strcat(const char* a, const char* b) — 字符串拼接
hs_strcat:
    push rbp
    mov rbp, rsp
    sub rsp, 48    ; shadow + locals
    ; rcx = a, rdx = b
    mov [rbp-8], rcx    ; save a
    mov [rbp-16], rdx   ; save b
    ; la = strlen(a)
    sub rsp, 32
    call strlen
    add rsp, 32
    mov [rbp-24], rax   ; la
    ; lb = strlen(b)
    mov rcx, [rbp-16]
    sub rsp, 32
    call strlen
    add rsp, 32
    mov [rbp-32], rax   ; lb
    ; total = la + lb + 1
    mov r8, [rbp-24]
    add r8, rax
    inc r8
    ; r = malloc(total)
    mov rcx, r8
    sub rsp, 32
    call malloc
    add rsp, 32
    mov [rbp-40], rax   ; r
    ; memcpy(r, a, la)
    mov rcx, rax
    mov rdx, [rbp-8]
    mov r8, [rbp-24]
    sub rsp, 32
    call memcpy
    add rsp, 32
    ; memcpy(r+la, b, lb+1)
    mov rcx, [rbp-40]
    add rcx, [rbp-24]
    mov rdx, [rbp-16]
    mov r8, [rbp-32]
    inc r8
    sub rsp, 32
    call memcpy
    add rsp, 32
    ; return r
    mov rax, [rbp-40]
    leave
    ret


global main
main:
    push rbp
    mov rbp, rsp
    sub rsp, 32    ; shadow space for main
    mov rax, [g_s1]    ; s1
    push rax
    lea rax, [str_3]    ; ", ..."
    push rax
    pop rdx    ; right (str)
    pop rcx    ; left (str)
    sub rsp, 32    ; shadow space
    call hs_strcat
    add rsp, 32    ; cleanup shadow
    push rax    ; result string ptr
    mov rax, [g_s2]    ; s2
    push rax
    pop rdx    ; right (str)
    pop rcx    ; left (str)
    sub rsp, 32    ; shadow space
    call hs_strcat
    add rsp, 32    ; cleanup shadow
    push rax    ; result string ptr
    lea rax, [str_4]    ; "!..."
    push rax
    pop rdx    ; right (str)
    pop rcx    ; left (str)
    sub rsp, 32    ; shadow space
    call hs_strcat
    add rsp, 32    ; cleanup shadow
    push rax    ; result string ptr
    pop rdx    ; print value
    lea rcx, [str_5]
    call printf
    lea rcx, [str_6]
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
    lea rcx, [str_5]
    call printf
    lea rcx, [str_6]
    call printf
    add rsp, 32    ; restore shadow space
    pop rbp
    xor rcx, rcx    ; exit code 0
    call ExitProcess
    int3    ; safety net (never reached)