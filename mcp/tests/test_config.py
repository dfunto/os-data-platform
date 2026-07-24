from app.config import Config


def test_config_reads_cube_url_and_secret_from_env(monkeypatch):
    monkeypatch.setenv("CUBE_URL", "http://cube:4000")
    monkeypatch.setenv("CUBEJS_API_SECRET", "s3cret")

    cfg = Config.from_env()

    assert cfg.cube_url == "http://cube:4000"
    assert cfg.api_secret == "s3cret"


def test_config_defaults_to_localhost_when_unset(monkeypatch):
    monkeypatch.delenv("CUBE_URL", raising=False)
    monkeypatch.delenv("CUBEJS_API_SECRET", raising=False)

    cfg = Config.from_env()

    assert cfg.cube_url == "http://localhost:4000"
    assert cfg.api_secret == "dev-secret"
