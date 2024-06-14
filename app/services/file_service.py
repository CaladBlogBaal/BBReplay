from app import replay_controller

# Allowed extensions for file uploads
ALLOWED_EXTENSIONS = ("dat")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


async def upload_replay(filename: str, data: bytes):

    if allowed_file(filename):
        return await replay_controller.create_replay(data)

