import asyncio
import logging
import functools
import aiohttp

logger = logging.getLogger(__name__)


class RequestFailed(Exception):
    pass


def error_handle(f):
    @functools.wraps(f)
    async def exception(*args, **kwargs):
        try:
            return await f(*args, **kwargs)
        except (asyncio.TimeoutError, aiohttp.ClientConnectorError, aiohttp.InvalidURL) as e:
            raise e

    return exception


class Request:
    MAX_RETRIES = 3

    def __init__(self):
        self.session = None
        self.queue = None      # ❗ Do NOT create here
        self._shutdown = False

    async def start(self):
        """Start the async worker running in the correct event loop."""
        loop = asyncio.get_running_loop()
        self.queue = asyncio.LifoQueue()   # ✔ created in correct loop
        self.session = aiohttp.ClientSession()
        asyncio.create_task(self.worker())  # ✔ don't await here

    async def worker(self):
        while not self._shutdown:
            url, data, retries, method = await self.queue.get()
            try:
                if method == "post":
                    await self.post(url, data=data, headers={"Content-Type": "application/octet-stream"})
                else:
                    await self.fetch(url)

                logger.info(f"Worker finished task with {url}")

            except RequestFailed:
                if retries < self.MAX_RETRIES:
                    logger.info(f"Request failed retrying {url} ({retries+1}/{self.MAX_RETRIES})...")
                    await self.queue.put((url, data, retries + 1, method))

            self.queue.task_done()

    async def return_content(self, response: aiohttp.ClientResponse, headers: str):
        if response.status != 200:
            if response.request_info.method == "POST":
                self.queue.put_nowait((response.url, await response.read(), 0, "post"))
            else:
                self.queue.put_nowait((response.url, None, 0, "get"))

        if "json" in headers:
            return await response.json()
        return await response.read()

    @error_handle
    async def fetch(self, url, **kwargs):
        async with self.session.get(url, **kwargs) as response:
            if response.status != 200:
                raise RequestFailed(f"Unexpected error for `{response.url}`.")

            headers = response.headers.get("Content-Type", "")
            return await self.return_content(response, headers)

    @error_handle
    async def post(self, url, **kwargs):
        async with self.session.post(url, **kwargs) as response:
            headers = response.headers.get("Content-Type", "")
            return await self.return_content(response, headers)

    async def stop(self):
        self._shutdown = True
        if self.session:
            await self.session.close()

request_handler = Request() 