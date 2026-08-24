"""Módulo de generación de contenido avanzado para LinkedIn (Multi-LLM: Gemini, OpenAI, Claude, DeepSeek, Groq, OpenRouter, Ollama)."""

import time
from typing import Any, Dict, List, Optional, Tuple
from src.evaluator import evaluate_linkedin_post
from src.llm_client import generate_llm_text


SYSTEM_INSTRUCTION_ES = """
Sos un Senior Software Engineer, MVP y Tech Lead redactando contenido de alto impacto para LinkedIn siguiendo la Estrategia Algorítmica de 2026 y el Manual Científico de Carruseles PDF para Canva AI.

TUS REGLAS DE ORO DE REDACCIÓN (ESPAÑOL):
1. **VOZ EN PRIMERA PERSONA DEL SINGULAR**: Redactá SIEMPRE como "Decidí", "Diseñé", "Implementé", "Mi arquitectura", "Mi enfoque". NUNCA uses "Decidimos", "Diseñamos" ni "Nuestro equipo".
2. **VERACIDAD ABSOLUTA (CERO ALUCINACIÓN)**: Basa todo 100% en el README, archivos y commits reales. NUNCA inventes métricas de millones de usuarios ni caídas falsas.
3. **GANCHO PODEROSO (< 220 caracteres)**: Primeras 2 líneas con el problema de ingeniería real o contraste antes del botón "Ver más".
4. **MOBILE-FIRST**: Párrafos de máximo 2-3 líneas con líneas en blanco entre párrafos.
5. **CERO CLICHÉS CORPORATIVOS / ANTI-AI**: Prohibido "En el vertiginoso mundo...", "Estoy emocionado de compartir", "Game-changer", "Revolucionario".
6. **CTA DE GUARDADO (SAVES > LIKES)**: Invita a guardar el post/checklist/diagrama.
7. **CERO LINKS EN EL CUERPO**: El enlace va en el Primer Comentario.
8. **CARRUSEL CANVA AI (10 Slides Verticales 4:5 - 1200x1500px)**: Prohibido 16:9 y prohibido reallygreatsite.com. Prompt maestro con textos pre-redactados.
"""

SYSTEM_INSTRUCTION_EN = """
You are a Senior Software Engineer and Tech Lead writing high-impact engineering content for LinkedIn following the 2026 Algorithmic Strategy and Canva AI Mobile Carousel specs.

YOUR CRITICAL RULES (ENGLISH - US TECH STANDARD):
1. **FIRST-PERSON SINGULAR VOICE ONLY**: Always write as "I decided", "I designed", "I implemented", "My architecture", "My approach". NEVER use "We decided", "We designed" or "Our team". You are an individual engineer demonstrating personal technical ownership and craftsmanship.
2. **STRICT GROUNDING & ZERO HALLUCINATION**: Ground every claim 100% in the real repository files, code structure, and README. NEVER invent fake metrics ("reduced CPU by 95%", "100K users") or fake production outages.
3. **HOOK BEFORE 'SEE MORE' (< 220 characters)**: First 2 lines must present a concrete engineering challenge, trade-off, or contrarian design decision.
4. **MOBILE-FIRST FORMATTING**: Paragraphs of MAX 2-3 lines with mandatory blank lines in between. Agile, direct reading level.
5. **ZERO AI CLICHÉS / ANTI-AI TELLS**: FORBIDDEN: "In today's fast-paced tech landscape...", "I am thrilled/excited to share...", "Let's dive into...", "Game-changer", "Revolutionary", "A testament to...".
6. **SAVE-FOCUSED CTA (SAVES > LIKES)**: Encourage saving the post/checklist/diagram.
7. **NO EXTERNAL LINKS IN THE BODY**: The clean repo link goes in the First Comment.
8. **10-SLIDE CANVA AI CAROUSEL (Vertical 4:5 - 1200x1500px)**: Strictly NO 16:9 widescreen. NO placeholder domains like reallygreatsite.com. Include full slide texts inside the Master Prompt.
"""

PROJECT_PROMPT_TEMPLATE_ES = """
A partir de la siguiente actividad REAL en el repositorio '{repo_name}':

Commits y cambios técnicos reales:
{commits_text}

Generá el paquete completo de publicación en ESPAÑOL (Estrategia 2026):

1. **POST DE LINKEDIN (Storytelling en 1ª Persona Singular)**:
   - Gancho potente (< 200 caracteres).
   - Contexto del problema real, solución de arquitectura y trade-offs en párrafos de 2 líneas.
   - CTA de guardado y 3-4 hashtags técnicos.

2. **PRIMER COMENTARIO (Regla de los 60 minutos)**:
   - Texto para comentar inmediatamente con el link https://github.com/{repo_name}.

3. **GUION DE CARRUSEL CANVA AI (10 Slides - 1200x1500px Vertical - Anti-16:9)**:
   - Título del Documento para LinkedIn (< 150 chars).
   - Prompt Maestro para Canva AI Chat con los textos de las 10 slides incluidos.
   - Desglose de 10 Slides en primera persona singular.

4. **SUGERENCIA VISUAL**:
   - Diagrama de arquitectura o captura split.

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

PROJECT_PROMPT_TEMPLATE_EN = """
Based on the following REAL commit activity in repository '{repo_name}':

Real commits and technical changes:
{commits_text}

Generate the complete LinkedIn publication pack in professional ENGLISH (2026 Strategy):

1. **LINKEDIN POST (1st-Person Singular Storytelling)**:
   - Strong hook in the first 2 lines (< 200 chars).
   - Real problem, architecture solution, and engineering trade-offs in 2-line paragraphs with whitespace.
   - Save-focused CTA and 3-4 technical hashtags.

2. **FIRST COMMENT (60-minute rule)**:
   - Comment ready to post immediately with link https://github.com/{repo_name}.

3. **CANVA AI CAROUSEL SCRIPT (10 Slides - 1200x1500px Vertical - No 16:9 - No fake URLs)**:
   - LinkedIn Document Title (< 150 chars).
   - Canva Master Prompt containing the complete text for all 10 slides.
   - Slide-by-slide breakdown (1 to 10).

4. **VISUAL SUGGESTION**:
   - Architecture diagram or split terminal capture suggestion.

Respond EXACTLY with these section delimiters:

=== LINKEDIN_POST ===
[Complete LinkedIn post in English]

=== PRIMER_COMENTARIO ===
[First comment in English with repo link]

=== GUION_CARRUSEL_PDF ===
[Document title, Canva Master Prompt, and 10-slide breakdown in English]

=== SUGERENCIA_VISUAL ===
[Visual recommendation in English]
"""

SHOWCASE_PROMPT_TEMPLATE_ES = """
Sos Gustavo, un desarrollador senior presentando tu proyecto individual '{name}' en LinkedIn para reclutadores técnicos y Tech Leads.

Información real y verificada del proyecto:
- **Repositorio**: {full_name}
- **Descripción**: {description}
- **Stack / Lenguajes reales**: {languages}
- **Archivos clave**: {key_files}
- **Extracto del README real**:
{readme}

Generá el paquete completo de publicación de portafolio en ESPAÑOL (Estrategia 2026):

1. **POST DE LINKEDIN (Showcase en 1ª Persona Singular)**:
   - Gancho veraz (< 200 caracteres) con el desafío técnico real.
   - Decisiones de arquitectura y patrones reales que TÚ implementaste en párrafos de 2 líneas.
   - CTA de guardado y 3-4 hashtags técnicos.

2. **PRIMER COMENTARIO**:
   - Texto en 1ª persona con el link a https://github.com/{full_name}.

3. **GUION DE CARRUSEL CANVA AI (10 Slides - 1200x1500px Vertical - Anti-16:9)**:
   - Título del Documento LinkedIn (< 150 chars).
   - Prompt Maestro para Canva AI con las 10 slides redactadas en 1ª persona singular.
   - Desglose de 10 Slides (Portada, Problema, Arquitectura paso a paso, Síntesis, CTA con link real).

4. **SUGERENCIA VISUAL**:
   - Recomendación de diagrama C4 o captura de UI/Terminal genuina.

Entregá la respuesta respetando EXACTAMENTE esta estructura:

=== LINKEDIN_POST ===
[Aquí el post de showcase en español]

=== PRIMER_COMENTARIO ===
[Aquí el primer comentario con link al repo]

=== GUION_CARRUSEL_PDF ===
[Título de Documento, Prompt Maestro para Canva AI y desglose de 10 Slides]

=== SUGERENCIA_VISUAL ===
[Aquí la recomendación visual o diagrama]
"""

SHOWCASE_PROMPT_TEMPLATE_EN = """
You are Gustavo, a Senior Software Engineer presenting your individual project '{name}' on LinkedIn for technical recruiters and Engineering Managers.

Verified real project information:
- **Repository**: {full_name}
- **Description**: {description}
- **Real Tech Stack**: {languages}
- **Key Files**: {key_files}
- **README Extract**:
{readme}

Generate the complete portfolio publication pack in professional ENGLISH (2026 Strategy):

1. **LINKEDIN POST (1st-Person Singular Engineering Showcase)**:
   - Strong, grounded hook in the first 2 lines (< 200 chars).
   - Real architecture decisions, patterns, and trade-offs that YOU implemented in 2-line paragraphs.
   - Save-focused CTA and 3-4 strategic hashtags.

2. **FIRST COMMENT**:
   - Seed comment with clean link to https://github.com/{full_name}.

3. **CANVA AI CAROUSEL SCRIPT (10 Slides - 1200x1500px Vertical - No 16:9 - No fake URLs)**:
   - LinkedIn Document Title (< 150 chars).
   - Canva Master Prompt containing the complete 10-slide text.
   - 10-Slide Breakdown (Hook, Problem, Step-by-Step Architecture, Synthesis, CTA with real repo link).

4. **VISUAL SUGGESTION**:
   - Architecture diagram (C4 / Excalidraw) or terminal benchmark suggestion.

Respond EXACTLY with these section delimiters:

=== LINKEDIN_POST ===
[Complete LinkedIn showcase post in English]

=== PRIMER_COMENTARIO ===
[First comment in English with repo link]

=== GUION_CARRUSEL_PDF ===
[Document title, Canva Master Prompt, and 10-slide breakdown in English]

=== SUGERENCIA_VISUAL ===
[Visual suggestion in English]
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
1. PRIMERA PERSONA DEL SINGULAR ("I decided / Diseñé"). Elimina cualquier plural ("we decided / decidimos").
2. VERACIDAD ABSOLUTA (elimina cualquier número o historia inventada).
3. Formato mobile-first de 2 líneas con espacio en blanco.

Entregá únicamente el post mejorado en el bloque:
=== LINKEDIN_POST ===
[Aquí el post corregido]
"""


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
        result["first_comment"] = f"https://github.com/{default_name}"

    if not result["visual_suggestion"]:
        result["visual_suggestion"] = f"Architecture diagram or terminal metrics for {default_name}."

    return result


def _run_quality_gate(
    post_data: Dict[str, str],
    api_key: Optional[str],
    generator_model: str,
    repo_context_text: str = "",
    system_instruction: str = SYSTEM_INSTRUCTION_ES,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Quality Gate con LLM-as-a-Judge: audita primera persona singular, veracidad y formato."""
    post_text = post_data["post"]
    eval_result = evaluate_linkedin_post(
        post_text=post_text,
        api_key=api_key,
        repo_context=repo_context_text,
        provider=provider,
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
        refined_raw, _ = generate_llm_text(
            prompt=refine_prompt,
            system_instruction=system_instruction,
            temperature=0.3,
            provider=provider,
            model=generator_model,
            api_key=api_key,
        )
        if "=== LINKEDIN_POST ===" in refined_raw:
            post_data["post"] = refined_raw.replace("=== LINKEDIN_POST ===", "").strip()
            eval_result = evaluate_linkedin_post(post_data["post"], api_key, repo_context_text, provider=provider)
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
    api_key: Optional[str] = None,
    preferred_model: Optional[str] = None,
    language: str = "es",
    provider: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Genera el paquete de publicación para novedades de un proyecto específico con cualquier LLM."""
    commits_text = "\n".join([f"- {c}" for c in commits])
    
    if language == "en":
        prompt = PROJECT_PROMPT_TEMPLATE_EN.format(repo_name=repo_name, commits_text=commits_text)
        sys_inst = SYSTEM_INSTRUCTION_EN
    else:
        prompt = PROJECT_PROMPT_TEMPLATE_ES.format(repo_name=repo_name, commits_text=commits_text)
        sys_inst = SYSTEM_INSTRUCTION_ES

    raw_text, used_model = generate_llm_text(
        prompt=prompt,
        system_instruction=sys_inst,
        temperature=0.4,
        provider=provider,
        model=preferred_model,
        api_key=api_key,
    )
    if not raw_text:
        return None

    package = _parse_full_package(raw_text, repo_name)
    package["repo_name"] = repo_name
    package["language"] = language

    return _run_quality_gate(package, api_key, used_model, commits_text, sys_inst, provider=provider)


def generate_posts_by_project(
    activity_by_repo: Dict[str, List[str]],
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    language: str = "es",
    provider: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Genera posts independientes para cada repositorio activo con Quality Gate."""
    results = []
    for repo_name, commits in activity_by_repo.items():
        if not commits:
            continue
        print(f"[INFO] Generando post [{language.upper()}] para: {repo_name}...")
        project_result = generate_single_project_post(
            repo_name=repo_name,
            commits=commits,
            api_key=api_key,
            preferred_model=model_name,
            language=language,
            provider=provider,
        )
        if project_result and project_result.get("post"):
            results.append(project_result)
        time.sleep(1)
    return results


def generate_project_showcase_post(
    repo_context: Dict[str, Any],
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    language: str = "es",
    provider: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Genera un post de showcase de portafolio para reclutadores con cualquier LLM."""
    repo_context_text = (
        f"Project: {repo_context.get('name')}\n"
        f"Description: {repo_context.get('description')}\n"
        f"Stack: {', '.join(repo_context.get('languages', []))}\n"
        f"Files: {', '.join(repo_context.get('key_files', []))}\n"
        f"README:\n{repo_context.get('readme', '')[:2500]}"
    )

    if language == "en":
        prompt = SHOWCASE_PROMPT_TEMPLATE_EN.format(
            name=repo_context.get("name", "Project"),
            full_name=repo_context.get("full_name", ""),
            description=repo_context.get("description", "No description"),
            languages=", ".join(repo_context.get("languages", [])) or "Not specified",
            key_files=", ".join(repo_context.get("key_files", [])) or "Not available",
            readme=repo_context.get("readme", "No README available.")[:2500],
        )
        sys_inst = SYSTEM_INSTRUCTION_EN
    else:
        prompt = SHOWCASE_PROMPT_TEMPLATE_ES.format(
            name=repo_context.get("name", "Proyecto"),
            full_name=repo_context.get("full_name", ""),
            description=repo_context.get("description", "Sin descripción"),
            languages=", ".join(repo_context.get("languages", [])) or "No especificado",
            key_files=", ".join(repo_context.get("key_files", [])) or "No disponible",
            readme=repo_context.get("readme", "No hay README disponible.")[:2500],
        )
        sys_inst = SYSTEM_INSTRUCTION_ES

    raw_text, used_model = generate_llm_text(
        prompt=prompt,
        system_instruction=sys_inst,
        temperature=0.4,
        provider=provider,
        model=model_name,
        api_key=api_key,
    )
    if not raw_text:
        return None

    package = _parse_full_package(raw_text, repo_context.get("full_name", repo_context.get("name", "")))
    package["repo_name"] = repo_context.get("full_name", repo_context.get("name", ""))
    package["language"] = language

    return _run_quality_gate(package, api_key, used_model, repo_context_text, sys_inst, provider=provider)
