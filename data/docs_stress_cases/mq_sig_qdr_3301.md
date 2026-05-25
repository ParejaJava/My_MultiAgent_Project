# QDR-3301 Queue Ready Backlog Signature

Signature: `QDR-3301`.

When `messages_ready` grows while consumers are alive, compare publish rate and ack rate,
inspect consumer latency, and tune prefetch. Add consumers only after downstream capacity
is confirmed.

