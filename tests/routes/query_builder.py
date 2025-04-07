import pytest
from datetime import datetime
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.sqlite import dialect

from app.models.replay import Replay
from app.services.query_builder import QueryBuilder

Base = declarative_base()

def compile_query(query):
    return str(query.compile(dialect=dialect(), compile_kwargs={"literal_binds": True}))


@pytest.fixture
def qb():
    return QueryBuilder()


def test_simple_string_condition(qb):
    q = qb.build_query(Replay, {
        "p1": "Alice",
        "strict_side": False
    })
    sql = compile_query(q)

    assert "WHERE lower(replay_metadata.p1) LIKE '%alice%' OR lower(replay_metadata.p2) LIKE '%alice%'" in sql

    q = qb.build_query(Replay, {
        "p1": "Alice",
        "strict_side": True
    })
    sql = compile_query(q)

    assert "OR lower(replay_metadata.p2) LIKE '%alice%'" not in sql
    assert "WHERE lower(replay_metadata.p1) LIKE '%alice%'" in sql


def test_datetime_match(qb):
    dt = datetime(2023, 5, 12, 14, 30)
    q = qb.build_query(Replay, {"upload_datetime_": dt})
    sql = compile_query(q)
    assert "CAST(STRFTIME('%d', replay_metadata.upload_datetime_) AS INTEGER) = 12" in sql
    assert "CAST(STRFTIME('%H', replay_metadata.upload_datetime_) AS INTEGER) = 14" in sql
    assert "CAST(STRFTIME('%M', replay_metadata.upload_datetime_) AS INTEGER) = 30" in sql


def test_strict_side(qb):
    q = qb.build_query(Replay, {
        "p1": "Alice",
        "p2": "Bob",
        "p1_toon": 32,
        "strict_side": True
    })
    sql = compile_query(q)
    # Check that both (Alice = p1 and Bob = p2) AND the flipped values (Bob = p1 and Alice = p2) are present
    assert "lower(replay_metadata.p1) LIKE '%alice%' AND lower(replay_metadata.p2) LIKE '%bob%'" in sql
    assert "lower(replay_metadata.p1) LIKE '%bob%' AND lower(replay_metadata.p2) LIKE '%alice%'" in sql
    assert "AND replay_metadata.p1_toon = 32" in sql
    assert sql.count("OR") == 1


def test_flipped_side(qb):
    q = qb.build_query(Replay, {
        "p1": "Alice",
        "p2": "Bob",
        "p1_toon": 32,
        "strict_side": False
    })
    sql = compile_query(q)
    # if Alice is p1, she must have p1_toon = 32
    # ff Alice is p2, she must have p2_toon = 32
    assert "(lower(replay_metadata.p1) LIKE '%alice%' AND lower(replay_metadata.p2) LIKE '%bob%' OR lower(replay_metadata.p1) LIKE '%bob%' AND lower(replay_metadata.p2) LIKE '%alice%') AND (lower(replay_metadata.p1) LIKE '%alice%' AND replay_metadata.p1_toon = 32 " in sql
    assert "lower(replay_metadata.p2) LIKE '%bob%' OR lower(replay_metadata.p2) LIKE '%alice%' AND replay_metadata.p2_toon = 32 AND lower(replay_metadata.p1) LIKE '%bob%')" in sql
    assert sql.count("OR") > 1



def test_flipped_group_with_partial_fields(qb):
    q = qb.build_query(Replay, {
        "p1": "Alice",
        "p2_toon": 32,
        "strict_side": False
    })
    sql = compile_query(q)
    # Alice could be p1 or p2; p2_toon must match accordingly
    assert "lower(replay_metadata.p1) LIKE '%alice%'" in sql
    assert "replay_metadata.p2_toon = 32" in sql
    assert "lower(replay_metadata.p2) LIKE '%alice%'" in sql or "replay_metadata.p1_toon = 32" in sql

def test_datetime_range(qb):
    q = qb.build_query(Replay, {
        "datetime_": (datetime(2023, 1, 1), datetime(2023, 2, 1))
    })
    sql = compile_query(q)
    assert "replay_metadata.datetime_ BETWEEN '2023-01-01" in sql

def test_other_fields_only(qb):
    q = qb.build_query(Replay, {
        "filename": "game1",
        "recorder": "Alice"
    })
    sql = compile_query(q)
    assert "lower(replay_metadata.filename) LIKE '%game1%'" in sql
    assert "lower(replay_metadata.recorder) LIKE '%alice%'" in sql

def test_empty_query(qb):
    q = qb.build_query(Replay, {})
    sql = compile_query(q)
    assert "WHERE" not in sql
    assert sql.startswith("SELECT")