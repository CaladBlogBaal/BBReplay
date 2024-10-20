import base64

from app.models import Base

from sqlalchemy import (
    Column,
    Integer,
    String,
    Sequence, CheckConstraint,
)

from sqlalchemy.dialects.postgresql import BYTEA, SMALLINT, TIMESTAMP, BIGINT


class Replay(Base):
    __tablename__ = "replays"
    replay_id = Column(Integer, Sequence("replays_id_seq", start=1, increment=1), primary_key=True)
    replay = Column(BYTEA)
    p1 = Column(String(255))
    p1_character_id = Column(SMALLINT, CheckConstraint("p1_character_id >= 0 AND p1_character_id <= 35"))
    p2 = Column(String(255), CheckConstraint("p2_character_id >= 0 AND p2_character_id <= 35"))
    p2_character_id = Column(SMALLINT, CheckConstraint("p2_character_id >= 0 AND p2_character_id <= 35"))
    recorder = Column(String(255))
    winner = Column(Integer)
    filename = Column(String(255), unique=True)
    recorded_at = Column(type_=TIMESTAMP(timezone=True))
    upload_date = Column(type_=TIMESTAMP(timezone=True))
    p1_steamid64 = Column(BIGINT)
    p2_steamid64 = Column(BIGINT)
    recorder_steamid64 = Column(BIGINT)

    def to_dict(self, include_replay_data=False):
        model_dict = {column.name: getattr(self, column.name) for column in self.__table__.columns}
        if include_replay_data:
            replay = model_dict.get("replay")
            if replay:
                # Convert binary data to base64-encoded string
                model_dict["replay"] = base64.b64encode(self.replay).decode("utf-8")
        else:
            model_dict.pop("replay", None)

        return model_dict
