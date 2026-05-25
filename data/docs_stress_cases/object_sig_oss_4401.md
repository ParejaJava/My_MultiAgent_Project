# OSS-4401 Multipart Order Signature

Signature: `OSS-4401`.

For multipart complete failure, sort submitted parts by ascending `partNumber`, verify
that every ETag comes from the matching uploaded part, and check that all non-final
parts meet the minimum size.

