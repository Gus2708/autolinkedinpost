"""Módulo de generación de contenido avanzado para LinkedIn (Estrategia 2026 + Primera Persona Singular + Veracidad + Canva AI + Quality Gate)."""

import time
from typing import Any, Dict, List, Optional, Tuple
from google import genai
from google.genai import types

from src.evaluator import evaluate_linkedin_post


SYSTEM_INSTRUCTION = """
Sos un Senior Software Engineer, MVP y Tech Lead redactando contenido de alto impacto para LinkedIn siguiendo la Estrategia Algorítmica de 2026 y el Manual Científico de Carruseles PDF para Canva AI.

TUS REGLAS DE ORO DE REDACCIÓN (LINKEDIN 2026, PRIMERA PERSONA SINGULAR Y VERACIDAD):

1. **VOZ EN PRIMERA PERSONA DEL SINGULAR (AUTORÍA PERSONAL - CRÍTICO)**:
   - Redactá SIEMPRE en primera persona del singular: "Decidí", "Diseñé", "Implementé", "Mi arquitectura", "Mi enfoque", "Elegí", "Desarrollé".
   - PROHIBIDO usar el plural: NUNCA uses "Decidimos", "Diseñamos", "Pensamos", "Nuestro equipo" ni "Nuestra app". Sos un desarrollador individual (Gustavo) demostrando tu propio criterio técnico y autoría directa.

2. **VERACIDAD ABSOLUTA Y CERO ALUCINACIÓN (GROUNDING ESTRICTO)**:
   - PROHIBIDO inventar métricas ficticias ("redujimos 95% el CPU", "100K usuarios"), caídas falsas de servidores ("el servidor se cayó 3 veces") o empresas imaginarias.
   - Decí SIEMPRE LA VERDAD de lo que hace el repositorio, sus archivos, sus tecnologías y sus commits reales.
   - Si no hay métricas numéricas en el README o commits, enfocate en el **problema técnico real, la arquitectura de módulos, los trade-offs de diseño o los retos de integración que resuelve el código real**.

3. **EL GANCHO DEL POST (Primeras 2 líneas / Máx 220 caracteres)**:
   - Debe atrapar al lector antes del botón "Ver más".
   - Plantea el problema técnico real que resuelve el repositorio, una decisión de diseño contraintuitiva o un contraste de ingeniería real.
   - NUNCA uses preguntas retóricas vagas ("¿Alguna vez te has preguntado...?").

4. **FORMATO MOBILE-FIRST (Legibilidad extrema)**:
   - Párrafos de MÁXIMO 2 a 3 líneas con líneas en blanco obligatorias entre párrafos.
   - Nivel de lectura ágil (4º grado de primaria): claridad conceptual directa sin jerga corporativa inflada.

5. **CERO CLICHÉS CORPORATIVOS / ANTI-AI**:
   - PROHIBIDO: "En el vertiginoso mundo...", "Estoy emocionado de compartir", "Game-changer", "Revolucionario", "Sumerjámonos", "Un testimonio de".

6. **LLAMADA A LA ACCIÓN (CTA) DE GUARDADO (SAVES > LIKES)**:
   - En 2026, un post guardado multiplica el alcance un 60%. Invita a guardar el checklist, carrusel o diagrama.

7. **CERO LINKS EN EL CUERPO**:
   - El enlace al repositorio va en la sección del **Primer Comentario**.

8. **ESPECIFICACIONES ANTI-ERRORES PARA CANVA AI (10 Slides Verticales 4:5 - CERO 16:9)**:
   - **Formato Estricto**: 1200 x 1500 px (Vertical Móvil 4:5). PROHIBIDO 16:9 horizontal de PC.
   - **Cero Enlaces Falsos**: PROHIBIDO que Canva invente URLs ficticias de plantilla como 'reallygreatsite.com' o similares. El único enlace permitido en la Slide 10 es el repositorio real de GitHub.
   - **Longitud**: Exactamente 10 diapositivas estructuradas bajo el framework PAS (Problema, Agitación, Solución).
   - **El Prompt Maestro para Canva debe contener TODOS los textos de las 10 slides ya redactados** en primera persona del singular.
"""

PROJECT_PROMPT_TEMPLATE = """
A partir de la siguiente actividad REAL en el repositorio '{repo_name}':

Commits y cambios técnicos reales:
{commits_text}

INSTRUCCIÓN DE AUTORÍA Y VERACIDAD: 
- Escribe en PRIMERA PERSONA DEL SINGULAR ("Implementé", "Decidí", "Mi cambio"). NUNCA en plural ("decidimos").
- Basa todo el contenido 100% en los cambios y commits anteriores. NO inventes características que no se hayan modificado.

Generá el paquete completo de publicación optimizado según la Estrategia 2026 y el Manual de Carruseles Canva AI:

1. **POST DE LINKEDIN (Texto de Acompañamiento del Documento)**:
   - Gancho potente en las primeras 2 líneas (< 200 caracteres) basado en el cambio real.
   - Storytelling técnico en primera persona singular de 2-3 párrafos cortos (2 líneas cada uno) explicando el problema real, la solución de código aplicada y trade-offs.
   - CTA de guardado.
   - 3-4 hashtags técnicos.

2. **PRIMER COMENTARIO (Regla de los 60 minutos)**:
   - Texto para comentar inmediatamente después de publicar con el link https://github.com/{repo_name}.

3. **GUION DE CARRUSEL CANVA AI (10 Slides - 1200x1500px Vertical - Anti-16:9 - Anti-reallygreatsite)**:
   - **Título del Documento para LinkedIn** (máx 150 caracteres).
   - **Prompt Maestro para Canva AI Chat / Magic Studio** (con instrucción explícita de NO hacer 16:9 y NO usar reallygreatsite.com, e incluyendo el texto de cada slide).
   - **Desglose Slide por Slide (1 al 10)** en primera persona singular con títulos (<6 palabras), cuerpos (<25 palabras) y enlace real a https://github.com/{repo_name} en la slide 10.

4. **SUGERENCIA VISUAL**:
   - Diagrama de arquitectura o captura de terminal split correspondiente al código modificado.

Entregá la respuesta respetando EXACTAMENTE esta estructura:

=== LINKEDIN_POST ===
[Aquí el post para LinkedIn]

=== PRIMER_COMENTARIO ===
[Aquí el texto del primer comentario con link al repo]

=== GUION_CARRUSEL_PDF ===
[Título de Documento LinkedIn, Prompt Maestro para Canva y desglose de las 10 Slides]

=== SUGERENCIA_VISUAL ===
[Aquí la sugerencia visual o diagrama]
"""

SHOWCASE_PROMPT_TEMPLATE = """
Sos Gustavo, un desarrollador senior presentando tu proyecto individual '{name}' en LinkedIn. 

Información real y verificada del proyecto:
- **Repositorio**: {full_name}
- **Descripción**: {description}
- **Stack / Lenguajes reales**: {languages}
- **Archivos clave**: {key_files}
- **Extracto del README real**:
{readme}

INSTRUCCIÓN DE AUTORÍA Y VERACIDAD:
- Escribe SIEMPRE en PRIMERA PERSONA DEL SINGULAR ("Diseñé", "Decidí", "Implementé", "Mi arquitectura"). PROHIBIDO usar "Diseñamos / Decidimos".
- Basa cada afirmación en el README, descripción y archivos listados.
- NO inventes caídas ficticias de servidores, empresas inventadas ni cifras de millones de usuarios no documentadas.

Generá el paquete completo de publicación de portafolio para LinkedIn (Estrategia 2026 + Manual de Carruseles Canva AI):

1. **POST DE LINKEDIN (Showcase de Arquitectura para Reclutadores)**:
   - Gancho en primera persona en las primeras 2 líneas con el desafío técnico real del software.
   - Decisiones de arquitectura y patrones reales que TÚ implementaste basados en el stack y archivos clave.
   - Formato mobile-first (párrafos de máx 2-3 líneas).
   - CTA enfocado en guardados y valor duradero.
   - 3-4 hashtags estratégicos.

2. **PRIMER COMENTARIO (Semilla de conversación)**:
   - Texto en primera persona para comentar en el primer minuto con el link a https://github.com/{full_name} y contexto adicional.

3. **GUION DE CARRUSEL CANVA AI (10 Slides - 1200x1500px Vertical - Anti-16:9 - Anti-reallygreatsite)**:
   - **Título del Documento para LinkedIn** (< 150 caracteres).
   - **Prompt Maestro para Canva AI Chat / Magic Studio**:
     * Debe ordenar explícitamente: "FORMAT: 10-page vertical presentation (4:5 ratio, 1200x1500px). DO NOT create 16:9 widescreen. DO NOT use placeholder URLs like reallygreatsite.com."
     * Debe contener el contenido exacto de las 10 diapositivas en primera persona singular para que Canva arme el diseño directamente.
   - **Desglose de las 10 Slides (1 a 10)**:
     * Slide 1: Portada con Gancho gigante (<6 palabras).
     * Slide 2: El problema real del proyecto.
     * Slides 3 a 8: Decisiones técnicas paso a paso (<25 palabras por slide), con sugerencia de icono y conector visual.
     * Slide 9: Síntesis Antes vs Después.
     * Slide 10: CTA Activo con el link real a https://github.com/{full_name}.

4. **SUGERENCIA VISUAL**:
   - Recomendación de diagrama C4 o captura de terminal/UI genuina.

Entregá la respuesta respetando EXACTAMENTE esta estructura:

=== LINKEDIN_POST ===
[Aquí el post de showcase]

=== PRIMER_COMENTARIO ===
[Aquí el primer comentario con link al repo]

=== GUION_CARRUSEL_PDF ===
[Título de Documento, Prompt Maestro para Canva AI y desglose de 10 Slides]

=== SUGERENCIA_VISUAL ===
[Aquí la recomendación visual o diagrama]
"""

REFINEMENT_PROMPT_TEMPLATE = """
La siguiente publicación de LinkedIn fue auditada por nuestro sistema de evaluación (LLM-as-a-Judge) y requiere corrección:

CONTEXTO REAL DEL REPOSITORIO:
{repo_context}

POST ORIGINAL OBSERVADO:
{original_post}

FEEDBACK DEL JUEZ / RÚBRICA DE EVALUACIÓN:
{feedback}

Por favor reescribe el POST DE LINKEDIN asegurando:
1. PRIMERA PERSONA DEL SINGULAR ("Diseñé", "Decidí", "Mi proyecto"). Elimina cualquier plural ("diseñamos", "decidimos").
2. VERACIDAD ABSOLUTA (elimina cualquier número o historia inventada).
3. Formato mobile-first de 2 líneas con espacio en blanco.

Entregá únicamente el post mejorado en el bloque:
=== LINKEDIN_POST ===
[Aquí el post corregido]
"""

FALLBACK_MODELS = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
]


def _call_gemini_with_retry(
    prompt: str,
    api_key: str,
    preferred_model: str = "gemini-3.7-flash",
    max_retries: int = 1,
) -> Tuple[str, str]:
    """Ejecuta llamada a Gemini probando primero los modelos más inteligentes con salto inmediato."""
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
                        temperature=0.4,
                    ),
                )
                text = response.text or ""
                if text.strip():
                    return text, model
            except Exception as e:
                print(f"[WARN] Modelo {model} no disponible ({str(e)[:70]}), saltando al siguiente...")
                break
    return "", preferred_model


def _parse_full_package(raw_text: str, default_name: str) -> Dict[str, str]:
    """Parsea las 4 secciones del paquete completo de LinkedIn 2026 de forma robusta e insensible al orden."""
    import re
    
    delimiters = [
        ("post", r"===\s*(?:LINKEDIN_POST|POST)\s*==="),
        ("first_comment", r"===\s*(?:PRIMER_COMENTARIO|COMENTARIO)\s*==="),
        ("carousel_script", r"===\s*(?:GUION_CARRUSEL_PDF|GUION_CARRUSEL|CARRUSEL_CANVA|CARRUSEL)\s*==="),
        ("visual_suggestion", r"===\s*(?:SUGERENCIA_VISUAL|VISUAL|IMAGEN)\s*==="),
    ]

    found = []
    for key, pattern in delimiters:
        for m in re.finditer(pattern, raw_text, re.IGNORECASE):
            found.append((m.start(), m.end(), key))

    found.sort(key=lambda x: x[0])
    result = {
        "post": "",
        "first_comment": "",
        "carousel_script": "",
        "visual_suggestion": "",
    }

    if not found:
        result["post"] = raw_text.strip()
    else:
        for i in range(len(found)):
            start_content = found[i][1]
            end_content = found[i+1][0] if i+1 < len(found) else len(raw_text)
            key = found[i][2]
            result[key] = raw_text[start_content:end_content].strip()

    if not result["first_comment"]:
        result["first_comment"] = f"Dejo el enlace al repositorio acá para quienes quieran ver el código y la arquitectura: https://github.com/{default_name}"

    if not result["visual_suggestion"]:
        result["visual_suggestion"] = f"Diagrama de arquitectura o captura de terminal con métricas de {default_name}."

    return result


def _run_quality_gate(
    post_data: Dict[str, str],
    api_key: str,
    generator_model: str,
    repo_context_text: str = "",
) -> Dict[str, Any]:
    """Quality Gate con LLM-as-a-Judge: audita primera persona singular, veracidad y formato."""
    post_text = post_data["post"]
    eval_result = evaluate_linkedin_post(
        post_text=post_text,
        api_key=api_key,
        repo_context=repo_context_text,
        preferred_model="gemini-3.1-flash-lite",
    )
    
    score = eval_result.get("overall_score", 5.0)
    passed = eval_result.get("passed", True)
    print(f"[INFO] Generador: {generator_model} | Judge Score: {score}/5.0 (Passed: {passed})")

    if not passed and eval_result.get("actionable_feedback"):
        print("[INFO] Post reprobado por veracidad, plural o formato. Ejecutando auto-refinamiento...")
        refine_prompt = REFINEMENT_PROMPT_TEMPLATE.format(
            repo_context=repo_context_text,
            original_post=post_text,
            feedback=eval_result["actionable_feedback"],
        )
        refined_raw, _ = _call_gemini_with_retry(refine_prompt, api_key, generator_model)
        if "=== LINKEDIN_POST ===" in refined_raw:
            post_data["post"] = refined_raw.replace("=== LINKEDIN_POST ===", "").strip()
            eval_result = evaluate_linkedin_post(post_data["post"], api_key, repo_context_text, "gemini-3.1-flash-lite")
            post_data["quality_score"] = eval_result.get("overall_score", 4.8)
        else:
            post_data["quality_score"] = score
    else:
        post_data["quality_score"] = score

    post_data["eval_details"] = eval_result
    post_data["used_model"] = generator_model
    return post_data


def generate_single_project_post(
    repo_name: str,
    commits: List[str],
    api_key: str,
    preferred_model: str = "gemini-3.7-flash",
) -> Optional[Dict[str, Any]]:
    """Genera el paquete de publicación para novedades de un proyecto específico con Quality Gate veraz."""
    commits_text = "\n".join([f"- {c}" for c in commits])
    prompt = PROJECT_PROMPT_TEMPLATE.format(
        repo_name=repo_name,
        commits_text=commits_text,
    )
    raw_text, used_model = _call_gemini_with_retry(prompt, api_key, preferred_model)
    if not raw_text:
        return None

    package = _parse_full_package(raw_text, repo_name)
    package["repo_name"] = repo_name

    return _run_quality_gate(package, api_key, used_model, commits_text)


def generate_posts_by_project(
    activity_by_repo: Dict[str, List[str]],
    api_key: str,
    model_name: str = "gemini-3.7-flash",
) -> List[Dict[str, Any]]:
    """Genera posts independientes para cada repositorio activo con Quality Gate."""
    results = []
    for repo_name, commits in activity_by_repo.items():
        if not commits:
            continue
        print(f"[INFO] Generando post con {model_name} para proyecto: {repo_name}...")
        project_result = generate_single_project_post(
            repo_name=repo_name,
            commits=commits,
            api_key=api_key,
            preferred_model=model_name,
        )
        if project_result and project_result.get("post"):
            results.append(project_result)
        time.sleep(1)
    return results


def generate_project_showcase_post(
    repo_context: Dict[str, Any],
    api_key: str,
    model_name: str = "gemini-3.7-flash",
) -> Optional[Dict[str, Any]]:
    """Genera un post de showcase de portafolio para reclutadores en primera persona singular."""
    repo_context_text = (
        f"Proyecto: {repo_context.get('name')}\n"
        f"Descripción: {repo_context.get('description')}\n"
        f"Stack: {', '.join(repo_context.get('languages', []))}\n"
        f"Archivos: {', '.join(repo_context.get('key_files', []))}\n"
        f"README:\n{repo_context.get('readme', '')[:2500]}"
    )

    prompt = SHOWCASE_PROMPT_TEMPLATE.format(
        name=repo_context.get("name", "Proyecto"),
        full_name=repo_context.get("full_name", ""),
        description=repo_context.get("description", "Sin descripción"),
        languages=", ".join(repo_context.get("languages", [])) or "No especificado",
        key_files=", ".join(repo_context.get("key_files", [])) or "No disponible",
        readme=repo_context.get("readme", "No hay README disponible.")[:2500],
    )

    raw_text, used_model = _call_gemini_with_retry(prompt, api_key, model_name)
    if not raw_text:
        return None

    package = _parse_full_package(raw_text, repo_context.get("full_name", repo_context.get("name", "")))
    package["repo_name"] = repo_context.get("full_name", repo_context.get("name", ""))

    return _run_quality_gate(package, api_key, used_model, repo_context_text)
