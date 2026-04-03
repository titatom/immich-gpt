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

        # Build messages list - inject image into last user message
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

        return self._validate_result(data, raw)

    def _validate_result(self, data: dict, raw: str) -> AIClassificationResult:
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


class OllamaProvider(AIProvider):
    """Stub for Ollama provider. Not yet implemented."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llava"):
        self.base_url = base_url
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

    def classify_asset(
        self,
        prompt_messages: List[Dict[str, Any]],
        image_payload: Optional[dict] = None,
    ) -> AIClassificationResult:
        raise NotImplementedError("Ollama provider is not yet implemented")


class OpenRouterProvider(AIProvider):
    """Stub for OpenRouter provider. Uses OpenAI-compatible API."""

    def __init__(self, api_key: str, model: str = "openai/gpt-4o"):
        self._inner = OpenAIProvider(
            api_key=api_key,
            model=model,
            base_url="https://openrouter.ai/api/v1",
        )

    @property
    def provider_name(self) -> str:
        return "openrouter"

    def health_check(self) -> bool:
        return self._inner.health_check()

    def classify_asset(
        self,
        prompt_messages: List[Dict[str, Any]],
        image_payload: Optional[dict] = None,
    ) -> AIClassificationResult:
        return self._inner.classify_asset(prompt_messages, image_payload)


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
