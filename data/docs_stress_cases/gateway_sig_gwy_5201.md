# GWY-5201 Upstream Timeout Signature

Signature: `GWY-5201`.

For upstream timeout, correlate gateway access logs with application trace id, compare
gateway timeout with backend P95 and P99 latency, then inspect slow SQL and downstream
RPC timeout budgets.

