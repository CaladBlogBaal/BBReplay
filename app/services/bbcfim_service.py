import asyncio
import time
import typing
from io import BytesIO
from typing import AsyncGenerator

from app.utils.request import request_handler

class RateLimiter:
    def __init__(self, max_calls: int, period: float):
        self.max_calls = max_calls
        self.period = period
        self.calls = asyncio.Queue(maxsize=max_calls)
        self.lock = asyncio.Lock()

    async def acquire(self):
        # Only one coroutine at a time may inspect + modify the limiter state, so we need a lock
        async with self.lock:
            # Rolling window rate limiter:
            # We store timestamps of requests.
            # When we have reached max_calls, we remove the oldest timestamp and check
            # whether it is still within the time window (period), by seeing
            # how much of the allowed time window is already consumed between the oldest request and now
            # If it is, we sleep until that window expires.

            # Timestamp the request came at
            now = time.monotonic()

            if self.calls.full():
                oldest = await self.calls.get()
                # compute elapsed time since oldest request
                sleep_for = self.period - (now - oldest)
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
            # queue stores timestamps like [10.0, 20.0, 30.0]
            await self.calls.put(now)


class BBCFIM:
    BASE_URL = "http://89.167.76.6"

    def __init__(self):
       self.request_handler = request_handler

    async def download_files(self, filenames: typing.List[str], limit=3) -> AsyncGenerator[tuple[BytesIO, str, str], None]:
        # 30 requests per 1 minute
        limiter = RateLimiter(max_calls=30, period=60)
        for fn in filenames:
            await limiter.acquire()
            yield await self.download_file(fn)

    async def download_file(self, filename: str) -> typing.Tuple[BytesIO, str, str]:
        buffer = BytesIO(await self.request_handler.fetch(f"{self.BASE_URL}:5000/download/{filename}"))
        buffer.seek(0)
        buffer.name = filename
        return buffer, filename, "application/octet-stream"

    async def send_file(self, file_data: bytes):
        return await self.request_handler.post(f"{self.BASE_URL}:5000/upload", data=file_data, headers={"Content-Type": "application/octet-stream"})
