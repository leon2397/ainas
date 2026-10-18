# core/crypto.py — forwarding shim (deprecated)
#
# Migrated to modules.mod_auth.crypto
# This file forwards all exports for backward compatibility.
#
# Update your import to:
#   from modules.mod_auth import ConfigCrypto, config_crypto

import warnings
warnings.warn(
    "core.crypto is deprecated, use 'from modules.mod_auth import ConfigCrypto'",
    DeprecationWarning,
    stacklevel=2,
)

from modules.mod_auth.crypto import (
    ConfigCrypto,
    config_crypto,
    encrypt_password,
    decrypt_password,
)

__all__ = [
    "ConfigCrypto",
    "config_crypto",
    "encrypt_password",
    "decrypt_password",
]
