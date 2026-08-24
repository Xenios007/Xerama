"""Settings/config tests (MODULE-002 - Configuration & Environment)."""

from xerama.config import ModelRoleRegistry, Settings
from xerama.domain.enums import ModelRole


def test_settings_defaults_are_safe_for_local_and_test_runs() -> None:
    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite+aiosqlite:///./xerama.db"
    assert settings.asset_storage_path == "./storage"
    assert settings.ffmpeg_path == "ffmpeg"
    assert settings.xerama_mode == "standard"
    assert settings.openrouter_api_key.get_secret_value() == ""


def test_settings_env_override(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./other.db")
    monkeypatch.setenv("FFMPEG_PATH", "/usr/local/bin/ffmpeg")
    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite+aiosqlite:///./other.db"
    assert settings.ffmpeg_path == "/usr/local/bin/ffmpeg"


def test_openrouter_api_key_is_redacted_from_repr_and_str(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-super-secret-value")
    settings = Settings(_env_file=None)
    assert "sk-super-secret-value" not in repr(settings)
    assert "sk-super-secret-value" not in str(settings)
    assert "sk-super-secret-value" not in str(settings.openrouter_api_key)
    assert settings.openrouter_api_key.get_secret_value() == "sk-super-secret-value"


def test_model_role_registry_falls_back_to_free_defaults_when_unset() -> None:
    registry = ModelRoleRegistry(Settings(_env_file=None))
    resolved = registry.resolve(ModelRole.JUDGE)
    assert resolved.model  # a free-tier default, not empty
    assert resolved.role == ModelRole.JUDGE


def test_model_role_registry_respects_explicit_override() -> None:
    settings = Settings(_env_file=None, judge_model="my-org/pinned-model")
    registry = ModelRoleRegistry(settings)
    resolved = registry.resolve(ModelRole.JUDGE)
    assert resolved.model == "my-org/pinned-model"
