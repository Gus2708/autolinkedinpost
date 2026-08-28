"""Módulo de evaluación avanzada (LLM-as-a-Judge) para publicaciones de LinkedIn.
Audita calidad algorítmica, veracidad absoluta (Zero Hallucination) y anti-AI tells según la Guía 2026.
Compatible con cualquier LLM (Gemini, OpenAI, Anthropic, DeepSeek, Groq, OpenRouter, Ollama).
"""

import json
import re
from typing import Any, Dict, Optional
from src.llm_client import generate_llm_text


EVALUATION_RUBRIC_SYSTEM = """
Sos un Evaluador Experto y Auditor Técnico de Contenido de LinkedIn para Ingenieros de Software.
Tu tarea es auditar de manera rigurosa si una publicación cumple con los más altos estándares de VERACIDAD ABSOLUTA, sustancia técnica real y optimización para el algoritmo 2026.

RÚBRICA DE EVALUACIÓN (Escala 1 a 5):

1. **factual_grounding** (Veracidad Absoluta y CERO Alucinación - CRÍTICO):
   - 5: 100% Verídico y fundamentado. Describe exactamente lo que hace el repositorio o los commits. No inventa empresas ficticias, caídas de producción inventadas ("se cayó 3 veces el mes pasado"), ni métricas falsas si no están en el contexto.
   - 3: Algo exagerado en el dramatismo, pero respeta las herramientas y código real.
   - 1: INVENTO TOTAL. Falsifica métricas de millones de usuarios, caídas de producción inexistentes o tecnologías ausentes en el repo.

2. **hook_strength** (Gancho antes de 'Ver más' - máx 220 caracteres):
   - 5: Excelente. Inicia en las primeras 2 líneas con tensión técnica real, contraste o el desafío de arquitectura genuino del proyecto.
   - 3: Aceptable pero genérico.
   - 1: Pésimo. Pregunta retórica cliché ("¿Alguna vez te has preguntado...?"), saludo o divagación vaga.

3. **mobile_readability** (Formato Mobile-First):
   - 5: Perfecto. Párrafos de máximo 2 a 3 líneas con líneas en blanco obligatorias entre párrafos.
   - 3: Párrafos algo largos (4-5 líneas).
   - 1: Bloque de texto denso ilegible en pantallas móviles.

4. **anti_ai_tells** (Cero clichés de IA, Manifiesto Humanizer y 1ª Persona Singular):
   - 5: 100% Humano, auténtico y en PRIMERA PERSONA SINGULAR ("Diseñé", "Decidí", "Me costó"). Cero plurales ("diseñamos"), cero voz pasiva ("se implementó"). Cero AI slop: libre de "un testimonio de", "sin fisuras" (seamless), "game changer", "revolucionario", "en el vertiginoso mundo...", "no se trata de X sino de Y", o tríadas de adjetivos.
   - 3: Tono algo artificial o usa algún cliché menor o plural aislado.
   - 1: Típico texto generado por IA con clichés promocionales y vacío de sustancia humana.

5. **technical_authority** (Sustancia de Ingeniería y Arquitectura):
   - 5: Demuestra criterio senior real: decisiones concretas, trade-offs (latencia vs memoria, desacoplamiento, concurrencia), patrones o archivos reales.
   - 3: Superficial o genérico.
   - 1: Sin valor técnico.

6. **save_and_cta_factor** (Incentivo de Debate Técnico y Comentarios):
   - 5: Cierre excelente con pregunta técnica provocativa, concreta o invitación a debatir trade-offs/patrones entre colegas en comentarios.
   - 3: Cierre aceptable.
   - 1: Frases repetitivas/robóticas tipo 'Guardá este post si...' o clichés vacíos sin sustancia técnica.

INSTRUCCIONES CRÍTICAS:
- Primero encuentra la evidencia y escribe la JUSTIFICACIÓN para cada criterio (Chain-of-Thought).
- Si el post INVENTA historias o métricas que no están en el código/commits, 'factual_grounding' DEBE ser 1 o 2 y 'passed' DEBE ser false.
- Responde ÚNICAMENTE con un JSON válido estructurado.
"""

EVALUATION_PROMPT_TEMPLATE = """
Evalúa la siguiente publicación generada para LinkedIn contrastándola con el contexto real del repositorio:

=== CONTEXTO DEL REPOSITORIO / COMMITS ===
{repo_context}

=== PUBLICACIÓN A EVALUAR ===
{post_text}

Devuelve tu veredicto exclusivamente en formato JSON con la siguiente estructura exacta:
{{
  "evaluations": {{
    "factual_grounding": {{
      "justification": "Por qué es 100% verídico o qué métrica/hecho inventó...",
      "score": 5.0
    }},
    "hook_strength": {{
      "justification": "...",
      "score": 5.0
    }},
    "mobile_readability": {{
      "justification": "...",
      "score": 5.0
    }},
    "anti_ai_tells": {{
      "justification": "...",
      "score": 5.0
    }},
    "technical_authority": {{
      "justification": "...",
      "score": 5.0
    }},
    "save_and_cta_factor": {{
      "justification": "...",
      "score": 5.0
    }}
  }},
  "overall_score": 4.8,
  "passed": true,
  "actionable_feedback": "Sugerencias concretas si hubo invenciones o puntajes menores a 4.0..."
}}
"""


def _extract_json_object(raw: str) -> Optional[Dict[str, Any]]:
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


def _unevaluated_verdict(reason: str) -> Dict[str, Any]:
    """Veredicto fail-closed: si el juez no pudo emitir dictamen, el post NO se da por aprobado.

    'evaluated' distingue "el juez reprobó el post" de "el juez no pudo correr", para que el
    llamador no dispare un refinamiento inútil sobre un fallo de infraestructura.
    """
    return {
        "overall_score": 0.0,
        "passed": False,
        "evaluated": False,
        "actionable_feedback": "",
        "evaluations": {},
        "error": reason,
    }


def evaluate_linkedin_post(
    post_text: str,
    api_key: Optional[str] = None,
    repo_context: str = "",
    preferred_model: Optional[str] = None,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Evalúa un post con LLM-as-a-Judge usando cualquier proveedor configurado.

    Falla CERRADO: si la evaluación no se puede completar (error de red, JSON inválido,
    respuesta vacía), devuelve passed=False con evaluated=False en lugar de aprobar por defecto.
    """
    prompt = EVALUATION_PROMPT_TEMPLATE.format(
        repo_context=repo_context[:2000] or "No provisto",
        post_text=post_text,
    )

    try:
        raw_output, _ = generate_llm_text(
            prompt=prompt,
            system_instruction=EVALUATION_RUBRIC_SYSTEM,
            temperature=0.2,
            provider=provider,
            model=preferred_model,
            api_key=api_key,
        )
    except Exception as e:
        print(f"[WARN] El juez LLM no respondió: {e}. El post queda SIN aprobar.")
        return _unevaluated_verdict(f"excepción llamando al proveedor: {e}")

    result = _extract_json_object(raw_output)
    if result is None:
        preview = (raw_output or "")[:120].replace("\n", " ")
        print(f"[WARN] El juez LLM no devolvió JSON parseable. El post queda SIN aprobar. Respuesta: {preview!r}")
        return _unevaluated_verdict("respuesta del juez sin JSON válido")

    # El JSON puede ser sintácticamente válido pero traer tipos inesperados
    # ("overall_score": null, "evaluations" como lista). Sin esta protección, una
    # respuesta así lanzaba TypeError/AttributeError que subía hasta main() y
    # abortaba la generación de todos los repos del día.
    try:
        return _normalize_verdict(result)
    except (TypeError, ValueError, AttributeError, KeyError) as e:
        print(f"[WARN] El veredicto del juez tiene una forma inesperada ({e}). El post queda SIN aprobar.")
        return _unevaluated_verdict(f"veredicto con estructura inválida: {e}")


def _coerce_score(value: Any) -> Optional[float]:
    """Convierte un puntaje a float, o None si no es un número utilizable.

    Los booleanos se descartan explícitamente: en Python `True` es instancia de int
    y se colaría como un puntaje de 1.0.
    """
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _normalize_verdict(result: Dict[str, Any]) -> Dict[str, Any]:
    """Valida y completa el veredicto del juez, tolerando campos ausentes o mal tipados."""
    result["evaluated"] = True

    # 'evaluations' debe ser un dict de criterios; cualquier otra cosa se ignora.
    raw_scores = result.get("evaluations")
    scores: Dict[str, Any] = raw_scores if isinstance(raw_scores, dict) else {}
    if raw_scores is not None and not isinstance(raw_scores, dict):
        print("[WARN] El juez devolvió 'evaluations' con un tipo inesperado; se ignora el detalle por criterio.")
        result["evaluations"] = {}

    numeric = []
    for criterion in scores.values():
        if isinstance(criterion, dict):
            value = _coerce_score(criterion.get("score"))
            if value is not None:
                numeric.append(value)

    overall = _coerce_score(result.get("overall_score"))
    if overall is None:
        # Derivar del promedio en vez de asumir aprobado.
        overall = round(sum(numeric) / len(numeric), 2) if numeric else 0.0
    result["overall_score"] = overall

    passed = result.get("passed")
    if not isinstance(passed, bool):
        passed = overall >= 4.0

    # Veracidad es criterio eliminatorio: sin grounding no hay publicación.
    grounding = scores.get("factual_grounding")
    if isinstance(grounding, dict):
        grounding_score = _coerce_score(grounding.get("score"))
        if grounding_score is not None and grounding_score < 4:
            passed = False

    result["passed"] = passed
    return result
