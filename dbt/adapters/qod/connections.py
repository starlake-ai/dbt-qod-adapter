from contextlib import contextmanager
from typing import Any, ContextManager, Optional

import adbc_driver_flightsql.dbapi as flight_sql
from adbc_driver_flightsql import DatabaseOptions

from dbt.adapters.contracts.connection import (
    AdapterResponse,
    Connection,
    ConnectionState,
)
from dbt.adapters.events.logging import AdapterLogger
from dbt.adapters.sql import SQLConnectionManager
from dbt_common.exceptions import DbtRuntimeError

from dbt.adapters.qod.credentials import QodCredentials

logger = AdapterLogger("qod")

# Substring of the benign ADBC error raised when an update-count statement
# (DROP / INSERT / UPDATE / DELETE) advertises a `Count` FlightInfo schema but
# returns an empty stream. The statement has still executed.
_INCONSISTENT_SCHEMA = "inconsistent schema"


class QodCursor:
    """DBAPI cursor wrapper that forces server-side execution.

    The qod edge runs a statement on `do_get` (fetch), not at prepare, so DDL/DML
    only takes effect once the result is pulled. We fetch eagerly into a buffer on
    `execute()` and serve dbt's later `fetch*` calls from it. SELECTs are buffered
    the same way (dbt materializes them to agate tables anyway). ACL denials raise
    at prepare (inside `execute`) and propagate.
    """

    def __init__(self, cursor: Any) -> None:
        self._cursor = cursor
        self._buffer: list = []
        self._pos = 0

    def execute(self, sql: str, bindings: Optional[Any] = None) -> None:
        self._pos = 0
        if bindings is None:
            self._cursor.execute(sql)
        else:
            self._cursor.execute(sql, bindings)
        try:
            self._buffer = self._cursor.fetchall()
        except Exception as e:  # noqa: BLE001
            if _INCONSISTENT_SCHEMA in str(e):
                self._buffer = []  # update-count statement; it still ran
            else:
                raise

    @property
    def description(self):
        return self._cursor.description

    @property
    def rowcount(self) -> int:
        try:
            rc = self._cursor.rowcount
            return rc if rc is not None else -1
        except Exception:  # noqa: BLE001
            return -1

    def fetchone(self):
        if self._pos >= len(self._buffer):
            return None
        row = self._buffer[self._pos]
        self._pos += 1
        return row

    def fetchmany(self, size: int = 1):
        chunk = self._buffer[self._pos : self._pos + size]
        self._pos += len(chunk)
        return chunk

    def fetchall(self):
        rest = self._buffer[self._pos :]
        self._pos = len(self._buffer)
        return rest

    def close(self) -> None:
        try:
            self._cursor.close()
        except Exception:  # noqa: BLE001
            pass


class QodConnectionHandle:
    """Minimal DBAPI connection wrapper around an ADBC FlightSQL connection."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def cursor(self) -> QodCursor:
        return QodCursor(self._conn.cursor())

    def cancel(self) -> None:
        pass

    def commit(self) -> None:
        pass  # edge is autocommit

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:  # noqa: BLE001
            pass


class QodConnectionManager(SQLConnectionManager):
    TYPE = "qod"

    @classmethod
    def open(cls, connection: Connection) -> Connection:
        if connection.state == ConnectionState.OPEN:
            logger.debug("Connection is already open, skipping open.")
            return connection

        creds: QodCredentials = connection.credentials
        scheme = "tls" if creds.use_tls else "tcp"
        uri = f"grpc+{scheme}://{creds.host}:{creds.port}"

        header = DatabaseOptions.RPC_CALL_HEADER_PREFIX.value
        db_kwargs = {
            header + "tenant": str(creds.tenant),
            header + "pool": str(creds.pool),
        }
        if creds.username:
            db_kwargs["username"] = str(creds.username)
        if creds.password:
            db_kwargs["password"] = str(creds.password)
        if creds.use_tls and creds.tls_skip_verify:
            db_kwargs[DatabaseOptions.TLS_SKIP_VERIFY.value] = "true"
        if creds.superuser:
            db_kwargs[header + "superuser"] = "true"

        try:
            conn = flight_sql.connect(uri=uri, db_kwargs=db_kwargs)
        except Exception as e:  # noqa: BLE001
            logger.debug(f"Error connecting to qod edge at {uri}: {e}")
            connection.handle = None
            connection.state = ConnectionState.FAIL
            raise DbtRuntimeError(f"Could not connect to qod edge at {uri}: {e}") from e

        connection.handle = QodConnectionHandle(conn)
        connection.state = ConnectionState.OPEN
        return connection

    @contextmanager
    def exception_handler(self, sql: str) -> ContextManager:  # type: ignore[override]
        try:
            yield
        except DbtRuntimeError:
            raise
        except Exception as e:  # noqa: BLE001
            logger.debug(f"Error running SQL: {sql}")
            raise DbtRuntimeError(str(e)) from e

    def cancel(self, connection: Connection) -> None:
        # FlightSQL statements run server-side per-call; nothing to cancel here.
        pass

    @classmethod
    def get_response(cls, cursor: Any) -> AdapterResponse:
        rows = getattr(cursor, "rowcount", -1)
        rows = rows if rows is not None else -1
        return AdapterResponse(_message="OK", rows_affected=rows)

    @classmethod
    def data_type_code_to_name(cls, type_code) -> str:
        """Map a result column's type to a DuckDB SQL type name.

        The ADBC FlightSQL driver reports `cursor.description` type codes as
        pyarrow DataType objects (used by dbt for snapshots / schema inference).
        """
        import pyarrow as pa

        t = type_code
        if not isinstance(t, pa.DataType):
            return str(t).upper()
        if pa.types.is_boolean(t):
            return "BOOLEAN"
        if pa.types.is_decimal(t):
            return f"DECIMAL({t.precision},{t.scale})"
        if pa.types.is_integer(t):
            return "BIGINT"
        if pa.types.is_floating(t):
            return "DOUBLE"
        if pa.types.is_timestamp(t):
            return "TIMESTAMP"
        if pa.types.is_date(t):
            return "DATE"
        if pa.types.is_time(t):
            return "TIME"
        if pa.types.is_string(t) or pa.types.is_large_string(t):
            return "VARCHAR"
        if pa.types.is_binary(t) or pa.types.is_large_binary(t):
            return "BLOB"
        return str(t).upper()

    # The edge is autocommit and statements may route across pool nodes, so never
    # emit BEGIN / COMMIT (they would be node-local and meaningless).
    def add_begin_query(self):
        pass

    def add_commit_query(self):
        pass

    def begin(self):
        connection = self.get_thread_connection()
        connection.transaction_open = True
        return connection

    def commit(self):
        connection = self.get_thread_connection()
        connection.transaction_open = False
        return connection