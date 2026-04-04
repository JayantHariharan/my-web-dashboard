"""
Database layer for PlayNexus.
Provides BaseRepository for generic CRUD and specific repositories per domain.
Supports SQLite (development) and PostgreSQL (production).
"""

import logging
import sqlite3
from contextlib import contextmanager
from typing import Optional, Dict, Any, List

from ..config import settings

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Base database exception."""

    pass


class ConnectionError(DatabaseError):
    """Database connection error."""

    pass


def configure_sqlite_connection(conn: sqlite3.Connection) -> sqlite3.Connection:
    """Apply SQLite pragmas that are safer for this local runtime environment."""
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = MEMORY")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA temp_store = MEMORY")
    return conn


def get_connection(is_postgres: bool, db_url: str, schema: str = "public"):
    """
    Get a raw database connection.
    Args:
        is_postgres: Whether to use PostgreSQL driver
        db_url: Database connection URL
        schema: PostgreSQL schema to use (sets search_path). Ignored for SQLite.
    Returns:
        DB-API connection object
    """
    try:
        if is_postgres:
            if not db_url or not db_url.startswith(("postgresql://", "postgres://")):
                # Fallback to SQLite if URL is missing/wrong (Render boot safety)
                db_path = settings.database.url.replace("sqlite:///", "")
                conn = sqlite3.connect(db_path)
                return configure_sqlite_connection(conn)

            import psycopg2
            from psycopg2.extras import RealDictCursor

            conn = psycopg2.connect(db_url)
            conn.cursor_factory = RealDictCursor
            # Set search_path to use custom schema (falls back to public)
            with conn.cursor() as cur:
                cur.execute(f"SET search_path TO {schema}, public")
            return conn
        else:
            # SQLite connection
            db_path = db_url.replace("sqlite:///", "")
            conn = sqlite3.connect(db_path)
            return configure_sqlite_connection(conn)
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise ConnectionError(f"Database connection failed: {e}") from e


class BaseRepository:
    """Base repository with generic CRUD operations. Extend for each table."""

    def __init__(self, table_name: str):
        self.table_name = table_name
        self._is_postgres = settings.database.is_postgres
        self._db_url = settings.database.url
        self._db_schema = settings.database.db_schema

    def _get_connection(self):
        """Get a database connection."""
        self._db_url = settings.database.url
        self._db_schema = settings.database.db_schema
        return get_connection(self._is_postgres, self._db_url, self._db_schema)

    @contextmanager
    def get_cursor(self):
        """
        Context manager for database cursor.
        Automatically handles connection, commit, and cleanup.
        """
        conn = self._get_connection()
        cursor = None
        try:
            if self._is_postgres:
                # Check if we actually got a PG connection or a fallback SQLite one
                # Base DB-API doesn't have a standardized 'driver' attribute, 
                # but we can check if it's from sqlite3.
                if isinstance(conn, sqlite3.Connection):
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                else:
                    cursor = conn.cursor()
            else:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database operation failed on {self.table_name}: {e}")
            raise DatabaseError(f"Database error: {e}") from e
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_all(self) -> List[Dict[str, Any]]:
        """Retrieve all records from the table."""
        with self.get_cursor() as cursor:
            cursor.execute(f"SELECT * FROM {self.table_name}")
            rows = cursor.fetchall()
            return [dict(row) for row in rows] if rows else []

    def get_by_id(self, pk_value) -> Optional[Dict[str, Any]]:
        """Retrieve a record by its primary key (id)."""
        with self.get_cursor() as cursor:
            placeholder = "%s" if self._is_postgres else "?"
            cursor.execute(
                f"SELECT * FROM {self.table_name} WHERE id = {placeholder}", (pk_value,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def create(self, data: Dict[str, Any]) -> int:
        """Create a new record."""
        columns = list(data.keys())
        placeholders = ["%s" if self._is_postgres else "?"] * len(columns)
        cols_str = ", ".join(columns)
        placeholders_str = ", ".join(placeholders)
        sql = f"INSERT INTO {self.table_name} ({cols_str}) VALUES ({placeholders_str})"
        with self.get_cursor() as cursor:
            cursor.execute(sql, tuple(data.values()))
            if self._is_postgres:
                # Handle SQLite fallback in PG mode
                if hasattr(cursor, 'lastrowid') and cursor.lastrowid is not None:
                    return cursor.lastrowid
                cursor.execute("SELECT LASTVAL() as id")
                result = cursor.fetchone()
                return result["id"]
            else:
                return cursor.lastrowid

    def update(self, pk_value, data: Dict[str, Any]) -> bool:
        """Update a record by primary key."""
        if not data:
            return False
        set_items = [
            f"{col} = {'%s' if self._is_postgres else '?'}" for col in data.keys()
        ]
        values = list(data.values())
        values.append(pk_value)
        sets_str = ", ".join(set_items)
        placeholder = "%s" if self._is_postgres else "?"
        sql = f"UPDATE {self.table_name} SET {sets_str} WHERE id = {placeholder}"
        with self.get_cursor() as cursor:
            cursor.execute(sql, tuple(values))
            return cursor.rowcount > 0

    def delete(self, pk_value) -> bool:
        """Delete a record by primary key."""
        with self.get_cursor() as cursor:
            placeholder = "%s" if self._is_postgres else "?"
            cursor.execute(
                f"DELETE FROM {self.table_name} WHERE id = {placeholder}", (pk_value,)
            )
            return cursor.rowcount > 0

    def count(self) -> int:
        """Count all records in the table."""
        with self.get_cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) as count FROM {self.table_name}")
            result = cursor.fetchone()
            # Support both dict and tuple access
            try:
                return result["count"]
            except (TypeError, KeyError):
                return result[0]

    def find_one(self, conditions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single record matching conditions."""
        if not conditions:
            raise ValueError("Conditions required")
        where_clauses = []
        values = []
        for col, val in conditions.items():
            placeholder = "%s" if self._is_postgres else "?"
            where_clauses.append(f"{col} = {placeholder}")
            values.append(val)
        where_str = " AND ".join(where_clauses)
        sql = f"SELECT * FROM {self.table_name} WHERE {where_str} LIMIT 1"
        with self.get_cursor() as cursor:
            cursor.execute(sql, tuple(values))
            row = cursor.fetchone()
            return dict(row) if row else None

    def find_many(
        self,
        conditions: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Find multiple records matching conditions."""
        if conditions:
            where_clauses = []
            values = []
            for col, val in conditions.items():
                placeholder = "%s" if self._is_postgres else "?"
                where_clauses.append(f"{col} = {placeholder}")
                values.append(val)
            where_str = " AND ".join(where_clauses)
            sql = f"SELECT * FROM {self.table_name} WHERE {where_str}"
        else:
            sql = f"SELECT * FROM {self.table_name}"
            values = []
        if order_by:
            sql += f" ORDER BY {order_by}"
        with self.get_cursor() as cursor:
            cursor.execute(sql, tuple(values))
            rows = cursor.fetchall()
            return [dict(row) for row in rows] if rows else []

    def delete_where(self, conditions: Dict[str, Any]) -> bool:
        """Delete rows that match the given conditions."""
        if not conditions:
            raise ValueError("Conditions required")
        where_clauses = []
        values = []
        for col, val in conditions.items():
            placeholder = "%s" if self._is_postgres else "?"
            where_clauses.append(f"{col} = {placeholder}")
            values.append(val)
        where_str = " AND ".join(where_clauses)
        sql = f"DELETE FROM {self.table_name} WHERE {where_str}"
        with self.get_cursor() as cursor:
            cursor.execute(sql, tuple(values))
            return cursor.rowcount > 0


class UserRepository(BaseRepository):
    """Repository for user-specific operations."""

    def __init__(self):
        from ..config import settings
        table_name = f"users{settings.database.table_suffix}"
        super().__init__(table_name)

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        return self.find_one({"username": username})

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        return self.get_by_id(user_id)

    def create_user(
        self, username: str, password_hash: str, created_ip: Optional[str] = None
    ) -> int:
        """Create a new user."""
        if self.get_user_by_username(username):
            raise ValueError(f"Username '{username}' already exists")

        data = {"username": username, "password": password_hash}
        if created_ip:
            data["created_ip"] = created_ip

        return self.create(data)

    def update_login_tracking(
        self, username: str, login_ip: Optional[str] = None
    ) -> bool:
        """Update last_login_at and last_login_ip for a user."""
        sets = ["last_login_at = CURRENT_TIMESTAMP"]
        values = []
        placeholder = "%s" if self._is_postgres else "?"
        if login_ip:
            sets.append(f"last_login_ip = {placeholder}")
            values.append(login_ip)
        values.append(username)
        sql = f"UPDATE {self.table_name} SET {', '.join(sets)} WHERE username = {placeholder}"
        with self.get_cursor() as cursor:
            cursor.execute(sql, tuple(values))
            return cursor.rowcount > 0

    def update_password(self, username: str, new_password_hash: str) -> bool:
        """Update user password."""
        placeholder = "%s" if self._is_postgres else "?"
        sql = f"UPDATE {self.table_name} SET password = {placeholder} WHERE username = {placeholder}"
        with self.get_cursor() as cursor:
            cursor.execute(sql, (new_password_hash, username))
            return cursor.rowcount > 0

    def delete_user_by_username(self, username: str) -> bool:
        """Delete a user account by username."""
        return self.delete_where({"username": username})

    def migrate_plain_passwords(self) -> int:
        """Migrate plain-text passwords to bcrypt hashes."""
        migrated_count = 0
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            placeholder = "%s" if self._is_postgres else "?"
            query = f\"\"\"
                SELECT id, username, password
                FROM {self.table_name}
                WHERE password NOT LIKE '$2b$%'
                  AND password NOT LIKE '$2a$%'
                  AND password NOT LIKE '$2y$%'
                  AND password NOT LIKE '$pbkdf2-sha256$%'
            \"\"\"
            cursor.execute(query)
            users = cursor.fetchall()
            if not users:
                cursor.close()
                conn.close()
                return 0
            for user in users:
                user_id, username, plain_password = user[0], user[1], user[2]
                from .security import hash_password
                new_hash = hash_password(plain_password)
                update_sql = f"UPDATE {self.table_name} SET password = {placeholder} WHERE id = {placeholder}"
                cursor.execute(update_sql, (new_hash, user_id))
                migrated_count += 1
            conn.commit()
            cursor.close()
            conn.close()
            return migrated_count
        except Exception:
            if conn:
                conn.rollback()
                conn.close()
            return 0


class UserProfileRepository(BaseRepository):
    """Repository for user profiles."""

    def __init__(self):
        from ..config import settings
        table_name = f"user_profiles{settings.database.table_suffix}"
        super().__init__(table_name)

    def get_profile_by_user_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user profile by user_id."""
        return self.find_one({"user_id": user_id})

    def create_profile(self, user_id: int, **kwargs) -> int:
        """Create a new user profile."""
        data = {"user_id": user_id, "preferences": "{}"}
        data.update({k: v for k, v in kwargs.items() if v is not None})
        return self.create(data)

    def update_profile(self, user_id: int, **kwargs) -> bool:
        """Update user profile."""
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        if not update_data:
            return False
        sets = []
        values = []
        placeholder = "%s" if self._is_postgres else "?"
        for k, v in update_data.items():
            sets.append(f"{k} = {placeholder}")
            values.append(v)
        values.append(user_id)
        sql = f"UPDATE {self.table_name} SET {', '.join(sets)} WHERE user_id = {placeholder}"
        with self.get_cursor() as cursor:
            cursor.execute(sql, tuple(values))
            return cursor.rowcount > 0


# Global repository instances
user_repo = UserRepository()
user_profile_repo = UserProfileRepository()
