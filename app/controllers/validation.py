import re
import typing
from datetime import datetime
from typing import Union, Dict, Any, Tuple, List

import pytz
from dateutil import parser
from pydantic import ValidationError

from app.models.replay import Replay
from app.schema import ReplayQuery


def cast_attributes_to_types(replay_instance: typing.Union[Replay, ReplayQuery, dict]):
    # Type hints dictionary mapping attribute names to their type hints
    type_hints = {
        'replay_id': int,
        'replay': bytes,
        'p1': str,
        'p1_character_id': int,
        'p2': str,
        'p2_character_id': int,
        'recorder': str,
        'winner': int,
        'filename': str,
        'recorded_at': parse_date_string,
        'upload_date': parse_date_string,
        'p1_steamid64': int,
        'p2_steamid64': int,
        'recorder_steamid64': int
    }

    for attr_name, attr_type in type_hints.items():
        if hasattr(replay_instance, attr_name):

            attr_value = getattr(replay_instance, attr_name)
        else:
            attr_value = replay_instance.get(attr_name, None)

        if attr_value is not None:

            casted_value = attr_type(attr_value)

            if not isinstance(replay_instance, dict):
                setattr(replay_instance, attr_name, casted_value)
            else:
                replay_instance[attr_name] = casted_value


def parse_date_string(date_object: typing.Union[str, datetime, typing.Tuple[Any], typing.List[Any]]) -> Union[
                    datetime, tuple[Union[datetime, tuple[datetime]], ...]]:
    try:
        # Parse object into a datetime object
        timezone = pytz.timezone("UTC")
        localized_datetime = timezone.localize(parser.parse(date_object))
        return localized_datetime
    except (ValueError, TypeError):
        if isinstance(date_object, datetime):
            return date_object

        elif isinstance(date_object, tuple) or isinstance(date_object, list):
            dates = []
            for element in date_object:
                dates.append(parse_date_string(element))
            return tuple(dates)
        else:
            raise TypeError("Invalid object was passed for date.")


def validate_model_data(data: Dict[str, Union[str, int, bytes]],
                        model: typing.Union[typing.Type[Replay], typing.Type[ReplayQuery]]) \
        -> Union[Replay, ReplayQuery, Dict[str, Any]]:
    try:
        pattern = r'"(.*?)"'
        # validate
        for key, value in data.items():
            # check if it's tuple or list string
            if not isinstance(value, str):
                continue

            if value.startswith("[") or value.startswith("(") and value.endswith("]") or value.endswith(")"):
                data[key] = re.findall(pattern, value)

        model = model(**data)
        return model

    except (ValidationError, TypeError) as e:
        return {"error": str(e)}
