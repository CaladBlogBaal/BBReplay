# BBReplay
## Introduction

BBReplay is a website to host and serve replay data from the game BlazBlue Central Fiction. Replays can be uploaded to the site to be later served and displayed. They can be filtered on the site through searches, by recorded_at date, player names, or characters used. The replays can be automatically uploaded through the BBCF Improvement Mod. This site was created as a personal project but can be used by others. Unlike the barebones BBCFIM site, BBReplay includes CSS for a better user experience. The site also exposes a public API for managing replays.
## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Features](#features)
- [Dependencies](#dependencies)
- [Configuration](#configuration)
- [Documentation](#documentation)
- [Contributors](#contributors)
- [License](#license)
<a name="installation"></a>
## Installation
Docker Setup

This project uses Docker for containerization. Follow the steps below to set up the project:

Build the Docker Image:
```shell
docker build -t bbreplay .
```
Run Docker Compose:

```shell
docker-compose -f compose.yaml up
```
Docker Compose File

The **\`compose.yaml`** file defines the services required for the application:
```yaml

services:
  db:
    image: postgres:latest
    container_name: postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: AuraKingdom1
      POSTGRES_DB: replaydb
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - my_network
  api:
    build:
      dockerfile: Dockerfile
      context: .
    ports:
      - "5000:5000"
    depends_on:
      - db
    networks:
      - my_network
    restart: "always"
  memcached:
    container_name: memcached
    image: memcached:latest
    networks:
      - my_network
    ports:
      - "11211:11211"
    restart: "always"

volumes:
  postgres_data:

networks:
  my_network:
```

The **\`Dockerfile`** specifies how the Docker image for the application is built:

```dockerfile

FROM python:3.9-slim

RUN apt-get update

ENV DATABASE_URL=postgresql+asyncpg://postgres:AuraKingdom1@db:5432/replaydb
ENV API_KEY=thunderiscute
ENV SECRET_KEY=API_KEY

COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip && pip install -r /tmp/requirements.txt

COPY . .

CMD ["python", "manage.py", "init-db"]

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app.wsgi:create_app()"]
```
<a name="usage"></a>
## Usage

The **\`manage.py`** file uses Flask CLI commands for application management. Here are the commands:
### Initialize the Database

To initialize the database, run:
```sh
python manage.py init_db
```

<a name="features"></a>
## Features

- Dockerized web application
- Replay management system with binary data handling
- Public API for retrieving replays

<a name="dependencies"></a>
## Dependencies

The following dependencies are specified for this project:

```plaintext
asyncpg==0.29.0
Flask[async]==3.0.3
Flask_Limiter==3.7.0
flask_wtf==1.2.1
pydantic==2.7.1
pydantic_settings==2.2.1
python-dotenv==1.0.1
python_dateutil==2.9.0.post0
pytz==2024.1
SQLAlchemy==2.0.30
WTForms==3.1.2
gunicorn==22.0.0
pymemcache==4.0.0
```
## Configuration

Configuration details can be managed through environment variables as defined in the `Dockerfile`:

- **\`DATABASE_URL`**: The URL for the PostgreSQL database
- **\`API_KEY`**: An API key for application use
- **\`SECRET_KEY`**: A secret key for security purposes

<a name="documentation"></a>
## Documentation

### API Endpoints

The routes are defined in routes/replay_routes.py
#### 1. GET /replays

- Description: Retrieve a list of all replays or filter replays based on query parameters.
- Parameters:

  - query_params (optional): Parameters for filtering replays.
  Response:
   Returns a JSON array containing replay data.
  
#### 2. POST /replays

- Description: Create a new replay.
- Request Body:
  - Binary data of the replay file.
- Response:
  - Returns JSON data of the created replay.

#### 3. GET /replays/{replay_id}

- Description: Retrieve a specific replay by its ID.
- Parameters:
   - replay_id: ID of the replay to retrieve. 
- Response:
   - Returns JSON data of the specified replay.

#### 4. PUT /replays/{replay_id}

- Description: Update an existing replay.
- Parameters:
   - replay_id: ID of the replay to update.
- Request Body:
   - JSON data containing attributes to update.
- Response:
   - Returns JSON data of the updated replay.

#### 5. DELETE /replays/{replay_id}

- Description: Delete a specific replay by its ID.
- Parameters:
   - replay_id: ID of the replay to delete.
- Response:
   - Returns a success message upon successful deletion.

#### 6. GET /replays/{replay_id}/download

- Description: Download a specific replay file by its ID.
- Parameters:
   - replay_id: ID of the replay to download.
- Response:
   - Returns the replay file as a downloadable attachment.

#### 7. POST /replays/download

- Description: Download multiple replays as a compressed ZIP file.
- Request Body:
   - JSON array of replay IDs to download.
- Response:
   - Returns a compressed ZIP file containing the requested replays.

Usage:

    Make HTTP requests to the respective endpoints using the appropriate HTTP methods (GET, POST, PUT, DELETE).
    Ensure that request parameters and body payloads adhere to the specified formats.
    Handle responses as per HTTP status codes returned by the API.

Note:

    Proper authentication and authorization mechanisms are implemented to secure access to UPDATE, DELETE API endpoints.

Troubleshooting

Contributors

License