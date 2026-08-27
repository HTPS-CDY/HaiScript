"""
HaiScript 命令历史记录模块
"""
from pathlib import Path
from typing import List, Optional

from haiscript.core.constants import HISTORY_FILE


class HistoryManager:
    """命令历史管理器"""

    def __init__(self, limit: int = 100):
        self.history_file = HISTORY_FILE
        self.limit = limit
        self.history: List[str] = []
        self._load()

    def _load(self):
        """加载历史记录"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = [line.strip() for line in f.readlines()[-self.limit:]]
            except Exception:
                self.history = []

    def _save(self):
        """保存历史记录"""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                for cmd in self.history[-self.limit:]:
                    f.write(cmd + '\n')
        except Exception:
            pass

    def add(self, command: str):
        """添加一条历史记录"""
        if command and command.strip():
            self.history.append(command.strip())
            if len(self.history) > self.limit:
                self.history = self.history[-self.limit:]
            self._save()

    def get_recent(self, count: int = 20) -> List[str]:
        """获取最近N条记录"""
        return self.history[-count:] if self.history else []

    def get_all(self) -> List[str]:
        """获取所有历史记录"""
        return self.history.copy()

    def clear(self):
        """清空历史记录"""
        self.history.clear()
        self._save()
