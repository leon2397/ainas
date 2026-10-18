# database/db.py — forwarding shim (deprecated)
#
# Migrated to modules.mod_database.db
# This file forwards all exports for backward compatibility.
#
# Update your import to:
#   from modules.mod_database import Database, get_db, db

import warnings
warnings.warn(
    "database.db is deprecated, use 'from modules.mod_database import Database, get_db'",
    DeprecationWarning,
    stacklevel=2,
)

from modules.mod_database.db import (
    Database,
    get_db,
    db,
    DATABASE_PATH,
    CREATE_TABLES_SQL,
)

__all__ = [
    "Database",
    "get_db",
    "db",
    "DATABASE_PATH",
    "CREATE_TABLES_SQL",
]
