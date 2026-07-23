"""Runtime configuration, read from the environment.

Defaults target local development where Cube runs via ``semantic/docker-compose``
and is reachable on ``localhost:4000`` with the ``dev-secret`` API secret.
"""

import os
from dataclasses import dataclass


@dataclass
class Config:
    cube_url: str
    api_secret: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            cube_url=os.environ.get("CUBE_URL", "http://localhost:4000"),
            api_secret=os.environ.get("CUBEJS_API_SECRET", "dev-secret"),
        )
