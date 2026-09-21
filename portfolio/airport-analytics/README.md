# Airport Operations Analytics

A repeatable CSV-to-SQL pipeline that validates flight records and reports airport departure performance. The included six-flight dataset is synthetic and does not represent actual airline operations.

## Run

Requires Python 3.11+. From this directory:

```sh
python pipeline.py sample_flights.csv --db :memory:
python pipeline.py sample_flights.csv --db flights.db
python -m unittest discover -v
```

The CLI emits JSON containing accepted/rejected row counts, rejection reasons and source line numbers, and aggregate metrics. A persistent database accumulates flights across files; reports cover all stored rows. Reruns update matching `(flight_id, flight_date)` records rather than duplicating them. This is an incremental load, not a snapshot replacement.

## Input contract

Header order: `flight_id,flight_date,origin,destination,delay_minutes,cancelled`.

- Flight dates must parse as ISO dates; IDs cannot be blank.
- Origin/destination normalize to uppercase three-letter codes and must differ. Codes are format-checked, not checked against an airport registry.
- `cancelled` is exactly `0` or `1`.
- Operated flights require an integer delay between -180 and 2880 minutes. Early departures are negative.
- Cancelled flights store a null delay regardless of the source delay field.
- Within one file, the first valid flight/date occurrence wins and subsequent duplicates are rejected.

Malformed rows are excluded and listed in the quality output. Valid rows commit together. An invalid header fails the load. Rejected rows are not persisted; capture the JSON output if an audit artifact is required. Exit 0 means the pipeline completed, even when individual rows were rejected; file/schema/database failures exit 2.

## Metric definitions

| Metric | Definition | ORD sample result |
| --- | --- | --- |
| Total flights | All stored departures | 3 |
| Cancellation percentage | Cancelled / total × 100 | 33.33 |
| Mean delay | Mean signed delay for operated flights | 15 minutes |
| On-time percentage | Operated flights with delay < 15 / operated × 100 | 50 |

An airport with only cancelled flights has null mean delay and null on-time percentage. The report SQL is kept separately for easy review.

## Verification and limitations

Eight tests cover metric denominators, reruns/corrections, invalid rows/duplicates, the 15-minute boundary, preservation of data after a bad header, and clean CLI errors for invalid database paths.

This is a small-data demonstration: validated records are buffered in memory before a transaction. It does not use Spark, stream live data, or predict delays. Extensions could include chunked ingestion, provenance tables, date filters, and a dashboard.

Malformed CSV quoting fails the complete load with exit 2 and preserves prior data. Rejection line numbers refer to physical source lines, including files with multiline quoted fields.
