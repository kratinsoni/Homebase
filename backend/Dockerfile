FROM python:3.12-slim

FROM python:3.12-slim

# uv, copied from its official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1

COPY . .
RUN uv sync --frozen --all-packages

ENV PATH="/app/.venv/bin:$PATH"