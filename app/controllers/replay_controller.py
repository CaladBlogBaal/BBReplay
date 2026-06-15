import contextlib
import typing
from io import BytesIO

from zipfile import ZipFile
from typing import Union, Dict, Optional

import sqlalchemy
from sqlalchemy import RowMapping
from sqlalchemy.exc import NoResultFound

from quart import request

from app.schema import ReplayCreate, ReplayUpdate, ReplayQuery
from app.models.replay import Replay
from app.controllers.validation import validate_model_data, cast_attributes_to_types
from app.services.replay_service import ReplayService

from app.utils.helpers import read_data, friendly_file
from app.utils.constants import CHARACTERS


class ReplayController:
    def __init__(self, service: ReplayService):
        self.service = service

    async def stream_replay_projection(self, query_params: Dict[str, Union[int, str, bytes]],
                                       columns: typing.List[typing.Union[sqlalchemy.Column, sqlalchemy.Label]],
                                       per_page=None, page=1,
                                       assign_wins = True) -> typing.AsyncGenerator[RowMapping, None]:

        validated_data = validate_model_data(query_params, ReplayQuery)
        if type(validated_data) in (Replay, ReplayQuery):

            try:
                cast_attributes_to_types(query_params)
                async for row in self.service.stream_replay_projection(query_params, columns,
                                                                       per_page=per_page, page=page,
                                                                       assign_wins= assign_wins):
                    yield row

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

    async def count_replay_timestamps(self):
        return await self.service.count_replay_timestamps()

    async def get_all_filenames(self):
        return self.service.get_all_filenames()

    async def stream_replay_rows(self, query_params: Dict[str, Union[int, str, bytes]] = None,
                                 per_page=None, page=1,
                                 columns=None
                                 )  -> typing.AsyncGenerator[RowMapping, None]:
        if query_params:
            async for row in self.stream_replay_projection(query_params, columns, per_page=per_page, page=page):
                yield row
        else:
            async for row in self.service.stream_all_replay_projections(columns, per_page=per_page, page=page):
                yield row

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

    async def update_replay(self, filename: str) -> Optional[Union[dict[str, str], Replay]]:
        data = await request.get_json()
        replay_update = ReplayUpdate(**data)

        try:
            replay = await self.service.update_replay(filename, replay_update)
            return replay
        except NoResultFound:
            return

    async def delete_replay(self, filename: str) -> bool:

        try:
            await self.service.delete_replay(filename)
            return True
        except NoResultFound:
            return False

    async def download_replay(self, filename: str) -> Optional[tuple[BytesIO, str, str]]:
        try:
            data, filename, mimetype = await self.service.load_replay(filename)
            return data, filename, mimetype
        except NoResultFound:
            return

    async def download_replays(self, filenames: typing.List[str]) -> Optional[tuple[BytesIO, str, str]]:
        # to change later
        replays = []

        with contextlib.suppress(NoResultFound):
            async for replay in await self.service.load_replays(filenames):
                replays.append(replay)

            if not replays:
                return

            _, filename, _ = replays[0]
            base_filename, archive_mimetype = friendly_file(await anext(self.stream_replay_projection(
                {"filename": filename},[Replay.p1, Replay.p2, Replay.p1_toon, Replay.p2_toon])))
            stream = BytesIO()

            filename = base_filename.split("(")
            middle = filename[1].split("_")
            p1_initials = filename[0][0] + filename[0][-1]
            p1_toon_initials = middle[0][0] + middle[0][-2]
            p2_initials = middle[1][0] + middle[1][-1]
            p2_toon_initials = filename[2][0] + filename[2][-6]
            filename = f"{p1_initials}{p1_toon_initials}{p2_initials}{p2_toon_initials}.dat".lower()


            with ZipFile(stream, "w") as zf:
                for i, replay in enumerate(replays):
                    data, _, mimetype = replay
                    extension = f"({i}).dat" if i > 0 else ".dat"
                    zf.writestr(filename.replace(".dat", extension), data.getvalue())

            stream.seek(0)
            return stream, base_filename.replace("dat", "zip"), archive_mimetype
