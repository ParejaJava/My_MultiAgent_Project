# OSS-4403 Gateway Body Limit Signature

Signature: `OSS-4403`.

For large object upload returning body size errors, verify gateway body limit,
read timeout, send timeout, chunk size, and presigned direct-upload flow. Avoid one
large request through the application gateway.

