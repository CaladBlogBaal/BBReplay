import typing
from datetime import timedelta

from urllib.parse import urlencode

from quart import Blueprint, request, jsonify, Quart, send_file, Response
from quart_rate_limiter import limit_blueprint, rate_limit
from pydantic import BaseModel
from sqlalchemy.exc import NoResultFound

from app.services.bbcfim_service import BBCFIM
from app.utils.cache import cache
from app.utils.constants import CHARACTERS
from app.utils.helpers import require_api_key, get_character_icon, clear_cache_on_success, order_by_criteria_replays, \
    parse_bool
from app.utils.helpers import collapse_replays_into_sets
from app import replay_controller as controller
from app.schema import ReplayQuery

app = Quart("app")

bp = Blueprint("replays", __name__, url_prefix="/")
# Set a default limit of 1 request per second,
# which can be changed granular in each route.
limit_blueprint(bp, 1, timedelta(seconds=1))


def page_out_of_bounds(page: int, max_page: int) -> tuple[Response, int]:
    if page > max_page > 1:
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


def validate_replay_query(params: dict, model: typing.Type[BaseModel]) -> None:
    valid_keys = model.__fields__.keys()
    param_copy = params.copy()
    for key in param_copy:
        if key not in valid_keys:
            del params[key]


def dict_to_url_query(params: dict):
    return urlencode(params)


@bp.route("/api/replay-sets", methods=["GET"])
@rate_limit(2, timedelta(seconds=1))
async def get_replays_into_sets():
    page = request.args.get("page", 1, type=int)
    page = page if page > 1 else 1
    per_page = 100  # Default number of replays per page
    params = dict(request.args)
    # to not break old urls with the field name changes
    if "p1_character_id" in params:
        params["p1_toon"] = params.pop("p1_character_id")

    if "p2_character_id" in params:
        params["p2_toon"] = params.pop("p2_character_id")

    if "strict_side" in params:
        try:
            strict_side = parse_bool(params["strict_side"])
        except ValueError:
            strict_side = False
    else:
        strict_side = False

    params["page"] = str(page)
    params["strict_side"]  = strict_side
    replay_cache = cache
    cached_data = replay_cache.get(params)
    params.pop("page", None)
    pos = request.cookies.get("pos", "")
    outcome = request.cookies.get("outcome", "")
    validate_replay_query(params, ReplayQuery)

    if cached_data:
        replays = cached_data
    else:
        try:
            replays_list = [await replay.to_dict() async for replay in controller.get_replays(params, page=page,
                                                                                            per_page=per_page)]
        except NoResultFound:
            return jsonify({"error": f"Replay(s) with query parameters `{dict_to_url_query(params)}` not found"}), 404

        replay_cache.set(params, replays_list)
        replays = replay_cache.get(params)

    max_page = await controller.get_total_pages(params, per_page=per_page)

    check = page_out_of_bounds(page, max_page)

    if check:
        return check

    replays = collapse_replays_into_sets(replays)

    replays.sort(key=lambda r: r["datetime_"], reverse=True)

    if outcome or pos:
        search = [params[key] for key in params]
        order_by_criteria_replays(replays, pos=pos, outcome=outcome, search=search)

    return jsonify(replays=replays, current_page=page, max_page=max_page)


@bp.route("/api/character-icons", methods=["GET"])
@rate_limit(2, timedelta(seconds=1))
def get_character_icons():
    character_icons = []
    for key, val in CHARACTERS.items():
        icon = get_character_icon(val)
        img_path = f"/static/img/{icon}"
        character_icons.append(
            {"id": key, "path": img_path, "name": val}
        )
    return jsonify(character_icons)

@bp.route("/api/filenames", methods=["GET"])
@rate_limit(2, timedelta(seconds=1))
async def get_all_filenames():
    data = await controller.get_all_filenames()
    return jsonify([filename async for filename in data])

@bp.route("/api/replays", methods=["GET"])
@rate_limit(2, timedelta(seconds=1))
async def get_replays_api():
    query_params = request.args.to_dict()

    for key in query_params:
        try:
            query_params[key] = int(query_params[key])
        except ValueError:
            pass  # Keep as is if it cannot be converted to int

    if "strict_side" in query_params:
        try:
            strict_side = parse_bool(query_params["strict_side"])
        except ValueError:
            strict_side = True
    else:
        strict_side = True

    query_params["strict_side"]  = strict_side


    limit = 10000
    per_page = query_params.pop("per_page", 100)
    page = query_params.pop("page", 1)
    include = query_params.pop("include", False)
    # Enforce limits
    per_page = max(1, min(per_page, limit))
    max_page = await controller.get_total_pages(query_params, per_page=per_page)

    check = page_out_of_bounds(page, max_page)

    if check:
        return check

    validate_replay_query(query_params, ReplayQuery)
    try:
        replays = [await replay.to_dict(include_replay_data=bool(include))
                   async for replay in controller.get_replays(query_params, per_page=per_page, page=page)]

    except NoResultFound:
        return jsonify({"error": f"Replay(s) with query parameters `{dict_to_url_query(query_params)}` not found"}), 404

    return jsonify(replays=replays, current_page=page, max_page=max_page)


@bp.route("/api/replay/<filename>", methods=["GET"])
@rate_limit(10, timedelta(seconds=1))
async def get_replay_api(filename):

    async for replay in controller.get_replay({"filename": filename}):
        response = jsonify(await replay.to_dict(include_replay_data=True))
        code = 200
        return clear_cache_on_success(response, code)

    response = {"error": "Replay doesn't exist"}
    code = 404
    return jsonify(response), code


@bp.route("/api/replay", methods=["POST"])
@rate_limit(1, timedelta(seconds=1))
async def create_replay_api():
    # replay = await controller.create_replay(request.data)
    # if replay is None:
    #     response = {"error": "Replay already exists"}
    #     code = 404
    # else:
    #     response = jsonify(replay.to_dict())
    #     code = 201
    # return clear_cache_on_success(response, code)

    replay = await BBCFIM().send_file(await request.data)
    # this always return a success so will probably check if the replay exists later
    if replay is None:
        response = {"error": "Replay already exists"}
        code = 404
    else:
        response = jsonify(replay)
        code = 201

    return clear_cache_on_success(response, code)



@bp.route("/api/replay/<filename>", methods=["PUT"])
@rate_limit(1, timedelta(seconds=1))
@require_api_key
async def update_replay_api(filename):

    replay = await controller.update_replay(filename)
    if replay is None:
        response = jsonify({"error": "Replay not found"})
        code = 404
    else:
        response = jsonify(await replay.to_dict())
        code = 204

    return clear_cache_on_success(response, code)


@bp.route("/api/replay/<filename>", methods=["DELETE"])
@rate_limit(1, timedelta(seconds=30))
@require_api_key
async def delete_replay_api(filename):

    delete = await controller.delete_replay(filename)

    if delete:
        response = jsonify({"message": f"Successfully deleted replay with id {filename}"})
        code = 204
    else:
        response = jsonify({"error": "Replay not found"})
        code = 404

    return clear_cache_on_success(response, code)


@bp.route("download", methods=["GET"])
@rate_limit(2, timedelta(seconds=1))
async def download_replay():

    filename = request.args.get("filename")
    replay_data = await controller.download_replay(filename)

    if replay_data is None:
        return jsonify({"error": "Replay not found"}), 404

    data, filename, mimetype = replay_data
    return await send_file(data, as_attachment=True,  mimetype=mimetype, attachment_filename=filename)


@bp.route("download-set", methods=["GET"])
@rate_limit(2, timedelta(seconds=1))
async def download_set():
    data = request.args.to_dict(flat=False)

    if "filenames" not in data:
        return jsonify({"error": f"filenames, is a required parameter"}), 401

    filenames = []

    for filename in data["filenames"][0].split(","):
        filenames.append(filename)

    set_data = await controller.download_replays(filenames)

    if not set_data:
        return jsonify({"error": f"Replay(s) with ID(s): {','.join(n for n in filenames)} not found"}), 404

    stream, filename, mimetype = set_data

    return await send_file(stream, as_attachment=True, mimetype=mimetype, attachment_filename=filename), 200


@bp.route("/api/replay/character-usage", methods=["GET"])
async def character_usage():
    data = await controller.get_character_usage_statistics()
    return jsonify(data)


@bp.route("/api/replay/matchup-rarity", methods=["GET"])
async def matchup_rarity():
    data = await controller.get_matchup_rarity()
    return jsonify(data)


@bp.route("/api/replay/total", methods=["GET"])
async def get_total_replays():
    data = await controller.get_total_replays()
    return jsonify(data)


@bp.route("/api/replay/total-players", methods=["GET"])
async def get_total_players():
    data = await controller.get_total_unique_players()
    return jsonify({"total": data})


@bp.route("/api/replay/total-per-character", methods=["GET"])
async def get_total_replays_per_character():
    data = await controller.get_total_replays_per_character()
    return jsonify(data)


@bp.route("/api/replay/character-matchup-stats", methods=["GET"])
async def character_matchup():

    character_id = request.args.get("character_id", None, type=int)

    data = await controller.get_character_matchup_statistics(character_id)
    return jsonify(data)


@bp.route("api/replay-timestamps", methods=["GET"])
async def get_all_timestamps():
    data = await controller.get_all_replay_timestamps()
    return jsonify([timestamp async for timestamp in data])
