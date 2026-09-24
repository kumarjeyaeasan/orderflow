# Build context: the repo root (so the image can install libs/common from the workspace).
# Pattern follows uv's Docker integration guide; flags verified against uv 0.12.18.

FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.18 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0
WORKDIR /app

# 1) Third-party dependencies only: this layer is cached until uv.lock or a pyproject changes.
COPY pyproject.toml uv.lock .python-version ./
COPY libs/common/pyproject.toml libs/common/pyproject.toml
COPY monolith/pyproject.toml monolith/pyproject.toml
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --package monolith --no-install-workspace

# 2) Our code, installed non-editable so the runtime image needs only the venv.
COPY libs/common libs/common
COPY monolith monolith
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --package monolith --no-editable


FROM python:3.12-slim
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app monolith/alembic.ini monolith/alembic.ini
COPY --chown=app:app monolith/migrations monolith/migrations
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
# Migrate, then serve. `exec` makes uvicorn PID 1 so it receives SIGTERM from `docker stop`.
CMD ["sh", "-c", "alembic -c monolith/alembic.ini upgrade head && exec uvicorn monolith.main:create_app --factory --host 0.0.0.0 --port 8000"]
