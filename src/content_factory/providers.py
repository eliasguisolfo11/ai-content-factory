import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


class OllamaProvider:
    """Small replaceable adapter for Ollama's local chat API."""

    def __init__(self, model: str):
        self.model = model
        self.base_url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")

    def list_models(self) -> list[str]:
        request = Request(f"{self.base_url}/api/tags")
        try:
            with urlopen(request, timeout=8) as response:
                payload = json.loads(response.read())
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Ollama respondió HTTP {exc.code}: {detail or exc.reason}") from exc
        except URLError as exc:
            raise RuntimeError(
                f"No se pudo conectar con Ollama en {self.base_url}. "
                "Abrí Ollama y comprobá que su servidor local esté activo. "
                f"Detalle: {exc.reason}"
            ) from exc
        return [item["name"] for item in payload.get("models", []) if item.get("name")]

    def generate_json(self, prompt: str) -> dict:
        payload = json.dumps({"model": self.model, "stream": False, "format": "json",
                              "messages": [{"role": "user", "content": prompt}]}).encode()
        request = Request(f"{self.base_url}/api/chat", data=payload,
                          headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=300) as response:
                content = json.loads(response.read()).get("message", {}).get("content", "")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()
            raise RuntimeError(
                f"Ollama respondió HTTP {exc.code}: {detail or exc.reason}. "
                f"Verificá que el modelo '{self.model}' esté instalado con `ollama pull {self.model}`."
            ) from exc
        except URLError as exc:
            raise RuntimeError(
                f"No se pudo conectar con Ollama en {self.base_url}. "
                "Abrí Ollama y comprobá que su servidor local esté activo. "
                f"Detalle: {exc.reason}"
            ) from exc
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("Ollama no devolvió JSON válido.") from exc
