FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
	&& playwright install --with-deps --only-shell chromium \
	&& rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

COPY alembic.ini ./
COPY alembic ./alembic
COPY assets ./assets
COPY sistema ./sistema

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn sistema.app.main:app --host 0.0.0.0 --port 8000"]
