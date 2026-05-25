# LMX-2103 Database Duplicate Message Signature

Signature: `LMX-2103`.

For duplicate entry after queue replay, treat the unique key conflict as an idempotency
signal. Acknowledge the duplicate message only after confirming that the existing row
represents the same business request.

