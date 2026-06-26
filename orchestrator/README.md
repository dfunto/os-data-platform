# Orchestrator

# Build and push image

```shell
docker-compose build
docker push dadutra2/os-data-platform-orchestrator:latest
```

```shell
docker-compose up -d user_code

# Test definitions
docker-compose exec user_code dagster definitions validate -m src.definitions

# Test asset
docker-compose exec user_code dagster asset materialize --select ingest_source1_table1 -m src.definitions
```