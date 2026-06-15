import logging
import typing

from io import BytesIO
from datetime import datetime
from typing import AsyncGenerator

import sqlalchemy
from sqlalchemy import func, or_, case, cast, Select, RowMapping, desc
from sqlalchemy.future import select
from sqlalchemy.exc import NoResultFound

from app import db_manager
from app.models.replay import Replay
from app.schema import ReplayCreate, ReplayUpdate
from app.services.bbcfim_service import BBCFIM
from app.services.query_builder import QueryBuilder

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
        self.query_builder = QueryBuilder()

    def acquire(self):
        return _ContextDBAcquire(self.db_manager)

    async def get_replay(self, filename: str) -> Replay:

        async with self.acquire() as session:
            replay = await session.get(Replay, filename)

            if not replay:
                raise NoResultFound("Replay not found")

            logger.info(f"Returned replay with ID: {filename}")
            return replay

    async def get_total_replays_query_count(self, query_params: dict = None) -> int:
        async with self.acquire() as session:
            if query_params:
                query = self.query_builder.build_query(Replay, query_params)
                count_query = query.with_only_columns(func.count())  # Count query
                result = await session.execute(count_query)
                total_replays = result.scalar()
            else:
                result = await session.execute(select(func.count(Replay.filename)))
                total_replays = result.scalar()  # Get the total count of replays

            return total_replays

    async def get_total_pages(self, query_params: dict = None, per_page=10) -> int:
        """Calculate the total number of pages."""
        total_replays = await self.get_total_replays_query_count(query_params)
        total_pages = (total_replays + per_page - 1) // per_page  # Round up to next page if there are leftovers
        return total_pages

    @staticmethod
    async def _stream_query_results(
            acquire_session: _ContextDBAcquire.__aenter__,
            query_factory: typing.Callable[[], Select],
            yield_per: int = 10000,
    ) -> AsyncGenerator[typing.Any, None]:

        async with acquire_session() as session:
            try:
                query = query_factory()
                stream = await session.stream(query.execution_options(yield_per=yield_per))

                async for row in stream:
                    yield row

            except Exception as e:
                await session.rollback()
                logger.exception("Streaming query failed: %s", str(e))
                raise

    @staticmethod
    async def _stream_mappings(query, session) -> typing.AsyncGenerator[Replay, None]:
        check = True
        stream = await session.stream(query)

        async for row in stream.mappings():
            check = False
            yield row

        # If the stream is empty nothing was found
        if check:
            raise NoResultFound("Replay(s) not found")

    async def get_total_replays(self):
        async with self.acquire() as session:
            logger.info(f"Returned total count of replays.")
            return (await session.execute(select(func.count(Replay.filename)))).scalar()

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
                func.count(Replay.p1_toon == Replay.p2_toon).label("total"),
                Replay.p1_toon.label("character_id")
            ).group_by(
                Replay.p1_toon
            ).order_by(func.count().desc())

            results = (await session.execute(query)).fetchall()

            logger.info(f"Returned total replays per character.")
            return results

    async def get_matchup_statistics(self, character_id: int = None):
        async with self.acquire() as session:
            matchup_query = (
                select(
                    func.least(Replay.p1_toon, Replay.p2_toon).label("character_1_id"),
                    func.greatest(Replay.p1_toon, Replay.p2_toon).label("character_2_id"),
                    func.count().label("matches_played"),
                    # Calculate win rates for each character by dividing their wins by total matches and converting that to a percentage
                    func.round(
                        (func.sum(
                            case(

                                ((Replay.p1_toon == func.least(Replay.p1_toon,
                                                               Replay.p2_toon)) & (
                                         Replay.winner == 0), 1),
                                ((Replay.p2_toon == func.least(Replay.p1_toon,
                                                               Replay.p2_toon)) & (
                                         Replay.winner == 1), 1)
                                ,
                                else_=0
                            )
                        ) / func.count()) * 100, 2
                    ).label("p1_win_rate"),

                    func.round(
                        (func.sum(
                            case(

                                ((Replay.p1_toon == func.greatest(Replay.p1_toon,
                                                                  Replay.p2_toon)) & (
                                         Replay.winner == 0), 1),
                                ((Replay.p2_toon == func.greatest(Replay.p1_toon,
                                                                  Replay.p2_toon)) & (
                                         Replay.winner == 1), 1)
                                ,
                                else_=0
                            )
                        ) / func.count()) * 100, 2
                    ).label("p2_win_rate")
                )
                .group_by(
                    func.least(Replay.p1_toon, Replay.p2_toon),
                    func.greatest(Replay.p1_toon, Replay.p2_toon)
                )
                .order_by(func.count().desc())
            )
            if character_id:
                matchup_query = matchup_query.where(
                    or_(Replay.p1_toon == character_id,
                        Replay.p2_toon == character_id))

            results = (await session.execute(matchup_query)).fetchall()
            logger.info(f"Returned matchup statistics.")
            return results

    async def get_matchup_rarity(self):
        async with self.acquire() as session:
            # Subquery to calculate total replays
            total_replays_subquery = select(func.count(Replay.filename)).scalar_subquery()

            matchup_rarity = (
                select(
                    func.least(Replay.p1_toon, Replay.p2_toon).label("character_1_id"),
                    func.greatest(Replay.p1_toon, Replay.p2_toon).label("character_2_id"),
                    func.count().label("matchup_count"),
                    func.round(
                        (func.count() / total_replays_subquery)
                        * 100, 2).label("percentage")
                )
                .group_by(
                    func.least(Replay.p1_toon, Replay.p2_toon),
                    func.greatest(Replay.p1_toon, Replay.p2_toon)
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
                    Replay.p1_toon.label("character_id"),
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
                .group_by(Replay.p1_toon)
            )

            # Subquery for player 2 statistics
            p2_query = (
                select(
                    Replay.p2_toon.label("character_id"),
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
                .group_by(Replay.p2_toon)
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

    async def count_replay_timestamps(self):
        async with self.acquire() as session:
            result = await session.execute(
                select(
                    func.hour(Replay.datetime_).label("hour"),
                    func.count().label("total")
                )
                .group_by(func.hour(Replay.datetime_))
                .order_by(func.hour(Replay.datetime_))
            )

            return result.mappings().all()

    async def get_all_filenames(self):
        async for row in self._stream_query_results(
                acquire_session=self.acquire,
                query_factory=lambda: select(Replay.filename),
                yield_per=10000
        ):
            yield row.filename

        logger.info(f"Returned all filenames.")

    async def stream_replay_projection(self, query_params: typing.Dict[str, typing.Union[int, str, bytes]],
                                       columns: typing.List[typing.Union[sqlalchemy.Column, sqlalchemy.Label]],
                                       per_page=1000, page=1,
                                       assign_wins=True
                                       ) -> typing.AsyncGenerator[RowMapping, None]:
        async with self.acquire() as session:
            if assign_wins:
                p1wins = case(
                    (
                        Replay.recorder_steamid64 == Replay.p1_steamid64,
                        case((Replay.winner == 0, 1), else_=0),
                    ),
                    else_=(1 - Replay.winner),
                ).label("p1wins")

                p2wins = (1 - p1wins).label("p2wins")
                columns.append(p1wins)
                columns.append(p2wins)

            query = self.query_builder.build_query(Replay, query_params, projection=True, columns=columns)

            query = query.order_by(desc(Replay.datetime_))

            if per_page:  # Add pagination to the query
                offset = (page - 1) * per_page
                query = query.limit(per_page).offset(offset)

            count = 0

            async for replay in self._stream_mappings(query, session):
                yield replay
                count += 1

            logger.info(f"Returned {count} replays")

    async def stream_all_replay_projections(self, columns,
                                            per_page=None,
                                            page=1) -> typing.AsyncGenerator[Replay, None]:
        async with self.acquire() as session:

            query = select(*columns)

            if per_page:  # Apply pagination
                offset = (page - 1) * per_page
                query = select(Replay).limit(per_page).offset(offset)

            async for row in self._stream_mappings(query, session):
                yield row

            if per_page:
                logger.info(f"Returned all replays for page {page}")
            else:
                logger.info(f"Returned all replays")

    async def create_replay(self, replay_create: ReplayCreate) -> Replay:
        new_replay = Replay(
            filename=replay_create.filename,
            datetime_=replay_create.datetime_,
            upload_datetime_=datetime.now(),
            winner=replay_create.winner,
            p1=replay_create.p1,
            p2=replay_create.p2,
            p1_toon=replay_create.p1_toon,
            p2_toon=replay_create.p2_toon,
            recorder=replay_create.recorder,
            p1_steamid64=replay_create.p1_steamid64,
            p2_steamid64=replay_create.p2_steamid64,
            recorder_steamid64=replay_create.recorder_steamid64
        )

        async with self.acquire() as session:
            session.add(new_replay)
            await session.commit()
            await session.refresh(new_replay)
            logger.info(f"Created new replay with ID: {new_replay.filename}")
            return new_replay

    async def update_replay(self, filename: str, replay_update: ReplayUpdate) -> Replay:
        async with self.acquire() as session:
            replay = await anext(self.stream_replay_projection({"filename": filename}))

            for key, value in replay_update.dict(exclude_unset=True).items():
                setattr(replay, key, value)

            await session.commit()
            await session.refresh(replay)
            logger.info(f"Updated replay with ID: {replay.filename}")
            return replay

    async def delete_replay(self, filename: str) -> None:
        async with self.acquire() as session:
            replay = await self.get_replay(filename)
            await session.delete(replay)
            await session.commit()
            logger.info(f"Deleted user with ID: {replay.id}")

    async def load_replay(self, filename: str) -> tuple[BytesIO, str, str]:
        # going to change this later
        return await BBCFIM().download_file(filename)

        # replay = await self.get_replay(filename)
        # filename, mimetype = friendly_file(replay)
        # buffer = BytesIO(replay.replay)
        # buffer.seek(0)
        # buffer.name = replay.filename
        # return buffer, filename, mimetype

    async def load_replays(self, filenames: typing.List[str]) -> AsyncGenerator[typing.Union[str, BytesIO], None]:
        # going to change this later
        return BBCFIM().download_files(filenames)

        # for fn in filenames:
        #     yield await self.load_replay(fn)
