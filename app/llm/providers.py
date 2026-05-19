"""LLM providers used by RAG answer generation."""

from __future__ import annotations

import os
import re
from typing import Any, Protocol

from dotenv import load_dotenv

from app.config import PROJECT_ROOT


load_dotenv(PROJECT_ROOT / ".env")


class LLMProvider(Protocol):
    """Protocol implemented by all LLM providers."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate text from prompts."""


class MockLLMProvider:
    """Deterministic provider for tests and offline development."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return a deterministic diagnostic answer without network calls."""
        citations = sorted(set(re.findall(r"\[source: [^\]]+\]", user_prompt)))
        citation_text = " ".join(citations)
        return (
            "可能原因: mock provider 基于检索上下文生成诊断结论。\n"
            "排查步骤: 优先核对上下文中的错误码、日志关键词和相关指标。\n"
            "解决方案: 按检索上下文中的修复建议执行，并在变更后复测。\n"
            f"引用来源: {citation_text}"
        ).strip()


class KimiLLMProvider:
    """Kimi provider using the OpenAI-compatible Moonshot API."""

    def __init__(
        self,
        model: str = "kimi-k2-turbo-preview",
        base_url: str = "https://api.moonshot.cn/v1",
        api_key_env: str = "MOONSHOT_API_KEY",
        temperature: float | None = 0.6,
        max_tokens: int | None = 4096,
        timeout: float = 60,
        top_p: float | None = None,
        frequency_penalty: float | None = None,
        presence_penalty: float | None = None,
        n: int | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("Kimi LLM provider requires a non-empty base_url")

        api_key = os.getenv(api_key_env)
        if not api_key:
            raise ValueError(f"{api_key_env} is required for the kimi LLM provider")

        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise ImportError("The openai package >= 1.0 is required for the kimi LLM provider") from exc

        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.n = n
        self.extra_body = extra_body
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Call the Kimi chat completion API."""
        try:
            request_kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            }
            optional_params = {
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "top_p": self.top_p,
                "frequency_penalty": self.frequency_penalty,
                "presence_penalty": self.presence_penalty,
                "n": self.n,
                "extra_body": self.extra_body,
            }
            request_kwargs.update({key: value for key, value in optional_params.items() if value is not None})
            response = self.client.chat.completions.create(**request_kwargs)
        except Exception as exc:
            raise RuntimeError(f"Kimi API call failed: {exc}") from exc

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Kimi API returned an empty response")
        return content


def create_llm_provider(config: dict[str, Any]) -> LLMProvider:
    """Create an LLM provider from config."""
    llm_config = config.get("llm", {})
    if llm_config is None:
        llm_config = {}
    if not isinstance(llm_config, dict):
        raise ValueError("RAG config field 'llm' must be a mapping")

    provider = str(llm_config.get("provider", "mock")).lower()
    if provider == "mock":
        return MockLLMProvider()
    if provider == "kimi":
        base_url_env = llm_config.get("base_url_env")
        base_url = os.getenv(str(base_url_env)) if base_url_env else llm_config.get("base_url")
        return KimiLLMProvider(
            model=str(llm_config.get("model", "kimi-k2-turbo-preview")),
            base_url=str(base_url or "https://api.moonshot.cn/v1"),
            api_key_env=str(llm_config.get("api_key_env", "MOONSHOT_API_KEY")),
            temperature=parse_optional_float(llm_config.get("temperature", 0.6)),
            max_tokens=parse_optional_int(llm_config.get("max_tokens", 4096)),
            timeout=float(llm_config.get("timeout", 60)),
            top_p=parse_optional_float(llm_config.get("top_p")),
            frequency_penalty=parse_optional_float(llm_config.get("frequency_penalty")),
            presence_penalty=parse_optional_float(llm_config.get("presence_penalty")),
            n=parse_optional_int(llm_config.get("n")),
            extra_body=parse_optional_mapping(llm_config.get("extra_body")),
        )

    raise ValueError(
        "Unsupported LLM provider. Expected one of: mock, kimi; "
        f"got {provider or '<missing>'}"
    )


def parse_optional_float(value: Any) -> float | None:
    """Parse an optional float config value."""
    if value is None:
        return None
    return float(value)


def parse_optional_int(value: Any) -> int | None:
    """Parse an optional int config value."""
    if value is None:
        return None
    return int(value)


def parse_optional_mapping(value: Any) -> dict[str, Any] | None:
    """Parse an optional mapping config value."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("LLM config field 'extra_body' must be a mapping")
    return value
