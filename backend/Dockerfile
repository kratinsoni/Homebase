# syntax=docker/dockerfile:1
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1

# 1. Only the files that list the packages
COPY pyproject.toml uv.lock ./
COPY api/pyproject.toml api/pyproject.toml
COPY worker/pyproject.toml worker/pyproject.toml

# 2. Install the third-party packages only.
#    This layer is cached until pyproject.toml or uv.lock changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --all-packages --no-install-workspace

# 3. Now the source code
COPY . .

# 4. Install your own packages (api, worker). This takes a few seconds.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --all-packages

ENV PATH="/app/.venv/bin:$PATH"