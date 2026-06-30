# dbt-qod

A [dbt](https://www.getdbt.com/) adapter for the
[Quack-on-Demand](https://github.com/starlake-ai/quack-on-demand) FlightSQL edge.

qod is a multi-tenant Arrow Flight SQL gateway in front of DuckDB Quack + DuckLake.
`dbt-qod` lets dbt build models, seeds, snapshots, and tests against it over the
Arrow ADBC FlightSQL driver, with the qod tenant/pool routing and RBAC applied.

Verified end-to-end (views, table, incremental, seed, snapshot, tests) against a
live edge, and the full `dbt-tests-adapter` conformance suite passes (12/12) - see
[`examples/jaffle_tpch/RUN_REPORT.md`](examples/jaffle_tpch/RUN_REPORT.md).

## Install

```bash
pip install dbt-core dbt-qod      # dbt-qod from this checkout: pip install -e .
```

Requires Python 3.10-3.13 (dbt-core does not yet support 3.14).

## Profile

```yaml
# ~/.dbt/profiles.yml
my_project:
  target: dev
  outputs:
    dev:
      type: qod
      host: localhost
      port: 31338
      database: acme_tpch     # qod tenant-db / DuckLake catalog
      schema: dbt_jaffle      # where dbt writes models
      tenant: acme            # gRPC routing header
      pool: bi                # gRPC routing header
      username: admin
      password: admin
      superuser: true         # optional; system-realm login
      use_tls: true           # grpc+tls (default)
      tls_skip_verify: true   # self-signed dev cert
      threads: 4
```

`dbt init` is supported too (a `profile_template.yml` ships with the adapter).

## Supported

| dbt feature | status |
| --- | --- |
| `view` / `table` materializations | yes |
| `incremental` (append, delete+insert) | yes |
| `seed` | yes |
| `snapshot` (timestamp / check) | yes |
| generic tests, sources, refs | yes |
| `dbt docs generate` (catalog) | yes |

## How it works

The backend SQL dialect is DuckDB, so the adapter reuses dbt's default macros and
overrides only the DuckDB/Flight specifics. Three design decisions matter:

1. **`database` = tenant-db, `schema` = DuckLake schema.** dbt's three-part
   relations render as `<database>.<schema>.<identifier>`
   (e.g. `acme_tpch.dbt_jaffle.stg_customer`). That both satisfies the edge's ACL
   qualification and targets the shared DuckLake catalog, so objects are visible
   across every node of a pool.
2. **No TEMP intermediates.** dbt's table/incremental/snapshot flows build
   intermediate relations. DuckDB `TEMPORARY` tables are node-local and would break
   across a multi-node pool, so the adapter materializes intermediates as real,
   uniquely-suffixed DuckLake tables (visible everywhere) and drops them after.
3. **Eager execution in the connection manager.** The qod edge executes a statement
   on `do_get` (fetch), not at prepare, so the ADBC cursor is wrapped to pull the
   result and force execution of DDL/DML. Update-count statements (DROP/INSERT/...)
   return an empty stream against a `Count` schema, which ADBC flags as
   `inconsistent schema`; that one case is treated as benign. ACL denials surface
   earlier (at prepare) and propagate as dbt errors.

Other adapter notes:

- The edge does not implement parameter-bound statements, so `dbt seed` inlines
  literal values instead of using `%s` bindings.
- DuckDB exposes a single unqualified `information_schema` spanning all catalogs;
  metadata macros filter by `catalog_name` / `table_catalog` rather than qualifying
  the path.

## Example project

[`examples/jaffle_tpch`](examples/jaffle_tpch) is a runnable project (sources over
`tpch1`, staging views, a mart table, an incremental model, a seed, a snapshot, and
tests). With a qod stack up and TPC-H loaded:

```bash
cd examples/jaffle_tpch
dbt build --full-refresh --profiles-dir .
```

## Layout

```
dbt/adapters/qod/    credentials, connections (ADBC), relation, column, impl, Plugin
dbt/include/qod/     dbt_project.yml, profile_template.yml, macros/ (DuckDB dialect)
examples/jaffle_tpch/  runnable demo project + RUN_REPORT.md
```

## Development & publishing

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e '.[test]'          # adapter + dbt-tests-adapter conformance suite

# conformance suite (needs a live qod edge + TPC-H demo; override via QOD_* env)
pytest tests/functional

# build + validate distributions
python -m build && twine check dist/*
```

Publishing is automated: pushing a `vX.Y.Z` tag triggers
[`.github/workflows/publish.yml`](.github/workflows/publish.yml), which builds and
uploads to PyPI via **Trusted Publishing** (OIDC, no stored token). One-time setup:
on PyPI, add a GitHub trusted publisher for this repo pointing at `publish.yml` and
the `pypi` environment. The version is single-sourced from
`dbt/adapters/qod/__version__.py`.

To get listed in dbt's adapter docs, run the full `dbt-tests-adapter` suite green
and open a PR to `dbt-labs/docs.getdbt.com`.

## License

Apache-2.0