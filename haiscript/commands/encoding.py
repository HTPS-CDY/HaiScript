"""
HaiScript 编码命令模块
"""
import base64
import re
from typing import List

from haiscript.utils.colors import print_success, print_error, print_info


class EncodingCommands:
    """编码解码命令处理器"""

    def cmd_base64(self, args: List[str]) -> bool:
        """Base64编码/解码: base64 <文本>

        自动判断：如果能解码就解码，否则编码
        """
        if not args:
            print_error("用法: base64 <文本>")
            return False

        text = ' '.join(args).strip()

        # 尝试解码
        try:
            decoded = base64.b64decode(text).decode('utf-8')
            # 判断是否是可读文本
            if all(32 <= ord(c) < 127 or c in '\r\n\t' for c in decoded):
                print_success("解码结果:")
                print(decoded)
                return True
        except Exception:
            pass

        # 执行编码
        try:
            encoded = base64.b64encode(text.encode('utf-8')).decode('utf-8')
            print_success("编码结果:")
            print(encoded)
            return True
        except Exception as e:
            print_error(f"Base64操作失败: {e}")
            return False

    def cmd_hex(self, args: List[str]) -> bool:
        """十六进制编码/解码: hex <文本>"""
        if not args:
            print_error("用法: hex <文本>")
            return False

        text = ' '.join(args).strip()

        # 判断是否是纯十六进制格式
        hex_pattern = re.compile(r'^[0-9a-fA-F\s]+$')
        compact = text.replace(' ', '').replace('\n', '')
        if hex_pattern.match(text) and len(compact) % 2 == 0:
            try:
                decoded = bytes.fromhex(compact).decode('utf-8')
                print_success("解码结果:")
                print(decoded)
                return True
            except Exception:
                # 解码失败，走编码
                pass

        # 执行编码
        try:
            encoded = text.encode('utf-8').hex()
            # 每两个字符加空格
            formatted = ' '.join(encoded[i:i+2] for i in range(0, len(encoded), 2))
            print_success("编码结果:")
            print(formatted)
            return True
        except Exception as e:
            print_error(f"十六进制操作失败: {e}")
            return False
