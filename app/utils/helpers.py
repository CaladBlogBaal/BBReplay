import os
import glob
import struct
import hashlib
import fnmatch
import typing
import pytz

from datetime import datetime, timedelta

from functools import wraps
from typing import Union, Any

import flask

from flask import request, abort, current_app, Flask

from app.models.replay import Replay
from app.utils.cache import cache
from app.utils.constants import CHARACTERS

app = Flask("app")
# Normalize time zones to a common one (UTC in this case)
UTC_TIMEZONE = pytz.utc


def run_search(search: typing.Union[int, str], value: typing.Union[int, str]) -> bool:
    """Helper function to validate a term"""
    if isinstance(search, str) and isinstance(value, str):
        return search.lower() in value.lower()
    elif isinstance(search, int) and isinstance(value, int):
        return search == value
    return False


def swap_set_icons(replay):
    """helper function to swap player icons."""
    p1icon = replay["p1icon"]
    p2icon = replay["p2icon"]

    replay["p1icon"] = p2icon
    replay["p2icon"] = p1icon


def swap_set_wins(replay):
    """helper function to swap player scores."""
    p1wins = replay["p1wins"]
    p2wins = replay["p2wins"]

    replay["p1wins"] = p2wins
    replay["p2wins"] = p1wins


def swap_players(replay):
    """Helper function to swap players based on position."""

    p1 = replay["p1"]
    p1_steam = replay["p1_steamid64"]
    p1_character = replay["p1_character_id"]

    p2 = replay["p2"]
    p2_steam = replay["p2_steamid64"]
    p2_character = replay["p2_character_id"]

    replay["p1"] = p2
    replay["p1_steamid64"] = p2_steam
    replay["p1_character_id"] = p2_character

    replay["p2"] = p1
    replay["p2_steamid64"] = p1_steam
    replay["p2_character_id"] = p1_character


def set_outcome(replay, player_side: str) -> str:
    if player_side == "p1":
        return "WON" if replay["p1wins"] > replay["p2wins"] else "LOST"
    return "WON" if replay["p2wins"] > replay["p1wins"] else "LOST"


def order_by_criteria_replays(replays: typing.List[dict], **options: typing.Dict[str, typing.Any]):
    """
     Filters and reorders a list of replays based on the given criteria in the options.

     Args:
         replays
         **options (dict): Optional filter criteria. Possible keys include:
             - "pos" (str): The player position to consider ("LEFT" or "RIGHT").
             - "outcome" (str): The outcome to match for removal or player swapping.
             - "search" (tuple): A sequence of terms to search for within replay values. The search will match replays
               containing any of these terms.
     """
    pos = options.get("pos", "")
    outcome = options.get("outcome", "")
    search_terms = options.get("search", ())

    exclude_keys = ["p1wins", "p2wins"]

    # Iterate in reverse to avoid issues with list modification
    for i in range(len(replays) - 1, -1, -1):
        replay = replays[i]

        for key, value in replay.items():

            if key in exclude_keys:
                continue

            if any(run_search(search_option, value) for search_option in search_terms):

                if "p2" in key:
                    # delete replay
                    if set_outcome(replay, "p2") != outcome:
                        del replays[i]
                        continue
                    # Swap players if position is specified
                    if pos == "LEFT":
                        swap_players(replay)
                        swap_set_wins(replay)
                        swap_set_icons(replay)

                elif "p1" in key:
                    # delete replay
                    if set_outcome(replay, "p1") != outcome:
                        del replays[i]
                        continue
                    # Swap players if position is specified
                    if pos == "RIGHT":
                        swap_players(replay)
                        swap_set_wins(replay)
                        swap_set_icons(replay)

    return replays


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def friendly_file(replay: typing.Type[Replay]) -> tuple[str, str]:
    p1 = replay.p1
    p2 = replay.p2

    p1char_name = CHARACTERS[replay.p1_character_id].lower()
    p2char_name = CHARACTERS[replay.p2_character_id].lower()

    filename = f"{p1}({p1char_name})_{p2}({p2char_name}).dat"
    return filename, "application/octet-stream"


def read_date(date: typing.Union[str, datetime]) -> datetime:
    if isinstance(date, str):
        return datetime.strptime(date, "%a, %d %b %Y %H:%M:%S %Z")
    return date


def within_10_minutes(date1: datetime, date2: datetime) -> bool:
    date1 = read_date(date1)
    date2 = read_date(date2)
    # Calculate the absolute difference between the two dates
    time_difference = abs(date1.astimezone(UTC_TIMEZONE) - date2.astimezone(UTC_TIMEZONE))
    return time_difference <= timedelta(minutes=10)


def aggregate_replays(replays: typing.List[Replay]) -> list[list[Replay]]:
    sorted_replays = sorted(replays, key=lambda r: read_date(r["recorded_at"]).astimezone(UTC_TIMEZONE))

    sets = []
    current_set = []
    previous_match = sorted_replays[0]

    for match in sorted_replays:

        if (
                match["p1"] == previous_match["p1"] and
                match["p1_character_id"] == previous_match["p1_character_id"] and
                match["p2"] == previous_match["p2"] and
                match["p2_character_id"] == previous_match["p2_character_id"] and
                within_10_minutes(match["recorded_at"], previous_match["recorded_at"])
        ):
            current_set.append(match)
        else:
            sets.append(current_set)
            current_set = [match]

        previous_match = match

    if current_set:
        sets.append(current_set)

    return sets


def total_up_wins(row: typing.List[Replay]) -> tuple[int, int]:
    p1wins = 0
    p2wins = 0

    for replay in row:
        assign_wins(replay)
        p1wins += replay["p1wins"]
        p2wins += replay["p2wins"]

    return p1wins, p2wins


def collapse_aggregated_replays(og_replays: typing.List[typing.List[Replay]]) -> list[Replay]:
    replays = [
        {**row[0], "set": [r["replay_id"] for r in row], "p1wins": p1wins, "p2wins": p2wins}
        for row in og_replays
        for p1wins, p2wins in [total_up_wins(row)]
    ]

    return replays


def collapse_replays_into_sets(replays: typing.List[Replay]) -> list[Replay]:
    replays = aggregate_replays(replays)
    replays = collapse_aggregated_replays(replays)
    for replay in replays:
        assign_icons(replay)
    return replays


def walk_path(path):
    # using glob to return paths that meet the pattern
    paths = glob.glob(path)
    if not paths:
        return []
    result = []
    for p in paths:
        # yields a tuple of dirpath, dirnames and filenames
        result.extend(os.walk(p))

    return result


def get_files(pattern, path):
    for dirpath, _, filenames in walk_path(path):
        for f in filenames:
            if fnmatch.fnmatch(f, pattern):
                yield os.path.join(dirpath, f), f


def get_character_icon(search: str) -> Union[bytes, str]:
    img_path = os.path.join(app.root_path, "static", "img")
    icons = get_files(f"*{search}*.png", img_path)
    _, icon = next(icons)
    return icon


def assign_icons(replay: dict):
    replay["p1icon"] = get_character_icon(CHARACTERS[replay["p1_character_id"]])
    replay["p2icon"] = get_character_icon(CHARACTERS[replay["p2_character_id"]])


def assign_wins(replay: dict):
    recorder = replay["recorder_steamid64"]
    is_player1 = (recorder == replay["p1_steamid64"])
    # Set the win values based on winner, winner just means the person who recorded the replay won.
    if is_player1:
        # for some odd reason 0 becomes True, 1 becomes false, if the recorder is on p1 side, instead of p2 side
        replay["p1wins"] = int(1 - (not replay["winner"] == 0))  # If they won the replay as they're on p1 side this
        # evaluates to 0 else 1
        replay["p2wins"] = 1 - replay["p1wins"]  # This is evaluated to the opposite of p1wins

    else:
        replay["p1wins"] = int(1 - replay["winner"])  # If they won the replay as they're on p2 side this evaluates
        # to 0 else 1
        replay["p2wins"] = 1 - replay["p1wins"]


def require_api_key(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get("x-api-key")
        if api_key and api_key == current_app.config["API_KEY"]:
            return func(*args, **kwargs)
        else:
            abort(403)  # Forbidden

    return decorated_function


def parse_replay_data(data: typing.Union[bytearray, bytes]) -> typing.Dict:
    bytes_metadata = {}

    bytes_metadata["replay"] = data

    # Extract and unpack "recorded_at" as a string of 24 bytes
    bytes_metadata["recorded_at"] = struct.unpack_from("24s", data, 0x38)[0]

    # Extract and unpack "winner" as a single byte (unsigned char)
    bytes_metadata["winner"] = struct.unpack_from("B", data, 0x98)[0]

    # Extract and unpack "p1" and "p2" as sequence of 36 bytes each
    bytes_metadata["p1"] = struct.unpack_from("36s", data, 0xA4)[0]
    bytes_metadata["p2"] = struct.unpack_from("36s", data, 0x16E)[0]

    # Extract and unpack "p1_character_id" and "p2_character_id" as  a 4-byte sequence
    bytes_metadata["p1_character_id"] = struct.unpack_from("4s", data, 0x230)[0]
    bytes_metadata["p2_character_id"] = struct.unpack_from("4s", data, 0x234)[0]
    # Extract and unpack "recorder" as a string of 36 bytes
    bytes_metadata["recorder"] = struct.unpack_from("36s", data, 0x240)[0]

    # Extract and unpack "p1_steamid64", "p2_steamid64", and "recorder_steamid64" as 8-byte sequence
    bytes_metadata["p1_steamid64"] = struct.unpack_from("8s", data, 0x9C)[0]
    bytes_metadata["p2_steamid64"] = struct.unpack_from("8s", data, 0x166)[0]
    bytes_metadata["recorder_steamid64"] = struct.unpack_from("8s", data, 0x238)[0]

    # Extract and unpack "replay_inputs" as a sequence of 63280 bytes
    bytes_metadata["replay_inputs"] = struct.unpack_from(f"{0xF730}s", data, 0x8D0)[0]

    return bytes_metadata


def get_hashed_filename(data: typing.Union[bytearray, bytes, dict]) -> str:
    if not isinstance(data, dict):
        data = parse_replay_data(data)

    bytes_to_hash = (data["p1_character_id"] +
                     data["p2_character_id"] +
                     data["p1_steamid64"] +
                     data["p2_steamid64"] +
                     data["replay_inputs"])

    # Hashing with SHA-256
    sha256 = hashlib.sha256()
    sha256.update(bytes_to_hash)
    hashed_data = sha256.hexdigest()

    # Truncate to keep the filename reasonably short
    sha256_filename = hashed_data[:25] + ".dat"

    return sha256_filename


def decode_replay(data: dict) -> None:
    data["filename"] = get_hashed_filename(data)
    data["recorded_at"] = data["recorded_at"].decode("utf-8")
    data["p1"] = data["p1"].decode("utf-16").split("\x00")[0]
    data["p2"] = data["p2"].decode("utf-16").split("\x00")[0]
    data["p1_character_id"] = int.from_bytes(data["p1_character_id"], byteorder="little")
    data["p2_character_id"] = int.from_bytes(data["p2_character_id"], byteorder="little")
    data["recorder"] = data["recorder"].decode("utf-16").split("\x00")[0]

    try:
        data["recorded_at"] = datetime.strptime(data["recorded_at"], "%a, %d %b %Y %H:%M:%S %Z")
    except ValueError:
        data["recorded_at"] = datetime.strptime(data["recorded_at"], "%a %b %d %H:%M:%S %Y")

    data["p1_steamid64"] = int.from_bytes(data["p1_steamid64"], byteorder="little")
    data["p2_steamid64"] = int.from_bytes(data["p2_steamid64"], byteorder="little")
    data["recorder_steamid64"] = int.from_bytes(data["recorder_steamid64"], byteorder="little")


def read_data(data: typing.Union[bytearray, bytes]) -> typing.Dict:
    data = parse_replay_data(data)
    data["filename"] = get_hashed_filename(data)
    decode_replay(data)
    return data


def process_network_response(response: flask.wrappers.Response) -> Union[Union[dict[str, str], dict[str, str]], Any]:
    try:
        if response.is_json:
            data = response.get_json()
            if response.status_code == 200:
                return data
            else:
                return {"error": f"Error {response.status_code}: {data.get('message', 'Unknown error')}"}

        return {"error": "Response is not JSON"}

    except ValueError:
        return {"error": "Invalid JSON response"}


def clear_cache_on_success(response, code):
    if code in (204, 201, 200):
        cache.clear()
    return response
