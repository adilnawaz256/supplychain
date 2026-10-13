from typing import Dict, Any, List, Optional, Iterator
import time
import datetime
from decimal import Decimal
import uuid
from sqlalchemy import create_engine, inspect, text
from backend.app.core.config import settings

def _serialize_value(val: Any) -> Any:
    if isinstance(val, (datetime.date, datetime.datetime)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, uuid.UUID):
        return str(val)
    return val

def _quote_table(table_name: str) -> str:
    """Quote a table name (optionally schema-qualified) as a SQL identifier."""
    parts = [p for p in (table_name or "").strip().split(".") if p]
    if not parts:
        raise ValueError("No source table selected")
    return ".".join('"' + p.replace('"', '""') + '"' for p in parts)

class DirectDBConnector:
    """
    Direct Database Connector (PostgreSQL, SQLite, MySQL).
    Connects to target database credentials, inspects real tables/columns,
    and returns live schema metadata for canonical mapping and data ingestion.
    """
    def __init__(self, host: str = "", port: int = 5432, database: str = "", username: str = "", password: str = "", ssl_mode: str = "disable"):
        self.host = (host or "").strip()
        self.port = int(port) if port else 5432
        self.database = (database or "").strip()
        self.username = (username or "").strip()
        self.password = (password or "").strip()
        self.ssl_mode = ssl_mode
        self.last_error: Optional[str] = None

    def _get_connection_url(self) -> str:
        # If no host is provided, default to the internal application database
        if not self.host:
            return settings.DATABASE_URL

        import urllib.parse
        encoded_user = urllib.parse.quote_plus(self.username) if self.username else ""
        encoded_pass = urllib.parse.quote_plus(self.password) if self.password else ""

        if encoded_user and encoded_pass:
            user_pass = f"{encoded_user}:{encoded_pass}@"
        elif encoded_user:
            user_pass = f"{encoded_user}@"
        else:
            user_pass = ""

        db_name = self.database if self.database else "postgres"
        ssl_suffix = "?sslmode=require" if self.ssl_mode in ["require", "true", "ssl"] else ""
        return f"postgresql://{user_pass}{self.host}:{self.port}/{db_name}{ssl_suffix}"

    def test_connection(self) -> Dict[str, Any]:
        """Attempt real database connection test"""
        start_time = time.time()
        url = self._get_connection_url()
        try:
            connect_args = {"connect_timeout": 5} if "postgresql" in url else {}
            engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1")).scalar()
            latency = int((time.time() - start_time) * 1000)
            return {
                "status": "SUCCESS",
                "message": f"Successfully connected to PostgreSQL database '{self.database or 'postgres'}' at {self.host or 'internal'}:{self.port}",
                "latency_ms": latency,
                "server_version": "PostgreSQL Relational Engine"
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Could not connect to {self.host or 'host'}:{self.port}/{self.database or 'db'}. Details: {str(e)}"
            }

    def discover_tables(self) -> List[Dict[str, Any]]:
        """Dynamically inspect real tables and columns from the database"""
        url = self._get_connection_url()
        try:
            connect_args = {"connect_timeout": 5} if "postgresql" in url else {}
            engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
            inspector = inspect(engine)
            discovered = []
            table_names = inspector.get_table_names()

            with engine.connect() as conn:
                for t_name in table_names:
                    try:
                        count_res = conn.execute(text(f'SELECT COUNT(*) FROM {_quote_table(t_name)}')).scalar()
                    except Exception:
                        count_res = 0
                    columns = [c['name'] for c in inspector.get_columns(t_name)]
                    discovered.append({
                        "table_name": t_name,
                        "table_key": t_name,
                        "record_count": count_res or 0,
                        "columns": columns
                    })
            return discovered
        except Exception as e:
            print(f"DirectDBConnector discovery error: {e}")
            self.last_error = str(e)
            return []

    def preview_data(self, table_key: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Preview live records from connected database table"""
        url = self._get_connection_url()
        try:
            engine = create_engine(url)
            with engine.connect() as conn:
                res = conn.execute(text(f'SELECT * FROM {_quote_table(table_key)} LIMIT :limit'), {"limit": limit})
                rows = []
                for row in res:
                    row_dict = {k: _serialize_value(v) for k, v in dict(row._mapping).items()}
                    rows.append(row_dict)
                return rows
        except Exception as e:
            print(f"DirectDBConnector preview error: {e}")
            return []

    def fetch_records(self, table_name: str, limit: int = 10000, offset: int = 0) -> List[Dict[str, Any]]:
        """Fetch records from the source table. Raises on connection/query errors so callers can report them."""
        url = self._get_connection_url()
        connect_args = {"connect_timeout": 10} if "postgresql" in url else {}
        engine = create_engine(url, connect_args=connect_args)
        try:
            with engine.connect() as conn:
                res = conn.execute(
                    text(f'SELECT * FROM {_quote_table(table_name)} LIMIT :limit OFFSET :offset'),
                    {"limit": limit, "offset": offset}
                )
                return [{k: _serialize_value(v) for k, v in dict(row._mapping).items()} for row in res]
        finally:
            engine.dispose()

    def count_rows(self, table_name: str) -> int:
        url = self._get_connection_url()
        connect_args = {"connect_timeout": 10} if "postgresql" in url else {}
        engine = create_engine(url, connect_args=connect_args)
        try:
            with engine.connect() as conn:
                return int(conn.execute(text(f"SELECT COUNT(*) FROM {_quote_table(table_name)}")).scalar() or 0)
        finally:
            engine.dispose()

    def stream_records(self, table_name: str, batch_size: int = 5000) -> Iterator[List[Dict[str, Any]]]:
        """Yield the whole table in batches from one server-side cursor, so memory stays flat
        and rows are neither skipped nor repeated (unlike LIMIT/OFFSET paging)."""
        url = self._get_connection_url()
        connect_args = {"connect_timeout": 10} if "postgresql" in url else {}
        engine = create_engine(url, connect_args=connect_args)
        try:
            with engine.connect() as conn:
                res = conn.execution_options(stream_results=True, yield_per=batch_size).execute(
                    text(f"SELECT * FROM {_quote_table(table_name)}"))
                while True:
                    rows = res.fetchmany(batch_size)
                    if not rows:
                        break
                    yield [{k: _serialize_value(v) for k, v in dict(r._mapping).items()} for r in rows]
        finally:
            engine.dispose()
