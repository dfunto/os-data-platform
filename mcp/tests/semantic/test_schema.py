import pytest

from app.tools.semantic.schema import Schema, ValidationError, parse_meta, validate_query

SAMPLE_META = {
    "cubes": [
        {
            "name": "noaa_ghcn_stations",
            "title": "Stations",
            "measures": [
                {"name": "noaa_ghcn_stations.count", "type": "count", "title": "Count"},
            ],
            "dimensions": [
                {"name": "noaa_ghcn_stations.country_name", "type": "string", "title": "Country"},
                {"name": "noaa_ghcn_stations.state_name", "type": "string", "title": "State"},
            ],
        },
        {
            "name": "noaa_ghcn_station_year",
            "title": "Station year",
            "measures": [
                {"name": "noaa_ghcn_station_year.observation_count", "type": "sum"},
            ],
            "dimensions": [
                {"name": "noaa_ghcn_station_year.country_name", "type": "string"},
            ],
        },
    ]
}


def test_parse_meta_collects_measures_and_dimensions():
    schema = parse_meta(SAMPLE_META)

    assert "noaa_ghcn_stations.count" in schema.measures
    assert "noaa_ghcn_station_year.observation_count" in schema.measures
    assert "noaa_ghcn_stations.country_name" in schema.dimensions
    assert len(schema.cubes) == 2


def test_validate_query_accepts_known_members():
    schema = parse_meta(SAMPLE_META)

    # does not raise
    validate_query(
        {"measures": ["noaa_ghcn_stations.count"], "dimensions": ["noaa_ghcn_stations.country_name"]},
        schema,
    )


def test_validate_query_rejects_unknown_measure():
    schema = parse_meta(SAMPLE_META)

    with pytest.raises(ValidationError) as exc:
        validate_query({"measures": ["noaa_ghcn_stations.total_rainfall"]}, schema)

    assert "noaa_ghcn_stations.total_rainfall" in str(exc.value)


def test_validate_query_rejects_unknown_dimension_in_time_dimensions():
    schema = parse_meta(SAMPLE_META)

    with pytest.raises(ValidationError) as exc:
        validate_query(
            {"timeDimensions": [{"dimension": "noaa_ghcn_stations.made_up_date", "granularity": "year"}]},
            schema,
        )

    assert "noaa_ghcn_stations.made_up_date" in str(exc.value)


def test_validate_query_rejects_unknown_member_in_filters():
    schema = parse_meta(SAMPLE_META)

    with pytest.raises(ValidationError) as exc:
        validate_query(
            {
                "measures": ["noaa_ghcn_stations.count"],
                "filters": [{"member": "noaa_ghcn_stations.bogus", "operator": "equals", "values": ["x"]}],
            },
            schema,
        )

    assert "noaa_ghcn_stations.bogus" in str(exc.value)


def test_validate_query_requires_at_least_one_measure_or_dimension():
    schema = parse_meta(SAMPLE_META)

    with pytest.raises(ValidationError):
        validate_query({}, schema)
