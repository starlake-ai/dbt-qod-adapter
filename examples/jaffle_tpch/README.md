# jaffle_tpch

A small end-to-end demo of the [dbt-qod](../../README.md) adapter: a
jaffle-shop-style dbt project built on the TPC-H tables of a
[Quack-on-Demand](https://github.com/starlake-ai/quack-on-demand) tenant.

It exercises every core dbt feature the adapter supports:

- **sources** over the `tpch1` schema (`customer`, `orders`, `nation`, `region`)
- **view** models (`stg_customer`, `stg_orders`)
- a **table** model (`customer_order_summary`, revenue per market segment)
- an **incremental** model (`orders_incremental`, delete+insert on `order_key`)
- a **seed** (`market_segment_labels.csv`)
- a **snapshot** (`orders_snapshot`, timestamp strategy)
- generic **tests** (`not_null`, `unique`) on all models
- **dbt docs generate** with a populated catalog

A full log of a successful run is in [RUN_REPORT.md](RUN_REPORT.md).

## Prerequisites

- Python 3.10-3.13 with `dbt-core` and `dbt-qod` installed
  (`pip install dbt-core dbt-qod`, or `pip install -e '.[dbt]'` from the repo
  root to use this checkout).
- A running qod edge with the demo tenant `acme`, tenant-db `acme_tpch`, and
  pool `bi`, with TPC-H data loaded into the `tpch1` schema. See the
  [Quack-on-Demand](https://github.com/starlake-ai/quack-on-demand) docs for
  bootstrapping the demo stack and loading TPC-H.

  Note: the CI compose stack in this repo
  ([.github/ci/qod-stack.yml](../../.github/ci/qod-stack.yml)) creates the
  demo tenants but loads no TPC-H data, and it runs with TLS off; it is meant
  for the conformance suite, not this demo.

## Connection

[profiles.yml](profiles.yml) lives in the project directory, so dbt picks it
up automatically when you run from here. Defaults:

| setting | value | meaning |
| --- | --- | --- |
| `host` / `port` | `localhost:31338` | FlightSQL edge |
| `database` | `acme_tpch` | tenant-db / DuckLake catalog |
| `schema` | `dbt_jaffle` | where dbt writes; `tpch1` stays untouched |
| `tenant` / `pool` | `acme` / `bi` | gRPC routing headers |
| `username` / `password` | `admin` / `admin` | demo credentials |
| `use_tls` / `tls_skip_verify` | `true` / `true` | self-signed dev cert |

Adjust these to match your edge (for a plain-gRPC edge set `use_tls: false`).

## Run

```bash
cd examples/jaffle_tpch

dbt debug          # connection check
dbt build          # seeds + models + snapshot + tests (14 steps)
dbt docs generate  # catalog

# incremental behavior: second run only loads new orders
dbt run --select orders_incremental
```

Expect individual steps to take ~10s each: every DuckLake DDL commit pays a
fixed cost at the edge, so the demo completes in under a minute with 4
threads rather than instantly.

## Layout

```
models/staging/    sources.yml + stg_customer, stg_orders (views)
models/marts/      customer_order_summary (table), orders_incremental
                   (incremental), schema.yml (tests)
seeds/             market_segment_labels.csv
snapshots/         orders_snapshot.sql (timestamp strategy, orders <= 100)
```

Everything materializes into `acme_tpch.dbt_jaffle`, so you can drop that
schema to reset the demo.
