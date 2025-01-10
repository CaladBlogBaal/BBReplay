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