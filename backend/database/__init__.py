# database — forwarding shim (deprecated)
#
# All database logic has been migrated to modules.mod_database.
# This file is kept for backward compatibility during transition.
#
# If you see this, update your import to:
#   from modules.mod_database import Database, get_db, db

from modules.mod_database import Database, get_db, db, DATABASE_PATH

__all__ = ["Database", "get_db", "db", "DATABASE_PATH"]
