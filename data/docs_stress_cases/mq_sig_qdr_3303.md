# QDR-3303 Queue Declaration Mismatch Signature

Signature: `QDR-3303`.

For `PRECONDITION_FAILED inequivalent arg`, compare queue durability, auto-delete,
dead-letter exchange, TTL, and max length arguments. Create a migration queue instead
of mutating immutable queue properties in place.

