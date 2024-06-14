import os
import contextlib
import typing
from io import BytesIO

from zipfile import ZipFile
from typing import Union, Dict

import sqlalchemy
from sqlalchemy.exc import NoResultFound

from flask import request, jsonify, Response, send_file

from app.schema import ReplayCreate, ReplayUpdate, ReplayQuery
from app.models.replay import Replay
from app.controllers.validation import validate_model_data, cast_attributes_to_types
from app.services.replay_service import ReplayService

from app.utils.helpers import read_data


class ReplayController:
    def __init__(self, service: ReplayService):
        self.service = service

    async def get_replay(self, query_params: Dict[str, Union[int, str, bytes]]) -> Union[
                            Response, tuple[Response, int]]:
        validated_data = validate_model_data(query_params, ReplayQuery)
        if type(validated_data) in (Replay, ReplayQuery):

            try:
                cast_attributes_to_types(query_params)
                replays = await self.service.get_replays(query_params)
                return jsonify([replay.to_dict() for replay in replays]), 201
            except NoResultFound:
                return jsonify({"message": "Replay(s) not found"}), 404
        else:
            # Data is invalid, return error response
            return jsonify(validated_data), 400

    async def get_replays(self, query_params: Dict[str, Union[int, str, bytes]] = None) -> Union[
                            Response, tuple[Response, int]]:
        if query_params:
            return await self.get_replay(query_params)

        replays = await self.service.get_all_replays()
        return jsonify([replay.to_dict() for replay in replays]), 201

    async def create_replay(self, data: bytes) -> Union[Response, tuple[Response, int]]:
        data = read_data(data)
        replay_create = ReplayCreate(**data)

        try:
            replay = await self.service.create_replay(replay_create)
        except sqlalchemy.exc.IntegrityError:
            return jsonify({"message": "Replay already exists"}), 404
        return jsonify(replay.to_dict()), 201

    async def update_replay(self, replay_id: int) -> Union[Response, tuple[Response, int]]:
        data = request.get_json()
        replay_update = ReplayUpdate(**data)

        try:
            user = await self.service.update_replay(replay_id, replay_update)
            return jsonify(user.to_dict()), 204
        except NoResultFound:
            return jsonify({"message": "Replay not found"}), 404

    async def delete_replay(self, replay_id: int) -> Union[tuple[str, int], tuple[Response, int]]:

        try:
            await self.service.delete_replay(replay_id)
            return "", 204
        except NoResultFound:
            return jsonify({"message": "Replay not found"}), 404

    async def download_replay(self, replay_id: int) -> Union[tuple[Response, int], None]:
        try:
            data, filename, mimetype = await self.service.load_replay(replay_id)
        except NoResultFound:
            return jsonify({"message": "Replay not found"}), 404

        return send_file(data, as_attachment=True, download_name=filename, mimetype=mimetype), 200

    async def download_replays(self, replay_ids: typing.Collection[int]) -> Union[tuple[Response, int], None]:
        replays = []

        with contextlib.suppress(NoResultFound):
            async for replay in self.service.load_replays(replay_ids):
                replays.append(replay)

            if not replays:
                return jsonify(
                    {"message": f"Replay(s) with ID(s): {','.join(str(n) for n in replay_ids)} not found"}), 404

            stream = BytesIO()

            with ZipFile(stream, "w") as zf:
                for i, replay in enumerate(replays):
                    data, filename, mimetype = replay
                    zf.writestr(filename + f"_{i}", data.getvalue())

            _, filename, _ = replays[0]

            stream.seek(0)
            return send_file(stream, as_attachment=True,
                             download_name=f"replays-{os.path.splitext(filename)[0]}.zip"), 200
