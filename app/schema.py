import typing
from datetime import datetime

from pydantic import BaseModel


class ReplayCreate(BaseModel):
    replay: bytes
    p1: str
    p1_toon: int
    p2: str
    p2_toon: int
    recorder: str
    winner: bool
    filename: str
    datetime_: datetime
    p1_steamid64: int
    p2_steamid64: int
    recorder_steamid64: int


class ReplayUpdate(BaseModel):
    replay: bytes = None
    p1: str = None
    p1_toon: int = None
    p2: str = None
    p2_toon: int = None
    recorder: str = None
    winner: bool = None
    filename: str = None
    datetime_: datetime = None
    p1_steamid64: int = None
    p2_steamid64: int = None
    recorder_steamid64: int = None


class ReplayQuery(ReplayUpdate):
    datetime_: typing.Union[datetime, tuple[typing.Union[str, datetime]], list[typing.Union[str, datetime]]] = None

