import io
import asyncio

import pytest
from starlette.datastructures import UploadFile

from utils.uploads import UploadTooLargeError, read_upload_limited


def test_read_upload_limited_accepts_boundary_size():
    upload = UploadFile(filename="ok.txt", file=io.BytesIO(b"abcde"))
    data = asyncio.run(read_upload_limited(upload, max_bytes=5, chunk_size=2))
    assert data == b"abcde"


def test_read_upload_limited_rejects_oversized_payload():
    upload = UploadFile(filename="big.txt", file=io.BytesIO(b"abcdef"))
    with pytest.raises(UploadTooLargeError):
        asyncio.run(read_upload_limited(upload, max_bytes=5, chunk_size=2))
