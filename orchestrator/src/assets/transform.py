import dagster as dg

from collections.abc import Iterable
from pathlib import Path
from dagster_sqlmesh import sqlmesh_assets, SQLMeshContextConfig, SQLMeshResource, SQLMeshDagsterTranslator
from sqlmesh import Context


TRANSFORM_PATH = str(Path(__file__).resolve().parents[2] / ".." / "transform")


class CustomTranslator(SQLMeshDagsterTranslator):
    """Maps SQLMesh external table refs to ingestion asset keys.

    Ingestion assets use key format: raw_{source}_{table}
    SQLMesh refs raw tables as: raw.{table}
    """

    def get_asset_key(self, context: Context, fqn: str) -> dg.AssetKey:
        parts = self.get_asset_key_name(fqn)
        # FQNs come as ['', 'schema', 'table_name']
        # Flatten to single key: {schema}_{table_name}
        if parts[0] == '' and len(parts) == 3:
            return dg.AssetKey(f"{parts[1]}_{parts[2]}")
        return super().get_asset_key(context, fqn)


class CustomSQLMeshContextConfig(SQLMeshContextConfig):
    def get_translator(self) -> CustomTranslator:
        return CustomTranslator()


sqlmesh_config = CustomSQLMeshContextConfig(
    path=TRANSFORM_PATH,
    gateway="clickhouse",
)

def build_transform_assets():
    @sqlmesh_assets(
        environment="prod",
        config=sqlmesh_config,
    )
    def transform_assets(
        context: dg.AssetExecutionContext,
        sqlmesh: SQLMeshResource
    ) -> Iterable[dg.MaterializeResult]:
        yield from sqlmesh.run(
            context,
            config=sqlmesh_config,
            environment="prod",
        )

    return transform_assets
