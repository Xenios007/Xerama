"""Real fal.ai image provider (flux/schnell) - see providers/image.py for
the `ImageProvider` Protocol every adapter (fake or real) implements.

fal's synchronous endpoint (`fal.run/...`) blocks until the image is ready
and returns the result inline - no queue/polling needed for a model this
fast. The result carries a download URL, not raw bytes, so `generate`
makes one follow-up GET to fetch the actual image content."""

import httpx

from xerama.domain.enums import ProviderErrorKind
from xerama.providers.errors import ProviderError, classify_status_code
from xerama.providers.image import ImageEditRequest, ImageGenerationRequest, ImageProviderCapabilities

_PROVIDER_NAME = "fal_flux"
_MODEL_PATH = "fal-ai/flux/schnell"

# Nearest fal `image_size` presets to each aspect ratio Xerama might request -
# a vertical 1080x1920 microdrama frame needs an explicit width/height object,
# not one of fal's named presets (which top out at 16:9).
_ASPECT_TO_SIZE = {
    "9:16": {"width": 1080, "height": 1920},
    "16:9": {"width": 1920, "height": 1080},
    "1:1": {"width": 1024, "height": 1024},
}


class FalImageProvider:
    """Implements the `ImageProvider` Protocol against fal.ai's FLUX.1 [schnell]."""

    def __init__(
        self,
        api_key: str,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(timeout=timeout)

    @property
    def name(self) -> str:
        return _PROVIDER_NAME

    @property
    def capabilities(self) -> ImageProviderCapabilities:
        return ImageProviderCapabilities(
            supports_reference_images=False,
            supports_edit=False,
            supported_aspects=list(_ASPECT_TO_SIZE.keys()),
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _headers(self) -> dict:
        return {"Authorization": f"Key {self._api_key}", "Content-Type": "application/json"}

    async def _run_sync(self, prompt: str, negative_prompt: str, aspect_ratio: str) -> bytes:
        if not self._api_key:
            raise ProviderError(ProviderErrorKind.AUTHENTICATION, "FAL_API_KEY is not configured")

        payload = {
            "prompt": prompt,
            "image_size": _ASPECT_TO_SIZE.get(aspect_ratio, _ASPECT_TO_SIZE["9:16"]),
            "output_format": "png",
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        try:
            response = await self._client.post(
                f"https://fal.run/{_MODEL_PATH}", headers=self._headers(), json=payload
            )
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

        body = response.json()
        images = body.get("images") or []
        if not images:
            raise ProviderError(ProviderErrorKind.UNKNOWN, "fal.ai response had no images")
        image_url = images[0]["url"]

        try:
            image_response = await self._client.get(image_url)
            image_response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(
                ProviderErrorKind.TRANSIENT_FAILURE, f"failed to download fal.ai image: {exc!r}"
            ) from exc
        return image_response.content

    async def generate(self, request: ImageGenerationRequest, reference_images: list[bytes]) -> bytes:
        return await self._run_sync(request.prompt, request.negative_prompt, request.aspect_ratio)

    async def edit(
        self, request: ImageEditRequest, base_image: bytes, mask: bytes | None = None
    ) -> bytes:
        # capabilities.supports_edit=False keeps the router from ever routing
        # an edit request here (see providers/image.py's Protocol docstring).
        raise ProviderError(ProviderErrorKind.INVALID_REQUEST, "fal_flux does not support edit")


def _safe_error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
        return str(body.get("detail") or body.get("error") or response.text)[:500]
    except ValueError:
        return response.text[:500]
