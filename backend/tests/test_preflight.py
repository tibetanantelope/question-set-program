from backend.preflight import collect_config_issues


def test_preflight_reports_partial_llm_configuration(monkeypatch):
    monkeypatch.setenv("SQL_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("API_KEY", "configured")
    monkeypatch.setenv("MODEL_NAME", "")
    monkeypatch.setenv("API_URL", "")
    monkeypatch.setenv("ALIPAY_APP_ID", "")
    monkeypatch.setenv("ALIPAY_PRIVATE_KEY_PATH", "")
    monkeypatch.setenv("ALIPAY_PUBLIC_KEY_PATH", "")

    issues = collect_config_issues()

    assert any("LLM 配置不完整" in issue for issue in issues)


def test_preflight_accepts_complete_core_configuration(monkeypatch):
    monkeypatch.setenv("SQL_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    for name in (
        "API_KEY",
        "MODEL_NAME",
        "API_URL",
        "ALIPAY_APP_ID",
        "ALIPAY_PRIVATE_KEY_PATH",
        "ALIPAY_PUBLIC_KEY_PATH",
    ):
        monkeypatch.setenv(name, "")

    assert collect_config_issues() == []
