from dbt.adapters.base import AdapterPlugin

from dbt.adapters.qod.connections import QodConnectionManager
from dbt.adapters.qod.credentials import QodCredentials
from dbt.adapters.qod.impl import QodAdapter
from dbt.include import qod

Plugin = AdapterPlugin(
    adapter=QodAdapter,  # type: ignore[arg-type]
    credentials=QodCredentials,
    include_path=qod.PACKAGE_PATH,
)

__all__ = ["QodAdapter", "QodConnectionManager", "QodCredentials", "Plugin"]