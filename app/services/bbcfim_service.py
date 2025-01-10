import typing
from io import BytesIO

from app.utils.request import request_handler


class BBCFIM:
    BASE_URL = "http://50.118.225.175"

    def __init__(self):
       self.request_handler = request_handler

    async def download_files(self, filenames: typing.List[str]) -> typing.AsyncGenerator[typing.Union[str, BytesIO], None]:
        for fn in filenames:
            yield await self.download_file(fn)

    async def download_file(self, filename: str) -> typing.Tuple[BytesIO, str, str]:
        buffer = BytesIO(await self.request_handler.fetch(f"{self.BASE_URL}/uploads/{filename}"))
        buffer.seek(0)
        buffer.name = filename
        return buffer, filename, "application/octet-stream"

    async def send_file(self, file_data: bytes):
        return await self.request_handler.post(f"{self.BASE_URL}:5000/upload", data=file_data, headers={"Content-Type": "application/octet-stream"})
