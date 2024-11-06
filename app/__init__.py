import asyncio
import os

from flask import Flask

from app.config import settings
from app.controllers.replay_controller import ReplayController
from app.db_manager import DBManager
from app.core import limiter
from app.services.replay_service import ReplayService

# Set the event loop explicitly so the DBManager and Flask use the same loop
asyncio.set_event_loop(asyncio.new_event_loop())

db_manager = DBManager()
replay_service = ReplayService(db_manager)
replay_controller = ReplayController(replay_service)


def create_app():

    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_folder = os.path.join(current_dir, "templates")

    app = Flask(__name__,  template_folder=os.path.join(os.getcwd(), template_folder))
    limiter.init_app(app)  # Rate limiter
    app.config["DATABASE_URL"] = settings.database_url
    app.config["API_KEY"] = settings.api_key
    app.config["SECRET_KEY"] = settings.secret
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB limit
    # Initialize DBManager with a logger instance
    logger_handler_instance = app.logger  # Use Flask's logger
    db_manager.initialize(logger_handler_instance)
    # Setup controllers
    app.replay_controller = replay_controller

    with app.app_context():
        # Import parts of our application
        from .routes import replay_routes, page_routes

        # Register Blueprints
        app.register_blueprint(replay_routes.bp)
        app.register_blueprint(page_routes.bp)

        return app


# Add a method to initialize the models
async def init_models():
    await db_manager.init_models()
