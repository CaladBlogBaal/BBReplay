#!/bin/sh
set -e

# Run the database initialization script
python manage.py init-db

# Start the hypercorn server
exec hypercorn --bind 0.0.0.0:5000 "app.asgi:create_app()"