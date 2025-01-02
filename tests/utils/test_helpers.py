import pytest

from tests.constants import REPLAYS, REPlAYS_2ND, REPlAYS_3RD, REPLAYS_SET
from tests.helpers import generate_mock_replays_from_data
from app.utils.helpers import total_up_wins, collapse_replays_into_sets, order_by_criteria_replays


@pytest.mark.unit
def test_total_up_wins():
    p1wins, p2wins = total_up_wins(REPLAYS["replays"])
    assert p1wins == 8
    assert p2wins == 0
    p1wins, p2wins = total_up_wins(REPlAYS_2ND["replays"])
    assert p1wins == 1
    assert p2wins == 8
    p1wins, p2wins = total_up_wins(REPlAYS_3RD["replays"])
    assert p2wins == 20
    assert p1wins == 13


@pytest.mark.unit
def test_collapse_replays_into_sets():
    replays = [replay.to_dict(include_replay_data=False)
               for replay in generate_mock_replays_from_data(REPLAYS)]
    replays = collapse_replays_into_sets(replays)

    assert replays[0]["filename"] == REPLAYS["replays"][-1]["filename"]


@pytest.mark.unit
def test_order_replays_by_options():
    replays = REPLAYS_SET["replays"]
    order_by_criteria_replays(replays, pos="LEFT", search=[76561198079498381])
    assert all(replay["p1"] == "Dark Souls II" for replay in replays)
    order_by_criteria_replays(replays, pos="RIGHT", search=["Dark"])
    assert all(replay["p2"] == "Dark Souls II" for replay in replays)
    order_by_criteria_replays(replays, pos="LEFT", search=["Dark"], outcome="WON")
    assert all(replay["p1"] == "Dark Souls II" and replay["p1wins"] > replay["p2wins"] for replay in replays)
