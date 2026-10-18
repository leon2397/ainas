# mod_plugins — 插件管理模块

## 职责

插件加载、生命周期管理、插件间通信。

## 对外接口

```python
from modules.mod_plugins import PluginManager, get_plugin_manager

manager = get_plugin_manager()
engine = manager.get_ai_engine('cpu', config)
storage = manager.get_storage('local', config)
```

## PluginManager

| 方法 | 说明 |
|------|------|
| `get_ai_engine(name, config)` | 获取 AI 引擎实例 |
| `get_storage(name, config)` | 获取存储实例 |
| `list_ai_engines()` | 列出可用 AI 引擎 |
| `list_storage()` | 列出可用存储 |
| `register_ai_engine(name, class)` | 注册自定义引擎 |
| `register_storage(name, class)` | 注册自定义存储 |

## 内置插件

- AI: cpu, bm1688, face
- Storage: local, ssh, smb, nas

## 依赖

- `modules.mod_ai`
- `modules.mod_storage`
- `core.logger`
