"""Módulo de generación de contenido avanzado para LinkedIn (Estrategia 2026 + LLM-as-a-Judge Quality Gate)."""

import time
from typing import Any, Dict, List, Optional
from google import genai
from google.genai import types

from src.evaluator import evaluate_linkedin_post


SYSTEM_INSTRUCTION = """
Sos un Senior Software Engineer, MVP y Tech Lead redactando contenido de alto impacto para LinkedIn siguiendo la Estrategia Algorítmica de 2026.

TUS REGLAS DE ORO DE REDACCIÓN (LINKEDIN 2026 & ANTI-AI TELLS):
1. **EL GANCHO (HOOK) ES TODO (Primeras 2 líneas / Máx 220 caracteres)**:
   - Debe atrapar al lector antes del botón "Ver más".
   - Usá números concretos, contrastes fuertes ("En 2024 tardábamos X, hoy tardamos Y"), problemas dolorosos o lecciones contraintuitivas.
   - NUNCA uses preguntas retóricas vagas ("¿Alguna vez te has preguntado...?").
2. **FORMATO MOBILE-FIRST (Legibilidad extrema)**:
   - Párrafos de MÁXIMO 2 a 3 líneas.
   - OBLIGATORIO dejar una línea en blanco entre cada párrafo.
   - Claridad conceptual sobre lenguaje rebuscado (nivel de lectura ágil y directo).
   - Pirámide invertida: la conclusión o solución técnica va en las primeras líneas.
3. **CERO CLICHÉS CORPORATIVOS / ANTI-AI**:
   - PROHIBIDO: "En el vertiginoso mundo...", "Estoy emocionado de compartir", "Game-changer", "Revolucionario", "Sumerjámonos", "Un testimonio de".
   - Tono: Natural, apasionado por la ingeniería, humano, honesto sobre los errores y trade-offs técnicos.
4. **LLAMADA A LA ACCIÓN (CTA) ORIENTADA A GUARDADOS (SAVES)**:
   - En 2026, un post guardado multiplica el alcance un 60%.
   - Tu CTA debe invitar a guardar el checklist, diagrama o tip ("Guardá este post para cuando diseñes tu próximo pipeline...").
   - PROHIBIDO terminar con "¿Qué opinas?" o "Los leo en comentarios".
5. **CERO LINKS EN EL CUERPO DEL POST**:
   - Poner links en el texto reduce el alcance. Generá una sección dedicada para el **Primer Comentario** donde irá el enlace al repositorio y el disparador de conversación.
"""

PROJECT_PROMPT_TEMPLATE = """
A partir de la siguiente actividad reciente en el repositorio '{repo_name}':

Commits y cambios técnicos:
{commits_text}

Generá el paquete completo de publicación según la Estrategia 2026:

1. **POST DE LINKEDIN (Storytelling de Ingeniería)**:
   - Gancho potente en las primeras 2 líneas.
   - Contexto del problema, arquitectura aplicada y trade-offs en párrafos de 2 líneas con espacios en blanco.
   - CTA orientado a guardados (saves) o debate técnico.
   - 3-4 hashtags técnicos relevantes (#SoftwareArchitecture #Python #DevOps #Engineering).

2. **PRIMER COMENTARIO (Regla de los 60 minutos)**:
   - Texto listo para que el autor comente inmediatamente después de publicar.
   - Incluye el link al repo (https://github.com/{repo_name}) y una pregunta/aporte extra para activar la conversación.

3. **GUION DE CARRUSEL PDF (Formato de 24% Engagement)**:
   - Estructura breve de 5 a 6 diapositivas (proporción 4:5 vertical) resumiendo el aprendizaje técnico.

4. **SUGERENCIA VISUAL**:
   - Propuesta de captura split (modo oscuro) o diagrama de arquitectura (C4 / Excalidraw).

Entregá la respuesta respetando EXACTAMENTE esta estructura con los delimitadores:

=== LINKEDIN_POST ===
[Aquí el post para LinkedIn]

=== PRIMER_COMENTARIO ===
[Aquí el texto del primer comentario con el link al repo]

=== GUION_CARRUSEL_PDF ===
[Slide 1: Portada y Promesa]
[Slide 2-4: Problema, Solución y Arquitectura]
[Slide 5: Resumen y CTA de Guardado]

=== SUGERENCIA_VISUAL ===
[Aquí la recomendación visual para acompañar el post]
"""

SHOWCASE_PROMPT_TEMPLATE = """
Sos un desarrollador senior presentando tu proyecto '{name}' en LinkedIn para posicionarte como referente técnico frente a reclutadores y Engineering Managers.

Información del proyecto:
- **Repositorio**: {full_name}
- **Descripción**: {description}
- **Stack / Lenguajes**: {languages}
- **Archivos clave**: {key_files}
- **Extracto del README**:
{readme}

Generá el paquete completo de publicación de portafolio para LinkedIn (Estrategia 2026):

1. **POST DE LINKEDIN (Showcase de Arquitectura para Reclutadores)**:
   - Gancho brutal en las primeras 2 líneas con métricas, escala o dolor de negocio resuelto.
   - Decisiones de arquitectura, patrones utilizados (RAG, Outbox, Caching, Concurrencia) y trade-offs asumidos.
   - Formato mobile-first (párrafos de máx 2-3 líneas).
   - CTA enfocado en guardados y valor duradero.
   - 3-4 hashtags estratégicos.

2. **PRIMER COMENTARIO (Semilla de conversación)**:
   - Texto para comentar en el primer minuto con el link a https://github.com/{full_name} y contexto adicional.

3. **GUION DE CARRUSEL PDF (Educativo y Guardable)**:
   - Estructura de 5-6 diapositivas para Canva/PDF resumiendo el caso de estudio técnico.

4. **SUGERENCIA VISUAL**:
   - Recomendación de diagrama C4 o captura de benchmark ideal.

Entregá la respuesta respetando EXACTAMENTE esta estructura:

=== LINKEDIN_POST ===
[Aquí el post de showcase]

=== PRIMER_COMENTARIO ===
[Aquí el primer comentario con link al repo]

=== GUION_CARRUSEL_PDF ===
[Slide 1 a 5 con la estructura del carrusel]

=== SUGERENCIA_VISUAL ===
[Aquí la recomendación visual o diagrama]
"""

REFINEMENT_PROMPT_TEMPLATE = """
La siguiente publicación de LinkedIn fue auditada por nuestro sistema de evaluación (LLM-as-a-Judge) y requiere optimizaciones antes de ser aprobada:

POST ORIGINAL:
{original_post}

FEEDBACK DEL JUEZ / RÚBRICA DE EVALUACIÓN:
{feedback}

Por favor reescribe el POST DE LINKEDIN aplicando estrictamente las correcciones indicadas (asegurando hook < 220 chars, párrafos de 2 líneas, cero clichés y CTA de guardado).

Entregá únicamente el post mejorado en el bloque:
=== LINKEDIN_POST ===
[Aquí el post corregido]
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


def _parse_full_package(raw_text: str, default_name: str) -> Dict[str, str]:
    """Parsea las 4 secciones del paquete completo de LinkedIn 2026."""
    post = ""
    first_comment = ""
    carousel = ""
    visual = ""

    parts = raw_text

    if "=== LINKEDIN_POST ===" in parts:
        after_post = parts.split("=== LINKEDIN_POST ===")[1]
        if "=== PRIMER_COMENTARIO ===" in after_post:
            post = after_post.split("=== PRIMER_COMENTARIO ===")[0].strip()
            rest = after_post.split("=== PRIMER_COMENTARIO ===")[1]
            
            if "=== GUION_CARRUSEL_PDF ===" in rest:
                first_comment = rest.split("=== GUION_CARRUSEL_PDF ===")[0].strip()
                rest2 = rest.split("=== GUION_CARRUSEL_PDF ===")[1]
                
                if "=== SUGERENCIA_VISUAL ===" in rest2:
                    carousel = rest2.split("=== SUGERENCIA_VISUAL ===")[0].strip()
                    visual = rest2.split("=== SUGERENCIA_VISUAL ===")[1].strip()
                else:
                    carousel = rest2.strip()
            elif "=== SUGERENCIA_VISUAL ===" in rest:
                first_comment = rest.split("=== SUGERENCIA_VISUAL ===")[0].strip()
                visual = rest.split("=== SUGERENCIA_VISUAL ===")[1].strip()
            else:
                first_comment = rest.strip()
        else:
            post = after_post.strip()
    else:
        post = raw_text.strip()

    if not first_comment:
        first_comment = f"Dejo el enlace al repositorio acá para quienes quieran ver el código y la arquitectura: https://github.com/{default_name}"

    if not visual:
        visual = f"Diagrama de arquitectura o captura de terminal con métricas de {default_name}."

    return {
        "post": post,
        "first_comment": first_comment,
        "carousel_script": carousel,
        "visual_suggestion": visual,
    }


def _run_quality_gate(
    post_data: Dict[str, str],
    api_key: str,
    model_name: str,
) -> Dict[str, Any]:
    """Quality Gate con LLM-as-a-Judge: evalúa y auto-refina el post si el score es bajo."""
    post_text = post_data["post"]
    eval_result = evaluate_linkedin_post(post_text, api_key, model_name)
    
    score = eval_result.get("overall_score", 5.0)
    print(f"[INFO] LLM-as-a-Judge Score: {score}/5.0 (Passed: {eval_result.get('passed', True)})")

    # Si el puntaje es menor a 4.0, hacer una pasada de auto-refinamiento
    if score < 4.0 and eval_result.get("actionable_feedback"):
        print("[INFO] Post por debajo del umbral de calidad. Ejecutando auto-refinamiento...")
        refine_prompt = REFINEMENT_PROMPT_TEMPLATE.format(
            original_post=post_text,
            feedback=eval_result["actionable_feedback"],
        )
        refined_raw = _call_gemini_with_retry(refine_prompt, api_key, model_name)
        if "=== LINKEDIN_POST ===" in refined_raw:
            post_data["post"] = refined_raw.replace("=== LINKEDIN_POST ===", "").strip()
            # Re-evaluar post refinado
            eval_result = evaluate_linkedin_post(post_data["post"], api_key, model_name)
            post_data["quality_score"] = eval_result.get("overall_score", 4.8)
        else:
            post_data["quality_score"] = score
    else:
        post_data["quality_score"] = score

    post_data["eval_details"] = eval_result
    return post_data


def generate_single_project_post(
    repo_name: str,
    commits: List[str],
    api_key: str,
    preferred_model: str = "gemini-3.6-flash",
) -> Optional[Dict[str, Any]]:
    """Genera el paquete de publicación para novedades de un proyecto específico con Quality Gate."""
    commits_text = "\n".join([f"- {c}" for c in commits])
    prompt = PROJECT_PROMPT_TEMPLATE.format(
        repo_name=repo_name,
        commits_text=commits_text,
    )
    raw_text = _call_gemini_with_retry(prompt, api_key, preferred_model)
    if not raw_text:
        return None

    package = _parse_full_package(raw_text, repo_name)
    package["repo_name"] = repo_name

    # Aplicar Quality Gate con LLM-as-a-Judge
    return _run_quality_gate(package, api_key, preferred_model)


def generate_posts_by_project(
    activity_by_repo: Dict[str, List[str]],
    api_key: str,
    model_name: str = "gemini-3.6-flash",
) -> List[Dict[str, Any]]:
    """Genera posts independientes para cada repositorio activo con Quality Gate."""
    results = []
    for repo_name, commits in activity_by_repo.items():
        if not commits:
            continue
        print(f"[INFO] Generando post optimizado 2026 para proyecto: {repo_name}...")
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
) -> Optional[Dict[str, Any]]:
    """Genera un post de showcase de portafolio para reclutadores con Quality Gate."""
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

    package = _parse_full_package(raw_text, repo_context.get("full_name", repo_context.get("name", "")))
    package["repo_name"] = repo_context.get("full_name", repo_context.get("name", ""))

    # Aplicar Quality Gate con LLM-as-a-Judge
    return _run_quality_gate(package, api_key, model_name)
