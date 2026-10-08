import asyncio

from jobs import DelayedJobs, JobQueue, WorkerPool


def test_jobs_come_out_oldest_first():
    async def main():
        queue = JobQueue()
        await queue.put_many(["a", "b"])
        await queue.put("c")
        assert len(queue) == 3
        return [await queue.get() for _ in range(3)]

    assert asyncio.run(main()) == ["a", "b", "c"]


def test_worker_pool_processes_jobs():
    async def main():
        queue = JobQueue()
        done = []

        async def handler(job):
            if job == "bad":
                raise ValueError(job)
            done.append(job)

        pool = WorkerPool(queue, handler, size=2)
        pool.start()
        await queue.put_many(["a", "bad", "b"])
        while pool.completed + pool.failed < 3:
            await asyncio.sleep(0)
        await pool.stop()
        return sorted(done), pool.failed

    assert asyncio.run(main()) == (["a", "b"], 1)


def test_delayed_jobs_are_moved_to_the_queue_when_due():
    async def main():
        now = [0.0]
        queue = JobQueue()
        delayed = DelayedJobs(queue, clock=lambda: now[0])
        runner = asyncio.ensure_future(delayed.run())
        await delayed.schedule("later", 0)
        job = await queue.get()
        await delayed.stop()
        await runner
        return job

    assert asyncio.run(main()) == "later"
