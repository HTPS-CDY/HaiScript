"""
HaiScript 别名管理模块
"""
import json
from pathlib import Path
from typing import Dict, Optional

from haiscript.core.constants import ALIAS_FILE, DANGEROUS_PATTERNS
import re


class AliasManager:
    """命令别名管理器"""

    def __init__(self, security_manager=None):
        self.aliases_file = ALIAS_FILE
        self.aliases: Dict[str, str] = {}
        self.security = security_manager
        self._load_aliases()

    def _load_aliases(self):
        """加载别名配置"""
        if self.aliases_file.exists():
            try:
                with open(self.aliases_file, 'r', encoding='utf-8') as f:
                    self.aliases = json.load(f)
            except Exception:
                self.aliases = {}
        self._validate_aliases()

    def _validate_aliases(self):
        """验证已有别名，移除危险别名"""
        if not self.security:
            return
        dangerous = []
        for name, cmd in self.aliases.items():
            is_danger, _ = self.security.check_dangerous_patterns(cmd)
            if is_danger:
                dangerous.append(name)
        for name in dangerous:
            del self.aliases[name]
        if dangerous:
            self._save_aliases()

    def _save_aliases(self):
        """保存别名配置"""
        try:
            self.aliases_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.aliases_file, 'w', encoding='utf-8') as f:
                json.dump(self.aliases, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def add_alias(self, name: str, command: str) -> bool:
        """添加别名（安全检查）"""
        if name in ['alias', 'unalias']:
            return False

        if not name or not name.isidentifier():
            return False

        # 安全检查
        if self.security:
            is_danger, reason = self.security.check_dangerous_patterns(command)
            if is_danger:
                return False

        self.aliases[name] = command
        self._save_aliases()
        return True

    def remove_alias(self, name: str) -> bool:
        """移除别名"""
        if name in self.aliases:
            del self.aliases[name]
            self._save_aliases()
            return True
        return False

    def remove_all(self):
        """移除所有别名"""
        self.aliases.clear()
        self._save_aliases()

    def list_aliases(self) -> Dict[str, str]:
        """列出所有别名"""
        return self.aliases.copy()

    def expand_alias(self, command: str) -> str:
        """展开别名"""
        parts = command.strip().split(maxsplit=1)
        if not parts:
            return command

        cmd_name = parts[0]
        if cmd_name in self.aliases:
            alias_cmd = self.aliases[cmd_name]
            if len(parts) > 1:
                return f"{alias_cmd} {parts[1]}"
            return alias_cmd
        return command
