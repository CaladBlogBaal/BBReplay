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
            replay_id=replay_data['replay_id'],
            replay=b'\x00\x01\x02\x03',  # Example binary data
            p1=replay_data['p1'],
            p1_character_id=replay_data['p1_character_id'],
            p1_steamid64=replay_data['p1_steamid64'],
            p2=replay_data['p2'],
            p2_character_id=replay_data['p2_character_id'],
            p2_steamid64=replay_data['p2_steamid64'],
            recorder=replay_data['recorder'],
            winner=replay_data['winner'],
            filename=replay_data['filename'],
            recorded_at=datetime.strptime(replay_data['recorded_at'], '%a, %d %b %Y %H:%M:%S GMT'),
            upload_date=datetime.strptime(replay_data['upload_date'], '%a, %d %b %Y %H:%M:%S GMT'),
            recorder_steamid64=replay_data['recorder_steamid64'],
        )
        mock_replays.append(replay)

    return mock_replays
