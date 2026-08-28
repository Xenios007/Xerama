"""Xerama Assistant - an in-app chat panel.

Not the Claude Agent SDK: Anthropic's terms don't allow a third-party
product to route its own users' usage through a personal claude.ai login
("Unless previously approved, Anthropic does not allow third party
developers to offer claude.ai login or rate limits for their products,
including agents built on the Claude Agent SDK" -
code.claude.com/docs/en/agent-sdk/overview), and this session has no
Anthropic Console API key to use instead. So the assistant rides
OpenRouter's own commercial API access - already configured for story
generation - streaming plain OpenAI-compatible chat completions. The
default model is a Claude model (`runtime_settings.chat_model`), so this
still is Claude, just billed through OpenRouter rather than a personal
login or a separate Anthropic key.

WebSocket, not a one-shot POST, so the panel can hold a real multi-turn
conversation: the socket's lifetime is the chat session, server-side
history accumulates per connection (OpenRouter's endpoint is otherwise
stateless - unlike the Agent SDK, there's no server-side session to
`resume`).
"""

import asyncio
import json
import logging

import httpx
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from xerama.api.deps import get_runtime_settings_repo
from xerama.config import get_settings
from xerama.repositories.sqlalchemy_impl import SQLAlchemyRuntimeSettingsRepository

logger = logging.getLogger("xerama.chat")

router = APIRouter(prefix="/chat", tags=["chat"])

_SYSTEM_PROMPT = (
    "You are Xerama Assistant, a creative copilot embedded in Xerama - an AI "
    "microdrama production system. Help the user write and refine story "
    "concepts, shot prompts, and creative direction for Xerama's pipeline "
    "(concept -> series bible -> characters -> season plan -> episode "
    "scripts -> shots -> media generation). Be concise and concrete; when "
    "asked for a prompt, give one that's ready to paste in, not a lecture."
)

_NOT_CONFIGURED_CLOSE_CODE = 4404


class ChatStatusResponse(BaseModel):
    configured: bool
    model: str


@router.get("/status", response_model=ChatStatusResponse)
async def chat_status(
    repo: SQLAlchemyRuntimeSettingsRepository = Depends(get_runtime_settings_repo),
) -> ChatStatusResponse:
    settings = get_settings()
    runtime = await repo.get_or_create()
    return ChatStatusResponse(
        configured=bool(settings.openrouter_api_key.get_secret_value()), model=runtime.chat_model
    )


async def _stream_reply(
    websocket: WebSocket,
    history: list[dict],
    user_text: str,
    model: str,
    api_key: str,
    base_url: str,
) -> None:
    history.append({"role": "user", "content": user_text})
    assistant_text = ""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client, client.stream(
            "POST",
            f"{base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/Xenios007/Xerama",
                "X-Title": "Xerama Assistant",
            },
            json={"model": model, "messages": history, "stream": True},
        ) as response:
            if response.status_code >= 400:
                body = await response.aread()
                await websocket.send_json(
                    {
                        "type": "error",
                        "text": f"OpenRouter error {response.status_code}: "
                        f"{body.decode(errors='replace')[:300]}",
                    }
                )
                return
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[len("data: ") :]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                delta = (chunk.get("choices") or [{}])[0].get("delta", {}).get("content")
                if delta:
                    assistant_text += delta
                    await websocket.send_json({"type": "text", "text": delta})
    except asyncio.CancelledError:
        pass
    except httpx.HTTPError as exc:
        await websocket.send_json({"type": "error", "text": f"Request failed: {exc!r}"})
    finally:
        if assistant_text:
            history.append({"role": "assistant", "content": assistant_text})
        await websocket.send_json({"type": "turn_complete"})


@router.websocket("/ws")
async def chat_ws(websocket: WebSocket) -> None:
    settings = get_settings()
    api_key = settings.openrouter_api_key.get_secret_value()
    if not api_key:
        await websocket.close(code=_NOT_CONFIGURED_CLOSE_CODE, reason="OPENROUTER_API_KEY not configured")
        return

    session_factory = websocket.app.state.session_factory
    async with session_factory() as session:
        runtime = await SQLAlchemyRuntimeSettingsRepository(session).get_or_create()

    await websocket.accept()

    history: list[dict] = [{"role": "system", "content": _SYSTEM_PROMPT}]
    current_task: asyncio.Task | None = None

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if message.get("type") == "interrupt":
                if current_task is not None and not current_task.done():
                    current_task.cancel()
            elif message.get("type") == "message" and message.get("text"):
                if current_task is not None and not current_task.done():
                    current_task.cancel()
                current_task = asyncio.create_task(
                    _stream_reply(
                        websocket,
                        history,
                        message["text"],
                        runtime.chat_model,
                        api_key,
                        settings.openrouter_base_url,
                    )
                )
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("chat websocket session failed")
    finally:
        if current_task is not None and not current_task.done():
            current_task.cancel()
