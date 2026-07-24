"""Integration tests against a live Cube instance.

Requires Cube reachable at ``CUBE_URL`` (default localhost:4000), i.e.
``make forward`` + ``make cube`` from the repo root. Run with:

    uv run --extra dev pytest -m integration
"""

import os

import pytest

from app.tools.semantic.client import CubeClient
from app.tools.semantic.schema import ValidationError
from app.tools.semantic.service import describe_schema, run_query

pytestmark = pytest.mark.integration


def live_client() -> CubeClient:
    return CubeClient(
        base_url=os.environ.get("CUBE_URL", "http://localhost:4000"),
        api_secret=os.environ.get("CUBEJS_API_SECRET", "dev-secret"),
    )


def test_describe_schema_returns_the_noaa_cubes():
    result = describe_schema(live_client())

    names = {c["name"] for c in result["cubes"]}
    assert {"noaa_ghcn_stations", "noaa_ghcn_station_year", "noaa_ghcn_observations"} <= names


def test_run_query_returns_station_count_by_country():
    rows = run_query(
        live_client(),
        {
            "measures": ["noaa_ghcn_stations.count"],
            "dimensions": ["noaa_ghcn_stations.country_name"],
            "order": {"noaa_ghcn_stations.count": "desc"},
            "limit": 5,
        },
    )

    assert rows
    assert "noaa_ghcn_stations.count" in rows[0]


def test_unmodelled_member_fails_closed():
    with pytest.raises(ValidationError):
        run_query(live_client(), {"measures": ["noaa_ghcn_stations.made_up_measure"]})
