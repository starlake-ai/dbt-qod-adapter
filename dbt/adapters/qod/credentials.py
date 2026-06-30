from dataclasses import dataclass
from typing import Optional, Tuple

from dbt.adapters.contracts.connection import Credentials


@dataclass
class QodCredentials(Credentials):
    """Profile fields for the Quack-on-Demand FlightSQL edge.

    `database` is the qod tenant-db / DuckLake catalog (e.g. `acme_tpch`) and
    `schema` is the DuckLake schema (e.g. `tpch1`); both are inherited from the
    base Credentials. dbt's three-part relations then render as
    `<database>.<schema>.<identifier>`, which both satisfies the edge's ACL
    qualification and targets the shared DuckLake catalog (visible across all
    nodes of a pool).

    `tenant` and `pool` are the gRPC routing headers the edge requires; the ADBC
    driver forwards them on every RPC including the Basic-auth handshake.
    """

    host: str = "localhost"
    port: int = 31338
    tenant: str = ""
    pool: str = ""
    username: Optional[str] = None
    password: Optional[str] = None
    superuser: bool = False
    use_tls: bool = True
    tls_skip_verify: bool = False

    _ALIASES = {"user": "username", "dbname": "database", "catalog": "database"}

    @property
    def type(self) -> str:
        return "qod"

    @property
    def unique_field(self) -> str:
        # Used by dbt to scope the connection cache; one per edge + tenant-db.
        return f"{self.host}:{self.port}/{self.database}"

    def _connection_keys(self) -> Tuple[str, ...]:
        # Shown by `dbt debug` (values for non-secret keys).
        return (
            "host",
            "port",
            "database",
            "schema",
            "tenant",
            "pool",
            "username",
            "superuser",
            "use_tls",
            "tls_skip_verify",
        )