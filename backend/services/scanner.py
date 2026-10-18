# services/scanner.py — forwarding shim (deprecated)
#
# Migrated to modules.mod_media.scanner

import warnings
warnings.warn(
    "services.scanner is deprecated, use 'from modules.mod_media import MediaScanner'",
    DeprecationWarning,
    stacklevel=2,
)

from modules.mod_media.scanner import MediaScanner, get_scanner

__all__ = ["MediaScanner", "get_scanner"]
