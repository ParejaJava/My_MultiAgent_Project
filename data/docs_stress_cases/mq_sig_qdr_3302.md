# QDR-3302 Queue Unacked Backlog Signature

Signature: `QDR-3302`.

When `messages_unacknowledged` grows, inspect stuck consumers, missing ack paths,
long handler execution, and `consumer_timeout`. Restarting consumers without checking
idempotency can duplicate side effects.

