#!/bin/sh
set -e

# Run the database initialization script
python manage.py init-db

# Start the Gunicorn server
exec gunicorn --bind 0.0.0.0:5000 "app.wsgi:create_app()"