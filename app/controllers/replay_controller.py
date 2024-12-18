import contextlib
import typing
from io import BytesIO

from zipfile import ZipFile
from typing import Union, Dict, Optional, Any

import sqlalchemy
from sqlalchemy.exc import NoResultFound

from flask import request

from app.schema import ReplayCreate, ReplayUpdate, ReplayQuery
from app.models.replay import Replay
from app.controllers.validation import validate_model_data, cast_attributes_to_types
from app.services.replay_service import ReplayService

from app.utils.helpers import read_data
from app.utils.constants import CHARACTERS


class ReplayController:
    def __init__(self, service: ReplayService):
        self.service = service

    async def get_replay(self, query_params: Dict[str, Union[int, str, bytes]], per_page=None, page=1) -> \
            typing.AsyncGenerator[Replay, None]:
        validated_data = validate_model_data(query_params, ReplayQuery)
        if type(validated_data) in (Replay, ReplayQuery):

            try:
                cast_attributes_to_types(query_params)
                async for replay in self.service.get_replays(query_params, per_page=per_page, page=page):
                    yield replay

            except NoResultFound:
                return
        else:
            # Data is invalid, return error response
            yield {"message": "data is invalid"}.update(validated_data)

    async def get_character_usage_statistics(self):

        rows = await self.service.get_character_usage_statistics()
        character_stats = [
            {
                "character_id": row.character_id,
                "total_matches": row.total_matches,
                "average_win_rate": row.average_win_rate
            }
            for row in rows
        ]

        return character_stats

    async def get_character_matchup_statistics(self, character_id: int = None):
        rows = await self.service.get_matchup_statistics(character_id)

        matchup_stats = [
            {
                "character_1_id": row.character_1_id,
                "character_2_id": row.character_2_id,
                "matches_played": row.matches_played,
                "character_1_win_rate": row.p1_win_rate,
                "character_2_win_rate": row.p2_win_rate,
                "character_1_name": CHARACTERS[row.character_1_id],
                "character_2_name": CHARACTERS[row.character_2_id]
            }
            for row in rows if row.character_1_id != row.character_2_id
        ]

        return matchup_stats

    async def get_total_replays(self):
        return await self.service.get_total_replays()

    async def get_total_replays_per_character(self):
        rows = await self.service.get_total_replays_per_character()
        total_per_character = [
            {
                "character_id": row.character_id,
                "total": row.total,
                "character_name": CHARACTERS[row.character_id]
            }
            for row in rows
        ]
        return total_per_character

    async def get_matchup_rarity(self):
        rows = await self.service.get_matchup_rarity()
        matchup_rarity = [
            {
                "character_1_id": row.character_1_id,
                "character_2_id": row.character_2_id,
                "matchup_count": row.matchup_count,
                "percentage": row.percentage,
                "character_1_name": CHARACTERS[row.character_1_id],
                "character_2_name": CHARACTERS[row.character_2_id]

            }
            for row in rows
        ]
        return matchup_rarity

    async def get_total_unique_players(self):
        return await self.service.get_total_unique_players()

    async def get_all_replay_timestamps(self):
        return self.service.get_all_replay_timestamps()

    async def get_replays(self, query_params: Dict[str, Union[int, str, bytes]] = None, per_page=None, page=1) \
            -> typing.AsyncGenerator[Replay, None]:
        if query_params:
            async for replay in self.get_replay(query_params, per_page=per_page, page=page):
                yield replay
        else:
            async for replay in self.service.get_all_replays(per_page=per_page, page=page):
                yield replay

    async def get_total_pages(self, query_params: dict = None, per_page=10) -> int:
        return await self.service.get_total_pages(query_params, per_page=per_page)

    async def create_replay(self, data: bytes) -> Optional[Union[dict[str, str], Replay]]:
        data = read_data(data)
        replay_create = ReplayCreate(**data)

        try:
            replay = await self.service.create_replay(replay_create)
        except sqlalchemy.exc.IntegrityError:
            return
        return replay

    async def update_replay(self, replay_id: int) -> Optional[Union[dict[str, str], Replay]]:
        data = request.get_json()
        replay_update = ReplayUpdate(**data)

        try:
            replay = await self.service.update_replay(replay_id, replay_update)
            return replay
        except NoResultFound:
            return

    async def delete_replay(self, replay_id: int) -> bool:

        try:
            await self.service.delete_replay(replay_id)
            return True
        except NoResultFound:
            return False

    async def download_replay(self, replay_id: int) -> Optional[tuple[BytesIO, str, str]]:
        try:
            data, filename, mimetype = await self.service.load_replay(replay_id)
            return data, filename, mimetype
        except NoResultFound:
            return

    async def download_replays(self, replay_ids: typing.Collection[int]) -> Optional[tuple[BytesIO, str, str]]:
        replays = []

        with contextlib.suppress(NoResultFound):
            async for replay in self.service.load_replays(replay_ids):
                replays.append(replay)

            if not replays:
                return

            _, base_filename, _ = replays[0]
            stream = BytesIO()
            archive_mimetype = "application/octet-stream"

            with ZipFile(stream, "w") as zf:
                for i, replay in enumerate(replays):
                    data, filename, mimetype = replay

                    filename = filename.split("(")
                    middle = filename[1].split("_")

                    extension = f"({i}).dat" if i > 0 else ".dat"
                    p1_initials = filename[0][0] + filename[0][-1]
                    p1_toon_initials = middle[0][0] + middle[0][-2]
                    p2_initials = middle[1][0] + middle[1][-1]
                    p2_toon_initials = filename[2][0] + filename[2][-6]
                    filename = f"{p1_initials}_{p1_toon_initials}_{p2_initials}_{p2_toon_initials}{extension}".lower()

                    zf.writestr(filename, data.getvalue())

            stream.seek(0)
            return stream, base_filename, archive_mimetype
