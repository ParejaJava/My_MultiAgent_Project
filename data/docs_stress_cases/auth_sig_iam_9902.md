# IAM-9902 JWKS Rotation Signature

Signature: `IAM-9902`.

For sudden signature verification failure, inspect JWKS cache TTL, key id, issuer
metadata, clock skew, and whether gateway instances refreshed the signing key set.

