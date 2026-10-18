"""
配置兼容层

⚠️ 已废弃！所有代码应改用：
    from core.config_manager import config, ai_config_wrapper

此文件仅保留用于兼容旧代码，最终将移除。
"""

# 统一入口：重导出 config_manager 中的所有公共接口
from core.config_manager import (
    config,              # ConfigManager 实例，替代旧 Settings
    ai_config_wrapper,  # _AICfg 实例，替代旧 ai_config_wrapper
    get_config,         # get_config() 函数
)

# ─────────────────────────────────────────────────────────────────────────────
# 以下是旧 API 的兼容导出（已废弃，请勿在新代码中使用）
# ─────────────────────────────────────────────────────────────────────────────

# 旧的 raw dict（直接从 YAML 加载的原始数据）
# 现在通过 config_manager 访问，例如：
#   config.get('models.image_classification.model_path')
# 不要直接访问这些 dict：
global_config   = config.get('global', {})
device_config   = config.get('devices', {})
cloud_config    = config.get('cloud', {})
storage_config  = config.get('storage', {})

# 空的 Pydantic Settings（仅用于兼容 import）
# 所有新代码应直接使用 config.get() 系列方法
class Settings:
    pass

settings = Settings()
