# services/monitor.py — forwarding shim (deprecated)
#
# Migrated to modules.mod_monitor.monitor

import warnings
warnings.warn(
    "services.monitor is deprecated, use 'from modules.mod_monitor import SystemMonitor'",
    DeprecationWarning,
    stacklevel=2,
)

from modules.mod_monitor.monitor import SystemMonitor, get_monitor

__all__ = ["SystemMonitor", "get_monitor"]
