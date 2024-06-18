FROM python:3.9-slim

RUN apt-get update

ENV DATABASE_URL=postgresql+asyncpg://postgres:AuraKingdom1@db:5432/replaydb
ENV API_KEY=...
ENV SECRET_KEY=API_KEY

COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip && pip install -r /tmp/requirements.txt

COPY . .

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]