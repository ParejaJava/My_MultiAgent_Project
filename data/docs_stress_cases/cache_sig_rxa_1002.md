# RXA-1002 Cache Eviction Storm Signature

Signature: `RXA-1002`.

When eviction storms appear after a traffic spike, inspect `used_memory`, `maxmemory`,
`evicted_keys`, TTL coverage, and large key distribution. Split oversized keys before
raising memory limits.

