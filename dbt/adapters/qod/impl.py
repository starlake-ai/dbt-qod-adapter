from typing import Optional

from dbt.adapters.sql import SQLAdapter

from dbt.adapters.qod.column import QodColumn
from dbt.adapters.qod.connections import QodConnectionManager
from dbt.adapters.qod.relation import QodRelation


class QodAdapter(SQLAdapter):
    """dbt adapter for the Quack-on-Demand FlightSQL edge (DuckDB dialect)."""

    ConnectionManager = QodConnectionManager
    Relation = QodRelation
    Column = QodColumn

    @classmethod
    def date_function(cls) -> str:
        return "now()"

    @classmethod
    def is_cancelable(cls) -> bool:
        return False

    def valid_incremental_strategies(self):
        # DuckDB/DuckLake: append and delete+insert are safe; both use the default
        # dbt macros over real (non-temp) intermediate relations.
        return ["append", "delete+insert", "microbatch"]

    def debug_query(self) -> None:
        self.execute("select 1 as id")

    @classmethod
    def convert_datetime_type(cls, agate_table, col_idx) -> str:
        return "timestamp"

    @classmethod
    def convert_date_type(cls, agate_table, col_idx) -> str:
        return "date"

    @classmethod
    def convert_time_type(cls, agate_table, col_idx) -> str:
        return "time"

    @classmethod
    def convert_number_type(cls, agate_table, col_idx) -> str:
        import agate

        decimals = agate_table.aggregate(agate.MaxPrecision(col_idx))  # type: ignore
        return "double" if decimals else "bigint"

    @classmethod
    def convert_boolean_type(cls, agate_table, col_idx) -> str:
        return "boolean"

    @classmethod
    def convert_text_type(cls, agate_table, col_idx) -> str:
        return "varchar"

    def timestamp_add_sql(self, add_to: str, number: int = 1, interval: str = "hour") -> str:
        return f"{add_to} + interval '{number} {interval}'"