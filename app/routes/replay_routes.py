from datetime import datetime

from flask import Blueprint, request, jsonify, Flask
from app.utils.cache import cache
from app.utils.constants import CHARACTERS
from app.utils.helpers import require_api_key, get_character_icon, clear_cache_on_success
from app.utils.helpers import process_network_response, chunks, collapse_replays_into_sets
from app.core import limiter
from app import replay_controller as controller

app = Flask("app")
bp = Blueprint("replays", __name__, url_prefix="/")
# Set a default limit of 1 request per second,
# which can be changed granular in each route.
limiter.limit("1/second")(bp)


@bp.route("/api/replays", methods=["GET"])
@limiter.limit("20 per 10 second")
async def get_paginated_replays():
    page = request.args.get("page", 1, type=int)
    per_page = 30  # Number of replays per page
    params = dict(request.args)
    params.pop("page", None)
    replay_cache = cache

    cached_data = replay_cache.get(params)

    if cached_data:
        replays = cached_data
    else:
        response, _ = await controller.get_replays(params)
        replays_list = process_network_response(response)

        if not isinstance(replays_list, list):
            return jsonify(replays_list), 404

        replays_list.sort(key=lambda r: datetime.strptime(r["recorded_at"], "%a, %d %b %Y %H:%M:%S %Z"), reverse=True)
        replays_list = list(chunks(replays_list, per_page))
        replay_cache.set(params, replays_list)
        replays = replay_cache.get(params)

    max_page = len(replays)

    if page > max_page:
        return jsonify({
            "error": "Page out of bounds",
            "message": f"The requested page {page} exceeds the maximum page number {max_page}.",
            "max_page": max_page
        }), 404

    replays = [r for r in replays[page - 1]]
    replays = collapse_replays_into_sets(replays)

    return jsonify(replays=replays, max_page=max_page)


@bp.route("/api/character-icons", methods=["GET"])
@limiter.limit("20 per 10 second")
def get_character_icons():
    character_icons = []
    for key, val in CHARACTERS.items():
        icon = get_character_icon(val)
        img_path = f"/static/img/{icon}"
        character_icons.append(
            {"id": key, "path": img_path, "name": val}
        )
    return jsonify(character_icons)


@bp.route("/api", methods=["GET"])
@limiter.limit("20 per 10 second")
async def get_replays_api():
    query_params = request.args.to_dict()

    for key in query_params:
        try:
            query_params[key] = int(query_params[key])
        except ValueError:
            pass  # Keep as is if it cannot be converted to int

    return await controller.get_replays(query_params)


@bp.route("/api", methods=["POST"])
@limiter.limit("10 per 10 second")
async def create_replay_api():
    return clear_cache_on_success(*(await controller.create_replay(request.data)))


@bp.route("/api", methods=["PUT"])
@limiter.limit("5 per 10 second")
@require_api_key
async def update_replay_api(replay_id: int):
    return clear_cache_on_success(*(controller.update_replay(replay_id)))


@bp.route("/api", methods=["DELETE"])
@limiter.limit("3 per 10 second")
@require_api_key
async def delete_replay_api(replay_id: int):
    return clear_cache_on_success(*(controller.delete_replay(replay_id)))


@bp.route("/download", methods=["GET"])
@limiter.limit("20 per 10 second")
async def download_replay():
    replay_id = int(request.args.get("replay_id", None))
    return await controller.download_replay(replay_id)


@bp.route("/download_set", methods=["GET"])
@limiter.limit("20 per 10 second")
async def download_set():
    data = request.args.to_dict(flat=False)
    replay_ids = [int(n) for n in data["replay_ids"][0].split(",")]
    return await controller.download_replays(replay_ids)
