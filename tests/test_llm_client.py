"""Tests del cliente LLM unificado: credenciales y familias de modelos."""

import pytest

from src.llm_client import _is_reasoning_model, validate_provider_credentials


class TestProviderCredentials:
    """Sin key, la cascada de modelos hacia cinco llamadas fallidas antes de rendirse."""

    @pytest.mark.parametrize(
        "provider,env_var",
        [
            ("gemini", "GEMINI_API_KEY"),
            ("openai", "OPENAI_API_KEY"),
            ("anthropic", "ANTHROPIC_API_KEY"),
            ("groq", "GROQ_API_KEY"),
            ("deepseek", "DEEPSEEK_API_KEY"),
            ("openrouter", "OPENROUTER_API_KEY"),
        ],
    )
    def test_missing_key_is_detected(self, provider, env_var, monkeypatch):
        monkeypatch.delenv(env_var, raising=False)
        ok, error = validate_provider_credentials(provider)
        assert ok is False
        assert env_var in error

    def test_present_key_passes(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        assert validate_provider_credentials("gemini")[0] is True

    def test_ollama_needs_no_key(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
        assert validate_provider_credentials("ollama")[0] is True

    def test_unknown_provider_is_not_blocked(self):
        assert validate_provider_credentials("proveedor-raro")[0] is True


class TestReasoningModelDetection:
    """Los modelos o1/o3/gpt-5 rechazan max_tokens y temperature en Chat Completions."""

    @pytest.mark.parametrize(
        "model", ["o1", "o1-mini", "o3", "o3-mini", "o4-mini", "gpt-5", "openai/o3-mini"]
    )
    def test_reasoning_models_detected(self, model):
        assert _is_reasoning_model(model) is True

    @pytest.mark.parametrize(
        "model",
        [
            "gpt-4o",
            "gpt-4o-mini",
            "deepseek-chat",
            "llama-3.3-70b-versatile",
            "anthropic/claude-3.7-sonnet",
            "mistral-large",
            "",
        ],
    )
    def test_standard_models_not_flagged(self, model):
        assert _is_reasoning_model(model) is False
