from typing import Union

from flask import Response

from app.services import file_service


async def upload_file(filename: str, data: bytes) -> Union[Response, tuple[Response, int]]:
    return await file_service.upload_replay(filename, data)

