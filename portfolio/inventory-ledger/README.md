# Inventory Ledger

A local command-line inventory system that tracks products and stock movements in a persistent SQLite database. Demonstrates reliable backend operations for a small warehouse scenario.

## Run

Requires Python 3.11+. From this directory:

```sh
python inventory.py add USB "USB-C hub" --reorder-point 3
python inventory.py move USB 10 --request-id delivery-001
python inventory.py move USB -7 --request-id order-001
python inventory.py list --low-stock
python inventory.py history USB
python -m unittest discover -v
```

The remaining stock is 3, which appears in the low-stock report. Repeating the same movement command returns `{"applied": false}` without changing stock. Use a fresh request ID for a different operation. Repeating product creation reports an error.

Use `python inventory.py --db example.db ...` to select another database. Commands emit JSON and validation failures exit with code 2.

## Design

`products` stores the current balance; `movements` stores an audit trail linked by SKU. Stock starts at zero and changes only through movements in the application. SQL parameters separate user input from query text.

`BEGIN IMMEDIATE` acquires a write reservation before checking the request ID. The conditional update prevents negative stock. The stock update and audit insertion commit together or roll back together. A unique request ID makes retries safe; reusing an ID for another payload is rejected.

SQLite's database-level writer serialization is a deliberate simplicity tradeoff. This is appropriate for a local demonstration; a high-throughput service would need a server database, authentication, authorization, migration management, and operational monitoring. Direct database edits can bypass application audit rules. There is no web API or multi-user access layer.

## Verification

Eleven automated tests cover retries, rollback, conflicting IDs, reorder boundaries, invalid inputs, two concurrent sales competing for the last item, integer overflow, oversized quantities, and database-open failures. Stock is limited to signed 64-bit integers; overflow attempts roll back without changing the audit trail. Tests use disposable databases.

Possible extensions: an ASP.NET Core API, SQL Server persistence, stock reservations, and authenticated warehouse roles. These extensions are not implemented.

SKU whitespace is normalized consistently for creation, movement, and history. Reorder points must be nonnegative signed 64-bit integers.
