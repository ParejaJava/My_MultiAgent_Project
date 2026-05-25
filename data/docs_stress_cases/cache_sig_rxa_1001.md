# RXA-1001 Cache Replica Write Signature

Signature: `RXA-1001`.

When a write request reaches a read-only cache replica, rebuild the client topology cache,
force the connection pool to reconnect, and verify that the primary endpoint is selected.
Do not flush data. The validation command is `INFO replication`.

