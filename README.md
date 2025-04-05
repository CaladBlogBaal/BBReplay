# BBReplay
## Introduction

[BBReplay](https://bbreplay.ovh/) is a website to host and serve replay data from the game BlazBlue Central Fiction. Replays can be uploaded to the site to be served and displayed. They can be filtered on the site through creation date, player names, or characters used. Replays can be automatically uploaded through the [BBCF Improvement Mod fork](https://github.com/libreofficecalc/BBCF-Improvement-Mod/releases). This site was created as a personal project but can be used by others. The site also exposes a public API for managing replays.
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
docker build -t bbreplay_external .
```
Run Docker Compose:

```shell
docker compose -f compose.yaml up
```
Docker Compose File

The **\`compose.yaml`** file defines the services required for the application:
```yaml
services:
  api:
    build:
      dockerfile: Dockerfile
      context: .
    ports:
      - "5000:5000"
    volumes:
      - upload-files:/app/upload-files  # Docker volume for persistent storage
    networks:
      - my_network
    restart: "always"

volumes:
      - upload-files:/app/upload-files

networks:
  my_network:
```

The **\`Dockerfile`** specifies how the Docker image for the application is built:

```dockerfile
FROM python:3.9-slim

RUN apt-get update

ENV DATABASE_URL=mysql+asyncmy://username:password@host/database
ENV API_KEY=...
ENV SECRET_KEY=API_KEY

COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip && pip install -r /tmp/requirements.txt

COPY . .

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
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
aiohttp==3.11.11
asyncmy==0.2.10
pydantic==2.7.1
pydantic_settings==2.2.1
python-dotenv==1.0.1
python_dateutil==2.9.0.post0
pytz==2024.1
SQLAlchemy==2.0.30
Hypercorn==0.17.3
python-dateutil~=2.9.0.post0
pytest-asyncio==0.25.2
pydantic-settings~=2.2.1
quart-rate-limiter==0.11.0
quart-wtforms==1.0.3
Quart==0.20.0
WTForms==3.1.2
pytest==8.3.3
```
## Configuration

Configuration details can be managed through environment variables as defined in the `Dockerfile`:

- **\`DATABASE_URL`**: The URL for the database
- **\`API_KEY`**: An API key for application use
- **\`SECRET_KEY`**: A secret key for security purposes

<a name="documentation"></a>
## Documentation

### API Endpoints

The routes are defined in routes/replay_routes.py
#### 1. GET /api/filenames

- Description: Returns the names of all files in the database.
- Response:
  - Returns JSON array of filenames.
  
#### 2. GET /api/replays

- Description: Retrieve a list of all replays or filter replays based on query parameters.
- Parameters:
  - query_params (optional):

| query_params         | Type    | Description                                                                                 |
|----------------------|---------|---------------------------------------------------------------------------------------------|
| `filename`           | Integer | Unique identifier for each replay.                                                          |
| `p1`                 | String  | Player 1's name.                                                                            |
| `p1_toon`            | Integer | Character ID for Player 1, must be within the specified range. (0-35)                       |
| `p2`                 | String  | Player 2's name.                                                                            |
| `p2_toon`            | Integer | Character ID for Player 2, must be within the specified range. (0-35)                       |
| `recorder`           | String  | Name of the person who recorded the replay.                                                 |
| `p1_steamid64`       | Integer | Steam ID for Player 1.                                                                      |
| `p2_steamid64`       | Integer | Steam ID for Player 2.                                                                      |
| `recorder_steamid64` | Integer | Steam ID for the recorder.                                                                  |
| `include`            | Boolean | A flag for including replay binary.                                                         |
| `strict_side"`       | Boolean | A flag to decide to greedily ( check both sides ) for replays, default behaviour is greedy. |

  - Response:
   Returns a JSON array containing replay data.
  
#### 3. POST /api/replay

- Description: Create a new replay.
- Request Body:
  - Binary data of the replay file.
- Response:
  - Returns JSON data of the created replay.

#### 4. GET /api/replay?filename=<str:filename>

- Description: Retrieve a specific replay by its ID.
- Parameters:
   - filename: ID of the replay to retrieve. 
- Response:
   - Returns JSON data of the specified replay.

#### 5. PUT /api/replay?filename=<str:filename>

- Description: Update an existing replay.
- Parameters:
   - filename: ID of the replay to update.
- Request Body:
   - JSON data containing attributes to update.
- Response:
   - Returns JSON data of the updated replay.

#### 6. DELETE /api/replay?filename=<str:filename>

- Description: Delete a specific replay by its ID.
- Parameters:
   - filename: ID of the replay to delete.
- Response:
   - Returns a success message upon successful deletion.

#### 7. GET /download?filename=<str:filename>

- Description: Download a specific replay file by its ID.
- Parameters:
   - filename: ID of the replay to download.
- Response:
   - Returns the replay file as a downloadable attachment.

#### 8. POST /download-set?filenames=<json:str[]>

- Description: Download multiple replays as a compressed ZIP file.
- Request Body:
   - JSON array of replay filenames to download.
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