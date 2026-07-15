from __future__ import annotations

from fastapi import UploadFile


class UploadTooLargeError(ValueError):
    pass


async def read_upload_limited(
    upload: UploadFile,
    *,
    max_bytes: int,
    chunk_size: int = 1024 * 1024,
) -> bytes:
    if max_bytes <= 0:
        raise UploadTooLargeError("Upload limits are misconfigured.")
    total = 0
    chunks: list[bytes] = []
    while True:
        chunk = await upload.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise UploadTooLargeError(f"Upload exceeded {max_bytes} bytes limit.")
        chunks.append(chunk)
    return b"".join(chunks)
