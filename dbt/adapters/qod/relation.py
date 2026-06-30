from dataclasses import dataclass, field

from dbt.adapters.base.relation import BaseRelation, Policy


@dataclass
class QodQuotePolicy(Policy):
    # DuckDB is case-insensitive for unquoted identifiers and the demo tables are
    # lowercase, so default to NOT quoting (matches `tpch1.customer`, etc.).
    database: bool = False
    schema: bool = False
    identifier: bool = False


@dataclass
class QodIncludePolicy(Policy):
    # Always render the full catalog.schema.identifier. The catalog is the qod
    # tenant-db, which is what the edge's ACL qualifies against and what makes the
    # relation resolve to the shared DuckLake catalog across all pool nodes.
    database: bool = True
    schema: bool = True
    identifier: bool = True


@dataclass(frozen=True, eq=False, repr=False)
class QodRelation(BaseRelation):
    quote_policy: Policy = field(default_factory=QodQuotePolicy)
    include_policy: Policy = field(default_factory=QodIncludePolicy)
    quote_character: str = '"'