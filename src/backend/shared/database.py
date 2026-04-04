"""
Database layer for PlayNexus.
"""

import logging
import sqlite3
from contextlib import contextmanager
from typing import Optional, Dict, Any, List

from ..config import settings

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    pass


class ConnectionError(DatabaseError):
    pass


def _is_safe_identifier(value: str) -> bool:
    return isinstance(value, str) and value.isidentifier()


def _safe_log_error(message: str):
    """Prevent leaking sensitive DB info."""
    logger.error(message)


def configure_sqlite_connection(conn: sqlite3.Connection) -> sqlite3.Connection:
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = MEMORY")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA temp_store = MEMORY")
    return conn


def get_connection(is_postgres: bool, db_url: str, schema: str = "public"):
    try:
        if is_postgres:
            if not db_url or not db_url.startswith(("postgresql://", "postgres://")):
                db_path = settings.database.url.replace("sqlite:///", "")
                conn = sqlite3.connect(db_path)
                return configure_sqlite_connection(conn)

            import psycopg2
            from psycopg2.extras import RealDictCursor

            conn = psycopg2.connect(db_url, connect_timeout=5)
            conn.cursor_factory = RealDictCursor

            if not _is_safe_identifier(schema):
                raise ValueError("Invalid schema")

            # ✅ safer quoting
            with conn.cursor() as cur:
                cur.execute(f'SET search_path TO "{schema}", public')

            return conn
        else:
            db_path = db_url.replace("sqlite:///", "")
            conn = sqlite3.connect(db_path)
            return configure_sqlite_connection(conn)

    except Exception:
        _safe_log_error("Failed to connect to database")
        raise ConnectionError("Database connection failed")


class BaseRepository:
    def __init__(self, table_name: str):
        if not _is_safe_identifier(table_name):
            raise ValueError("Invalid table name")

        self.table_name = table_name
        self._is_postgres = settings.database.is_postgres
        self._db_url = settings.database.url
        self._db_schema = settings.database.db_schema

    def _get_connection(self):
        return get_connection(self._is_postgres, self._db_url, self._db_schema)

    @contextmanager
    def get_cursor(self):
        conn = self._get_connection()
        cursor = None
        try:
            if self._is_postgres and not isinstance(conn, sqlite3.Connection):
                cursor = conn.cursor()
            else:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

            yield cursor
            conn.commit()

        except Exception:
            if conn:
                conn.rollback()
            _safe_log_error(f"Database operation failed on {self.table_name}")
            raise DatabaseError("Database operation failed")

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def _validate_column(self, col: str):
        if not _is_safe_identifier(col):
            raise ValueError(f"Invalid column name: {col}")
        return col

    def get_all(self) -> List[Dict[str, Any]]:
        with self.get_cursor() as cursor:
            cursor.execute(f"SELECT * FROM {self.table_name}")
            return [dict(row) for row in cursor.fetchall()]

    def get_by_id(self, pk_value) -> Optional[Dict[str, Any]]:
        with self.get_cursor() as cursor:
            placeholder = "%s" if self._is_postgres else "?"
            cursor.execute(
                f"SELECT * FROM {self.table_name} WHERE id = {placeholder}",
                (pk_value,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def create(self, data: Dict[str, Any]) -> int:
        if not data:
            raise ValueError("No data provided")

        columns = [self._validate_column(c) for c in data.keys()]
        placeholders = ["%s" if self._is_postgres else "?"] * len(columns)

        sql = f"INSERT INTO {self.table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"

        with self.get_cursor() as cursor:
            cursor.execute(sql, tuple(data.values()))

            if self._is_postgres:
                cursor.execute("SELECT LASTVAL() as id")
                result = cursor.fetchone()
                return result["id"]
            else:
                return cursor.lastrowid

    def update(self, pk_value, data: Dict[str, Any]) -> bool:
        if not data:
            return False

        placeholder = "%s" if self._is_postgres else "?"
        set_items = []
        values = []

        for col, val in data.items():
            safe_col = self._validate_column(col)
            set_items.append(f"{safe_col} = {placeholder}")
            values.append(val)

        values.append(pk_value)

        sql = f"UPDATE {self.table_name} SET {', '.join(set_items)} WHERE id = {placeholder}"

        with self.get_cursor() as cursor:
            cursor.execute(sql, tuple(values))
            return cursor.rowcount > 0

    def delete(self, pk_value) -> bool:
        with self.get_cursor() as cursor:
            placeholder = "%s" if self._is_postgres else "?"
            cursor.execute(
                f"DELETE FROM {self.table_name} WHERE id = {placeholder}",
                (pk_value,),
            )
            return cursor.rowcount > 0

    def count(self) -> int:
        with self.get_cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) as count FROM {self.table_name}")
            result = cursor.fetchone()
            return result["count"] if isinstance(result, dict) else result[0]

    def find_one(self, conditions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not conditions:
            raise ValueError("Conditions required")

        placeholder = "%s" if self._is_postgres else "?"
        where = []
        values = []

        for col, val in conditions.items():
            safe_col = self._validate_column(col)
            where.append(f"{safe_col} = {placeholder}")
            values.append(val)

        sql = f"SELECT * FROM {self.table_name} WHERE {' AND '.join(where)} LIMIT 1"

        with self.get_cursor() as cursor:
            cursor.execute(sql, tuple(values))
            row = cursor.fetchone()
            return dict(row) if row else None

    def find_many(self, conditions=None, order_by=None):
        placeholder = "%s" if self._is_postgres else "?"
        sql = f"SELECT * FROM {self.table_name}"
        values = []

        if conditions:
            where = []
            for col, val in conditions.items():
                safe_col = self._validate_column(col)
                where.append(f"{safe_col} = {placeholder}")
                values.append(val)
            sql += f" WHERE {' AND '.join(where)}"

        if order_by:
            if not _is_safe_identifier(order_by):
                raise ValueError("Invalid order_by")
            sql += f" ORDER BY {order_by}"

        with self.get_cursor() as cursor:
            cursor.execute(sql, tuple(values))
            return [dict(row) for row in cursor.fetchall()]

    def delete_where(self, conditions: Dict[str, Any]) -> bool:
        if not conditions:
            raise ValueError("Conditions required")

        placeholder = "%s" if self._is_postgres else "?"
        where = []
        values = []

        for col, val in conditions.items():
            safe_col = self._validate_column(col)
            where.append(f"{safe_col} = {placeholder}")
            values.append(val)

        sql = f"DELETE FROM {self.table_name} WHERE {' AND '.join(where)}"

        with self.get_cursor() as cursor:
            cursor.execute(sql, tuple(values))
            return cursor.rowcount > 0


class UserRepository(BaseRepository):
    def __init__(self):
        table_name = f"users{settings.database.table_suffix}"
        super().__init__(table_name)

    def get_user_by_username(self, username: str):
        return self.find_one({"username": username})

    def create_user(self, username, password_hash, created_ip=None):
        if self.get_user_by_username(username):
            raise ValueError("Username already exists")

        data = {"username": username, "password": password_hash}
        if created_ip:
            data["created_ip"] = created_ip

        return self.create(data)

    def migrate_plain_passwords(self) -> int:
        migrated = 0
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    f"SELECT id, password FROM {self.table_name} WHERE password NOT LIKE '$2%'"
                )
                users = cursor.fetchall()

                from .security import hash_password

                for user in users:
                    user_id = user["id"] if isinstance(user, dict) else user[0]
                    plain = user["password"] if isinstance(user, dict) else user[1]

                    new_hash = hash_password(plain)
                    cursor.execute(
                        f"UPDATE {self.table_name} SET password = %s WHERE id = %s",
                        (new_hash, user_id),
                    )
                    migrated += 1

            return migrated

        except Exception:
            _safe_log_error("Password migration failed")
            return 0


class UserProfileRepository(BaseRepository):
    def __init__(self):
        table_name = f"user_profiles{settings.database.table_suffix}"
        super().__init__(table_name)

    def get_profile_by_user_id(self, user_id):
        return self.find_one({"user_id": user_id})


user_repo = UserRepository()
user_profile_repo = UserProfileRepository()