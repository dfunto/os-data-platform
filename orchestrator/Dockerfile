FROM python:3.12-slim

# uv binary from official image (faster than pip-installing it)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /orchestrator/

# Make sure that logs show up immediately instead of being buffered
ENV PYTHONUNBUFFERED=1
# uv: compile to bytecode at build time, copy instead of hardlink across mounts
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml README.md ./
COPY src/ src/
COPY --from=libs . /libs/
COPY --from=transform . /transform/

RUN uv pip install --system -e .

# Build the dbt manifest at image build (parse needs no DB; profiles have env
# defaults). dagster-dbt loads assets from this manifest at import time.
RUN dbt parse --project-dir /transform --profiles-dir /transform

EXPOSE 80
