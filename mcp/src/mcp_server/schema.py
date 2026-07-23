"""Governed schema parsing and query validation.

The schema is derived solely from Cube's ``/meta`` response, so the set of
queryable members is exactly what the semantic model exposes. ``validate_query``
rejects any member outside that set before a request ever reaches Cube, which is
how the server fails closed on anything unmodelled.
"""

from dataclasses import dataclass, field


class ValidationError(ValueError):
    """Raised when a query references members outside the governed schema."""


@dataclass
class Member:
    name: str
    type: str
    title: str = ""
    description: str = ""


@dataclass
class Cube:
    name: str
    title: str
    measures: list[Member] = field(default_factory=list)
    dimensions: list[Member] = field(default_factory=list)


@dataclass
class Schema:
    cubes: list[Cube] = field(default_factory=list)
    measures: set[str] = field(default_factory=set)
    dimensions: set[str] = field(default_factory=set)


def _member(raw: dict) -> Member:
    return Member(
        name=raw["name"],
        type=raw.get("type", ""),
        title=raw.get("title", ""),
        description=raw.get("description", ""),
    )


def parse_meta(meta: dict) -> Schema:
    """Turn a Cube ``/meta`` payload into a governed :class:`Schema`."""
    schema = Schema()
    for raw_cube in meta.get("cubes", []):
        measures = [_member(m) for m in raw_cube.get("measures", [])]
        dimensions = [_member(d) for d in raw_cube.get("dimensions", [])]
        schema.cubes.append(
            Cube(
                name=raw_cube["name"],
                title=raw_cube.get("title", raw_cube["name"]),
                measures=measures,
                dimensions=dimensions,
            )
        )
        schema.measures.update(m.name for m in measures)
        schema.dimensions.update(d.name for d in dimensions)
    return schema


def validate_query(query: dict, schema: Schema) -> None:
    """Raise :class:`ValidationError` if the query touches unmodelled members."""
    measures = query.get("measures", []) or []
    dimensions = query.get("dimensions", []) or []
    time_dimensions = query.get("timeDimensions", []) or []
    filters = query.get("filters", []) or []

    if not measures and not dimensions and not time_dimensions:
        raise ValidationError(
            "Query must reference at least one measure, dimension, or time dimension."
        )

    unknown: list[str] = []
    unknown += [m for m in measures if m not in schema.measures]
    unknown += [d for d in dimensions if d not in schema.dimensions]
    unknown += [
        td.get("dimension")
        for td in time_dimensions
        if td.get("dimension") not in schema.dimensions
    ]
    unknown += _unknown_filter_members(filters, schema)

    if unknown:
        raise ValidationError(
            "Unknown members not in the semantic model: " + ", ".join(sorted(set(unknown)))
        )


def _unknown_filter_members(filters: list, schema: Schema) -> list[str]:
    known = schema.measures | schema.dimensions
    unknown: list[str] = []
    for f in filters:
        member = f.get("member")
        if member is not None and member not in known:
            unknown.append(member)
        # boolean filters nest child conditions under and/or
        for key in ("and", "or"):
            if key in f:
                unknown += _unknown_filter_members(f[key], schema)
    return unknown
