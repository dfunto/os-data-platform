import httpx
import jwt as pyjwt
import pytest
import respx

from mcp_server.cube import CubeClient, CubeError

BASE = "http://cube.test:4000"
SECRET = "dev-secret"


def make_client() -> CubeClient:
    return CubeClient(base_url=BASE, api_secret=SECRET)


@respx.mock
def test_meta_calls_cube_and_returns_payload():
    route = respx.get(f"{BASE}/cubejs-api/v1/meta").mock(
        return_value=httpx.Response(200, json={"cubes": [{"name": "c"}]})
    )

    meta = make_client().meta()

    assert meta == {"cubes": [{"name": "c"}]}
    assert route.called


@respx.mock
def test_requests_carry_a_valid_bearer_token():
    captured = {}

    def handler(request):
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"cubes": []})

    respx.get(f"{BASE}/cubejs-api/v1/meta").mock(side_effect=handler)

    make_client().meta()

    assert captured["auth"].startswith("Bearer ")
    token = captured["auth"].removeprefix("Bearer ")
    # signed with the shared secret, so Cube can verify it
    pyjwt.decode(token, SECRET, algorithms=["HS256"])


@respx.mock
def test_load_posts_query_and_returns_rows():
    route = respx.post(f"{BASE}/cubejs-api/v1/load").mock(
        return_value=httpx.Response(200, json={"data": [{"noaa_ghcn_stations.count": "42"}]})
    )

    rows = make_client().load({"measures": ["noaa_ghcn_stations.count"]})

    assert rows == [{"noaa_ghcn_stations.count": "42"}]
    sent = route.calls.last.request
    assert b"noaa_ghcn_stations.count" in sent.content


@respx.mock
def test_load_raises_cube_error_on_error_response():
    respx.post(f"{BASE}/cubejs-api/v1/load").mock(
        return_value=httpx.Response(400, json={"error": "Some error"})
    )

    with pytest.raises(CubeError) as exc:
        make_client().load({"measures": ["bad"]})

    assert "Some error" in str(exc.value)


@respx.mock
def test_sql_returns_compiled_sql_string():
    respx.post(f"{BASE}/cubejs-api/v1/sql").mock(
        return_value=httpx.Response(200, json={"sql": {"sql": ["SELECT 1 FROM t WHERE x = ?", ["a"]]}})
    )

    sql = make_client().sql({"measures": ["noaa_ghcn_stations.count"]})

    assert "SELECT 1 FROM t" in sql
