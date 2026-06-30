# dbt-qod run report

Live end-to-end run of the `examples/jaffle_tpch` project against a qod edge
(released 0.3.4 jar, TPC-H SF1, tenant `acme` / catalog `acme_tpch`, ACL enabled),
using dbt-core 1.11.11 + dbt-qod 0.1.0 over the Arrow ADBC FlightSQL driver.

## dbt debug
```
15:44:33  adapter type: qod
15:44:33  adapter version: 0.1.0
15:44:34    Connection test: [OK connection ok]
15:44:34  All checks passed!
```

## dbt build --full-refresh (seeds, models, snapshots, tests)
```
18:33:51  Concurrency: 4 threads (target='dev')
18:33:51  
18:33:52  1 of 14 START sql view model dbt_jaffle.stg_customer ........................... [RUN]
18:33:52  2 of 14 START sql view model dbt_jaffle.stg_orders ............................. [RUN]
18:33:52  3 of 14 START seed file dbt_jaffle.market_segment_labels ....................... [RUN]
18:33:52  4 of 14 START snapshot dbt_jaffle.orders_snapshot .............................. [RUN]
18:33:52  2 of 14 OK created sql view model dbt_jaffle.stg_orders ........................ [OK in 0.42s]
18:33:52  5 of 14 START test not_null_stg_orders_order_key ............................... [RUN]
18:34:02  3 of 14 OK loaded seed file dbt_jaffle.market_segment_labels ................... [CREATE 5 in 10.38s]
18:34:02  6 of 14 START test unique_stg_orders_order_key ................................. [RUN]
18:34:02  4 of 14 OK snapshotted dbt_jaffle.orders_snapshot .............................. [OK in 10.43s]
18:34:02  1 of 14 OK created sql view model dbt_jaffle.stg_customer ...................... [OK in 10.58s]
18:34:02  7 of 14 START test not_null_stg_customer_customer_key .......................... [RUN]
18:34:02  8 of 14 START test unique_stg_customer_customer_key ............................ [RUN]
18:34:03  5 of 14 PASS not_null_stg_orders_order_key ..................................... [PASS in 10.28s]
18:34:13  6 of 14 PASS unique_stg_orders_order_key ....................................... [PASS in 10.31s]
18:34:13  9 of 14 START sql incremental model dbt_jaffle.orders_incremental .............. [RUN]
18:34:13  7 of 14 PASS not_null_stg_customer_customer_key ................................ [PASS in 10.27s]
18:34:13  8 of 14 PASS unique_stg_customer_customer_key .................................. [PASS in 10.28s]
18:34:13  10 of 14 START sql table model dbt_jaffle.customer_order_summary ............... [RUN]
18:34:23  9 of 14 OK created sql incremental model dbt_jaffle.orders_incremental ......... [OK in 10.33s]
18:34:23  11 of 14 START test not_null_orders_incremental_order_key ...................... [RUN]
18:34:23  12 of 14 START test unique_orders_incremental_order_key ........................ [RUN]
18:34:23  10 of 14 OK created sql table model dbt_jaffle.customer_order_summary .......... [OK in 10.35s]
18:34:23  13 of 14 START test not_null_customer_order_summary_market_segment ............. [RUN]
18:34:23  14 of 14 START test unique_customer_order_summary_market_segment ............... [RUN]
18:34:33  11 of 14 PASS not_null_orders_incremental_order_key ............................ [PASS in 10.31s]
18:34:33  12 of 14 PASS unique_orders_incremental_order_key .............................. [PASS in 10.33s]
18:34:33  13 of 14 PASS not_null_customer_order_summary_market_segment ................... [PASS in 10.27s]
18:34:33  14 of 14 PASS unique_customer_order_summary_market_segment ..................... [PASS in 10.28s]
18:34:33  
18:34:33  Finished running 1 incremental model, 1 seed, 1 snapshot, 1 table model, 8 data tests, 2 view models in 0 hours 0 minutes and 42.47 seconds (42.47s).
18:34:33  
18:34:33  Completed successfully
18:34:33  
18:34:33  Done. PASS=14 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=14
```

## What this exercises

- **view** materializations (stg_customer, stg_orders) reading dbt **sources** (tpch1)
- **table** materialization (customer_order_summary) over **ref()**
- **incremental** materialization (orders_incremental, delete+insert strategy)
- **seed** (market_segment_labels.csv) loaded via inlined literal INSERTs
- **snapshot** (orders_snapshot, timestamp strategy)
- generic **tests** (not_null, unique) across all models
- **dbt docs generate** (catalog) produces a populated `catalog.json`

## Conformance suite (dbt-tests-adapter)

The full standard adapter conformance suite (`tests/`) passes against a live edge
(the published `starlakeai/quack-on-demand` image, TLS off, acme/acme_tpch): **12
passed, 0 failed** in ~18 min. Classes covered:

- SimpleMaterializations (view/table/incremental + materialization swaps)
- SingularTests, SingularTestsEphemeral, GenericTests
- Empty, Ephemeral
- Incremental, IncrementalNotSchemaChange
- SnapshotCheckCols, SnapshotTimestamp
- AdapterMethod, ValidateConnection

This is wired into CI (`.github/workflows/ci.yml`, `conformance` job) on a nightly
schedule + manual dispatch; it is slow because each DuckLake DDL commit takes a few
seconds, which is why it is gated rather than run on every push.
