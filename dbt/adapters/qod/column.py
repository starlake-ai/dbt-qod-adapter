from dataclasses import dataclass

from dbt.adapters.base.column import Column


@dataclass
class QodColumn(Column):
    """DuckDB-flavored column. DuckDB's type names are largely ANSI, so the base
    Column behavior is reused; this subclass exists for adapter identity and a few
    DuckDB-specific type spellings."""

    @classmethod
    def string_type(cls, size: int) -> str:
        return "varchar"

    def is_string(self) -> bool:
        return self.dtype.lower() in (
            "text",
            "character varying",
            "varchar",
            "string",
            "char",
        )