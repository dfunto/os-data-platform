"""Request models for the MCP tools.

``CubeQuery`` is the single shape shared by every query-style tool. FastMCP
introspects it to build the tool input schema, and ``to_cube`` renders the Cube
REST payload (``exclude_none`` drops unset members; the ``timeDimensions`` alias
matches Cube's camelCase vocabulary).
"""

from typing import Any

from pydantic import BaseModel, Field


class CubeQuery(BaseModel):
    measures: list[str] | None = None
    dimensions: list[str] | None = None
    filters: list[dict[str, Any]] | None = None
    time_dimensions: list[dict[str, Any]] | None = Field(
        default=None, serialization_alias="timeDimensions"
    )
    order: dict[str, str] | None = None
    limit: int | None = None

    def to_cube(self) -> dict:
        """Render the Cube REST query payload, dropping unset members."""
        return self.model_dump(by_alias=True, exclude_none=True)