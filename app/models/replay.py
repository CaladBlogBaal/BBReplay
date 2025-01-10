import base64

from app.models import Base

from sqlalchemy import (
    Column,
    Integer,
    String,
    Sequence, CheckConstraint, DateTime,
)

from sqlalchemy.dialects.postgresql import BYTEA, SMALLINT, TIMESTAMP, BIGINT

from app.services.bbcfim_service import BBCFIM
from app.utils.request import RequestFailed


class Replay(Base):
    __tablename__ = "replay_metadata"
    p1 = Column(String(255))
    p1_toon = Column(Integer)
    p2 = Column(String(255))
    p2_toon = Column(Integer)
    recorder = Column(String(255))
    winner = Column(Integer)
    filename = Column(String(255), primary_key=True)
    upload_datetime_ = Column(type_=DateTime)
    datetime_ = Column(type_=DateTime)
    p1_steamid64 = Column(BIGINT)
    p2_steamid64 = Column(BIGINT)
    recorder_steamid64 = Column(BIGINT)

    async def to_dict(self, include_replay_data=False):
        model_dict = {column.name: getattr(self, column.name) for column in self.__table__.columns}
        if include_replay_data:
            try:
                replay, _, _ = await BBCFIM().download_file(model_dict["filename"])
                model_dict["replay"] = base64.b64encode(replay.read()).decode("utf-8")
            except RequestFailed as e:
                return
        else:
            model_dict.pop("replay", None)

        return model_dict
