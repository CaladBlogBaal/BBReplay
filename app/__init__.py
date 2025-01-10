import asyncio
import os

from quart import Quart

from app.config import settings
from app.controllers.replay_controller import ReplayController
from app.db_manager import DBManager
from app.core import limiter
from app.services.replay_service import ReplayService

# Set the event loop explicitly so the DBManager and Quart use the same loop
asyncio.set_event_loop(asyncio.new_event_loop())

db_manager = DBManager()
replay_service = ReplayService(db_manager)
replay_controller = ReplayController(replay_service)

def create_app():

    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_folder = os.path.join(current_dir, "templates")

    # Use Quart instead of Flask
    app = Quart(__name__, template_folder=os.path.join(os.getcwd(), template_folder))
    app.config["UPLOAD_FOLDER"] = os.path.join(os.getcwd(), "upload-files")
    app.config["DATABASE_URL"] = settings.database_url
    app.config["API_KEY"] = settings.api_key
    app.config["SECRET_KEY"] = settings.secret
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB limit
    # Initialize DBManager with a logger instance
    logger_handler_instance = app.logger  # Use Quart's logger
    db_manager.initialize(logger_handler_instance)
    # Setup controllers
    app.replay_controller = replay_controller

    # Quart requires async app context setup for things like imports
    @app.before_serving
    async def before_serving():
        # Import parts of our application
        from .routes import replay_routes, page_routes
        from app.utils.request import request_handler
        # run the worker in the background
        print("Starting the request handler worker...")
        asyncio.create_task(request_handler.start())
        # Register Blueprints
        app.register_blueprint(replay_routes.bp)
        app.register_blueprint(page_routes.bp)

    @app.after_serving
    async def shutdown():
        # import parts of the app to gracefully clean resources
        from app.utils.request import request_handler
        """Stop the async worker after the app stops serving requests."""
        print("Stopping the request handler worker...")
        await request_handler.stop()

    return app


# Add a method to initialize the models
async def init_models():
    await db_manager.init_models()
