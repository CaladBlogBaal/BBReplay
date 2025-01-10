import typing
from datetime import datetime
from app.models.replay import Replay


async def async_generator_mock(data: typing.Iterable):
    for item in data:
        yield item


# Function to generate mock Replay instances from the provided REPLAYS data
def generate_mock_replays_from_data(replays_data: dict) -> typing.List[Replay]:
    mock_replays = []
    for replay_data in replays_data['replays']:
        replay = Replay(
            filename=replay_data['filename'],
            p1=replay_data['p1'],
            p1_toon=replay_data['p1_toon'],
            p1_steamid64=replay_data['p1_steamid64'],
            p2=replay_data['p2'],
            p2_toon=replay_data['p2_toon'],
            p2_steamid64=replay_data['p2_steamid64'],
            recorder=replay_data['recorder'],
            winner=replay_data['winner'],
            datetime_=datetime.strptime(replay_data['datetime_'], '%a, %d %b %Y %H:%M:%S GMT'),
            upload_datetime_=datetime.strptime(replay_data['upload_datetime_'], '%a, %d %b %Y %H:%M:%S GMT'),
            recorder_steamid64=replay_data['recorder_steamid64'],
        )
        mock_replays.append(replay)

    return mock_replays
