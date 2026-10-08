import asyncio

import pytest
from upload import BufferSink, SinkClosed, UploadFailed, etag, split_parts, upload_all


async def store(part, sink):
    await sink.write(part.offset, part.data)
    return etag(part.data)


def test_upload_assembles_the_payload():
    payload = b"0123456789abcdefghij"
    parts = split_parts(payload, 6)

    async def main():
        sink = BufferSink()
        etags = await upload_all(parts, store, sink, limit=2)
        return sink, etags

    sink, etags = asyncio.run(main())
    assert sink.getvalue() == payload and sink.closed
    assert etags == [etag(p.data) for p in parts]


def test_a_failing_part_raises_and_closes_the_sink():
    parts = split_parts(b"x" * 10, 5)

    async def reject(part, sink):
        raise UploadFailed(part, 400)

    async def main():
        sink = BufferSink()
        with pytest.raises(UploadFailed):
            await upload_all(parts, reject, sink)
        return sink

    assert asyncio.run(main()).closed


def test_writes_after_close_are_rejected():
    async def main():
        sink = BufferSink()
        await sink.close()
        with pytest.raises(SinkClosed):
            await sink.write(0, b"late")

    asyncio.run(main())


def test_part_size_is_validated():
    with pytest.raises(ValueError):
        split_parts(b"abc", 1)
