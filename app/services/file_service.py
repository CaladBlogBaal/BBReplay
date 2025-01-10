from quart import jsonify

from app.services.bbcfim_service import BBCFIM
from app.utils.helpers import clear_cache_on_success



async def upload_replay(data: bytes):
    # this always return a success so will probably check if the replay exists later
    replay = await BBCFIM().send_file(data)

    if replay is None:
        response = {"error": "Replay already exists"}
        code = 404
    else:
        response = jsonify(replay)
        code = 201

    return clear_cache_on_success(response, code)


