"""
HaiScript 配置管理模块
"""
import json
from pathlib import Path
from typing import Any, Dict

from haiscript.core.constants import CONFIG_DIR, CONFIG_FILE, DEFAULT_CONFIG


class Config:
    """配置管理类"""

    def __init__(self):
        self.config_path = CONFIG_FILE
        self.data: Dict[str, Any] = DEFAULT_CONFIG.copy()
        self._ensure_config_dir()
        self.load()

    def _ensure_config_dir(self):
        """确保配置目录存在"""
        if not CONFIG_DIR.exists():
            try:
                CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

    def load(self):
        """加载配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                self._merge_config(loaded_data)
            except (json.JSONDecodeError, Exception):
                self._create_default_config()
        else:
            self._create_default_config()

    def _merge_config(self, loaded_data: Dict[str, Any]):
        """合并配置，只保留已知键"""
        for key in DEFAULT_CONFIG.keys():
            if key in loaded_data:
                self.data[key] = loaded_data[key]

    def _create_default_config(self):
        """创建默认配置文件"""
        try:
            self.save()
        except Exception:
            pass

    def save(self):
        """保存配置"""
        try:
            self._ensure_config_dir()
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self.data.get(key, default)

    def set(self, key: str, value: Any):
        """设置配置项"""
        self.data[key] = value
        self.save()

    def __getitem__(self, key: str) -> Any:
        return self.data.get(key)

    def __setitem__(self, key: str, value: Any):
        self.set(key, value)
