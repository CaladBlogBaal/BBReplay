from app import replay_controller


async def upload_replay(data: bytes):
    return await replay_controller.create_replay(data)

