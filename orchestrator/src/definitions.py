import dagster as dg


@dg.asset()
def ingest_s3(context: dg.AssetExecutionContext):
    """Transform raw orders into clean table."""
    context.log.info("todo...")
    # TODO: replace with actual transformation logic
    return {"rows": 0}
