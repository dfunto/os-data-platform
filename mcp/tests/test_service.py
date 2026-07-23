import pytest

from mcp_server.schema import ValidationError
from mcp_server.service import describe_schema, preview_sql, run_query

META = {
    "cubes": [
        {
            "name": "noaa_ghcn_stations",
            "title": "Stations",
            "measures": [{"name": "noaa_ghcn_stations.count", "type": "count", "title": "Count"}],
            "dimensions": [
                {"name": "noaa_ghcn_stations.country_name", "type": "string", "title": "Country"}
            ],
        }
    ]
}


class FakeCube:
    """Stand-in for CubeClient that records calls instead of doing HTTP."""

    def __init__(self):
        self.load_calls: list[dict] = []
        self.sql_calls: list[dict] = []

    def meta(self) -> dict:
        return META

    def load(self, query: dict) -> list[dict]:
        self.load_calls.append(query)
        return [{"noaa_ghcn_stations.count": "5"}]

    def sql(self, query: dict) -> str:
        self.sql_calls.append(query)
        return "SELECT count(*) FROM curated.noaa_ghcn_stations"


def test_describe_schema_lists_governed_members():
    result = describe_schema(FakeCube())

    cube = result["cubes"][0]
    assert cube["name"] == "noaa_ghcn_stations"
    assert {"noaa_ghcn_stations.count"} == {m["name"] for m in cube["measures"]}
    assert {"noaa_ghcn_stations.country_name"} == {d["name"] for d in cube["dimensions"]}


def test_run_query_passes_valid_query_and_returns_rows():
    fake = FakeCube()

    rows = run_query(fake, {"measures": ["noaa_ghcn_stations.count"]})

    assert rows == [{"noaa_ghcn_stations.count": "5"}]
    assert fake.load_calls == [{"measures": ["noaa_ghcn_stations.count"]}]


def test_run_query_fails_closed_and_never_calls_load_on_unknown_member():
    fake = FakeCube()

    with pytest.raises(ValidationError):
        run_query(fake, {"measures": ["noaa_ghcn_stations.made_up"]})

    assert fake.load_calls == []  # never reached Cube


def test_preview_sql_validates_then_returns_sql():
    fake = FakeCube()

    sql = preview_sql(fake, {"measures": ["noaa_ghcn_stations.count"]})

    assert "curated.noaa_ghcn_stations" in sql
    assert fake.sql_calls == [{"measures": ["noaa_ghcn_stations.count"]}]


def test_preview_sql_fails_closed_on_unknown_member():
    fake = FakeCube()

    with pytest.raises(ValidationError):
        preview_sql(fake, {"dimensions": ["noaa_ghcn_stations.nope"]})

    assert fake.sql_calls == []
