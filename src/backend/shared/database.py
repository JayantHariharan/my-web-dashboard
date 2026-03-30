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


def get_connection(is_postgres: bool, db_url: str):
    """
    Get a raw database connection.
    Args:
        is_postgres: Whether to use PostgreSQL driver
        db_url: Database connection URL
    Returns:
        DB-API connection object
    """
    try:
        if is_postgres:
            # Import psycopg2 only when needed (PostgreSQL)
            import psycopg2
            from psycopg2.extras import RealDictCursor

            conn = psycopg2.connect(db_url)
            conn.cursor_factory = RealDictCursor
            return conn
        else:
            # SQLite connection
            db_path = db_url.replace("sqlite:///", "")
            return sqlite3.connect(db_path)
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise ConnectionError(f"Database connection failed: {e}") from e


class BaseRepository:
    """Base repository with generic CRUD operations. Extend for each table."""

    def __init__(self, table_name: str):
        self.table_name = table_name
        self._is_postgres = settings.database.is_postgres
        self._db_url = settings.database.url

    def _get_connection(self):
        """Get a database connection."""
        return get_connection(self._is_postgres, self._db_url)

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
                cursor = conn.cursor()
            else:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database operation failed on {self.table_name}: {e}")
            raise DatabaseError(f"Database error: {e}") from e
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def get_all(self) -> List[Dict[str, Any]]:
        """Retrieve all records from the table."""
        with self.get_cursor() as cursor:
            # SAFE: table_name is hardcoded in each repository subclass
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
        """
        Create a new record.
        Args:
            data: Dict of column values
        Returns:
            The new record's primary key
        Raises:
            IntegrityError if unique constraint violated
        """
        columns = list(data.keys())
        placeholders = ["%s" if self._is_postgres else "?"] * len(columns)
        cols_str = ", ".join(columns)
        placeholders_str = ", ".join(placeholders)
        sql = f"INSERT INTO {self.table_name} ({cols_str}) VALUES ({placeholders_str})"
        with self.get_cursor() as cursor:
            cursor.execute(sql, tuple(data.values()))
            if self._is_postgres:
                cursor.execute("SELECT LASTVAL() as id")
                result = cursor.fetchone()
                return result["id"]
            else:
                return cursor.lastrowid

    def update(self, pk_value, data: Dict[str, Any]) -> bool:
        """
        Update a record by primary key.
        Args:
            pk_value: Primary key value
            data: Dict of column values to update
        Returns:
            True if updated, False if not found
        """
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
        """
        Delete a record by primary key.
        Returns:
            True if deleted, False if not found
        """
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
            if self._is_postgres:
                return result["count"]
            else:
                return result[0]

    def find_one(self, conditions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find a single record matching conditions.
        Args:
            conditions: Dict of column=value pairs
        Returns:
            Record dict or None
        """
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
        """
        Find multiple records matching conditions.
        Args:
            conditions: Dict of column=value pairs (optional)
            order_by: Column name to order by (optional)
        Returns:
            List of record dicts
        """
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


class UserRepository(BaseRepository):
    """Repository for user-specific operations."""

    def __init__(self):
        super().__init__("users")

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        return self.find_one({"username": username})

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        return self.get_by_id(user_id)

    def create_user(
        self, username: str, password_hash: str, created_ip: Optional[str] = None
    ) -> int:
        """
        Create a new user.
        Returns the user ID.
        Raises ValueError if username already exists.
        """
        # Optional pre-check for better error message
        if self.get_user_by_username(username):
            raise ValueError(f"Username '{username}' already exists")

        data = {"username": username, "password": password_hash}
        if created_ip:
            data["created_ip"] = created_ip

        return self.create(data)

    def update_login_tracking(
        self, username: str, login_ip: Optional[str] = None
    ) -> bool:
        """
        Update last_login_at and last_login_ip for a user.
        Returns True if updated, False if user not found.
        """
        update_data = {"last_login_at": "CURRENT_TIMESTAMP"}  # Will be used as raw SQL
        if login_ip:
            update_data["last_login_ip"] = login_ip

        # Use raw SQL for timestamp to ensure database sets it
        is_postgres = self._is_postgres
        placeholder = "%s" if is_postgres else "?"
        sets = ["last_login_at = CURRENT_TIMESTAMP"]
        values = []

        if login_ip:
            sets.append(f"last_login_ip = {placeholder}")
            values.append(login_ip)

        values.append(username)
        sql = f"UPDATE users SET {', '.join(sets)} WHERE username = {placeholder}"

        with self.get_cursor() as cursor:
            cursor.execute(sql, tuple(values))
            return cursor.rowcount > 0

    def update_password(self, username: str, new_password_hash: str) -> bool:
        """Update user password."""
        is_postgres = self._is_postgres
        placeholder = "%s" if is_postgres else "?"
        sql = (
            f"UPDATE users SET password = {placeholder} WHERE username = {placeholder}"
        )
        with self.get_cursor() as cursor:
            cursor.execute(sql, (new_password_hash, username))
            return cursor.rowcount > 0

    def migrate_plain_passwords(self) -> int:
        """
        Migrate plain-text passwords to bcrypt hashes (with pepper).
        Returns number of users migrated.
        """
        migrated_count = 0
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            placeholder = "%s" if self._is_postgres else "?"
            query = """
                SELECT id, username, password
                FROM users
                WHERE password NOT LIKE '$2b$%'
                  AND password NOT LIKE '$2a$%'
                  AND password NOT LIKE '$2y$%'
            """
            cursor.execute(query)
            users = cursor.fetchall()

            if not users:
                logger.info("No plain-text passwords found.")
                cursor.close()
                conn.close()
                return 0

            logger.warning(f"Found {len(users)} plain-text passwords. Migrating...")
            for user in users:
                user_id, username, plain_password = user[0], user[1], user[2]
                from .security import hash_password

                new_hash = hash_password(plain_password)
                update_sql = (
                    f"UPDATE users SET password = {placeholder} "
                    f"WHERE id = {placeholder}"
                )
                cursor.execute(update_sql, (new_hash, user_id))
                if cursor.rowcount > 0:
                    migrated_count += 1
                    logger.info(f"Migrated user: {username}")
            conn.commit()
            logger.info(f"Migration complete: {migrated_count} updated.")
            cursor.close()
            conn.close()
            return migrated_count
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Migration error: {e}", exc_info=True)
            raise


class UserProfileRepository(BaseRepository):
    """Repository for user profiles."""

    def __init__(self):
        super().__init__("user_profiles")

    def get_profile_by_user_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user profile by user_id."""
        return self.find_one({"user_id": user_id})

    def create_profile(
        self,
        user_id: int,
        display_name: Optional[str] = None,
        bio: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Create a new user profile."""
        data = {
            "user_id": user_id,
            "display_name": display_name,
            "bio": bio,
            "preferences": preferences or {},
        }
        return self.create(data)

    def update_profile(self, user_id: int, **kwargs) -> bool:
        """Update user profile."""
        update_data = {}
        for key, value in kwargs.items():
            if value is not None:
                update_data[key] = value

        if not update_data:
            return False

        return self.update(
            user_id, update_data
        )  # Assuming user_id = profile id (will adjust later)


# Global repository instances (auth-related only)
user_repo = UserRepository()
user_profile_repo = UserProfileRepository()


def init_database():
    """Legacy function. Use migrator.apply_migrations() instead."""
    logger.warning("init_database() is deprecated. Use migrator.apply_migrations().")
