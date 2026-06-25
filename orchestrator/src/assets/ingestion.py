import dagster as dg

from common.models import IngestionConfig


def build_ingestion_asset(config: IngestionConfig):
    @dg.asset(name=f"ingest_{config.name}")
    def _asset(context: dg.AssetExecutionContext):
        context.log.info(f"Ingesting {config.source_type}: {config.name}")
        return {"rows": 0}
    return _asset
