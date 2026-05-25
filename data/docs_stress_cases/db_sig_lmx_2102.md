# LMX-2102 Database Deadlock Retry Signature

Signature: `LMX-2102`.

For deadlock during concurrent consumer writes, collect `SHOW ENGINE INNODB STATUS`,
make the business operation idempotent, and add bounded retry with jitter. Keep resource
update order consistent.

