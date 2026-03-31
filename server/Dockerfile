FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY server/pyproject.toml /app/pyproject.toml
COPY server/app /app/app
COPY server/tests /app/tests
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir ".[dev]"

CMD ["python", "-m", "app.main"]
