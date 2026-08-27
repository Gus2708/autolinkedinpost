"""Módulo de generación de contenido avanzado para LinkedIn (Multi-LLM: Gemini, OpenAI, Claude, DeepSeek, Groq, OpenRouter, Ollama)."""

import time
from typing import Any, Dict, List, Optional, Tuple
from src.evaluator import evaluate_linkedin_post
from src.humanizer_qc import process_and_enforce_humanizer_qc, audit_full_package_qc
from src.llm_client import generate_llm_text


SYSTEM_INSTRUCTION_ES = """
Sos un Senior Software Engineer, MVP y Tech Lead redactando contenido de alto impacto para LinkedIn siguiendo la Estrategia Algorítmica de 2026, el Manifiesto Humanizer Anti-AI-Slop y el Manual Técnico de Carruseles 4:5.

MANIFIESTO HUMANIZER ANTI-AI-SLOP (REGLAS OBLIGATORIAS):
Erradicá de raíz los 24 patrones delatores de texto generado por IA:
1. **VOZ EN PRIMERA PERSONA REAL**: Escribí siempre en 1ª persona singular ("Decidí", "Diseñé", "Me di cuenta", "Mi enfoque"). NUNCA uses "Decidimos", "Nuestro equipo" ni voz pasiva sin sujeto ("se implementó").
2. **CERO VOCABULARIO INFLADO DE IA**: PROHIBIDO usar "un testimonio de", "marca un antes y un después", "marca un hito", "crucial", "fundamental", "vital", "en el vertiginoso mundo...", "panorama en constante cambio", "revolucionario".
3. **CERO BUZZWORDS PROMOCIONALES**: PROHIBIDO "innovador", "fascinante", "sin fisuras" (seamless), "intuitivo", "impresionante", "ecosistema vibrante", "game changer", "elevar al siguiente nivel".
4. **CERO ESTRUCTURAS BINARIAS**: PROHIBIDO fórmulas predecibles tipo "No se trata de X, sino de Y".
5. **CERO TRÍADAS CLICHÉ**: PROHIBIDO listas de 3 adjetivos ("rápido, escalable y seguro"). Dos elementos concretos superan a tres adjetivos vacíos.
6. **CERO SALUDOS NI RELLENOS**: PROHIBIDO "Hola a todos", "Hola red", "Hoy quiero compartir...". Arrancá directo con la tensión técnica o el síntoma real.
7. **VERACIDAD ABSOLUTA (CERO ALUCINACIÓN)**: Basa todo 100% en el README, archivos y commits reales. NUNCA inventes caídas de producción ficticias ni números falsos.
8. **CALL TO ACTION (CTA) HUMANO**: PROHIBIDO decir "Guardá este post". Cerrá con una sola pregunta técnica constructiva para debatir trade-offs reales en comentarios.
9. **CARRUSEL 4:5 (1080x1350px)**: 10 láminas limpias delimitadas por '--- DIAPOSITIVA X / 10 ---', sin textos saturados, con títulos claros y viñetas concisas. PROHIBIDO inventar datos de contacto en la última lámina.
"""

SYSTEM_INSTRUCTION_EN = """
You are a Senior Software Engineer and Tech Lead writing high-impact engineering content for LinkedIn following the 2026 Strategy, the Anti-AI-Slop Humanizer Manifesto, and native 4:5 Carousels.

HUMANIZER ANTI-AI-SLOP MANIFESTO (MANDATORY RULES):
Detect and ruthlessly eliminate all 24 classic signs of AI-generated slop:
1. **FIRST-PERSON SINGULAR VOICE**: Always write as "I decided", "I designed", "I implemented", "My approach". NEVER use "We decided" or royal passive voice ("it was implemented").
2. **NO INFLATED AI SIGNIFICANCE**: FORBIDDEN: "a testament to", "pivotal moment", "vital role", "evolving landscape", "in today's fast-paced world", "revolutionary", "game changer".
3. **NO PROMOTIONAL BUZZWORDS**: FORBIDDEN: "seamless", "seamlessly", "intuitive", "fascinating", "vibrant ecosystem", "unlock potential", "delve into".
4. **NO FORMULAIC BINARY CONTRASTS**: FORBIDDEN: "It's not just about X, it's about Y".
5. **NO RULE-OF-THREE CLICHES**: FORBIDDEN: "fast, scalable, and resilient". Be specific instead of listing three empty adjectives.
6. **NO GREETING CRUTCHES**: FORBIDDEN: "Hello network", "Excited to share...". Start immediately with the raw engineering challenge or symptom.
7. **STRICT FACTUAL GROUNDING**: 100% grounded in real commits, files, and architecture. Never invent fake production outages or fake metrics.
8. **AUTHENTIC CTA**: FORBIDDEN to say "Save this post". Close with a single genuine engineering question discussing trade-offs in comments.
9. **10-SLIDE 4:5 CAROUSEL**: 10 clean slides delimited by '--- SLIDE X / 10 ---' with punchy titles and bullet points. Never generate fake contact details.
"""


PROJECT_PROMPT_TEMPLATE_ES = """
A partir de la siguiente actividad REAL en el repositorio '{repo_name}':

Commits y cambios técnicos reales:
{commits_text}

Generá el paquete completo de publicación en ESPAÑOL (Estrategia 2026 de Alto Impacto):

1. **EL GANCHO (Primeras 2 líneas - < 200 caracteres)**:
   - Captá la atención en los primeros 2 segundos con UNA PREGUNTA DIRECTA o UNA FRASE FUERTE que rompa un mito o mencione el problema técnico real.
   - PROHIBIDO saludos largos o de relleno ("Hola red", "Espero que estén bien", "Hoy quiero compartir..."). Directo al grano.

2. **EL CUERPO (El Valor y Solución Técnica)**:
   - Explicación corta: cómo diseñaste o solucionaste el problema.
   - Puntos clave: usá listas cortas y fáciles de escanear en formato de viñetas (- o •).
   - Tono humano: escribí en 1ª persona singular, conversacional, como si hablaras cara a cara con otro desarrollador.
   - Párrafos breves de 2 líneas con espacio en blanco.

3. **LLAMADO A LA ACCIÓN (CTA)**:
   - UNA SOLA INSTRUCCIÓN CLARA: decile a la persona exactamente qué hacer (ej: comentar abajo su punto de vista o alternativa técnica).
   - BENEFICIO CLARO: explicá qué gana si sigue la instrucción (ej: contrastar trade-offs o conocer mejores prácticas).
   - PROHIBIDO decir "Guardá este post".

4. **ETIQUETAS Y SEO**:
   - Integrá palabras clave naturales de tu área técnica (Software Engineering, System Design, stack real).
   - Usá entre 3 y 6 hashtags moderados y directamente relacionados con el sector.

5. **PRIMER COMENTARIO (Regla de los 60 minutos)**:
   - Texto para comentar inmediatamente con el link https://github.com/{repo_name} y una pregunta de seguimiento.

6. **GUION DE CARRUSEL TÉCNICO (10 Diapositivas - Formato 4:5 Vertical)**:
   - DIAPOSITIVA 1 (PORTADA): Título CORTO Y GRANDE que resuma el post con impacto (máx 5-7 palabras). Gancho fuerte sin texto saturado.
   - DIAPOSITIVAS 2 A 9: Diseño limpio, sin texto pequeño saturado. Título conciso y 2-3 viñetas cortas o explicación de máx 25 palabras por lámina.
   - DIAPOSITIVA 10 (CTA): Una sola instrucción clara + beneficio claro para el lector y pregunta de debate.
   - Delimitá cada diapositiva exactamente con '--- DIAPOSITIVA X / 10 ---' (Slide 1 Portada, 2 Problema/Mito, 3 a 8 Solución y arquitectura paso a paso, 9 Aprendizaje/Trade-off, 10 CTA y debate).

7. **SUGERENCIA VISUAL**:
   - Diagrama de arquitectura o captura de terminal.

Entregá la respuesta respetando EXACTAMENTE esta estructura:

=== LINKEDIN_POST ===
[Aquí el post para LinkedIn]

=== PRIMER_COMENTARIO ===
[Aquí el texto del primer comentario con link al repo]

=== GUION_CARRUSEL_PDF ===
[Guion estructurado del carrusel con las 10 diapositivas delimitadas por '--- DIAPOSITIVA X / 10 ---']

=== SUGERENCIA_VISUAL ===
[Aquí la sugerencia visual o diagrama]
"""

PROJECT_PROMPT_TEMPLATE_EN = """
Based on the following REAL commit activity in repository '{repo_name}':

Real commits and technical changes:
{commits_text}

Generate the complete LinkedIn publication pack in professional ENGLISH (2026 Strategy):

1. **LINKEDIN POST (1st-Person Singular Storytelling - Problem & Solution Framework)**:
   - Strong hook in the first 2 lines (< 200 chars) stating the real engineering challenge or bug.
   - If changes include bugfixes ('fix'), structure the post with:
     * **The Symptom / Problem**: What edge-case or failure was happening.
     * **The Root Cause**: Why it happened in data, logic, or system integration.
     * **The Solution / Fix**: How I designed and implemented the fix cleanly.
     * **The Takeaway**: Trade-off or engineering lesson learned.
   - 2-line paragraphs with whitespace.
   - Close with an open engineering question to drive comments and debate (FORBIDDEN to say "Save this post").
   - 3-4 technical hashtags.

2. **FIRST COMMENT (60-minute rule)**:
   - Comment ready to post immediately with link https://github.com/{repo_name}.

3. **CANVA AI CAROUSEL SCRIPT (10 Slides - 1200x1500px Vertical - No 16:9 - No fake URLs)**:
   - Must be a SINGLE SELF-CONTAINED MASTER PROMPT ready to paste directly into Canva AI Chat or Magic Design.
   - Must start with the strict imperative trigger:
     "Create a vertical carousel/presentation of exactly 10 pages (4:5 vertical format, 1200x1500 px). MANDATORY: Generate all 10 complete slides inside the same editable project, DO NOT generate only the cover."
   - Design parameters:
     "Style: Technical dark minimalist for software engineers. Background: #0F172A. Body text: #F8FAFC. Accents: #38BDF8. Font: Clean high-contrast sans-serif."
   - Delimit each slide with '--- SLIDE X / 10 ---' (Slide 1 Hook Cover, 2 Tension/Problem, 3 to 8 Step-by-step architecture/solution with max 25 words per slide, 9 Synthesis, 10 Technical Debate CTA).

4. **VISUAL SUGGESTION**:
   - Architecture diagram or split terminal capture suggestion.

Respond EXACTLY with these section delimiters:

=== LINKEDIN_POST ===
[Complete LinkedIn post in English]

=== PRIMER_COMENTARIO ===
[First comment in English with repo link]

=== GUION_CARRUSEL_PDF ===
[LinkedIn Document Title and Self-Contained Canva AI Master Prompt containing all 10 slides]

=== SUGERENCIA_VISUAL ===
[Visual recommendation in English]
"""

SHOWCASE_PROMPT_TEMPLATE_ES = """
Sos {author_name}, un desarrollador senior presentando tu proyecto individual '{name}' en LinkedIn para reclutadores técnicos y Tech Leads.

Información real y verificada del proyecto:
- **Repositorio**: {full_name}
- **Descripción**: {description}
- **Stack / Lenguajes reales**: {languages}
- **Archivos clave**: {key_files}
- **Extracto del README real**:
{readme}

Generá el paquete completo de publicación de portafolio en ESPAÑOL (Estrategia 2026 de Alto Impacto):

1. **EL GANCHO (Primeras 2 líneas - < 200 caracteres)**:
   - Captá la atención en los primeros 2 segundos con UNA PREGUNTA DIRECTA o UNA FRASE FUERTE que plantee el desafío técnico o rompa un mito.
   - PROHIBIDO saludos largos o de relleno ("Hola a todos", "Hoy les presento mi proyecto..."). Directo al grano.

2. **EL CUERPO (El Valor y Arquitectura Real)**:
   - Explicación corta y clara: qué problema resuelve el proyecto y cómo lo diseñaste.
   - Puntos clave: usá listas cortas y fáciles de escanear en viñetas (- o •) con decisiones técnicas concretas.
   - Tono humano: en 1ª persona singular, conversacional, como si hablaras cara a cara con otro Tech Lead.
   - Párrafos breves de 2 líneas con espacio en blanco.

3. **LLAMADO A LA ACCIÓN (CTA)**:
   - UNA SOLA INSTRUCCIÓN CLARA: decile a la persona exactamente qué hacer (ej: comentar abajo qué trade-off elegirían o revisar el código).
   - BENEFICIO CLARO: qué ganan al participar (ej: comparar enfoques de arquitectura o explorar el benchmark).
   - PROHIBIDO decir "Guardá este post".

4. **ETIQUETAS Y SEO**:
   - Integrá palabras clave del sector (Software Architecture, Fullstack, Frontend, Backend, stack real).
   - Usá entre 3 y 6 hashtags directamente relacionados con el sector técnico.

5. **PRIMER COMENTARIO (Regla de los 60 minutos)**:
   - Texto para comentar de inmediato con el link https://github.com/{full_name} y una pregunta de debate.

6. **GUION DE CARRUSEL TÉCNICO (10 Diapositivas - Micro-Ensayo Visual Autónomo Formato 4:5 Vertical)**:
   - **PRINCIPIO FUNDAMENTAL: EL CARRUSEL DEBE HABLAR POR SÍ SOLO**:
     NO escribas viñetas telegráficas ni frases sueltas pensadas como "material de apoyo para exponer". La mayoría de los ingenieros en LinkedIn en móvil solo deslizan el documento PDF sin abrir la descripción del post. El carrusel debe ser un micro-ensayo de ingeniería 100% autosuficiente que transmita todo el valor, decisiones y arquitectura sin requerir texto externo.
   - **ESTRUCTURA DE CONTENIDO POR DIAPOSITIVA (2 a 9)**:
     * **Título concreto y técnico**: Que plantee el problema, la decisión o el mecanismo.
     * **Párrafo contextual de 1-2 oraciones**: Explica el "por qué", el cuello de botella real o la motivación arquitectónica.
     * **2 a 3 viñetas técnicas con sustancia**: Detallá el "cómo" con patrones, librerías, estructuras de datos, métricas o trade-offs específicos.
     * **Volumen recomendado**: Entre 35 y 60 palabras por lámina para dar peso técnico y llenar el canvas armónicamente.
   - **DIAPOSITIVA 1 (PORTADA)**: Título de alto impacto visual (máx 5-8 palabras) + subtítulo explicativo de la arquitectura.
   - **DIAPOSITIVA 10 (CTA)**: Conclusión técnica sólida + pregunta de debate para la comunidad.
   - **PROTOCOLO HUMANIZER INTEGRADO**:
     * Escribí con voz de ingeniero senior en 1ª persona singular ("Implementé...", "Elegí X sobre Y porque...", "El cuello de botella era...").
     * PROHIBIDO clichés de IA: "revolucionario", "fascinante", "pieza clave", "en este vertiginoso mundo", "un antes y un después", "sin duda alguna".
     * Cero abstracciones vacías: todo anclado a código, latencias, memoria, estados y arquitectura real.
   - **ICONOS LUCIDE DINÁMICOS**: En cada diapositiva seleccioná el icono exacto de https://lucide.dev/icons con `[CATEGORIA | nombre-icono]` o `[ICON: nombre-icono]`. Podés usar `[ICON: icono]` al inicio de viñetas individuales.
   - Delimitá cada diapositiva exactamente con '--- DIAPOSITIVA X / 10 ---' (Slide 1 Portada, 2 Desafío/Tensión, 3 a 8 Arquitectura paso a paso, 9 Síntesis con trade-off, 10 CTA único y debate).

7. **SUGERENCIA VISUAL**:
   - Diagrama de arquitectura C4 o captura de UI/Terminal genuina.

Entregá la respuesta respetando EXACTAMENTE esta estructura:

=== LINKEDIN_POST ===
[Aquí el post de showcase en español]

=== PRIMER_COMENTARIO ===
[Aquí el primer comentario con link al repo]

=== GUION_CARRUSEL_PDF ===
[Guion estructurado del carrusel con las 10 diapositivas delimitadas por '--- DIAPOSITIVA X / 10 ---']

=== SUGERENCIA_VISUAL ===
[Aquí la recomendación visual o diagrama]
"""

SHOWCASE_PROMPT_TEMPLATE_EN = """
You are {author_name}, a Senior Software Engineer presenting your individual project '{name}' on LinkedIn for technical recruiters and Engineering Managers.

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
   - Close with a thought-provoking technical question to spark discussion and comments (FORBIDDEN to say "Save this post").
   - 3-4 strategic hashtags.

2. **FIRST COMMENT**:
   - Seed comment with clean link to https://github.com/{full_name}.

3. **TECHNICAL CAROUSEL SCRIPT (10 Slides - Autonomous Visual Essay 4:5 Vertical)**:
   - **CORE PRINCIPLE: THE CAROUSEL MUST STAND ON ITS OWN**:
     Do NOT write telegraphic bullet points designed as "speaker presentation notes". Most LinkedIn mobile users only swipe the PDF document without expanding the post caption. The carousel must be a 100% self-contained engineering micro-essay conveying the full architectural problem, decisions, trade-offs, and solution without external context.
   - **SLIDE STRUCTURE (Slides 2 to 9)**:
     * **Descriptive Technical Title**: States the specific challenge or architectural decision.
     * **1-2 Sentence Contextual Intro**: Explains the "why", the bottleneck, or the engineering trade-off.
     * **2-3 Substantive Bullet Points**: Details the "how" using concrete patterns, libraries, concurrency/cache mechanisms, or metrics.
     * **Target Volume**: 35 to 60 words per slide to fill the canvas with substance.
   - **SLIDE 1 (COVER)**: High-impact punchy title + architecture subtitle.
   - **SLIDE 10 (CTA)**: Solid engineering takeaway + thought-provoking debate question.
   - **HUMANIZER PROTOCOL**: 1st-person singular, direct and honest engineering voice. No AI buzzwords ("game-changer", "dive in", "unravel", "testament").
   - **DYNAMIC LUCIDE ICONS**: Pick specific Lucide icons using `[CATEGORY | icon-name]` or `[ICON: icon-name]`.
   - Delimit each slide with '--- SLIDE X / 10 ---'.

4. **VISUAL SUGGESTION**:
   - Architecture diagram (C4 / Excalidraw) or terminal benchmark suggestion.

Respond EXACTLY with these section delimiters:

=== LINKEDIN_POST ===
[Complete LinkedIn showcase post in English]

=== PRIMER_COMENTARIO ===
[First comment in English with repo link]

=== GUION_CARRUSEL_PDF ===
[LinkedIn Document Title and Self-Contained Canva AI Master Prompt containing all 10 slides]

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
4. Cierre con pregunta técnica para abrir debate en comentarios (elimina cualquier frase repetitiva como 'Guardá este post').

Entregá únicamente el post mejorado en el bloque:
=== LINKEDIN_POST ===
[Aquí el post corregido]
"""


def _parse_full_package(raw_text: str, default_name: str) -> Dict[str, str]:
    """Parsea las 4 secciones del paquete completo de LinkedIn 2026 de forma robusta e insensible al orden."""
    return parse_publication_sections(raw_text, default_name)


def humanize_text(text: str) -> str:
    """Aplica las reglas del skill Humanizer para erradicar patrones de IA y AI slop."""
    import re
    if not text:
        return text

    cleaned = text

    # 1. Eliminar saludos iniciales y muletillas robóticas
    greetings = [
        r"^Hola a todos[!\.,\s]*\n*",
        r"^Hola red[!\.,\s]*\n*",
        r"^¡Hola comunidad[!\.,\s]*\n*",
        r"^Espero que est[eé]n bien[!\.,\s]*\n*",
        r"^Hoy quiero compartir\s*(?:con ustedes)?\s*[:\.]?\s*\n*",
        r"^En el vertiginoso mundo\b.*?[,\.]\s*\n*",
        r"^En un mundo en constante (?:evolución|cambio)\b.*?[,\.]\s*\n*",
        r"^Hello network[!\.,\s]*\n*",
        r"^Hello everyone[!\.,\s]*\n*",
        r"^I am thrilled to announce\b.*?[,\.]\s*\n*",
        r"^In today's fast-paced\b.*?[,\.]\s*\n*",
    ]
    for g in greetings:
        cleaned = re.sub(g, "", cleaned, flags=re.IGNORECASE | re.MULTILINE)

    # 2. Reemplazos de vocabulario delator de IA (AI Slop Vocabulary)
    slop_replacements = [
        (r"(?i)\bun testimonio de\b", "una prueba de"),
        (r"(?i)\ba testament to\b", "proof of"),
        (r"(?i)\bmarca un hito\b", "representa un cambio"),
        (r"(?i)\bmarca un antes y un despu[eé]s\b", "cambió la forma en que lo hacíamos"),
        (r"(?i)\bpivotal moment\b", "turning point"),
        (r"(?i)\bdesempeña un papel crucial\b", "es necesario"),
        (r"(?i)\bde suma importancia\b", "importante"),
        (r"(?i)\bindeleble\b", "marcado"),
        (r"(?i)\bde manera fluida y sin fisuras\b", "sin bloqueos"),
        (r"(?i)\bsin fisuras\b", "limpio"),
        (r"(?i)\bseamlessly\b", "smoothly"),
        (r"(?i)\bseamless\b", "clean"),
        (r"(?i)\bgame[- ]changer\b", "cambio relevante"),
        (r"(?i)\brevolucionari[oa]s?\b", "efectivo"),
        (r"(?i)\bdelve into\b", "explore"),
        (r"(?i)\bintuitiv[oa]s?\b", "simple de usar"),
        (r"(?i)\becosistema vibrante\b", "entorno activo"),
        (r"(?i)\bevolving landscape\b", "tech stack"),
        (r"(?i)\belev[ao]r al siguiente nivel\b", "mejorar"),
        (r"(?i)\b(?:¡|!)?guard[aá] este post\b.*?[!\.]?\s*", ""),
        (r"(?i)\bsave this post\b.*?[!\.]?\s*", ""),
    ]

    for pattern, repl in slop_replacements:
        cleaned = re.sub(pattern, repl, cleaned)

    return cleaned.strip()


def parse_publication_sections(raw_text: str, default_name: str = "") -> Dict[str, str]:
    """Extrae las secciones de la respuesta del LLM a partir de los delimitadores."""
    import re
    sections = [
        ("=== LINKEDIN_POST ===", "post"),
        ("=== PRIMER_COMENTARIO ===", "first_comment"),
        ("=== GUION_CARRUSEL_PDF ===", "carousel_script"),
        ("=== SUGERENCIA_VISUAL ===", "visual_suggestion"),
    ]

    found = []
    for delimiter, key in sections:
        pos = raw_text.find(delimiter)
        if pos != -1:
            found.append((pos, pos + len(delimiter), key))

    found.sort(key=lambda x: x[0])

    result = {
        "post": "",
        "first_comment": "",
        "carousel_script": "",
        "visual_suggestion": "",
    }

    for i in range(len(found)):
        start_content = found[i][1]
        end_content = found[i+1][0] if i+1 < len(found) else len(raw_text)
        key = found[i][2]
        result[key] = raw_text[start_content:end_content].strip()

    # Sanitizar con Humanizer anti-slop
    result["post"] = humanize_text(result["post"])
    result["first_comment"] = humanize_text(result["first_comment"])
    result["carousel_script"] = humanize_text(result["carousel_script"])

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

    # Control de Calidad (QC) y Humanización obligatoria contra los 24 patrones de AI slop
    package, humanizer_qc = process_and_enforce_humanizer_qc(
        package,
        language=language,
        api_key=api_key,
        provider=provider,
        preferred_model=preferred_model,
    )
    package["humanizer_qc"] = humanizer_qc

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

    import os
    author_name = os.getenv("GH_AUTHOR_NAME") or os.getenv("GH_USERNAME") or "el autor y desarrollador senior"

    if language == "en":
        prompt = SHOWCASE_PROMPT_TEMPLATE_EN.format(
            author_name=author_name,
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
            author_name=author_name,
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

    # Control de Calidad (QC) y Humanización obligatoria contra los 24 patrones de AI slop
    package, humanizer_qc = process_and_enforce_humanizer_qc(
        package,
        language=language,
        api_key=api_key,
        provider=provider,
        preferred_model=model_name,
    )
    package["humanizer_qc"] = humanizer_qc

    return _run_quality_gate(package, api_key, used_model, repo_context_text, sys_inst, provider=provider)
