import asyncio


class AioPool:
    def __init__(self, num_workers, fn, worker_args=None) -> None:
        self.num_workers = num_workers
        self.fn = fn
        self.requests_queue = asyncio.Queue()
        self.responses_queue = asyncio.Queue()

        self.requests_count = 0
        self.responses_count = 0

        if worker_args is not None:
            assert len(worker_args) == num_workers

        self.tasks = []
        for i in range(num_workers):
            if worker_args:
                args = worker_args[i]
            else:
                args = tuple()

            self.tasks.append(
                asyncio.create_task(
                    self.worker(args),
                    name=f'AioPool-worker-{i}'
                )
            )

    async def worker(self, worker_args):
        try:
            while True:
                args, kwargs = await self.requests_queue.get()
                response = await self.fn(*worker_args, *args, **kwargs)
                await self.responses_queue.put((args, kwargs, response))
                self.requests_queue.task_done()
        except asyncio.CancelledError:
            pass

    def put_task(self, *args, **kwargs):
        self.requests_count += 1
        self.requests_queue.put_nowait((args, kwargs))

    async def results_iter(self):
        while self.responses_count < self.requests_count:
            r = await self.responses_queue.get()
            yield r
            self.responses_count += 1
            self.responses_queue.task_done()

    async def shutdown(self):
        if self.requests_count != self.responses_count:
            raise Exception('requests != responses')

        for i in self.tasks:
            i.cancel()
        for i in self.tasks:
            await i

        self.tasks = []


if __name__ == '__main__':
    async def myfn(wid, x):
        print(f'[{wid}] processing {x}')
        await asyncio.sleep(1)

        res = []
        if x < 10:
            res.append(x * 3)
            res.append(x * 5)
            res.append(x * 7)
        return x, res


    async def main():
        pool = AioPool(4, myfn, [(1,),(2,),(3,),(4,)])

        pool.put_task(1)

        already_fetched = set([1])
        results = []

        async for (args, kwargs, response) in pool.results_iter():
            print('result', args, kwargs, response)
            x, n = response
            results.append(x)

            for i in n:
                if i not in already_fetched:
                    already_fetched.add(i)
                    pool.put_task(i)

            print(f'l {len(already_fetched)}')
        
        print()
        print('DONE')
        print(pool.requests_count, pool.responses_count)

        await pool.shutdown()

        print(len(already_fetched))
        print(sorted(list(already_fetched)))

        print()
        print(sorted(results))
        print(len(results))

    asyncio.run(main(), debug=True)
