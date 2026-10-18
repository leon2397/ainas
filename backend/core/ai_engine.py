# core/ai_engine.py — forwarding shim (deprecated)
#
# Migrated to modules.mod_ai.base
# This file forwards all exports for backward compatibility.

import warnings
warnings.warn(
    "core.ai_engine is deprecated, use 'from modules.mod_ai import AIEngine'",
    DeprecationWarning,
    stacklevel=2,
)

from modules.mod_ai.base import AIEngine

__all__ = ["AIEngine"]
