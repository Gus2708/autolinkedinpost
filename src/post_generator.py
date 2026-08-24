"""Módulo de generación de contenido para LinkedIn usando Google Gemini."""

import time
from typing import Any, Dict, List, Optional
from google import genai
from google.genai import types


SYSTEM_INSTRUCTION = """
Sos un Senior Software Engineer y Tech Lead creando contenido de alto impacto para LinkedIn sobre tus proyectos y decisiones de arquitectura de software.

TUS REGLAS DE ORO DE REDACCIÓN (ANTI-AI TELLS):
1. PROHIBIDO sonar como un bot corporativo. NUNCA uses frases cliché como:
   - "En el vertiginoso mundo tecnológico..."
   - "Estoy emocionado/orgulloso de compartir..."
   - "Sumerjámonos en..." / "Vamos a profundizar..."
   - "Un testimonio de...", "Un antes y un después...", "Revolucionario", "Game-changer".
2. TONO: Natural, directo, profesional pero humano y técnico. Como si le hablaras a un colega en un café o un space técnico.
3. ESTRUCTURA DEL POST:
   - **Gancho (Hook)**: Primera línea potente (un problema real del proyecto, una decisión técnica contraintuitiva o un reto superado).
   - **Cuerpo (2-3 párrafos cortos)**: Contexto del desafío, la solución arquitectónica/técnica aplicada y el 'por qué' detrás de las decisiones.
   - **Aprendizaje / Cierre**: Un insight técnico concreto o una pregunta genuina que invite al debate entre desarrolladores.
   - **Hashtags**: Máximo 3 o 4 hashtags técnicos y relevantes al final (ej: #Architecture #SoftwareEngineering #Python #GoLang #DevOps).
4. SUGERENCIA DE CAPTURA / RECURSO VISUAL:
   - Proponé una sugerencia clara y específica de qué captura de pantalla, diagrama (arquitectura/flujo), snippet de código o terminal output sumaría más valor para este proyecto específico.
"""

PROJECT_PROMPT_TEMPLATE = """
A partir de la siguiente actividad reciente en el repositorio/proyecto '{repo_name}':

Commits y cambios técnicos:
{commits_text}

Generá:
1. El **Post para LinkedIn** enfocado EXCLUSIVAMENTE en este proyecto (en español).
2. La sección de **Sugerencia de Captura / Imagen** describiendo con precisión qué mostrar.

Entregá la respuesta respetando EXACTAMENTE esta estructura:

=== LINKEDIN_POST ===
[Aquí el texto completo del post para este proyecto]

=== SUGERENCIA_VISUAL ===
[Aquí la recomendación concreta de qué captura, diagrama o snippet capturar/adjuntar]
"""

SHOWCASE_PROMPT_TEMPLATE = """
Sos un desarrollador senior presentando tu proyecto de software '{name}' en LinkedIn para que reclutadores técnicos y Engineering Managers entiendan tus virtudes de ingeniería y tu criterio arquitectónico.

Información del proyecto:
- **Repositorio**: {full_name}
- **Descripción**: {description}
- **Stack / Lenguajes**: {languages}
- **Estructura de archivos clave**: {key_files}
- **Extracto del README**:
{readme}

Tu objetivo:
Redactar un post técnico de portafolio que demuestre:
1. **Problema Real y de Negocio/Técnico**: Qué resuelve este sistema y por qué era un desafío no trivial.
2. **Decisiones de Arquitectura y Patrones**: Por qué elegiste ciertas tecnologías, patrones (ej: RAG, Outbox, CQRS, Caching, Event-driven, Microservicios, Concurrencia) o estructuras de datos en lugar de soluciones genéricas.
3. **Escala, Latencia o Trade-offs**: Qué compromisos técnicos asumiste y cómo garantizaste mantenibilidad, velocidad o resiliencia.
4. **Cierre / Aprendizaje**: Una lección clara de ingeniería o una pregunta técnica que invite a comentar.

Entregá la respuesta respetando EXACTAMENTE esta estructura:

=== LINKEDIN_POST ===
[Aquí el post de showcase completo y listo para publicar]

=== SUGERENCIA_VISUAL ===
[Aquí la recomendación concreta del diagrama de arquitectura, esquema C4, métrica o captura de UI/Terminal ideal para acompañar este showcase]
"""

FALLBACK_MODELS = [
    "gemini-3.6-flash",
    "gemini-2.5-flash",
    "gemini-flash-latest",
]


def _call_gemini_with_retry(
    prompt: str,
    api_key: str,
    preferred_model: str = "gemini-3.6-flash",
    max_retries: int = 3,
) -> str:
    """Ejecuta una llamada a Gemini con reintentos y fallback de modelos."""
    client = genai.Client(api_key=api_key)
    models_to_try = [preferred_model] + [m for m in FALLBACK_MODELS if m != preferred_model]

    for model in models_to_try:
        for attempt in range(1, max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.7,
                    ),
                )
                text = response.text or ""
                if text.strip():
                    return text
            except Exception as e:
                print(f"[WARN] Error con {model} (intento {attempt}/{max_retries}): {e}")
                time.sleep(2 * attempt)
    return ""


def _parse_gemini_sections(raw_text: str, default_name: str) -> Dict[str, str]:
    """Parsea las secciones de LINKEDIN_POST y SUGERENCIA_VISUAL."""
    if "=== LINKEDIN_POST ===" in raw_text and "=== SUGERENCIA_VISUAL ===" in raw_text:
        parts = raw_text.split("=== SUGERENCIA_VISUAL ===")
        post_part = parts[0].replace("=== LINKEDIN_POST ===", "").strip()
        visual_part = parts[1].strip() if len(parts) > 1 else ""
        return {"post": post_part, "visual_suggestion": visual_part}
    return {
        "post": raw_text.strip(),
        "visual_suggestion": f"Captura de pantalla de la arquitectura o interfaz de {default_name}."
    }


def generate_single_project_post(
    repo_name: str,
    commits: List[str],
    api_key: str,
    preferred_model: str = "gemini-3.6-flash",
) -> Optional[Dict[str, str]]:
    """Genera un post para novedades de un proyecto específico."""
    commits_text = "\n".join([f"- {c}" for c in commits])
    prompt = PROJECT_PROMPT_TEMPLATE.format(
        repo_name=repo_name,
        commits_text=commits_text,
    )
    raw_text = _call_gemini_with_retry(prompt, api_key, preferred_model)
    if not raw_text:
        return None

    sections = _parse_gemini_sections(raw_text, repo_name)
    return {
        "repo_name": repo_name,
        "post": sections["post"],
        "visual_suggestion": sections["visual_suggestion"],
    }


def generate_posts_by_project(
    activity_by_repo: Dict[str, List[str]],
    api_key: str,
    model_name: str = "gemini-3.6-flash",
) -> List[Dict[str, str]]:
    """Genera posts independientes para cada repositorio activo en el changelog diario."""
    results = []
    for repo_name, commits in activity_by_repo.items():
        if not commits:
            continue
        print(f"[INFO] Generando post para proyecto: {repo_name}...")
        project_result = generate_single_project_post(
            repo_name=repo_name,
            commits=commits,
            api_key=api_key,
            preferred_model=model_name,
        )
        if project_result and project_result.get("post"):
            results.append(project_result)
        time.sleep(2)
    return results


def generate_project_showcase_post(
    repo_context: Dict[str, Any],
    api_key: str,
    model_name: str = "gemini-3.6-flash",
) -> Optional[Dict[str, str]]:
    """Genera un post de portafolio/showcase completo para reclutadores sobre un proyecto específico."""
    prompt = SHOWCASE_PROMPT_TEMPLATE.format(
        name=repo_context.get("name", "Proyecto"),
        full_name=repo_context.get("full_name", ""),
        description=repo_context.get("description", "Sin descripción"),
        languages=", ".join(repo_context.get("languages", [])) or "No especificado",
        key_files=", ".join(repo_context.get("key_files", [])) or "No disponible",
        readme=repo_context.get("readme", "No hay README disponible.")[:2500],
    )

    raw_text = _call_gemini_with_retry(prompt, api_key, model_name)
    if not raw_text:
        return None

    sections = _parse_gemini_sections(raw_text, repo_context.get("name", "proyecto"))
    return {
        "repo_name": repo_context.get("full_name", repo_context.get("name", "")),
        "post": sections["post"],
        "visual_suggestion": sections["visual_suggestion"],
    }
