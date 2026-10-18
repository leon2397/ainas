"""
配置管理器
从 YAML 文件加载配置，支持环境变量覆盖
统一配置入口，替代旧的 config.py Pydantic 层
"""

import os
import yaml
from typing import Any, Dict, Optional
from pathlib import Path

from core.logger import logger


class ConfigManager:
    """
    配置管理器单例

    使用方式：
        from core.config_manager import config
        config.get('auth.token_expire_hours', 24)         # 点号路径
        config.get_int('auth.token_expire_hours', 24)      # 整数
        config.get_bool('auth.enabled', True)              # 布尔
        config.get_list('server.cors_origins', [])         # 列表
        config.get_str('auth.algorithm', 'HS256')           # 字符串
        config['auth.algorithm']                            # 也支持 [] 语法
    """

    _instance: Optional['ConfigManager'] = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """加载所有配置文件"""
        # 从 backend/core/ 向上两级，到项目根目录
        backend_core_dir = Path(__file__).parent                # backend/core/
        project_root = backend_core_dir.parent.parent           # AI-NAS-Media-Manager-V6.0.3/
        config_dir = project_root / "config"

        config_files = [
            "global.yaml",
            "web.yaml",
            "ai_engine.yaml",
            "devices.yaml",
            "cloud.yaml",
            "storage.yaml",
        ]

        for filename in config_files:
            yaml_path = config_dir / filename
            if yaml_path.exists():
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    loaded = yaml.safe_load(f) or {}
                    self._deep_merge(self._config, loaded)
            else:
                logger.warning(f"配置文件不存在: {yaml_path}")

        logger.info(f"配置已加载: {config_dir}")

    def _deep_merge(self, base: dict, override: dict):
        """深度合并字典"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号路径"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def get_int(self, key: str, default: int = 0) -> int:
        value = self.get(key, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def get_str(self, key: str, default: str = '') -> str:
        value = self.get(key, default)
        return str(value) if value is not None else default

    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)

    def get_list(self, key: str, default: list = None) -> list:
        value = self.get(key, default or [])
        return list(value) if isinstance(value, (list, tuple)) else default or []

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    @property
    def all(self) -> Dict[str, Any]:
        return self._config.copy()


# ─────────────────────────────────────────────────────────────────────────────
# AI 配置访问器（兼容 Pydantic 风格嵌套属性）
# 让代码可以写 ai_config.image_classification.model_path
# ─────────────────────────────────────────────────────────────────────────────
class _AICfg:
    """兼容包装器：ai_config.image_classification.model_path"""

    def __init__(self, models_data: dict):
        # models_data 已经是 {'image_classification': {...}, 'face_detection': {...}}
        self._data = models_data or {}

    class _ModelCfg:
        def __init__(self, model_data: dict):
            self._d = model_data or {}

        def __getattr__(self, key):
            return self._d.get(key)

    @property
    def image_classification(self):
        return self._ModelCfg(self._data.get("image_classification", {}))

    @property
    def face_detection(self):
        return self._ModelCfg(self._data.get("face_detection", {}))

    @property
    def video_analysis(self):
        return self._ModelCfg(self._data.get("video_analysis", {}))

    @property
    def cpu_fallback(self):
        return self._ModelCfg(self._data.get("cpu_fallback", {}))


# ─────────────────────────────────────────────────────────────────────────────
# 全局实例（必须先创建 ConfigManager，才能创建 ai_config）
# ─────────────────────────────────────────────────────────────────────────────
config = ConfigManager()                              # 第 1 步：创建配置管理器（加载 YAML）
ai_config = _AICfg(config.get('models', {}))         # 第 2 步：从已加载的配置中提取 AI 部分
ai_config_wrapper = ai_config                         # 兼容旧名称


def get_config() -> ConfigManager:
    """获取配置管理器实例（兼容旧代码）"""
    return config
