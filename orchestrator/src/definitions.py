from dagster import (
    AssetExecutionContext,
    Definitions,
    ScheduleDefinition,
    asset,
    define_asset_job,
)


@asset
def raw_orders(context: AssetExecutionContext):
    """Ingest raw orders data from source."""
    context.log.info("Ingesting raw orders...")
    # TODO: replace with actual ingestion logic
    return {"rows": 0}


@asset(deps=[raw_orders])
def orders(context: AssetExecutionContext):
    """Transform raw orders into clean table."""
    context.log.info("Transforming orders...")
    # TODO: replace with actual transformation logic
    return {"rows": 0}


orders_job = define_asset_job(
    name="orders_job",
    selection=[raw_orders, orders],
)

orders_schedule = ScheduleDefinition(
    job=orders_job,
    cron_schedule="0 6 * * *",  # daily at 6am
)

defs = Definitions(
    assets=[raw_orders, orders],
    jobs=[orders_job],
    schedules=[orders_schedule],
)