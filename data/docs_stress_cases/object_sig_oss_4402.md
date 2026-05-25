# OSS-4402 Multipart Resume Signature

Signature: `OSS-4402`.

When upload resume restarts from the beginning, persist the tuple of file hash, bucket,
object name, and upload id. Use `ListParts` to rebuild completed part state after refresh.

