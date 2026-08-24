import pytest
from pydantic import BaseModel

from xerama.config import ModelRoleRegistry, Settings
from xerama.domain.enums import ModelRole, ProviderErrorKind
from xerama.pipeline.ai_gateway import AIGateway, XeramaGenerationError
from xerama.providers.errors import ProviderError
from xerama.providers.fake import FakeLLMProvider


class _Toy(BaseModel):
    value: int


def _gateway(provider: FakeLLMProvider) -> AIGateway:
    return AIGateway(provider=provider, roles=ModelRoleRegistry(Settings()), max_attempts=3)


@pytest.mark.asyncio
async def test_generate_returns_parsed_model_on_first_valid_response() -> None:
    provider = FakeLLMProvider(['{"value": 42}'])
    gateway = _gateway(provider)

    result = await gateway.generate(
        role=ModelRole.JUDGE, schema=_Toy, system_prompt="sys", user_prompt="user"
    )

    assert result.value == 42
    assert len(provider.calls) == 1


@pytest.mark.asyncio
async def test_generate_repairs_invalid_json_then_succeeds() -> None:
    provider = FakeLLMProvider(["not json at all", '{"value": 7}'])
    gateway = _gateway(provider)

    result = await gateway.generate(
        role=ModelRole.JUDGE, schema=_Toy, system_prompt="sys", user_prompt="user"
    )

    assert result.value == 7
    assert len(provider.calls) == 2
    # the repair attempt should carry the failed assistant turn + a correction request
    assert provider.calls[1].messages[-2].role == "assistant"
    assert provider.calls[1].messages[-1].role == "user"


@pytest.mark.asyncio
async def test_generate_repairs_schema_violation() -> None:
    provider = FakeLLMProvider(['{"value": "not-an-int"}', '{"value": 3}'])
    gateway = _gateway(provider)

    result = await gateway.generate(
        role=ModelRole.JUDGE, schema=_Toy, system_prompt="sys", user_prompt="user"
    )

    assert result.value == 3


@pytest.mark.asyncio
async def test_generate_raises_after_exhausting_repair_attempts() -> None:
    provider = FakeLLMProvider(["bad", "still bad", "still bad again"])
    gateway = _gateway(provider)

    with pytest.raises(XeramaGenerationError):
        await gateway.generate(role=ModelRole.JUDGE, schema=_Toy, system_prompt="sys", user_prompt="user")

    assert len(provider.calls) == 3


@pytest.mark.asyncio
async def test_generate_raises_immediately_on_non_retriable_provider_error() -> None:
    provider = FakeLLMProvider([ProviderError(ProviderErrorKind.AUTHENTICATION, "bad key")])
    gateway = _gateway(provider)

    with pytest.raises(XeramaGenerationError):
        await gateway.generate(role=ModelRole.JUDGE, schema=_Toy, system_prompt="sys", user_prompt="user")

    assert len(provider.calls) == 1


@pytest.mark.asyncio
async def test_generate_retries_on_retriable_provider_error() -> None:
    provider = FakeLLMProvider(
        [ProviderError(ProviderErrorKind.RATE_LIMIT, "slow down"), '{"value": 1}']
    )
    gateway = _gateway(provider)

    result = await gateway.generate(role=ModelRole.JUDGE, schema=_Toy, system_prompt="sys", user_prompt="user")

    assert result.value == 1
    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_resolve_model_uses_env_override(monkeypatch) -> None:
    monkeypatch.setenv("JUDGE_MODEL", "custom/judge-model:free")
    gateway = AIGateway(provider=FakeLLMProvider(), roles=ModelRoleRegistry(Settings()))

    assert gateway.resolve_model(ModelRole.JUDGE) == "custom/judge-model:free"
