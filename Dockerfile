FROM python:3.12-slim AS runtime

ARG PIP_INDEX_URL=
ARG PIP_EXTRA_INDEX_URL=
ARG PIP_TRUSTED_HOST=

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN set -eux; \
    pip_args=""; \
    if [ -n "$PIP_INDEX_URL" ]; then pip_args="$pip_args --index-url $PIP_INDEX_URL"; fi; \
    if [ -n "$PIP_EXTRA_INDEX_URL" ]; then pip_args="$pip_args --extra-index-url $PIP_EXTRA_INDEX_URL"; fi; \
    if [ -n "$PIP_TRUSTED_HOST" ]; then pip_args="$pip_args --trusted-host $PIP_TRUSTED_HOST"; fi; \
    pip install $pip_args -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts
COPY main.py .

RUN mkdir -p /files/articles

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
