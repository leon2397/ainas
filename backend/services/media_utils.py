# services/media_utils.py — forwarding shim (deprecated)
#
# Migrated to modules.mod_media.media_utils

import warnings
warnings.warn(
    "services.media_utils is deprecated, use 'from modules.mod_media import MediaFormatHandler'",
    DeprecationWarning,
    stacklevel=2,
)

from modules.mod_media.media_utils import MediaFormatHandler, get_media_handler

__all__ = ["MediaFormatHandler", "get_media_handler"]
