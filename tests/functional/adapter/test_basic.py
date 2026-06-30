"""Standard dbt adapter conformance suite (dbt-tests-adapter).

These exercise the adapter against a LIVE qod edge (they create schemas, models,
seeds, snapshots, and run tests). Run them with a stack up:

    pip install -e '.[test]'
    dbt-qod edge running + TPC-H demo loaded
    pytest tests/functional

Each class subclasses a base from dbt.tests.adapter.basic; the bases supply the
project files and assertions, so passing them is the bar for "behaves like dbt
expects".
"""

from dbt.tests.adapter.basic.test_base import BaseSimpleMaterializations
from dbt.tests.adapter.basic.test_singular_tests import BaseSingularTests
from dbt.tests.adapter.basic.test_singular_tests_ephemeral import (
    BaseSingularTestsEphemeral,
)
from dbt.tests.adapter.basic.test_empty import BaseEmpty
from dbt.tests.adapter.basic.test_ephemeral import BaseEphemeral
from dbt.tests.adapter.basic.test_incremental import (
    BaseIncremental,
    BaseIncrementalNotSchemaChange,
)
from dbt.tests.adapter.basic.test_generic_tests import BaseGenericTests
from dbt.tests.adapter.basic.test_snapshot_check_cols import BaseSnapshotCheckCols
from dbt.tests.adapter.basic.test_snapshot_timestamp import BaseSnapshotTimestamp
from dbt.tests.adapter.basic.test_adapter_methods import BaseAdapterMethod
from dbt.tests.adapter.basic.test_validate_connection import BaseValidateConnection


class TestSimpleMaterializationsQod(BaseSimpleMaterializations):
    pass


class TestSingularTestsQod(BaseSingularTests):
    pass


class TestSingularTestsEphemeralQod(BaseSingularTestsEphemeral):
    pass


class TestEmptyQod(BaseEmpty):
    pass


class TestEphemeralQod(BaseEphemeral):
    pass


class TestIncrementalQod(BaseIncremental):
    pass


class TestIncrementalNotSchemaChangeQod(BaseIncrementalNotSchemaChange):
    pass


class TestGenericTestsQod(BaseGenericTests):
    pass


class TestSnapshotCheckColsQod(BaseSnapshotCheckCols):
    pass


class TestSnapshotTimestampQod(BaseSnapshotTimestamp):
    pass


class TestBaseAdapterMethodQod(BaseAdapterMethod):
    pass


class TestValidateConnectionQod(BaseValidateConnection):
    pass