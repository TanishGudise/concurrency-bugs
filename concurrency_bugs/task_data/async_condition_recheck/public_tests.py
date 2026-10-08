import asyncio

from jobqueue import JobQueue


def test_jobs_come_out_oldest_first():
    async def main():
        queue = JobQueue()
        for job in ("a", "b", "c"):
            await queue.put(job)
        assert len(queue) == 3
        return [await queue.get() for _ in range(3)]

    assert asyncio.run(main()) == ["a", "b", "c"]


def test_get_waits_for_a_job():
    async def main():
        queue = JobQueue()
        worker = asyncio.ensure_future(queue.get())
        await asyncio.sleep(0)
        assert not worker.done()
        await queue.put("job")
        return await worker

    assert asyncio.run(main()) == "job"
