FROM python:3.12

WORKDIR /orchestrator/
COPY pyproject.toml .
COPY src/ src/

# Make sure that logs show up immediately instead of being buffered
ENV PYTHONUNBUFFERED=1

RUN pip install --upgrade pip uv
RUN uv pip install --system -e .
EXPOSE 80