FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90 AS base

FROM base AS build
WORKDIR /build
COPY pyproject.toml .
COPY app/ app/
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir '.[llm]'

FROM base
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    DB_PATH=/data/pilot.db

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home app \
    && install -d -m 0750 -o app -g app /data
COPY --from=build /opt/venv /opt/venv

USER app
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
