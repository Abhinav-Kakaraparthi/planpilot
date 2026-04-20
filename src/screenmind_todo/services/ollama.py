from __future__ import annotations

import httpx


class OllamaService:
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def summarize(self, context: str) -> tuple[str, int]:
        payload = {
            "model": self.model,
            "stream": False,
            "prompt": (
                "Summarize the user's current computer activity in one short sentence. "
                "Return plain text only.\n\n"
                f"Context:\n{context}"
            ),
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
        summary = data.get("response", "").strip()
        return summary[:300], 65 if summary else 0

