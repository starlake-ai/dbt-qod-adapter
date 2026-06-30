import os

import pytest

# Loads the dbt adapter test project fixtures (creates a temp project + unique
# schema per test class against the target below).
pytest_plugins = ["dbt.tests.fixtures.project"]


def pytest_addoption(parser):
    parser.addoption("--profile", action="store", default="qod", type=str)


@pytest.fixture(scope="class")
def dbt_profile_target():
    """Connection target for the conformance suite.

    Point these at a running qod edge with a tenant-db the test user can create
    schemas in. Defaults match the local TPC-H demo (tenant=acme, db=acme_tpch).
    Override via QOD_* env vars (a .env file is honored via pytest-dotenv).
    """
    return {
        "type": "qod",
        "host": os.getenv("QOD_HOST", "localhost"),
        "port": int(os.getenv("QOD_PORT", "31338")),
        "database": os.getenv("QOD_DATABASE", "acme_tpch"),
        "tenant": os.getenv("QOD_TENANT", "acme"),
        "pool": os.getenv("QOD_POOL", "bi"),
        "username": os.getenv("QOD_USER", "admin"),
        "password": os.getenv("QOD_PASSWORD", "admin"),
        "superuser": os.getenv("QOD_SUPERUSER", "true").lower() == "true",
        "use_tls": os.getenv("QOD_USE_TLS", "true").lower() == "true",
        "tls_skip_verify": os.getenv("QOD_TLS_SKIP_VERIFY", "true").lower() == "true",
        "threads": int(os.getenv("QOD_THREADS", "4")),
    }