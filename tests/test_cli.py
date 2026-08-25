"""MODULE-071 - the CLI entrypoint (`python -m xerama.cli`) had zero
test coverage: a contributor could break its wiring (it constructs its
own AIGateway/repositories independently of the API's `lifespan`) and
nothing would catch it short of a manual run against a real API key.
"""

import json

import pytest

import fixtures as fx
import xerama.cli as cli
from xerama.config import get_settings
from xerama.providers.fake import FakeLLMProvider


def test_parse_args_reads_required_and_default_fields() -> None:
    args = cli._parse_args(["--genre", "thriller"])
    assert args.genre == "thriller"
    assert args.name == "Trial 01"
    assert args.episode_count == 3
    assert args.episode_duration == 75


def test_parse_args_overrides_defaults() -> None:
    args = cli._parse_args(
        ["--genre", "romance", "--name", "My Project", "--episode-count", "5"]
    )
    assert args.genre == "romance"
    assert args.name == "My Project"
    assert args.episode_count == 5


async def test_main_runs_the_full_pipeline_without_a_real_provider(
    tmp_path, monkeypatch, capsys
) -> None:
    """Wires a `FakeLLMProvider` in place of `OpenRouterProvider` -
    everything else (Showrunner, repositories, DB) is the CLI's real
    code path, matching how `test_api.py`'s `client` fixture fakes only
    the provider boundary, not the pipeline itself."""
    db_path = tmp_path / "cli_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv(
        "OPENROUTER_API_KEY", "unused-because-the-provider-itself-is-faked-below"
    )
    get_settings.cache_clear()

    fake_provider = FakeLLMProvider(
        [
            json.dumps(fx.concept("A")),
            json.dumps(fx.concept("B")),
            json.dumps(fx.judge_result("A")),
            json.dumps(fx.bible()),
            json.dumps(fx.cast()),
            json.dumps(fx.season_plan()),
            json.dumps(fx.outline_set(3)),
            json.dumps(fx.script()),
            json.dumps(fx.shot_plan()),
        ]
    )
    monkeypatch.setattr(cli, "OpenRouterProvider", lambda **kwargs: fake_provider)
    monkeypatch.setattr(
        "sys.argv", ["xerama-cli", "--genre", "thriller", "--premise", "a locked-room mystery"]
    )

    try:
        await cli.main()
    finally:
        get_settings.cache_clear()

    output = json.loads(capsys.readouterr().out)
    assert output["episode1_id"]
    assert output["series_id"]
