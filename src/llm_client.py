"""Módulo de cliente unificado para múltiples proveedores de LLM (Gemini, OpenAI, Anthropic Claude, DeepSeek, Groq, OpenRouter, Ollama y Custom OpenAI-Compatible)."""

import json
import os
from typing import Any, Dict, List, Optional, Tuple
import requests

try:
    from google import genai
    from google.genai import types as genai_types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


GEMINI_FALLBACKS = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
]

PROVIDER_DEFAULT_MODELS = {
    "gemini": "gemini-3.7-flash",
    "openai": "gpt-4o",
    "anthropic": "claude-3-7-sonnet-20250219",
    "deepseek": "deepseek-chat",
    "groq": "llama-3.3-70b-versatile",
    "openrouter": "anthropic/claude-3.7-sonnet",
    "ollama": "llama3.2",
    "custom": "default",
}


def detect_provider() -> str:
    """Detecta automáticamente el proveedor de LLM configurado en el entorno."""
    explicit_provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if explicit_provider in PROVIDER_DEFAULT_MODELS:
        return explicit_provider

    # Detección heurística por API Keys disponibles
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("DEEPSEEK_API_KEY"):
        return "deepseek"
    if os.getenv("GROQ_API_KEY"):
        return "groq"
    if os.getenv("OPENROUTER_API_KEY"):
        return "openrouter"
    if os.getenv("OLLAMA_BASE_URL"):
        return "ollama"
    return "gemini"


def _call_gemini(
    prompt: str,
    system_instruction: str,
    api_key: str,
    model: str,
    temperature: float = 0.4,
) -> Tuple[str, str]:
    """Ejecuta llamada con Google Gemini y su cascada de fallback rápida."""
    if not GENAI_AVAILABLE:
        raise ImportError("google-genai no está instalado.")

    client = genai.Client(api_key=api_key)
    preferred_model = model or "gemini-3.7-flash"
    models_to_try = [preferred_model] + [m for m in GEMINI_FALLBACKS if m != preferred_model]

    for m in models_to_try:
        try:
            response = client.models.generate_content(
                model=m,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_instruction or None,
                    temperature=temperature,
                ),
            )
            text = response.text or ""
            if text.strip():
                return text.strip(), m
        except Exception as e:
            print(f"[WARN] Gemini {m} falló ({str(e)[:60]}), probando siguiente...")
            continue

    return "", preferred_model


def _call_openai_compatible(
    prompt: str,
    system_instruction: str,
    api_key: str,
    base_url: str,
    model: str,
    temperature: float = 0.4,
    extra_headers: Optional[Dict[str, str]] = None,
) -> Tuple[str, str]:
    """Llamada universal a cualquier endpoint compatible con OpenAI Chat Completions."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}" if api_key else "",
    }
    if extra_headers:
        headers.update(extra_headers)

    endpoint = base_url.rstrip("/") + "/chat/completions"

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    try:
        res = requests.post(endpoint, headers=headers, json=payload, timeout=45)
        if not res.ok:
            print(f"[ERROR] Provider HTTP {res.status_code}: {res.text[:120]}")
            return "", model

        data = res.json()
        choices = data.get("choices", [])
        if choices and len(choices) > 0:
            content = choices[0].get("message", {}).get("content", "")
            return content.strip(), model
    except Exception as e:
        print(f"[ERROR] Error llamando a endpoint OpenAI-Compatible ({base_url}): {e}")

    return "", model


def _call_anthropic(
    prompt: str,
    system_instruction: str,
    api_key: str,
    model: str,
    temperature: float = 0.4,
) -> Tuple[str, str]:
    """Llamada a la API nativa de Anthropic Claude."""
    endpoint = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    payload = {
        "model": model or "claude-3-7-sonnet-20250219",
        "max_tokens": 4096,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system_instruction:
        payload["system"] = system_instruction

    try:
        res = requests.post(endpoint, headers=headers, json=payload, timeout=45)
        if not res.ok:
            print(f"[ERROR] Anthropic HTTP {res.status_code}: {res.text[:120]}")
            return "", model

        data = res.json()
        content_blocks = data.get("content", [])
        text_parts = [b.get("text", "") for b in content_blocks if b.get("type") == "text"]
        return "".join(text_parts).strip(), model
    except Exception as e:
        print(f"[ERROR] Error llamando a Anthropic Claude: {e}")

    return "", model


def generate_llm_text(
    prompt: str,
    system_instruction: str = "",
    temperature: float = 0.4,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Tuple[str, str]:
    """Punto de entrada unificado para generar texto con cualquier LLM.
    
    Retorna: (texto_generado, modelo_utilizado)
    """
    prov = (provider or detect_provider()).strip().lower()
    chosen_model = model or os.getenv("LLM_MODEL") or os.getenv("GEMINI_MODEL") or PROVIDER_DEFAULT_MODELS.get(prov, "")

    if prov == "gemini":
        key = api_key or os.getenv("GEMINI_API_KEY", "")
        return _call_gemini(prompt, system_instruction, key, chosen_model, temperature)

    elif prov == "openai":
        key = api_key or os.getenv("OPENAI_API_KEY", "")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        return _call_openai_compatible(prompt, system_instruction, key, base_url, chosen_model or "gpt-4o", temperature)

    elif prov == "anthropic":
        key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        return _call_anthropic(prompt, system_instruction, key, chosen_model or "claude-3-7-sonnet-20250219", temperature)

    elif prov == "deepseek":
        key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        base_url = "https://api.deepseek.com/v1"
        return _call_openai_compatible(prompt, system_instruction, key, base_url, chosen_model or "deepseek-chat", temperature)

    elif prov == "groq":
        key = api_key or os.getenv("GROQ_API_KEY", "")
        base_url = "https://api.groq.com/openai/v1"
        return _call_openai_compatible(prompt, system_instruction, key, base_url, chosen_model or "llama-3.3-70b-versatile", temperature)

    elif prov == "openrouter":
        key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        base_url = "https://openrouter.ai/api/v1"
        headers = {
            "HTTP-Referer": "https://github.com/Gus2708/autolinkedinpost",
            "X-Title": "AutoLinkedInPost",
        }
        return _call_openai_compatible(prompt, system_instruction, key, base_url, chosen_model or "anthropic/claude-3.7-sonnet", temperature, extra_headers=headers)

    elif prov == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        return _call_openai_compatible(prompt, system_instruction, "", base_url, chosen_model or "llama3.2", temperature)

    elif prov == "custom":
        key = api_key or os.getenv("CUSTOM_LLM_API_KEY", "")
        base_url = os.getenv("CUSTOM_LLM_BASE_URL", "http://localhost:8000/v1")
        return _call_openai_compatible(prompt, system_instruction, key, base_url, chosen_model or "default", temperature)

    # Fallback por defecto a Gemini si no coincide
    key = api_key or os.getenv("GEMINI_API_KEY", "")
    return _call_gemini(prompt, system_instruction, key, chosen_model, temperature)
