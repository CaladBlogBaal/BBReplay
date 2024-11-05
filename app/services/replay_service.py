import logging
import typing

from io import BytesIO
from datetime import datetime, timezone

import sqlalchemy
from sqlalchemy import func, extract, or_, and_, desc, case, cast
from sqlalchemy.future import select
from sqlalchemy.exc import NoResultFound

from app import db_manager
from app.models.replay import Replay
from app.schema import ReplayCreate, ReplayUpdate
from app.utils.helpers import friendly_file

logger = logging.getLogger(__name__)


class _ContextDBAcquire:
    __slots__ = ("ctx", "session")

    def __init__(self, session_factory: db_manager):
        self.ctx = session_factory.get_db_session
        self.session = None

    def __await__(self):
        self.session = self.ctx.__await__()
        return self.session

    async def __aenter__(self):
        self.session = await self.ctx()
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session is None:
            return
        if exc_type is not None:
            await self.session.rollback()
        await self.session.close()


class ReplayService:
    def __init__(self, session_factory: db_manager):
        self.db_manager = session_factory

    def acquire(self):
        return _ContextDBAcquire(self.db_manager)

    async def get_replay(self, replay_id: int) -> Replay:

        async with self.acquire() as session:
            replay = await session.get(Replay, replay_id)

            if not replay:
                raise NoResultFound("Replay not found")

            logger.info(f"Returned replay with ID: {replay_id}")
            return replay

    def build_conditions(self, model, key, value, use_or=True):
        conditions = []

        if isinstance(value, str):
            value = value.strip().lower()
            if key.startswith("p"):
                p1 = key.replace("2", "1")
                p2 = p1.replace("1", "2")
                conditions.append(func.lower(getattr(model, p1)).like(f"%{value}%"))
                conditions.append(func.lower(getattr(model, p2)).like(f"%{value}%"))
            else:
                conditions.append(func.lower(getattr(model, key)).like(f"%{value}%"))

        elif isinstance(value, datetime):
            day_condition = extract("day", getattr(model, key)) == value.day
            month_condition = extract("month", getattr(model, key)) == value.month
            hour_condition = extract("hour", getattr(model, key)) == value.hour
            minute_condition = extract("minute", getattr(model, key)) == value.minute
            conditions.extend([day_condition, month_condition, hour_condition, minute_condition])

        elif isinstance(value, tuple) or isinstance(value, list) and len(value) == 2:
            start, end = value
            conditions.append(getattr(model, key).between(start, end))

        else:
            if key.startswith("p"):
                p1 = key.replace("2", "1")
                p2 = p1.replace("1", "2")
                conditions.append(getattr(model, p1) == value)
                conditions.append(getattr(model, p2) == value)
            else:
                conditions.append(getattr(model, key) == value)

        if use_or:
            return or_(*conditions)
        else:
            return and_(*conditions)

    def build_query(self, model, query_params, use_or=True):
        query = select(model)
        for key, value in query_params.items():
            condition = self.build_conditions(model, key, value, use_or=use_or)
            query = query.where(condition)
        return query

    async def get_total_replays_query_count(self, query_params: dict = None) -> int:
        async with self.acquire() as session:
            if query_params:
                query = self.build_query(Replay, query_params)
                count_query = query.with_only_columns(func.count())  # Count query
                result = await session.execute(count_query)
                total_replays = result.scalar()
            else:
                result = await session.execute(select(func.count(Replay.replay_id)))
                total_replays = result.scalar()  # Get the total count of replays

            return total_replays

    async def get_total_pages(self, query_params: dict = None, per_page=10) -> int:
        """Calculate the total number of pages."""
        total_replays = await self.get_total_replays_query_count(query_params)
        total_pages = (total_replays + per_page - 1) // per_page  # Round up to next page if there are leftovers
        return total_pages

    @staticmethod
    async def _stream_replays(query, session) -> typing.AsyncGenerator[Replay, None]:
        # Peek at the first result to check if there are any results
        query = query.order_by(desc(Replay.recorded_at))
        first_replay = await (await session.stream_scalars(query)).first()
        if not first_replay:
            raise NoResultFound("Replay(s) not found")

        async for replay in await session.stream_scalars(query):
            yield replay

    async def get_total_replays(self):
        async with self.acquire() as session:
            logger.info(f"Returned total count of replays.")
            return (await session.execute(select(func.count(Replay.replay_id)))).scalar()

    async def get_total_unique_players(self):
        async with self.acquire() as session:
            result = await session.execute(select(
                func.count(func.distinct(Replay.recorder_steamid64)))
            )
            total_players = result.scalar()
            logger.info(f"Returned total count of unique players.")
            return total_players

    async def get_total_replays_per_character(self):
        async with self.acquire() as session:
            query = select(
                func.count(Replay.p1_character_id == Replay.p2_character_id).label("total"),
                Replay.p1_character_id.label("character_id")
            ).group_by(
                Replay.p1_character_id
            ).order_by(func.count().desc())

            results = (await session.execute(query)).fetchall()

            logger.info(f"Returned total replays per character.")
            return results

    async def get_matchup_statistics(self, character_id: int = None):
        async with self.acquire() as session:
            matchup_query = (
                select(
                    func.least(Replay.p1_character_id, Replay.p2_character_id).label("character_1_id"),
                    func.greatest(Replay.p1_character_id, Replay.p2_character_id).label("character_2_id"),
                    func.count().label("matches_played"),
                    # Calculate win rates for each character by dividing their wins by total matches and converting that to a percentage
                    func.round(
                        (func.sum(
                            case(

                                ((Replay.p1_character_id == func.least(Replay.p1_character_id,
                                                                       Replay.p2_character_id)) & (
                                         Replay.winner == 0), 1),
                                ((Replay.p2_character_id == func.least(Replay.p1_character_id,
                                                                       Replay.p2_character_id)) & (
                                         Replay.winner == 1), 1)
                                ,
                                else_=0
                            )
                        ) / func.count()) * 100, 2
                    ).label("p1_win_rate"),

                    func.round(
                        (func.sum(
                            case(

                                ((Replay.p1_character_id == func.greatest(Replay.p1_character_id,
                                                                          Replay.p2_character_id)) & (
                                         Replay.winner == 0), 1),
                                ((Replay.p2_character_id == func.greatest(Replay.p1_character_id,
                                                                          Replay.p2_character_id)) & (
                                         Replay.winner == 1), 1)
                                ,
                                else_=0
                            )
                        ) / func.count()) * 100, 2
                    ).label("p2_win_rate")
                )
                .group_by(
                    func.least(Replay.p1_character_id, Replay.p2_character_id),
                    func.greatest(Replay.p1_character_id, Replay.p2_character_id)
                )
                .order_by(func.count().desc())
            )
            if character_id:
                matchup_query = matchup_query.where(
                    or_(Replay.p1_character_id == character_id,
                        Replay.p2_character_id == character_id))

            results = (await session.execute(matchup_query)).fetchall()
            logger.info(f"Returned matchup statistics.")
            return results

    async def get_matchup_rarity(self):
        async with self.acquire() as session:
            # Subquery to calculate total replays
            total_replays_subquery = select(func.count(Replay.replay_id)).scalar_subquery()

            matchup_rarity = (
                select(
                    func.least(Replay.p1_character_id, Replay.p2_character_id).label("character_1_id"),
                    func.greatest(Replay.p1_character_id, Replay.p2_character_id).label("character_2_id"),
                    func.count().label("matchup_count"),
                    func.round(
                        (func.count() / total_replays_subquery)
                        * 100, 2).label("percentage")
                )
                .group_by(
                    func.least(Replay.p1_character_id, Replay.p2_character_id),
                    func.greatest(Replay.p1_character_id, Replay.p2_character_id)
                )
                .order_by("matchup_count")
            )
            results = (await session.execute(matchup_rarity)).fetchall()

            logger.info(f"Returned matchup statistics.")
            return results

    async def get_character_usage_statistics(self):
        async with self.acquire() as session:
            # Subquery for player 1 statistics
            p1_query = (
                select(
                    Replay.p1_character_id.label("character_id"),
                    func.count().label("matches_played"),
                    func.round(
                        func.avg(
                            case(
                                # If p1 is the recorder and Replay.winner == 0, p1 won;
                                (Replay.recorder_steamid64 == Replay.p1_steamid64,
                                 cast(not Replay.winner == 0, sqlalchemy.Integer)),
                                else_=0
                            )
                        ) * 100, 2
                    ).label("win_rate")
                )
                .group_by(Replay.p1_character_id)
            )

            # Subquery for player 2 statistics
            p2_query = (
                select(
                    Replay.p2_character_id.label("character_id"),
                    func.count().label("matches_played"),
                    func.round(
                        func.avg(
                            case(
                                # If p2 is the recorder and Replay.winner == 1, p2 won
                                (Replay.recorder_steamid64 == Replay.p2_steamid64, Replay.winner),
                                else_=0
                            )
                        ) * 100, 2
                    ).label("win_rate")
                )
                .group_by(Replay.p2_character_id)
            )

            # Combine both queries with UNION to get overall statistics
            combined_query = p1_query.union_all(p2_query).subquery()

            # Summarize combined results by character_id
            final_query = (
                select(
                    combined_query.c.character_id,
                    func.sum(combined_query.c.matches_played).label("total_matches"),
                    func.round(func.avg(combined_query.c.win_rate), 2).label("average_win_rate")
                )
                .group_by(combined_query.c.character_id)
                .order_by(func.sum(combined_query.c.matches_played).desc())
            )

            results = (await session.execute(final_query)).fetchall()
            logger.info(f"Returned character usage statistics.")

            return results

    async def get_all_replay_timestamps(self):
        async with self.acquire() as session:
            query = select(Replay.recorded_at)

            async for replay in self._stream_replays(query, session):
                yield replay

            logger.info(f"Returned all replay timestamps.")

    async def get_replays(self, query_params: typing.Dict[str, typing.Union[int, str, bytes]],
                          per_page=None, page=1) -> typing.AsyncGenerator[Replay, None]:
        async with self.acquire() as session:

            query = self.build_query(Replay, query_params)

            if per_page:  # Add pagination to the query
                offset = (page - 1) * per_page
                query = query.limit(per_page).offset(offset)

            replay_ids = []

            async for replay in self._stream_replays(query, session):
                yield replay
                replay_ids.append(str(replay.replay_id))

            if replay_ids:
                logger.info(f"Returned replay(s) with ID(s): {','.join(replay_ids)}")

    async def get_all_replays(self, per_page=None, page=1) -> typing.AsyncGenerator[Replay, None]:
        async with self.acquire() as session:

            query = select(Replay)

            if per_page:  # Apply pagination
                offset = (page - 1) * per_page
                query = select(Replay).limit(per_page).offset(offset)

            async for replay in self._stream_replays(query, session):
                yield replay

            if per_page:
                logger.info(f"Returned all replays for page {page}")
            else:
                logger.info(f"Returned all replays")

    async def create_replay(self, replay_create: ReplayCreate) -> Replay:
        new_replay = Replay(
            replay=replay_create.replay,
            recorded_at=replay_create.recorded_at,
            winner=replay_create.winner,
            p1=replay_create.p1,
            p2=replay_create.p2,
            p1_character_id=replay_create.p1_character_id,
            p2_character_id=replay_create.p2_character_id,
            recorder=replay_create.recorder,
            filename=replay_create.filename,
            p1_steamid64=replay_create.p1_steamid64,
            p2_steamid64=replay_create.p2_steamid64,
            recorder_steamid64=replay_create.recorder_steamid64,
            upload_date=datetime.now(timezone.utc)
        )

        async with self.acquire() as session:
            session.add(new_replay)
            await session.commit()
            await session.refresh(new_replay)
            logger.info(f"Created new replay with ID: {new_replay.replay_id}")
            return new_replay

    async def update_replay(self, replay_id: int, replay_update: ReplayUpdate) -> Replay:
        async with self.acquire() as session:
            replay = await anext(self.get_replays({"replay_id": replay_id}))

            for key, value in replay_update.dict(exclude_unset=True).items():
                setattr(replay, key, value)

            await session.commit()
            await session.refresh(replay)
            logger.info(f"Updated replay with ID: {replay.id}")
            return replay

    async def delete_replay(self, replay_id: int) -> None:
        async with self.acquire() as session:
            replay = await self.get_replay(replay_id)
            await session.delete(replay)
            await session.commit()
            logger.info(f"Deleted user with ID: {replay.id}")

    async def load_replay(self, replay_id: int) -> tuple[BytesIO, str, str]:
        replay = await self.get_replay(replay_id)
        filename, mimetype = friendly_file(replay)
        buffer = BytesIO(replay.replay)
        buffer.seek(0)
        buffer.name = replay.filename
        return buffer, filename, mimetype

    async def load_replays(self, replay_ids: typing.Collection[int]) -> typing.Generator[BytesIO, str, str]:
        for ri in replay_ids:
            yield await self.load_replay(ri)
