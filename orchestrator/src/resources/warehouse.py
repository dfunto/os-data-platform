import dagster as dg
from dagster_clickhouse.resource import ClickhouseResource


class WarehouseResource(ClickhouseResource):
    host: str = dg.EnvVar("CLICKHOUSE_ENDPOINT_URL")
    port: int = dg.EnvVar("CLICKHOUSE_PORT")
    user: str = dg.EnvVar("CLICKHOUSE_USER")
    password: str = dg.EnvVar("CLICKHOUSE_PASSWORD")
    database: str = dg.EnvVar("CLICKHOUSE_DATABASE")

