# plugins/storage/__init__.py — forwarding shim (deprecated)
#
# Migrated to modules.mod_storage

import warnings
warnings.warn(
    "plugins.storage is deprecated, use 'from modules.mod_storage import LocalStorage'",
    DeprecationWarning,
    stacklevel=2,
)

from modules.mod_storage import LocalStorage, SSHStorage, SMBStorage, NasStorage, CloudStorage
from modules.mod_storage.loader import get_storage, get_storage_status

__all__ = [
    "LocalStorage",
    "SSHStorage",
    "SMBStorage",
    "NasStorage",
    "CloudStorage",
    "get_storage",
    "get_storage_status",
]
