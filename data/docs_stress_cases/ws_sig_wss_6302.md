# WSS-6302 WebSocket Idle Disconnect Signature

Signature: `WSS-6302`.

For intermittent WebSocket disconnect, compare heartbeat interval with gateway idle
timeout, inspect close code 1006, network switches, server restart, and oversized
message blocking.

