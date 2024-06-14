FROM python:3.9-slim

RUN apt-get update

ENV DATABASE_URL=postgresql+asyncpg://postgres:AuraKingdom1@db:5432/replaydb
ENV API_KEY=...
ENV SECRET_KEY=API_KEY

COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip && pip install -r /tmp/requirements.txt

COPY . .

CMD ["python", "manage.py", "init-db"]

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app.wsgi:create_app()"]