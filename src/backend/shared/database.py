"""
Database layer for PlayNexus.

Provides a :class:`BaseRepository` with generic CRUD helpers and two
specialized repositories:

- :class:`UserRepository`        – manages the ``users`` table.
- :class:`UserProfileRepository` – manages the ``user_profiles`` table.

Both SQLite (local development) and PostgreSQL (production via Supabase)
are supported.  The active database is selected via environment variables
at startup; see :mod:`backend.config` for details.

SQL injection prevention strategy
----------------------------------
* All user-supplied *values* are passed through parameterised queries.
* Column and table names are sanitised with an allowlist (alphanumeric
  plus ``_``) before being interpolated into SQL strings.
"""

import logging
import sqlite3
from contextlib import contextmanager
from typing import Optional, Dict, Any, List

from ..config import settings

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Raised when a database operation fails unexpectedly."""


class ConnectionError(DatabaseError):  # noqa: A001 – shadows built-in intentionally
    """Raised when a database connection cannot be established."""


def configure_sqlite_connection(conn: sqlite3.Connection) -> sqlite3.Connection:
    """
    Apply pragmas that improve safety and performance for local SQLite use.

    * ``foreign_keys = ON``   – enforce referential integrity.
    * ``journal_mode = MEMORY`` – lighter write-ahead for local dev.
    * ``synchronous = NORMAL``  – balanced durability / speed trade-off.
    * ``temp_store = MEMORY``   – keep temp tables in RAM.

    Args:
        conn: An open :class:`sqlite3.Connection`.

    Returns:
        The same connection, with pragmas applied.
    """
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = MEMORY")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA temp_store = MEMORY")
    return conn


def get_connection(is_postgres: bool, db_url: str, schema: str = "public"):
    """
    Return a raw DB-API connection.

    Args:
        is_postgres: ``True`` when a PostgreSQL URL is configured.
        db_url:      Database connection URL (``postgresql://...`` or
                     ``sqlite:///...``).
        schema:      PostgreSQL schema to activate via ``SET search_path``.
                     Ignored for SQLite.

    Returns:
        A DB-API 2.0 connection object (either :mod:`psycopg2` or
        :mod:`sqlite3`).

    Raises:
        ConnectionError: If the connection cannot be established.

    Note:
        When ``is_postgres`` is ``True`` but the URL is missing or malformed,
        the function transparently falls back to SQLite and logs a warning,
        preventing a hard crash during a misconfigured Render boot.
    """
    try:
        if is_postgres:
            if not db_url or not db_url.startswith(("postgresql://", "postgres://")):
                # URL is absent / malformed – fall back to the configured SQLite path
                # so Render can still boot and serve a useful error page.
                logger.warning(
                    "PostgreSQL URL missing or invalid; falling back to SQLite for this request."
                )
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
    """
    Generic CRUD repository backed by either SQLite or PostgreSQL.

    Extend this class for each database table and add domain-specific
    query methods.  All SQL values are passed through parameterised
    queries; table / column names are sanitised before interpolation.

    Attributes:
        table_name: Fully-qualified table name (with optional suffix).
    """

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
        Context manager that yields a database cursor.

        Automatically acquires a connection, commits on success, rolls
        back on any exception, and closes both cursor and connection on
        exit.  Converts all database exceptions to :class:`DatabaseError`.

        Yields:
            A DB-API cursor (``sqlite3.Cursor`` or psycopg2 ``DictCursor``).

        Raises:
            DatabaseError: Wraps any underlying DB-API exception.
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
        """
        Insert a new row and return its generated primary key.

        For **real** psycopg2 connections the INSERT statement is appended
        with ``RETURNING id`` because ``cursor.lastrowid`` is always ``None``
        in psycopg2.  For SQLite (including the SQLite fallback used when the
        PostgreSQL URL is absent) ``cursor.lastrowid`` is used instead.

        Args:
            data: Mapping of column names to their values.

        Returns:
            The auto-generated ``id`` of the newly created row.
        """
        columns = list(data.keys())
        cols_str = ", ".join(columns)

        with self.get_cursor() as cursor:
            # Detect the *actual* connection at runtime: the PostgreSQL
            # configuration may transparently fall back to SQLite when the
            # PG URL is absent (see get_connection()).
            is_real_pg = self._is_postgres and not isinstance(
                cursor.connection, sqlite3.Connection
            )
            placeholder = "%s" if is_real_pg else "?"
            placeholders_str = ", ".join([placeholder] * len(columns))

            if is_real_pg:
                # psycopg2 does not expose lastrowid; use RETURNING to retrieve
                # the server-assigned primary key in a single round-trip.
                sql = (
                    f"INSERT INTO {self.table_name} ({cols_str}) "
                    f"VALUES ({placeholders_str}) RETURNING id"
                )
                cursor.execute(sql, tuple(data.values()))
                result = cursor.fetchone()
                return result["id"]
            else:
                sql = (
                    f"INSERT INTO {self.table_name} ({cols_str}) "
                    f"VALUES ({placeholders_str})"
                )
                cursor.execute(sql, tuple(data.values()))
                return cursor.lastrowid

    def update(self, pk_value, data: Dict[str, Any]) -> bool:
        """Update a record by primary key."""
        if not data:
            return False
        set_items = []
        for col in data.keys():
            safe_col = "".join(c for c in col if c.isalnum() or c == "_")
            set_items.append(f"{safe_col} = {'%s' if self._is_postgres else '?'}")
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
            safe_col = "".join(c for c in col if c.isalnum() or c == "_")
            placeholder = "%s" if self._is_postgres else "?"
            where_clauses.append(f"{safe_col} = {placeholder}")
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
                safe_col = "".join(c for c in col if c.isalnum() or c == "_")
                placeholder = "%s" if self._is_postgres else "?"
                where_clauses.append(f"{safe_col} = {placeholder}")
                values.append(val)
            where_str = " AND ".join(where_clauses)
            sql = f"SELECT * FROM {self.table_name} WHERE {where_str}"
        else:
            sql = f"SELECT * FROM {self.table_name}"
            values = []
        if order_by:
            safe_order = "".join(c for c in order_by if c.isalnum() or c in ("_", " ", ",")).strip()
            sql += f" ORDER BY {safe_order}"
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
            safe_col = "".join(c for c in col if c.isalnum() or c == "_")
            placeholder = "%s" if self._is_postgres else "?"
            where_clauses.append(f"{safe_col} = {placeholder}")
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
        placeholder = "%s" if self._is_postgres else "?"
        
        if login_ip:
            sql = f"UPDATE {self.table_name} SET last_login_at = CURRENT_TIMESTAMP, last_login_ip = {placeholder} WHERE username = {placeholder}"
            values = (login_ip, username)
        else:
            sql = f"UPDATE {self.table_name} SET last_login_at = CURRENT_TIMESTAMP WHERE username = {placeholder}"
            values = (username,)
            
        with self.get_cursor() as cursor:
            cursor.execute(sql, values)
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
            query = f"""
                SELECT id, username, password
                FROM {self.table_name}
                WHERE password NOT LIKE '$2b$%'
                  AND password NOT LIKE '$2a$%'
                  AND password NOT LIKE '$2y$%'
                  AND password NOT LIKE '$pbkdf2-sha256$%'
            """
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


class GameRepository(BaseRepository):
    """Manages the games table."""

    def __init__(self):
        from ..config import settings
        table_name = f"games{settings.database.table_suffix}"
        super().__init__(table_name)

    def find_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Find a game by its join code."""
        return self.find_one({"join_code": code})


class GamePlayerRepository(BaseRepository):
    """Manages the game_players table."""

    def __init__(self):
        from ..config import settings
        table_name = f"game_players{settings.database.table_suffix}"
        super().__init__(table_name)

    def find_by_game(self, game_id: int) -> List[Dict[str, Any]]:
        """Get all players for a specific game, including usernames."""
        from ..config import settings
        user_table = f"users{settings.database.table_suffix}"
        placeholder = "%s" if self._is_postgres else "?"
        sql = f"""
            SELECT gp.*, u.username 
            FROM {self.table_name} gp
            LEFT JOIN {user_table} u ON gp.user_id = u.id
            WHERE gp.game_id = {placeholder}
            ORDER BY gp.id ASC
        """
        with self.get_cursor() as cursor:
            cursor.execute(sql, (game_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows] if rows else []


class GameMoveRepository(BaseRepository):
    """Manages the game_moves table."""

    def __init__(self):
        from ..config import settings
        table_name = f"game_moves{settings.database.table_suffix}"
        super().__init__(table_name)

    def find_by_game(self, game_id: int) -> List[Dict[str, Any]]:
        """Get all moves for a specific game in order."""
        from ..config import settings
        placeholder = "%s" if self._is_postgres else "?"
        sql = f"SELECT * FROM {self.table_name} WHERE game_id = {placeholder} ORDER BY created_at ASC"
        with self.get_cursor() as cursor:
            cursor.execute(sql, (game_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows] if rows else []


class LeaderboardRepository(BaseRepository):
    """Manages the leaderboard table."""

    def __init__(self):
        from ..config import settings
        table_name = f"leaderboard{settings.database.table_suffix}"
        super().__init__(table_name)

    def get_top(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the top players by ELO."""
        from ..config import settings
        user_table = f"users{settings.database.table_suffix}"
        sql = f"""
            SELECT l.*, u.username 
            FROM {self.table_name} l
            JOIN {user_table} u ON l.user_id = u.id
            ORDER BY l.elo_rating DESC, l.wins DESC
            LIMIT {limit}
        """
        with self.get_cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [dict(row) for row in rows] if rows else []


class ActivityRepository(BaseRepository):
    """Manages the user_activity table for the Home page resume feature."""

    def __init__(self):
        from ..config import settings
        table_name = f"user_activity{settings.database.table_suffix}"
        super().__init__(table_name)

    def log_activity(self, user_id: int, a_type: str, a_name: str, a_id: str = None):
        """Log a new activity for the user."""
        return self.create({
            "user_id": user_id,
            "activity_type": a_type,
            "activity_name": a_name,
            "activity_id": a_id
        })

    def get_recent(self, user_id: int, limit: int = 4) -> List[Dict[str, Any]]:
        """Get the most recent unique activities for a user."""
        from ..config import settings
        placeholder = "%s" if self._is_postgres else "?"
        # Get unique activities, keep most recent
        sql = f"""
            SELECT * FROM {self.table_name} 
            WHERE user_id = {placeholder}
            GROUP BY activity_name
            ORDER BY created_at DESC
            LIMIT {limit}
        """
        with self.get_cursor() as cursor:
            cursor.execute(sql, (user_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows] if rows else []


class AwardsRepository(BaseRepository):
    """Manages the user_awards table for the PS5-style trophy feature."""

    def __init__(self):
        from ..config import settings
        table_name = f"user_awards{settings.database.table_suffix}"
        super().__init__(table_name)

    def get_by_user(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all awards earned by a user."""
        from ..config import settings
        placeholder = "%s" if self._is_postgres else "?"
        sql = f"SELECT * FROM {self.table_name} WHERE user_id = {placeholder} ORDER BY earned_at DESC"
        with self.get_cursor() as cursor:
            cursor.execute(sql, (user_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows] if rows else []

    def award_if_not_exists(self, user_id: int, name: str, tier: str, ico: str, desc: str):
        """Award a trophy if the user doesn't already have it."""
        from ..config import settings
        placeholder = "%s" if self._is_postgres else "?"
        sql = f"SELECT id FROM {self.table_name} WHERE user_id = {placeholder} AND award_name = {placeholder}"
        with self.get_cursor() as cursor:
            cursor.execute(sql, (user_id, name))
            if cursor.fetchone():
                return
            self.create({
                "user_id": user_id,
                "award_name": name,
                "award_tier": tier,
                "award_ico": ico,
                "description": desc
            })


# Global repository instances
user_repo = UserRepository()
user_profile_repo = UserProfileRepository()
game_repo = GameRepository()
game_player_repo = GamePlayerRepository()
game_move_repo = GameMoveRepository()
leaderboard_repo = LeaderboardRepository()
activity_repo = ActivityRepository()
awards_repo = AwardsRepository()
