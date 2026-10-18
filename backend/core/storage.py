# core/storage.py — forwarding shim (deprecated)
#
# Migrated to modules.mod_storage.base

import warnings
warnings.warn(
    "core.storage is deprecated, use 'from modules.mod_storage import FileStorage'",
    DeprecationWarning,
    stacklevel=2,
)

from modules.mod_storage.base import FileStorage

__all__ = ["FileStorage"]
