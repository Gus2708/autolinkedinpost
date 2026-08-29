"""Módulo de generación de contenido avanzado para LinkedIn (Multi-LLM: Gemini, OpenAI, Claude, DeepSeek, Groq, OpenRouter, Ollama)."""

import os
import re
import time
from typing import Any, Dict, List, Optional
from src.evaluator import evaluate_linkedin_post
from src.humanizer_qc import process_and_enforce_humanizer_qc, sanitize_text_humanizer
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

   **FORMATO EXACTO DE CADA LÁMINA** (respetalo al pie de la letra):

   --- DIAPOSITIVA 1 / 10 ---
   [PORTADA]
   El bug silencioso que rompió mi RAG
   Escribía "ok: true" con cero vectores insertados.

   --- DIAPOSITIVA 2 / 10 ---
   [EL SÍNTOMA]
   400ms
   El p99 del agregado bajo carga concurrente.

   --- DIAPOSITIVA 3 / 10 ---
   [LA DECISIÓN]
   Redis sobre memoria local
   El proceso escala horizontal y el cache se duplicaba por réplica.
   - TTL de 300s con invalidación por evento
   - Lock distribuido para el thundering herd

   Reglas del formato:
   - Primera línea: la categoría entre corchetes, en mayúsculas y de 1 a 3 palabras.
   - Segunda línea: el TÍTULO en sí, escrito tal cual va a leerse. Máximo 6 palabras.
   - Después: una o dos oraciones de contexto, y opcionalmente viñetas con guion.
   - PROHIBIDO escribir rótulos como "TÍTULO:", "CONTENIDO:", "PORTADA" o "SUBTÍTULO:"
     como si fueran texto. La estructura la dan los corchetes y el orden de las líneas.
   - PROHIBIDO describir el diseño ("título grande y centrado", "texto en negrita").
     Vos escribís el contenido; el diseño lo resuelve el renderizador.
   - Cuando una lámina tenga una cifra como protagonista, poné SÓLO la cifra en la
     línea del título ("400ms", "94%", "3.2x") y el contexto debajo.



Entregá la respuesta respetando EXACTAMENTE esta estructura:

=== LINKEDIN_POST ===
[Aquí el post para LinkedIn]

=== PRIMER_COMENTARIO ===
[Aquí el texto del primer comentario con link al repo]

=== GUION_CARRUSEL_PDF ===
[Guion estructurado del carrusel con las 10 diapositivas delimitadas por '--- DIAPOSITIVA X / 10 ---']
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

3. **NATIVE 4:5 CAROUSEL SCRIPT (10 Slides - 1080x1350px Vertical - No fake URLs)**:
   - Delimit each slide with '--- SLIDE X / 10 ---' (Slide 1 Hook Cover, 2 Tension/Problem, 3 to 8 Step-by-step architecture/solution with bullet points, 9 Synthesis, 10 Technical Debate CTA).

   **EXACT SLIDE FORMAT** (follow it literally):

   --- SLIDE 1 / 10 ---
   [COVER]
   The silent bug that broke my RAG
   It logged "ok: true" with zero vectors inserted.

   --- SLIDE 2 / 10 ---
   [THE SYMPTOM]
   400ms
   The p99 of the billing aggregate under concurrent load.

   --- SLIDE 3 / 10 ---
   [THE DECISION]
   Redis over local memory
   The process scales horizontally, so the cache duplicated per replica.
   - 300s TTL with event-based invalidation
   - Distributed lock for the thundering herd

   Format rules:
   - First line: the category in brackets, uppercase, 1 to 3 words.
   - Second line: the TITLE itself, written exactly as it should read. Max 6 words.
   - Then: one or two sentences of context, and optionally dash bullets.
   - NEVER write labels like "TITLE:", "CONTENT:", "COVER" or "SUBTITLE:" as text.
     Structure comes from the brackets and the line order.
   - NEVER describe the design ("large centered title", "bold text").
     You write the content; the renderer handles the design.
   - When a slide has a figure as its protagonist, put ONLY the figure on the title
     line ("400ms", "94%", "3.2x") and the context underneath.



Respond EXACTLY with these section delimiters:

=== LINKEDIN_POST ===
[Complete LinkedIn post in English]

=== PRIMER_COMENTARIO ===
[First comment in English with repo link]

=== GUION_CARRUSEL_PDF ===
[LinkedIn Document Title and 10 Slides Carousel Script delimited by '--- SLIDE X / 10 ---']
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
   - Delimitá cada diapositiva exactamente con '--- DIAPOSITIVA X / 10 ---' (Slide 1 Portada, 2 Desafío/Tensión, 3 a 8 Arquitectura paso a paso, 9 Síntesis con trade-off, 10 CTA único y debate).

   **FORMATO EXACTO DE CADA LÁMINA** (respetalo al pie de la letra):

   --- DIAPOSITIVA 1 / 10 ---
   [PORTADA]
   El bug silencioso que rompió mi RAG
   Escribía "ok: true" con cero vectores insertados.

   --- DIAPOSITIVA 2 / 10 ---
   [EL SÍNTOMA]
   400ms
   El p99 del agregado bajo carga concurrente.

   --- DIAPOSITIVA 3 / 10 ---
   [LA DECISIÓN]
   Redis sobre memoria local
   El proceso escala horizontal y el cache se duplicaba por réplica.
   - TTL de 300s con invalidación por evento
   - Lock distribuido para el thundering herd

   Reglas del formato:
   - Primera línea: la categoría entre corchetes, en mayúsculas y de 1 a 3 palabras.
   - Segunda línea: el TÍTULO en sí, escrito tal cual va a leerse. Máximo 6 palabras.
   - Después: una o dos oraciones de contexto, y opcionalmente viñetas con guion.
   - PROHIBIDO escribir rótulos como "TÍTULO:", "CONTENIDO:", "PORTADA" o "SUBTÍTULO:"
     como si fueran texto. La estructura la dan los corchetes y el orden de las líneas.
   - PROHIBIDO describir el diseño ("título grande y centrado", "texto en negrita").
     Vos escribís el contenido; el diseño lo resuelve el renderizador.
   - Cuando una lámina tenga una cifra como protagonista, poné SÓLO la cifra en la
     línea del título ("400ms", "94%", "3.2x") y el contexto debajo.



Entregá la respuesta respetando EXACTAMENTE esta estructura:

=== LINKEDIN_POST ===
[Aquí el post de showcase en español]

=== PRIMER_COMENTARIO ===
[Aquí el primer comentario con link al repo]

=== GUION_CARRUSEL_PDF ===
[Guion estructurado del carrusel con las 10 diapositivas delimitadas por '--- DIAPOSITIVA X / 10 ---']
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
   - Delimit each slide with '--- SLIDE X / 10 ---'.

   **EXACT SLIDE FORMAT** (follow it literally):

   --- SLIDE 1 / 10 ---
   [COVER]
   The silent bug that broke my RAG
   It logged "ok: true" with zero vectors inserted.

   --- SLIDE 2 / 10 ---
   [THE SYMPTOM]
   400ms
   The p99 of the billing aggregate under concurrent load.

   --- SLIDE 3 / 10 ---
   [THE DECISION]
   Redis over local memory
   The process scales horizontally, so the cache duplicated per replica.
   - 300s TTL with event-based invalidation
   - Distributed lock for the thundering herd

   Format rules:
   - First line: the category in brackets, uppercase, 1 to 3 words.
   - Second line: the TITLE itself, written exactly as it should read. Max 6 words.
   - Then: one or two sentences of context, and optionally dash bullets.
   - NEVER write labels like "TITLE:", "CONTENT:", "COVER" or "SUBTITLE:" as text.
     Structure comes from the brackets and the line order.
   - NEVER describe the design ("large centered title", "bold text").
     You write the content; the renderer handles the design.
   - When a slide has a figure as its protagonist, put ONLY the figure on the title
     line ("400ms", "94%", "3.2x") and the context underneath.



Respond EXACTLY with these section delimiters:

=== LINKEDIN_POST ===
[Complete LinkedIn showcase post in English]

=== PRIMER_COMENTARIO ===
[First comment in English with repo link]

=== GUION_CARRUSEL_PDF ===
[LinkedIn Document Title and 10 Slides Carousel Script delimited by '--- SLIDE X / 10 ---']
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


def _parse_full_package(raw_text: str, default_name: str, language: str = "es") -> Dict[str, str]:
    """Parsea las 4 secciones del paquete completo de LinkedIn 2026 de forma robusta e insensible al orden."""
    return parse_publication_sections(raw_text, default_name, language)


def parse_publication_sections(
    raw_text: str,
    default_name: str = "",
    language: str = "es",
) -> Dict[str, str]:
    """Extrae las secciones de la respuesta del LLM a partir de los delimitadores."""
    sections = [
        ("=== LINKEDIN_POST ===", "post"),
        ("=== PRIMER_COMENTARIO ===", "first_comment"),
        ("=== GUION_CARRUSEL_PDF ===", "carousel_script"),
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
    }

    for i in range(len(found)):
        start_content = found[i][1]
        end_content = found[i+1][0] if i+1 < len(found) else len(raw_text)
        key = found[i][2]
        result[key] = raw_text[start_content:end_content].strip()

    # Si el modelo ignoró los delimitadores, el texto completo se toma como el post
    # en vez de devolver un paquete vacío que el llamador descarta en silencio.
    if not result["post"] and raw_text.strip():
        print("[WARN] La respuesta del LLM no traía delimitadores de sección; se usa el texto completo como post.")
        result["post"] = raw_text.strip()

    # Sanitizar con Humanizer anti-slop en el idioma del contenido
    for key in ("post", "first_comment", "carousel_script"):
        result[key] = sanitize_text_humanizer(result[key], language)

    if not result["first_comment"]:
        result["first_comment"] = f"https://github.com/{default_name}"

    return result


def _extract_refined_post(refined_raw: str) -> str:
    """Extrae el post del refinamiento, cortando en el siguiente delimitador de sección.

    La versión anterior hacía `.replace("=== LINKEDIN_POST ===", "")`, así que si el
    modelo devolvía además el comentario o el guion del carrusel, todo eso terminaba
    pegado dentro del post.
    """
    if not refined_raw or "=== LINKEDIN_POST ===" not in refined_raw:
        return ""

    body = refined_raw.split("=== LINKEDIN_POST ===", 1)[1]
    # Cortar en cualquier delimitador posterior (=== ALGO ===).
    next_section = re.search(r"^\s*===\s*[A-Z_]+\s*===", body, re.MULTILINE)
    if next_section:
        body = body[:next_section.start()]
    return body.strip()


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
    
    score = eval_result.get("overall_score", 0.0)
    passed = eval_result.get("passed", False)
    evaluated = eval_result.get("evaluated", True)

    if not evaluated:
        # El juez no llegó a emitir dictamen (red, JSON inválido). Refinar sería gastar
        # otra llamada a ciegas, así que se entrega el post marcando que nadie lo auditó.
        print(f"[WARN] Generador: {generator_model} | El juez no pudo evaluar el post: {eval_result.get('error', '')}")
        post_data["quality_score"] = 0.0
        post_data["quality_evaluated"] = False
        post_data["eval_details"] = eval_result
        post_data["used_model"] = generator_model
        return post_data

    print(f"[INFO] Generador: {generator_model} | Judge Score: {score}/5.0 (Passed: {passed})")
    post_data["quality_evaluated"] = True

    # El detalle por criterio se descartaba: un score bajo no se podía diagnosticar
    # sin volver a llamar al juez. Mismo punto ciego que tenía el QC visual.
    criterios = eval_result.get("evaluations") or {}
    if isinstance(criterios, dict) and criterios:
        flojos = [
            (k, v.get("score"))
            for k, v in criterios.items()
            if isinstance(v, dict) and isinstance(v.get("score"), (int, float)) and v["score"] < 4.5
        ]
        if flojos:
            detalle = ", ".join(f"{k}={s}" for k, s in sorted(flojos, key=lambda x: x[1]))
            print(f"       Criterios por debajo de 4.5: {detalle}")

    if not passed and eval_result.get("actionable_feedback"):
        motivo = " ".join(str(eval_result["actionable_feedback"]).split())[:220]
        print(f"[INFO] Post reprobado. Motivo: {motivo}")
        print("[INFO] Ejecutando auto-refinamiento...")
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
        refined_post = _extract_refined_post(refined_raw)
        if refined_post:
            post_data["post"] = refined_post
            eval_result = evaluate_linkedin_post(refined_post, api_key, repo_context_text, provider=provider)
            post_data["quality_score"] = eval_result.get("overall_score", 0.0)
            post_data["quality_evaluated"] = eval_result.get("evaluated", True)
        else:
            print("[WARN] El refinamiento no devolvió un post usable; se conserva la versión original.")
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

    package = _parse_full_package(raw_text, repo_name, language)
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

    package = _parse_full_package(
        raw_text,
        repo_context.get("full_name", repo_context.get("name", "")),
        language,
    )
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
