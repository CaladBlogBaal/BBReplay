from typing import Union

from flask import Response

from app.services import file_service


class CorruptedFile(Exception):
    pass


# Allowed extensions for file uploads
ALLOWED_EXTENSIONS = ("dat")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def verify_size(data: bytes):
    min_required_size = 0x8D0 + 0xF730  # Starting offset of "replay_inputs" + its size
    return len(data) == min_required_size


async def upload_file(filename: str, data: bytes) -> Union[Response, tuple[Response, int]]:
    if allowed_file(filename) and verify_size(data):
        return await file_service.upload_replay(data)

    raise CorruptedFile(f"Invalid replay data for file {filename}: data is too small/big or corrupted")
