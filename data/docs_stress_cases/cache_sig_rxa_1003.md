# RXA-1003 Cache Slow Command Signature

Signature: `RXA-1003`.

When intermittent cache timeout happens without process crash, inspect `SLOWLOG`,
`latency doctor`, blocked clients, and commands that scan large collections.
Replace broad key scans with bounded access patterns.

