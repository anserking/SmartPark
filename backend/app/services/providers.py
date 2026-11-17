from typing import Any

import httpx


class GeographicProviderError(RuntimeError):
    def __init__(
        self,
        provider: str,
        message: str,
        status_code: int | None = None,
        retry_after: str | None = None,
    ) -> None:
        super().__init__(f"{provider} provider error: {message}")
        self.provider = provider
        self.status_code = status_code
        self.retry_after = retry_after


def response_json(provider: str, response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise GeographicProviderError(provider, "response was not valid JSON") from exc
    if not isinstance(payload, dict):
        raise GeographicProviderError(provider, "response must be a JSON object")
    return payload
