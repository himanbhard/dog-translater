FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN set -ex
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY src /app/src
COPY .env.template /app/.env.template

EXPOSE 8000

CMD ["sh", "-c", "uvicorn src.backend.server:app --host 0.0.0.0 --port ${PORT:-8080}"]
