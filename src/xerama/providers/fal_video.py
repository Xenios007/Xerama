"""Real fal.ai video provider (Wan v2.6 image-to-video) - see
providers/video.py for the `VideoProvider` Protocol every adapter (fake or
real) implements.

Video generation is slow (up to a couple of minutes for a 15s clip), so
this uses fal's async queue API: submit -> poll status -> fetch result ->
download the resulting video bytes from its CDN url."""

import asyncio
import base64

import httpx

from xerama.domain.enums import ProviderErrorKind
from xerama.providers.errors import ProviderError, classify_status_code
from xerama.providers.video import VideoGenerationRequest, VideoProviderCapabilities

_PROVIDER_NAME = "fal_wan"
_MODEL_PATH = "wan/v2.6/image-to-video"
_SUBMIT_URL = f"https://queue.fal.run/{_MODEL_PATH}"

# Wan only accepts these three durations - a shot's actual duration_seconds
# is snapped to the nearest one, since the video is trimmed to the shot's
# real length during assembly (ffmpeg_assembler.py's `-t` clip normalization)
# regardless of the source clip's length.
_SUPPORTED_DURATIONS = (5, 10, 15)


def _nearest_duration(duration_seconds: float) -> str:
    return str(min(_SUPPORTED_DURATIONS, key=lambda d: abs(d - duration_seconds)))


class FalVideoProvider:
    """Implements the `VideoProvider` Protocol against fal.ai's Wan v2.6
    image-to-video model. Text-only (no first frame) generation isn't
    supported by this endpoint - `capabilities.text_to_video=False` keeps
    the router from selecting it for a text-to-video-only request."""

    def __init__(
        self,
        api_key: str,
        http_client: httpx.AsyncClient | None = None,
        poll_interval_seconds: float = 3.0,
        timeout_seconds: float = 300.0,
    ) -> None:
        self._api_key = api_key
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(timeout=60.0)
        self._poll_interval_seconds = poll_interval_seconds
        self._timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return _PROVIDER_NAME

    @property
    def capabilities(self) -> VideoProviderCapabilities:
        return VideoProviderCapabilities(
            text_to_video=False,
            image_to_video=True,
            first_frame=True,
            last_frame=False,
            # No dedicated multi-reference-image input on this endpoint -
            # identity consistency instead comes from anchoring on a
            # character-accurate first frame (already generated from the
            # character's description), a valid alternate mechanism for the
            # same capability rather than a missing one.
            subject_reference=True,
            native_audio=True,
            max_duration_seconds=15.0,
            supported_aspects=["9:16", "16:9", "1:1"],
            supported_resolutions=["1080x1920", "1280x720"],
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _headers(self) -> dict:
        return {"Authorization": f"Key {self._api_key}", "Content-Type": "application/json"}

    async def generate(
        self,
        request: VideoGenerationRequest,
        reference_images: list[bytes],
        first_frame: bytes | None = None,
        last_frame: bytes | None = None,
    ) -> bytes:
        if not self._api_key:
            raise ProviderError(ProviderErrorKind.AUTHENTICATION, "FAL_API_KEY is not configured")
        if first_frame is None:
            raise ProviderError(
                ProviderErrorKind.INVALID_REQUEST,
                "fal_wan is image-to-video only and needs a first frame",
            )

        image_data_uri = "data:image/png;base64," + base64.b64encode(first_frame).decode("ascii")
        payload = {
            "prompt": request.prompt,
            "image_url": image_data_uri,
            "duration": _nearest_duration(request.duration_seconds),
            "resolution": "1080p",
        }
        if request.negative_prompt:
            payload["negative_prompt"] = request.negative_prompt

        submission = await self._post_json(_SUBMIT_URL, payload)
        status_url = submission["status_url"]
        response_url = submission["response_url"]

        result = await self._poll_until_complete(status_url)
        video_url = result["video"]["url"]

        try:
            video_response = await self._client.get(video_url)
            video_response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(
                ProviderErrorKind.TRANSIENT_FAILURE, f"failed to download fal.ai video: {exc!r}"
            ) from exc
        return video_response.content

    async def _post_json(self, url: str, payload: dict) -> dict:
        try:
            response = await self._client.post(url, headers=self._headers(), json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderError(ProviderErrorKind.TIMEOUT, "fal.ai request timed out") from exc
        except httpx.RequestError as exc:
            raise ProviderError(
                ProviderErrorKind.TRANSIENT_FAILURE, f"fal.ai request failed: {exc!r}"
            ) from exc
        if response.status_code >= 400:
            raise ProviderError(
                classify_status_code(response.status_code),
                _safe_error_message(response),
                status_code=response.status_code,
            )
        return response.json()

    async def _get_json(self, url: str) -> dict:
        try:
            response = await self._client.get(url, headers=self._headers())
        except httpx.TimeoutException as exc:
            raise ProviderError(ProviderErrorKind.TIMEOUT, "fal.ai request timed out") from exc
        except httpx.RequestError as exc:
            raise ProviderError(
                ProviderErrorKind.TRANSIENT_FAILURE, f"fal.ai request failed: {exc!r}"
            ) from exc
        if response.status_code >= 400:
            raise ProviderError(
                classify_status_code(response.status_code),
                _safe_error_message(response),
                status_code=response.status_code,
            )
        return response.json()

    async def _poll_until_complete(self, status_url: str) -> dict:
        elapsed = 0.0
        while True:
            status_body = await self._get_json(status_url)
            status = status_body.get("status")
            if status == "COMPLETED":
                response_url = status_body.get("response_url")
                return await self._get_json(response_url) if response_url else status_body
            if status in ("FAILED", "CANCELLED", "ERROR"):
                raise ProviderError(
                    ProviderErrorKind.TRANSIENT_FAILURE, f"fal.ai generation {status.lower()}"
                )
            if elapsed >= self._timeout_seconds:
                raise ProviderError(ProviderErrorKind.TIMEOUT, "fal.ai generation timed out")
            await asyncio.sleep(self._poll_interval_seconds)
            elapsed += self._poll_interval_seconds


def _safe_error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
        return str(body.get("detail") or body.get("error") or response.text)[:500]
    except ValueError:
        return response.text[:500]
