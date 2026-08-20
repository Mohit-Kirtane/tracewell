import httpx


class TracewellClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.tracewell.dev",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._http = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
        )

    def start_trace(self, name: str) -> str:
        response = self._http.post("/api/v1/traces", json={"name": name})
        response.raise_for_status()
        return response.json()["id"]

    def update_trace(
        self, trace_id: str, status: str | None = None, spans: list[dict] | None = None
    ) -> None:
        payload: dict = {}
        if status is not None:
            payload["status"] = status
        if spans is not None:
            payload["spans"] = spans
        response = self._http.patch(f"/api/v1/traces/{trace_id}", json=payload)
        response.raise_for_status()
