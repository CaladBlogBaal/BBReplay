import os

from flask import Blueprint, request, jsonify, Flask, send_file
from app.utils.cache import cache
from app.utils.constants import CHARACTERS
from app.utils.helpers import require_api_key, get_character_icon, clear_cache_on_success
from app.utils.helpers import collapse_replays_into_sets
from app.core import limiter
from app import replay_controller as controller

app = Flask("app")
bp = Blueprint("replays", __name__, url_prefix="/")
# Set a default limit of 1 request per second,
# which can be changed granular in each route.
limiter.limit("1/second")(bp)


def page_out_of_bounds(page: int, max_page: int):
    if page > max_page:
        return jsonify({
            "error": "Page out of bounds",
            "message": f"The requested page {page} exceeds the maximum page number {max_page}.",
            "max_page": max_page
        }), 404

    if page < 0:
        return jsonify({
            "error": "Page out of bounds",
            "message": f"The requested page {page} is less than 0.",
            "max_page": max_page
        }), 404


@bp.route("/api/replay-sets", methods=["GET"])
@limiter.limit("20 per 10 second")
async def get_replays_into_sets():
    page = request.args.get("page", 1, type=int)
    per_page = 100  # Default number of replays per page
    params = dict(request.args)
    replay_cache = cache
    cached_data = replay_cache.get(params)
    params.pop("page", None)

    if cached_data:
        replays = cached_data
    else:
        replays_list = [replay.to_dict() async for replay in controller.get_replays(params, page=page,
                                                                                    per_page=per_page)]

        if not isinstance(replays_list, list):
            return jsonify(replays_list), 404

        replay_cache.set(params, replays_list)
        replays = replay_cache.get(params)

    max_page = await controller.get_total_pages(params, per_page=per_page)

    check = page_out_of_bounds(page, max_page)

    if check:
        return check

    replays = collapse_replays_into_sets(replays)
    replays.sort(key=lambda r: r["recorded_at"], reverse=True)

    return jsonify(replays=replays, current_page=page, max_page=max_page)


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


@bp.route("/api/replays", methods=["GET"])
@limiter.limit("20 per 10 second")
async def get_replays_api():
    query_params = request.args.to_dict()

    for key in query_params:
        try:
            query_params[key] = int(query_params[key])
        except ValueError:
            pass  # Keep as is if it cannot be converted to int

    limit = 10000
    per_page = query_params.pop("per_page", 100)
    page = query_params.pop("page", 1)
    # Enforce limits
    per_page = max(1, min(per_page, limit))
    max_page = await controller.get_total_pages(query_params, per_page=per_page)

    check = page_out_of_bounds(page, max_page)

    if check:
        return check

    replays = [replay.to_dict(include_replay_data=True)
               async for replay in controller.get_replays(query_params, per_page=per_page, page=page)]

    return jsonify(replays=replays, current_page=page, max_page=max_page)


@bp.route("/api/replay/<replay_id>", methods=["GET"])
@limiter.limit("10 per 10 second")
async def get_replay_api(replay_id):

    try:
        int(replay_id)
    except ValueError:
        return jsonify({"error": f"Invalid parameter given for replay_id, {replay_id} is not an integer"})

    async for replay in controller.get_replay({"replay_id": replay_id}):
        if replay is None:
            response = {"error": "Replay doesn't exist"}
            code = 404
        else:
            response = jsonify(replay.to_dict(include_replay_data=True))
            code = 200
        return clear_cache_on_success(response, code)


@bp.route("/api/replay", methods=["POST"])
@limiter.limit("10 per 10 second")
async def create_replay_api():
    replay = await controller.create_replay(request.data)
    if replay is None:
        response = {"error": "Replay already exists"}
        code = 404
    else:
        response = jsonify(replay.to_dict())
        code = 201
    return clear_cache_on_success(response, code)


@bp.route("/api/replay/<replay_id>", methods=["PUT"])
@limiter.limit("5 per 10 second")
@require_api_key
async def update_replay_api(replay_id):

    try:
        int(replay_id)
    except ValueError:
        return jsonify({"error": f"Invalid parameter given for replay_id, {replay_id} is not an integer"})

    replay = await controller.update_replay(replay_id)
    if replay is None:
        response = jsonify({"error": "Replay not found"})
        code = 404
    else:
        response = jsonify(replay.to_dict())
        code = 200

    return clear_cache_on_success(response, code)


@bp.route("/api/replay/<replay_id>", methods=["DELETE"])
@limiter.limit("3 per 10 second")
@require_api_key
async def delete_replay_api(replay_id):

    try:
        int(replay_id)
    except ValueError:
        return jsonify({"error": f"Invalid parameter given for replay_id, {replay_id} is not an integer"})

    delete = await controller.delete_replay(replay_id)

    if delete:
        response = jsonify({"message": f"Successfully deleted replay with id {replay_id}"})
        code = 204
    else:
        response = jsonify({"error": "Replay not found"})
        code = 404

    return clear_cache_on_success(response, code)


@bp.route("download", methods=["GET"])
@limiter.limit("20 per 10 second")
async def download_replay():
    replay_id = int(request.args.get("replay_id", None))
    replay_data = await controller.download_replay(replay_id)

    if replay_data is None:
        return jsonify({"error": "Replay not found"}), 404

    data, filename, mimetype = replay_data
    return send_file(data, as_attachment=True, download_name=filename, mimetype=mimetype)


@bp.route("download-set", methods=["GET"])
@limiter.limit("20 per 10 second")
async def download_set():
    data = request.args.to_dict(flat=False)
    replay_ids = [int(n) for n in data["replay_ids"][0].split(",")]

    set_data = await controller.download_replays(replay_ids)

    if not set_data:
        return jsonify({"error": f"Replay(s) with ID(s): {','.join(str(n) for n in replay_ids)} not found"}), 404

    stream, filename = set_data

    return send_file(stream, as_attachment=True,
                     download_name=f"replays-{os.path.splitext(filename)[0]}.zip"), 200
