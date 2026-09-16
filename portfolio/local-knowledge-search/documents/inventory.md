# Inventory operations (synthetic)

Every stock movement needs a unique request identifier.
Retries with the same request identifier do not change the stock balance twice.
Reject sales that would create negative stock.
Keep the stock movement and audit event in one database transaction.
