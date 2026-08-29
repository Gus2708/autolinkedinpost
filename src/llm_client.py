"""Módulo de cliente unificado para múltiples proveedores de LLM (Gemini, OpenAI, Anthropic Claude, DeepSeek, Groq, OpenRouter, Ollama y Custom OpenAI-Compatible)."""

import base64
import json
import os
import re
import time
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

# Cascada de respaldo para endpoints OpenAI-compatibles. Se usa cuando el modelo
# elegido devuelve un error transitorio persistente (429 por cuota, 503 por saturación).
# Configurable por entorno para poder cambiarla sin tocar código.
FALLBACK_MODELS = {
    "openrouter": [
        m.strip()
        for m in os.getenv(
            "OPENROUTER_FALLBACKS",
            "anthropic/claude-sonnet-4.5,openai/gpt-5,google/gemini-3.7-flash",
        ).split(",")
        if m.strip()
    ],
}

# Presupuesto de salida compartido. El paquete de publicación (post + comentario +
# guion de 10 láminas + sugerencia visual) no entra en 4096 tokens.
MAX_OUTPUT_TOKENS = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "8192"))

# Timeout y reintentos para los endpoints HTTP. Antes una sola falla de red
# perdía el post del día entero sin reintentar.
REQUEST_TIMEOUT = int(os.getenv("LLM_TIMEOUT_SECONDS", "90"))
MAX_RETRIES = 3
RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


# Familias de modelos de razonamiento que no aceptan 'max_tokens' ni 'temperature'
# en la API de Chat Completions.
_REASONING_MODEL_RE = re.compile(r"(?:^|/)(?:o[1-9](?:-|$)|gpt-5)", re.IGNORECASE)


def _is_reasoning_model(model: str) -> bool:
    """Indica si el modelo pertenece a una familia de razonamiento.

    Contempla el prefijo de proveedor que usa OpenRouter ('openai/o3-mini').
    """
    return bool(_REASONING_MODEL_RE.search(model or ""))


def _request_with_retries(
    endpoint: str,
    headers: Dict[str, str],
    payload: Dict[str, Any],
    provider_label: str,
) -> Optional[requests.Response]:
    """POST con backoff exponencial sobre errores transitorios y rate limits."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            res = requests.post(endpoint, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
            if res.ok:
                return res

            if res.status_code in RETRYABLE_STATUS and attempt < MAX_RETRIES:
                # Respetar Retry-After cuando el proveedor lo indica.
                wait = float(res.headers.get("Retry-After") or 0) or (2 ** attempt)
                print(
                    f"[WARN] {provider_label} HTTP {res.status_code} "
                    f"(intento {attempt}/{MAX_RETRIES}), reintentando en {wait:.0f}s..."
                )
                time.sleep(min(wait, 30))
                continue

            print(f"[ERROR] {provider_label} HTTP {res.status_code}: {res.text[:200]}")
            return None
        except requests.RequestException as e:
            if attempt < MAX_RETRIES:
                wait = 2 ** attempt
                print(f"[WARN] {provider_label} error de red (intento {attempt}/{MAX_RETRIES}): {e}. Reintento en {wait}s...")
                time.sleep(wait)
                continue
            print(f"[ERROR] {provider_label} inalcanzable tras {MAX_RETRIES} intentos: {e}")
    return None


PROVIDER_DEFAULT_MODELS = {
    "gemini": "gemini-3.7-flash",
    "openai": "gpt-4o",
    "anthropic": "claude-3-7-sonnet-20250219",
    "deepseek": "deepseek-chat",
    "groq": "llama-3.3-70b-versatile",
    "openrouter": "anthropic/claude-sonnet-4.5",
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


# Variable de entorno que aporta la credencial de cada proveedor.
PROVIDER_API_KEY_ENV = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "custom": "CUSTOM_LLM_API_KEY",
    # Ollama corre local y no usa API key.
}


def validate_provider_credentials(provider: str) -> Tuple[bool, str]:
    """Comprueba que exista la credencial del proveedor antes de empezar a generar.

    Sin esto, una key ausente recorría toda la cascada de modelos de fallback —cinco
    llamadas fallidas por cada texto— antes de rendirse con un post vacío.

    Retorna: (es_valido, mensaje_de_error)
    """
    prov = (provider or "").strip().lower()

    if prov == "ollama":
        if not os.getenv("OLLAMA_BASE_URL"):
            return True, ""  # usa el default localhost
        return True, ""

    env_var = PROVIDER_API_KEY_ENV.get(prov)
    if not env_var:
        return True, ""  # proveedor desconocido: dejar que falle en la llamada

    if not os.getenv(env_var):
        return False, (
            f"El proveedor '{prov}' está seleccionado pero {env_var} no está configurada. "
            f"Definí {env_var} o cambiá LLM_PROVIDER."
        )
    return True, ""


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

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
    }

    # Los modelos de razonamiento (o1, o3, o4, gpt-5...) rechazan 'max_tokens' y
    # 'temperature': usan 'max_completion_tokens' y sólo aceptan el default de temperatura.
    if _is_reasoning_model(model):
        payload["max_completion_tokens"] = MAX_OUTPUT_TOKENS
    else:
        payload["temperature"] = temperature
        payload["max_tokens"] = MAX_OUTPUT_TOKENS

    res = _request_with_retries(endpoint, headers, payload, f"Provider ({base_url})")

    # Red de seguridad para endpoints que rechazan un parámetro que no anticipamos:
    # reintentar una vez con el payload mínimo antes de darlo por perdido.
    if res is None and len(payload) > 2:
        print("[WARN] Reintentando con el payload mínimo (sin max_tokens ni temperature)...")
        res = _request_with_retries(
            endpoint,
            headers,
            {"model": model, "messages": messages},
            f"Provider ({base_url}) [payload mínimo]",
        )

    if res is None:
        return "", model

    try:
        data = res.json()
        choices = data.get("choices", [])
        if choices:
            choice = choices[0]
            content = (choice.get("message", {}) or {}).get("content", "") or ""

            if choice.get("finish_reason") == "length":
                print(f"[WARN] {model} cortó la respuesta por límite de tokens; el paquete puede venir incompleto.")

            return content.strip(), model
        print(f"[ERROR] El proveedor no devolvió 'choices': {str(data)[:200]}")
    except (ValueError, KeyError) as e:
        print(f"[ERROR] Respuesta inesperada del endpoint OpenAI-Compatible ({base_url}): {e}")

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
        # El paquete completo son post + primer comentario + 10 láminas + sugerencia
        # visual. Con 4096 tokens el guion del carrusel se cortaba a la mitad.
        "max_tokens": MAX_OUTPUT_TOKENS,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system_instruction:
        payload["system"] = system_instruction

    res = _request_with_retries(endpoint, headers, payload, "Anthropic")
    if res is None:
        return "", model

    try:
        data = res.json()
        content_blocks = data.get("content", [])
        text_parts = [b.get("text", "") for b in content_blocks if b.get("type") == "text"]

        if data.get("stop_reason") == "max_tokens":
            print(f"[WARN] Anthropic cortó la respuesta por max_tokens ({MAX_OUTPUT_TOKENS}); el paquete puede venir incompleto.")

        return "".join(text_parts).strip(), model
    except (ValueError, KeyError) as e:
        print(f"[ERROR] Respuesta inesperada de Anthropic: {e}")

    return "", model


def extract_json_object(raw: str) -> Optional[Dict[str, Any]]:
    """Extrae el primer objeto JSON balanceado del texto, tolerando fences de markdown y prosa."""
    if not raw:
        return None

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL | re.IGNORECASE)
    candidates = [fenced.group(1)] if fenced else []

    # Escaneo con conteo de llaves: soporta objetos anidados sin depender de un match greedy.
    depth = 0
    start = -1
    in_string = False
    escaped = False
    for i, ch in enumerate(raw):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start != -1:
                candidates.append(raw[start:i + 1])
                start = -1

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def _build_vision_messages(
    prompt: str,
    images: List[bytes],
    system_instruction: str,
    image_mime: str,
) -> List[Dict[str, Any]]:
    """Arma los mensajes multimodales en el formato de OpenAI Chat Completions.

    Las imágenes viajan como data URI en base64 dentro del array `content`, que es
    el formato que aceptan OpenRouter, OpenAI y el resto de endpoints compatibles.
    """
    messages: List[Dict[str, Any]] = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})

    content: List[Dict[str, Any]] = []
    for idx, raw in enumerate(images, start=1):
        b64 = base64.b64encode(raw).decode("ascii")
        content.append({"type": "text", "text": f"=== DIAPOSITIVA {idx} DE {len(images)} ==="})
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{image_mime};base64,{b64}"},
        })
    content.append({"type": "text", "text": prompt})

    messages.append({"role": "user", "content": content})
    return messages


def generate_llm_vision(
    prompt: str,
    images: List[bytes],
    system_instruction: str = "",
    temperature: float = 0.2,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    image_mime: str = "image/png",
    json_response: bool = False,
) -> Tuple[str, str]:
    """Genera texto a partir de un prompt y una lista de imágenes.

    La auditoría visual del carrusel estaba atada al SDK de Google: con cualquier otro
    proveedor configurado, esa capa simplemente no corría. Esta función la lleva al
    cliente unificado, de modo que funcione sobre cualquier endpoint multimodal
    compatible con OpenAI (OpenRouter, OpenAI, o uno propio).

    Retorna: (texto_generado, modelo_utilizado)
    """
    prov = (provider or detect_provider()).strip().lower()
    if not images:
        return "", model or ""

    # Gemini conserva su SDK nativo: ya está probado y evita una conversión extra.
    if prov == "gemini":
        return _call_gemini_vision(
            prompt, images, system_instruction,
            api_key or os.getenv("GEMINI_API_KEY", ""),
            model, temperature, image_mime,
        )

    key, base_url, extra_headers, default_model = _resolve_openai_compatible(prov, api_key)
    chosen = model or os.getenv("LLM_VISION_MODEL") or default_model
    candidatos = [chosen] + [m for m in FALLBACK_MODELS.get(prov, []) if m != chosen]

    endpoint = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}" if key else "",
    }
    if extra_headers:
        headers.update(extra_headers)

    messages = _build_vision_messages(prompt, images, system_instruction, image_mime)

    for candidato in candidatos:
        payload: Dict[str, Any] = {"model": candidato, "messages": messages}
        if not _is_reasoning_model(candidato):
            payload["temperature"] = temperature
            payload["max_tokens"] = MAX_OUTPUT_TOKENS
        else:
            payload["max_completion_tokens"] = MAX_OUTPUT_TOKENS
        if json_response:
            payload["response_format"] = {"type": "json_object"}

        res = _request_with_retries(endpoint, headers, payload, f"Vision ({candidato})")
        if res is None:
            print(f"[WARN] El modelo de visión {candidato} no respondió; probando siguiente...")
            continue

        try:
            data = res.json()
            choices = data.get("choices", [])
            if choices:
                content = (choices[0].get("message", {}) or {}).get("content", "") or ""
                if content.strip():
                    return content.strip(), candidato
            print(f"[WARN] {candidato} devolvió una respuesta vacía; probando siguiente...")
        except (ValueError, KeyError) as e:
            print(f"[WARN] Respuesta inesperada de {candidato}: {e}")

    return "", chosen


def _call_gemini_vision(
    prompt: str,
    images: List[bytes],
    system_instruction: str,
    api_key: str,
    model: Optional[str],
    temperature: float,
    image_mime: str,
) -> Tuple[str, str]:
    """Auditoría visual con el SDK nativo de Gemini y su cascada de respaldo."""
    if not GENAI_AVAILABLE or not api_key:
        return "", model or ""

    client = genai.Client(api_key=api_key)
    preferido = model or "gemini-3.5-flash"
    modelos = [preferido] + [m for m in GEMINI_FALLBACKS if m != preferido]

    contents: List[Any] = []
    for idx, raw in enumerate(images, start=1):
        contents.append(f"=== DIAPOSITIVA {idx} DE {len(images)} ===")
        contents.append(genai_types.Part.from_bytes(data=raw, mime_type=image_mime))
    contents.append(prompt)

    for m in modelos:
        try:
            response = client.models.generate_content(
                model=m,
                contents=contents,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_instruction or None,
                    temperature=temperature,
                    response_mime_type="application/json",
                ),
            )
            texto = (response.text or "").strip()
            if texto:
                return texto, m
        except Exception as e:
            print(f"[WARN] Visión con {m} falló ({str(e)[:80]}); probando siguiente...")
            continue

    return "", preferido


def _resolve_openai_compatible(
    prov: str,
    api_key: Optional[str] = None,
) -> Tuple[str, str, Optional[Dict[str, str]], str]:
    """Devuelve (api_key, base_url, extra_headers, modelo_por_defecto) del proveedor."""
    if prov == "openrouter":
        repo_slug = os.getenv("GITHUB_REPOSITORY") or "autolinkedinpost"
        return (
            api_key or os.getenv("OPENROUTER_API_KEY", ""),
            "https://openrouter.ai/api/v1",
            {
                "HTTP-Referer": os.getenv("OPENROUTER_REFERER", f"https://github.com/{repo_slug}"),
                "X-Title": os.getenv("OPENROUTER_TITLE", "AutoLinkedInPost"),
            },
            PROVIDER_DEFAULT_MODELS["openrouter"],
        )
    if prov == "openai":
        return (
            api_key or os.getenv("OPENAI_API_KEY", ""),
            os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            None,
            "gpt-4o-mini",
        )
    if prov == "groq":
        return (api_key or os.getenv("GROQ_API_KEY", ""), "https://api.groq.com/openai/v1", None, PROVIDER_DEFAULT_MODELS["groq"])
    if prov == "deepseek":
        return (api_key or os.getenv("DEEPSEEK_API_KEY", ""), "https://api.deepseek.com/v1", None, PROVIDER_DEFAULT_MODELS["deepseek"])
    if prov == "ollama":
        return ("", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"), None, PROVIDER_DEFAULT_MODELS["ollama"])

    return (
        api_key or os.getenv("CUSTOM_LLM_API_KEY", ""),
        os.getenv("CUSTOM_LLM_BASE_URL", "http://localhost:8000/v1"),
        None,
        "default",
    )


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
        # OpenRouter usa estas cabeceras para atribuir el tráfico. En un fork deben
        # apuntar al repo de quien lo corre, no al original.
        repo_slug = os.getenv("GITHUB_REPOSITORY") or "autolinkedinpost"
        headers = {
            "HTTP-Referer": os.getenv("OPENROUTER_REFERER", f"https://github.com/{repo_slug}"),
            "X-Title": os.getenv("OPENROUTER_TITLE", "AutoLinkedInPost"),
        }
        return _call_openai_compatible(prompt, system_instruction, key, base_url, chosen_model or PROVIDER_DEFAULT_MODELS["openrouter"], temperature, extra_headers=headers)

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
