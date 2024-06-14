import asyncio
from flask.cli import FlaskGroup
from app import create_app, init_models

app = create_app()

cli = FlaskGroup(app)


@cli.command()
def init_db():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_models())
    print("Initialised database.")


if __name__ == "__main__":
    cli()
