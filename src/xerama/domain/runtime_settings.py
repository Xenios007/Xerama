"""Runtime provider/model settings - changeable from the Settings UI without
a server restart, unlike `.env`-only config (see `api/app.py`'s
`rebuild_providers()`). Single row (`id="default"`). Never stores a secret -
API keys stay `.env`-only; this only records which provider/model to use.
"""

from datetime import datetime

from pydantic import BaseModel


class RuntimeSettings(BaseModel):
    id: str = "default"
    llm_provider: str = "openrouter"  # "openrouter" | "ollama"
    ollama_model: str = "qwen2.5:7b"
    ollama_base_url: str = "http://localhost:11434/v1"
    media_provider: str = "fake"  # "fal" | "fake" - "fake" is the default: no spend without explicit opt-in
    # Xerama Assistant (api/routers/chat.py) - an OpenRouter chat-completions
    # model, not the Claude Agent SDK: Anthropic's terms don't allow a
    # third-party product to run its own users' chat through a personal
    # claude.ai login, so this rides OpenRouter's own commercial API access
    # instead (already configured - no separate key needed). Defaults to a
    # Claude model since that's what was actually asked for.
    chat_model: str = "anthropic/claude-sonnet-5"
    updated_at: datetime | None = None
