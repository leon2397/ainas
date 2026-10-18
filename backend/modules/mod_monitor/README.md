# mod_monitor — 系统监控模块

## 职责

系统资源监控、健康检查、性能指标收集。

## 对外接口

```python
from modules.mod_monitor import SystemMonitor, get_system_status
```

## SystemMonitor

| 方法 | 说明 |
|------|------|
| `get_cpu_usage()` | CPU 使用率 |
| `get_memory_usage()` | 内存使用率 |
| `get_disk_usage(path)` | 磁盘使用率 |
| `get_network_io()` | 网络 IO |
| `get_system_info()` | 系统信息 |

## 依赖

- `core.logger`
- `psutil`
