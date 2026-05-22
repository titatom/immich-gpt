"""
AI Provider interface and implementations.

The provider is intentionally schema-agnostic: it speaks JSON to the
upstream model and returns a parsed `dict`. Validation against the
routing schema is done in the orchestrator with `AIRoutingResult`.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

from .url_validation import validate_service_url


class AIProvider(ABC):
    @abstractmethod
    def classify_routing(
        self,
        prompt_messages: List[Dict[str, Any]],
        image_payload: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """Send a JSON-mode chat request and return the parsed dict."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if provider is reachable."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass


def _inject_image(
    messages: List[Dict[str, Any]],
    image_payload: Optional[dict],
    detail: Optional[str] = "low",
) -> List[Dict[str, Any]]:
    """Append an image_url part to the last user message in-place (copy)."""
    msgs = list(messages)
    if not (image_payload and image_payload.get("data_url")):
        return msgs
    for i in range(len(msgs) - 1, -1, -1):
        if msgs[i].get("role") == "user":
            content = msgs[i]["content"]
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            image_url: Dict[str, Any] = {"url": image_payload["data_url"]}
            if detail:
                image_url["detail"] = detail
            content.append({"type": "image_url", "image_url": image_url})
            msgs[i] = {"role": "user", "content": content}
            break
    return msgs


def _parse_json_content(raw: str) -> Dict[str, Any]:
    """Best-effort JSON parse, stripping markdown code fences if present."""
    import json

    if not raw:
        raise ValueError("Empty response from provider")
    stripped = raw.strip()
    if stripped.startswith("```"):
        stripped = stripped[3:]
        newline = stripped.find("\n")
        if newline != -1:
            lang_tag = stripped[:newline].strip().lower()
            if lang_tag in ("json", ""):
                stripped = stripped[newline + 1:]
        stripped = stripped.strip()
        if stripped.endswith("```"):
            stripped = stripped[:-3].strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from provider: {e}\nRaw: {raw[:500]}")


class OpenAIProvider(AIProvider):
    DEFAULT_TIMEOUT_SECONDS = 120.0

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        from openai import OpenAI
        kwargs: Dict[str, Any] = {"api_key": api_key, "timeout": timeout}
        if base_url:
            kwargs["base_url"] = validate_service_url(base_url, field_name="Provider base URL")
        self._client = OpenAI(**kwargs)
        self.model = model

    @property
    def provider_name(self) -> str:
        return "openai"

    def health_check(self) -> bool:
        try:
            self._client.models.list()
            return True
        except Exception:
            return False

    def classify_routing(
        self,
        prompt_messages: List[Dict[str, Any]],
        image_payload: Optional[dict] = None,
    ) -> Dict[str, Any]:
        messages = _inject_image(prompt_messages, image_payload, detail="low")
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=1024,
        )
        raw = response.choices[0].message.content or "{}"
        return _parse_json_content(raw)


class OllamaProvider(AIProvider):
    """Ollama via the OpenAI-compatible /v1 endpoint (>= 0.1.24)."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llava"):
        self.base_url = validate_service_url(base_url, field_name="Ollama URL")
        self.model = model

    @property
    def provider_name(self) -> str:
        return "ollama"

    def health_check(self) -> bool:
        try:
            import httpx
            r = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def _is_vision_model(self) -> bool:
        keywords = ("llava", "moondream", "bakllava", "minicpm", "qwen2-vl", "pixtral")
        return any(kw in self.model.lower() for kw in keywords)

    def classify_routing(
        self,
        prompt_messages: List[Dict[str, Any]],
        image_payload: Optional[dict] = None,
    ) -> Dict[str, Any]:
        import httpx

        messages = (
            _inject_image(prompt_messages, image_payload, detail=None)
            if self._is_vision_model()
            else list(prompt_messages)
        )

        # Append a JSON-only reminder for non-instruct models.
        if messages and messages[-1].get("role") == "user":
            last = messages[-1]
            text = (
                last["content"] if isinstance(last["content"], str)
                else next((c["text"] for c in last["content"] if c.get("type") == "text"), "")
            )
            if "json" not in text.lower():
                hint = "\n\nRespond ONLY with valid JSON matching the required schema."
                if isinstance(last["content"], str):
                    messages[-1] = {"role": "user", "content": last["content"] + hint}
                else:
                    new_content = list(last["content"])
                    for i, part in enumerate(new_content):
                        if part.get("type") == "text":
                            new_content[i] = {"type": "text", "text": part["text"] + hint}
                            break
                    messages[-1] = {"role": "user", "content": new_content}

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.2},
            "format": "json",
        }
        try:
            with httpx.Client(timeout=120) as client:
                r = client.post(f"{self.base_url}/v1/chat/completions", json=payload)
                if r.status_code != 200:
                    raise ValueError(f"Ollama returned HTTP {r.status_code}: {r.text[:400]}")
                resp = r.json()
        except httpx.ConnectError as e:
            raise ValueError(f"Cannot connect to Ollama at {self.base_url}: {e}")
        except httpx.TimeoutException:
            raise ValueError(f"Ollama request timed out (model={self.model})")

        raw = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
        return _parse_json_content(raw)


class OpenRouterProvider(AIProvider):
    """OpenRouter — OpenAI-compatible API at openrouter.ai."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: str, model: str = "openai/gpt-4o"):
        self._api_key = api_key
        self._model = model
        self._extra_headers = {
            "HTTP-Referer": "https://github.com/titatom/immich-gpt",
            "X-Title": "immich-gpt",
        }
        from openai import OpenAI
        self._client = OpenAI(
            api_key=api_key,
            base_url=self.BASE_URL,
            default_headers=self._extra_headers,
        )

    @property
    def provider_name(self) -> str:
        return "openrouter"

    def health_check(self) -> bool:
        try:
            import httpx
            r = httpx.get(
                f"{self.BASE_URL}/auth/key",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    **self._extra_headers,
                },
                timeout=10,
            )
            return r.status_code in (200, 401)
        except Exception:
            return False

    def classify_routing(
        self,
        prompt_messages: List[Dict[str, Any]],
        image_payload: Optional[dict] = None,
    ) -> Dict[str, Any]:
        messages = _inject_image(prompt_messages, image_payload, detail="low")
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,  # type: ignore
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=1024,
            )
        except Exception as e:
            err = str(e).lower()
            if "response_format" in err or "json_object" in err or "unsupported" in err:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,  # type: ignore
                    temperature=0.2,
                    max_tokens=1024,
                )
            else:
                raise
        raw = response.choices[0].message.content or "{}"
        return _parse_json_content(raw)


def build_provider(provider_name: str, config: dict) -> AIProvider:
    """Factory function to instantiate the right provider."""
    if provider_name == "openai":
        return OpenAIProvider(
            api_key=config["api_key"],
            model=config.get("model_name", "gpt-4o"),
            base_url=config.get("base_url"),
            timeout=float(config.get("timeout", OpenAIProvider.DEFAULT_TIMEOUT_SECONDS)),
        )
    elif provider_name == "ollama":
        return OllamaProvider(
            base_url=config.get("base_url", "http://localhost:11434"),
            model=config.get("model_name", "llava"),
        )
    elif provider_name == "openrouter":
        return OpenRouterProvider(
            api_key=config["api_key"],
            model=config.get("model_name", "openai/gpt-4o"),
        )
    raise ValueError(f"Unknown provider: {provider_name}")
