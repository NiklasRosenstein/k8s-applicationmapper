FROM python:3.13-alpine
COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /bin/
COPY --from=alpine/helm:4.3.0 /usr/bin/helm /bin/
WORKDIR /app
COPY pyproject.toml README.md *.py uv.lock /app
RUN uv sync --frozen --no-dev
ENV PATH="$PATH:/app/.venv/bin"
CMD applicationmapper
