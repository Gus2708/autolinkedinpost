"""Tests del cliente LLM unificado: credenciales y familias de modelos."""

import pytest

import base64

from src.llm_client import (
    FALLBACK_MODELS,
    PROVIDER_DEFAULT_MODELS,
    _build_vision_messages,
    _is_reasoning_model,
    _resolve_openai_compatible,
    generate_llm_text,
    generate_llm_vision,
    validate_provider_credentials,
)


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


class TestVisionMessages:
    """La auditoría visual estaba atada al SDK de Google: con otro proveedor no corría."""

    def test_builds_openai_multimodal_format(self):
        msgs = _build_vision_messages("Audita.", [b"img1", b"img2"], "Sos un auditor.", "image/png")
        assert [m["role"] for m in msgs] == ["system", "user"]
        content = msgs[-1]["content"]
        assert [p["type"] for p in content] == ["text", "image_url", "text", "image_url", "text"]

    def test_images_travel_as_base64_data_uri(self):
        msgs = _build_vision_messages("Audita.", [b"\x89PNG-datos"], "", "image/png")
        url = msgs[-1]["content"][1]["image_url"]["url"]
        assert url.startswith("data:image/png;base64,")
        assert base64.b64decode(url.split(",", 1)[1]) == b"\x89PNG-datos"

    def test_prompt_goes_last(self):
        msgs = _build_vision_messages("La consigna.", [b"a"], "", "image/png")
        assert msgs[-1]["content"][-1]["text"] == "La consigna."

    def test_slides_are_numbered(self):
        msgs = _build_vision_messages("x", [b"a", b"b", b"c"], "", "image/png")
        etiquetas = [p["text"] for p in msgs[-1]["content"] if p["type"] == "text"]
        assert "=== DIAPOSITIVA 1 DE 3 ===" in etiquetas
        assert "=== DIAPOSITIVA 3 DE 3 ===" in etiquetas

    def test_no_system_message_when_empty(self):
        msgs = _build_vision_messages("x", [b"a"], "", "image/png")
        assert [m["role"] for m in msgs] == ["user"]

    def test_no_images_returns_early(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "fake")
        texto, modelo = generate_llm_vision("x", [], provider="openrouter")
        assert texto == ""


class TestOpenRouterResolution:
    def test_default_model_has_provider_prefix(self):
        """OpenRouter identifica los modelos como 'proveedor/modelo'."""
        assert "/" in PROVIDER_DEFAULT_MODELS["openrouter"]

    def test_default_model_heads_the_fallback_chain(self):
        """El modelo elegido debe ser el primero que se intenta."""
        assert FALLBACK_MODELS["openrouter"][0] == PROVIDER_DEFAULT_MODELS["openrouter"]

    def test_fallback_chain_is_configurable(self):
        assert FALLBACK_MODELS["openrouter"], "la cascada de respaldo no debe quedar vacía"

    def test_resolves_openrouter_endpoint(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
        key, base_url, headers, default_model = _resolve_openai_compatible("openrouter")
        assert key == "fake-key"
        assert base_url == "https://openrouter.ai/api/v1"
        assert "HTTP-Referer" in headers and "X-Title" in headers
        assert default_model == PROVIDER_DEFAULT_MODELS["openrouter"]

    def test_vision_falls_back_to_next_model(self, monkeypatch):
        """Si el primer modelo no responde, debe probar el siguiente de la cascada."""
        intentos = []

        class FakeRes:
            def json(self):
                return {"choices": [{"message": {"content": '{"passed": true}'}}]}

        def fake_request(endpoint, headers, payload, label):
            intentos.append(payload["model"])
            return None if len(intentos) == 1 else FakeRes()

        monkeypatch.setenv("OPENROUTER_API_KEY", "fake")
        monkeypatch.setattr("src.llm_client._request_with_retries", fake_request)
        texto, modelo = generate_llm_vision("x", [b"img"], provider="openrouter")

        assert len(intentos) >= 2, "no probó el modelo de respaldo"
        assert texto == '{"passed": true}'
        assert modelo == intentos[-1]

    def test_sonnet_5_is_default_and_reasoning_model(self):
        """Sonnet 5 debe ser el modelo por defecto y clasificado como razonamiento."""
        assert PROVIDER_DEFAULT_MODELS["openrouter"] == "anthropic/claude-sonnet-5"
        assert _is_reasoning_model("anthropic/claude-sonnet-5") is True
        assert _is_reasoning_model("anthropic/claude-sonnet-4.5") is False

    def test_openrouter_402_auto_recovery(self, monkeypatch):
        """Cuando OpenRouter responde 402 con saldo limitado, debe adaptar max_tokens y reintentar."""
        captured_payloads = []

        class Fake402Res:
            status_code = 402
            ok = False
            text = '{"error":{"message":"You requested up to 2200 tokens, but can only afford 1800."}}'

        class FakeSuccessRes:
            status_code = 200
            ok = True
            text = '{"choices":[{"message":{"content":"Post generado exitosamente"}}]}'
            def json(self):
                return {"choices": [{"message": {"content": "Post generado exitosamente"}}]}

        def fake_request(endpoint, headers, payload, label):
            captured_payloads.append(dict(payload))
            if len(captured_payloads) == 1:
                return Fake402Res()
            return FakeSuccessRes()

        monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
        monkeypatch.setattr("src.llm_client._request_with_retries", fake_request)

        texto, modelo = generate_llm_text("Prompt", provider="openrouter", model="anthropic/claude-sonnet-5")
        assert texto == "Post generado exitosamente"
        assert len(captured_payloads) == 2
        # El segundo payload debe haber adaptado max_tokens al saldo disponible (1800 - 50 = 1750)
        assert captured_payloads[1]["max_tokens"] == 1750
