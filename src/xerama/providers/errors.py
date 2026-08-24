"""Provider error taxonomy. See docs/ARCHITECTURE.md section 12 (Provider Health)."""

from xerama.domain.enums import ProviderErrorKind

# Error kinds that a health tracker should treat as retriable against the
# same provider/model after a short cool-down, versus kinds that should not
# be retried automatically (bad request shape, auth misconfiguration).
RETRIABLE_KINDS = {
    ProviderErrorKind.RATE_LIMIT,
    ProviderErrorKind.PROVIDER_SATURATION,
    ProviderErrorKind.TIMEOUT,
    ProviderErrorKind.TRANSIENT_FAILURE,
}


class ProviderError(Exception):
    """Raised by any `LLMProvider` (and future media providers) on failure."""

    def __init__(self, kind: ProviderErrorKind, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.status_code = status_code

    @property
    def retriable(self) -> bool:
        return self.kind in RETRIABLE_KINDS


def classify_status_code(status_code: int) -> ProviderErrorKind:
    if status_code == 401 or status_code == 403:
        return ProviderErrorKind.AUTHENTICATION
    if status_code == 402:
        return ProviderErrorKind.QUOTA
    if status_code == 429:
        return ProviderErrorKind.RATE_LIMIT
    if status_code == 408:
        return ProviderErrorKind.TIMEOUT
    if status_code in (400, 422):
        return ProviderErrorKind.INVALID_REQUEST
    if status_code == 503:
        return ProviderErrorKind.PROVIDER_SATURATION
    if 500 <= status_code < 600:
        return ProviderErrorKind.TRANSIENT_FAILURE
    return ProviderErrorKind.UNKNOWN
