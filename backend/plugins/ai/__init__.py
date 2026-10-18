# plugins/ai/__init__.py — forwarding shim (deprecated)
#
# Migrated to modules.mod_ai
# This file forwards all exports for backward compatibility.

import warnings
warnings.warn(
    "plugins.ai is deprecated, use 'from modules.mod_ai import CPUEngine'",
    DeprecationWarning,
    stacklevel=2,
)

from modules.mod_ai import CPUEngine, create_cpu_engine

__all__ = ["CPUEngine", "create_cpu_engine"]
