"""
AI Provider interface and implementations.
All provider-specific logic is isolated here.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class AIClassificationResult(BaseModel):
    bucket_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str
    description_suggestion: str
    tags: List[str]
    subalbum_suggestion: Optional[str] = None
    review_recommended: bool = True


AI_OUTPUT_SCHEMA = {
    "type": "object",
    "required": [
        "bucket_name", "confidence", "explanation",
        "description_suggestion", "tags", "review_recommended"
    ],
    "properties": {
        "bucket_name": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "explanation": {"type": "string"},
        "description_suggestion": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 20},
        "subalbum_suggestion": {"type": ["string", "null"]},
        "review_recommended": {"type": "boolean"},
    },
    "additionalProperties": False,
}


class AIProvider(ABC):
    @abstractmethod
    def classify_asset(
        self,
        prompt_messages: List[Dict[str, Any]],
        image_payload: Optional[dict] = None,
    ) -> AIClassificationResult:
        """Send classification request. Returns validated result."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if provider is reachable."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass


def _validate_result(data: dict, raw: str) -> AIClassificationResult:
    """Shared validation for any provider returning the standard JSON shape."""
    required_fields = [
        "bucket_name", "confidence", "explanation",
        "description_suggestion", "tags", "review_recommended"
    ]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field '{field}' in AI response. Raw: {raw[:500]}")

    confidence = float(data["confidence"])
    if not (0.0 <= confidence <= 1.0):
        raise ValueError(f"confidence must be 0.0-1.0, got {confidence}")

    tags = data["tags"]
    if not isinstance(tags, list):
        raise ValueError("tags must be a list")
    tags = [str(t) for t in tags[:20]]

    return AIClassificationResult(
        bucket_name=str(data["bucket_name"]),
        confidence=confidence,
        explanation=str(data["explanation"]),
        description_suggestion=str(data["description_suggestion"]),
        tags=tags,
        subalbum_suggestion=data.get("subalbum_suggestion"),
        review_recommended=bool(data.get("review_recommended", True)),
    )


class OpenAIProvider(AIProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: Optional[str] = None,
    ):
        from openai import OpenAI
        kwargs: Dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
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

    def classify_asset(
        self,
        prompt_messages: List[Dict[str, Any]],
        image_payload: Optional[dict] = None,
    ) -> AIClassificationResult:
        import json

        messages = list(prompt_messages)
        if image_payload and image_payload.get("data_url"):
            last_user = None
            for i in range(len(messages) - 1, -1, -1):
                if messages[i].get("role") == "user":
                    last_user = i
                    break
            if last_user is not None:
                content = messages[last_user]["content"]
                if isinstance(content, str):
                    content = [{"type": "text", "text": content}]
                content.append({
                    "type": "image_url",
                    "image_url": {"url": image_payload["data_url"], "detail": "low"},
                })
                messages[last_user] = {"role": "user", "content": content}

        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=1024,
        )

        raw = response.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from OpenAI: {e}\nRaw: {raw[:500]}")

        return _validate_result(data, raw)


class OllamaProvider(AIProvider):
    """
    Ollama provider via the OpenAI-compatible /v1 endpoint.

    Requires Ollama >= 0.1.24 (ships the /v1 API).
    Recommended vision models: llava, llava-phi3, moondream, bakllava.
    Text-only models (llama3, mistral, etc.) also work but receive no image.

    base_url should be the Ollama root, e.g. http://localhost:11434
    The provider appends /v1 automatically.
    """

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llava"):
        self.base_url = base_url.rstrip("/")
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
        """Heuristic: model names that support image input."""
        vision_keywords = ("llava", "moondream", "bakllava", "minicpm", "qwen2-vl", "pixtral")
        return any(kw in self.model.lower() for kw in vision_keywords)

    def classify_asset(
        self,
        prompt_messages: List[Dict[str, Any]],
        image_payload: Optional[dict] = None,
    ) -> AIClassificationResult:
        import json
        import httpx

        messages = list(prompt_messages)

        # Inject image into the last user message for vision-capable models.
        # Ollama /v1 accepts the same OpenAI image_url format.
        if image_payload and image_payload.get("data_url") and self._is_vision_model():
            last_user = None
            for i in range(len(messages) - 1, -1, -1):
                if messages[i].get("role") == "user":
                    last_user = i
                    break
            if last_user is not None:
                content = messages[last_user]["content"]
                if isinstance(content, str):
                    content = [{"type": "text", "text": content}]
                content.append({
                    "type": "image_url",
                    "image_url": {"url": image_payload["data_url"]},
                })
                messages[last_user] = {"role": "user", "content": content}

        # Append a reminder to return JSON when the model is not instruction-tuned
        # to do so by default.
        messages_with_hint = list(messages)
        if messages_with_hint and messages_with_hint[-1].get("role") == "user":
            last = messages_with_hint[-1]
            text_content = (
                last["content"] if isinstance(last["content"], str)
                else next((c["text"] for c in last["content"] if c.get("type") == "text"), "")
            )
            if "json" not in text_content.lower():
                hint = "\n\nRespond ONLY with valid JSON matching the required schema."
                if isinstance(last["content"], str):
                    messages_with_hint[-1] = {"role": "user", "content": last["content"] + hint}
                else:
                    new_content = list(last["content"])
                    for i, part in enumerate(new_content):
                        if part.get("type") == "text":
                            new_content[i] = {"type": "text", "text": part["text"] + hint}
                            break
                    messages_with_hint[-1] = {"role": "user", "content": new_content}

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages_with_hint,
            "stream": False,
            "options": {"temperature": 0.2},
            "format": "json",  # Ollama native JSON mode (>= 0.1.24)
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
        if not raw:
            raise ValueError(f"Empty response from Ollama (model={self.model})")

        # Strip markdown code fences some models add even in JSON mode
        stripped = raw.strip()
        if stripped.startswith("```"):
            stripped = stripped.lstrip("`").lstrip("json").strip()
            if stripped.endswith("```"):
                stripped = stripped[:-3].strip()

        try:
            data = json.loads(stripped)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from Ollama: {e}\nRaw: {raw[:500]}")

        return _validate_result(data, raw)


class OpenRouterProvider(AIProvider):
    """OpenRouter — OpenAI-compatible API at openrouter.ai."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: str, model: str = "openai/gpt-4o"):
        self._api_key = api_key
        self._model = model
        # Extra headers recommended by OpenRouter for attribution and routing.
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
        """Lightweight connectivity check against OpenRouter's auth endpoint."""
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

    def classify_asset(
        self,
        prompt_messages: List[Dict[str, Any]],
        image_payload: Optional[dict] = None,
    ) -> AIClassificationResult:
        import json

        messages = list(prompt_messages)
        if image_payload and image_payload.get("data_url"):
            last_user = None
            for i in range(len(messages) - 1, -1, -1):
                if messages[i].get("role") == "user":
                    last_user = i
                    break
            if last_user is not None:
                content = messages[last_user]["content"]
                if isinstance(content, str):
                    content = [{"type": "text", "text": content}]
                content.append({
                    "type": "image_url",
                    "image_url": {"url": image_payload["data_url"], "detail": "low"},
                })
                messages[last_user] = {"role": "user", "content": content}

        # Try with JSON mode first; fall back without it for models that don't support it.
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,  # type: ignore
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=1024,
            )
        except Exception as e:
            err_str = str(e).lower()
            if "response_format" in err_str or "json_object" in err_str or "unsupported" in err_str:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,  # type: ignore
                    temperature=0.2,
                    max_tokens=1024,
                )
            else:
                raise

        raw = response.choices[0].message.content or "{}"

        # Strip markdown fences some models include
        stripped = raw.strip()
        if stripped.startswith("```"):
            stripped = stripped.lstrip("`").lstrip("json").strip()
            if stripped.endswith("```"):
                stripped = stripped[:-3].strip()

        try:
            data = json.loads(stripped)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from OpenRouter ({self._model}): {e}\nRaw: {raw[:500]}")

        return _validate_result(data, raw)


def build_provider(provider_name: str, config: dict) -> AIProvider:
    """Factory function to instantiate the right provider."""
    if provider_name == "openai":
        return OpenAIProvider(
            api_key=config["api_key"],
            model=config.get("model_name", "gpt-4o"),
            base_url=config.get("base_url"),
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
