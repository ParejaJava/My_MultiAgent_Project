# LMX-2101 Database Lock Timeout Signature

Signature: `LMX-2101`.

For lock wait timeout during order update, inspect `information_schema.innodb_trx`,
blocking transaction age, and missing indexes in the update predicate. Kill or commit
the blocking transaction only after owner confirmation.

