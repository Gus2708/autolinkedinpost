"""Módulo de Control de Calidad (QC) y Humanización Avanzada de Textos.
Basado estrictamente en las directrices del skill Humanizer (WikiProject AI Cleanup, blader/humanizer, stop-slop).
Audita y elimina los 24 patrones clásicos de AI Slop en publicaciones de LinkedIn, comentarios y carruseles.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from src.llm_client import generate_llm_text


# ==============================================================================
# BASE DE DATOS DE PATRONES DE AI SLOP (24 PATRONES DEL HUMANIZER)
# ==============================================================================

# Patrones de vocabulario inflado, buzzwords y fórmulas típicas de LLM
SLOP_PATTERNS_ES = [
    # 1. Importancia inflada y trascendencia artificial
    (r"(?i)\bun testimonio de\b", "un testimonio de", "una prueba de / muestra"),
    (r"(?i)\bmarca un hito\b", "marca un hito", "es un avance / cambio"),
    (r"(?i)\bmarca un antes y un despu[eé]s\b", "marca un antes y un después", "cambió la forma en que lo hacíamos"),
    (r"(?i)\bdesempeña un papel (?:crucial|fundamental|vital)\b", "papel crucial/fundamental", "es necesario / clave"),
    (r"(?i)\ben el vertiginoso mundo\b.*?[,\.]", "en el vertiginoso mundo...", "arrancar directo sin preámbulos"),
    (r"(?i)\ben un mundo en constante (?:evolución|cambio)\b.*?[,\.]", "en un mundo en constante evolución", "eliminar frase de relleno"),
    (r"(?i)\bpanorama en constante cambio\b", "panorama en constante cambio", "contexto / entorno"),
    (r"(?i)\bde suma importancia\b", "de suma importancia", "importante / crítico"),
    (r"(?i)\bhuella indeleble\b", "huella indeleble", "impacto real"),

    # 2. Buzzwords promocionales y adjetivos vacíos
    (r"(?i)\bde manera fluida y sin fisuras\b", "de manera fluida y sin fisuras", "sin bloqueos / directo"),
    (r"(?i)\bsin fisuras\b", "sin fisuras", "limpio / estable"),
    (r"(?i)\bgame[- ]changer\b", "game changer", "cambio relevante"),
    (r"(?i)\brevolucionari[oa]s?\b", "revolucionario", "efectivo / útil"),
    (r"(?i)\becosistema vibrante\b", "ecosistema vibrante", "entorno activo"),
    (r"(?i)\belev[ao]r al siguiente nivel\b", "elevar al siguiente nivel", "optimizar / mejorar"),
    (r"(?i)\bdesbloquear el potencial\b", "desbloquear el potencial", "aprovechar"),
    (r"(?i)\bintuitiv[oa]s?\b", "intuitivo", "simple de usar"),
    (r"(?i)\bfascinante\b", "fascinante", "interesante"),

    # 3. Estructuras binarias predecibles ("No se trata de X, sino de Y")
    (r"(?i)\bno se trata (?:solo|únicamente)? de [^,]+, sino de\b", "fórmula binaria 'no se trata de X sino de Y'", "afirmar directamente sin antítesis teatral"),
    (r"(?i)\bno es (?:solo)? un[a]? [^,]+, es un[a]?\b", "fórmula binaria 'no es X, es Y'", "declarar el hecho directamente"),

    # 4. Tríadas cliché de 3 adjetivos
    (r"(?i)\br[aá]pido, escalable y (?:robusto|seguro)\b", "tríada cliché 'rápido, escalable y...'", "especificar una cualidad concreta"),
    (r"(?i)\bseguro, eficiente y escalable\b", "tríada cliché", "especificar la métrica real"),

    # 5. Saludos y muletillas iniciales
    (r"(?i)^hola a todos[!\.,\s]*", "saludo cliché 'Hola a todos'", "eliminar"),
    (r"(?i)^hola red[!\.,\s]*", "saludo cliché 'Hola red'", "eliminar"),
    (r"(?i)^espero que est[eé]n bien[!\.,\s]*", "muletilla 'Espero que estén bien'", "eliminar"),
    (r"(?i)^hoy quiero compartir\b.*?:", "apertura cliché 'Hoy quiero compartir'", "arrancar con el desafío"),

    # 6. Conclusiones formuladas y cierres repetitivos
    (r"(?i)\b(?:¡|!)?guard[aá] este post\b.*?[!\.]?", "CTA mecánico 'Guardá este post'", "hacer pregunta de debate"),
    (r"(?i)\ba pesar de (?:estos|los) desaf[ií]os.*?(?:el futuro|prometedor)\b", "cierre de falso optimismo", "conclusión realista de ingeniería"),

    # 7. Transiciones artificiales y relleno (Copywriting Tells)
    (r"(?i)\bcabe destacar que\b", "muletilla 'cabe destacar que'", "afirmar directamente sin preámbulo"),
    (r"(?i)\bdicho esto\b[,\.]?", "transición artificial 'dicho esto'", "ir al grano con la idea técnica"),
    (r"(?i)\ben su esencia\b", "cliché 'en su esencia'", "especificar en la práctica"),
    (r"(?i)\ben el panorama digital actual\b", "relleno 'panorama digital actual'", "arrancar con el problema real"),
    (r"(?i)\bprofundicemos en\b", "muletilla 'profundicemos en'", "analizar / examinar"),
    (r"(?i)\ben conclusión\b[,\.]?", "cierre escolar 'en conclusión'", "cerrar con el trade-off o la pregunta técnica"),

    # 8. CTAs débiles o pasivos (Copywriting Conversion Rules)
    (r"(?i)\b(?:hac[eé]|haz)\s+clic(?:\s+aqu[ií])?\b", "CTA débil 'hacé clic'", "usar [Verbo de Acción] + [Qué obtiene/debate]"),
    (r"(?i)\baprend[eé]\s+m[aá]s\b", "CTA débil 'aprendé más'", "especificar el aprendizaje técnico o benchmark"),
    (r"(?i)\bseguime para m[aá]s\b", "CTA genérico 'seguime para más'", "abrir debate sobre trade-offs en comentarios"),
]

SLOP_PATTERNS_EN = [
    (r"(?i)\ba testament to\b", "a testament to", "proof of / demonstrates"),
    (r"(?i)\bpivotal moment\b", "pivotal moment", "turning point / key step"),
    (r"(?i)\bplays a vital role\b", "plays a vital role", "is required / needed"),
    (r"(?i)\bin today's fast-paced\b.*?[,\.]", "in today's fast-paced...", "start directly with the problem"),
    (r"(?i)\bevolving landscape\b", "evolving landscape", "ecosystem / stack"),
    (r"(?i)\bseamlessly\b", "seamlessly", "smoothly / without friction"),
    (r"(?i)\bseamless\b", "seamless", "clean / stable"),
    (r"(?i)\bgame[- ]changer\b", "game-changer", "major improvement"),
    (r"(?i)\brevolutionary\b", "revolutionary", "effective / practical"),
    (r"(?i)\bdelve into\b", "delve into", "examine / analyze"),
    (r"(?i)\bunlock the potential\b", "unlock the potential", "enable"),
    (r"(?i)\bit's not just about [^,]+, it's about\b", "binary contrast formula", "state the point directly"),
    (r"(?i)\bfast, scalable,? and (?:resilient|robust)\b", "rule-of-three cliche", "state the specific technical gain"),
    (r"(?i)^hello network[!\.,\s]*", "greeting crutch", "remove"),
    (r"(?i)^excited to share[!\.,\s]*", "fluff opening", "remove"),
    (r"(?i)\bsave this post\b.*?[!\.]?", "boilerplate CTA 'save this post'", "ask an engineering debate question"),

    # Copywriting Transitions & Weak CTAs
    (r"(?i)\bthat being said\b[,\.]?", "mechanical transition 'that being said'", "state the point directly"),
    (r"(?i)\bit's worth noting that\b", "fluff opening 'it's worth noting that'", "state the technical fact directly"),
    (r"(?i)\bat its core\b", "cliche 'at its core'", "specifically / in production"),
    (r"(?i)\bin today's digital landscape\b", "empty context 'in today's digital landscape'", "cut fluff"),
    (r"(?i)\bin conclusion\b[,\.]?", "school essay transition 'in conclusion'", "conclude with the architectural trade-off"),
    (r"(?i)\bclick here\b", "weak CTA 'click here'", "use [Action Verb] + [What they get/discuss]"),
    (r"(?i)\blearn more\b", "weak CTA 'learn more'", "specify what to analyze or benchmark"),
    (r"(?i)\bfollow for more\b", "generic CTA 'follow for more'", "close with an engineering discussion prompt"),
]


# ==============================================================================
# AUDITORÍA HEURÍSTICA Y CONTROL DE CALIDAD (QC)
# ==============================================================================

def audit_text_humanizer_qc(text: str, language: str = "es") -> Dict[str, Any]:
    """Audita un texto contra los 24 patrones del skill Humanizer.
    
    Retorna un reporte detallado con score de 1.0 a 5.0, patrones encontrados y recomendaciones.
    """
    if not text or not text.strip():
        return {
            "score": 5.0,
            "passed": True,
            "violations_count": 0,
            "violations": [],
            "em_dash_count": 0,
            "plural_voice_detected": False,
        }

    violations = []
    patterns = SLOP_PATTERNS_ES if _is_spanish(language) else SLOP_PATTERNS_EN

    # 1. Detección de patrones de slop.
    # Se reporta UNA violación por patrón distinto, no una por ocurrencia: repetir
    # "seamless" tres veces es un solo problema de vocabulario, y contarlo tres veces
    # hacía que cualquier texto largo cayera al piso del score.
    for regex, pattern_name, suggestion in patterns:
        found = list(re.finditer(regex, text))
        if not found:
            continue
        first = found[0]
        start = max(0, first.start() - 25)
        end = min(len(text), first.end() + 25)
        snippet = text[start:end].replace("\n", " ").strip()
        violations.append({
            "pattern": pattern_name,
            "snippet": f"...{snippet}...",
            "suggestion": suggestion,
            "occurrences": len(found),
        })

    # 2. Detección de sobreuso de em-dash (—), proporcional al largo del texto.
    # Un carrusel de 10 láminas tolera más rayas que un post corto antes de que el
    # uso deje de ser puntuación y pase a ser una firma de redacción automática.
    em_dash_count = text.count("—") + text.count("–")
    word_count = max(1, len(text.split()))
    em_dash_budget = max(2, round(word_count / 120))
    if em_dash_count > em_dash_budget:
        violations.append({
            "pattern": f"Sobreuso de rayas em-dash ({em_dash_count} encontradas)",
            "snippet": "Uso excesivo de '—' típico de redactores de IA",
            "suggestion": "Reemplazar por comas o separar en oraciones cortas",
        })

    # 3. Detección de plural corporativo / pérdida de primera persona
    plural_voice_detected = False
    if _is_spanish(language):
        plural_matches = re.findall(r"(?i)\b(?:decidimos|diseñamos|implementamos|creamos|nuestro equipo|resolvimos|optamos)\b", text)
        if plural_matches:
            plural_voice_detected = True
            violations.append({
                "pattern": f"Voz plural corporativa detectada: {list(set(plural_matches))}",
                "snippet": ", ".join(plural_matches[:3]),
                "suggestion": "Escribir en 1ª persona singular: 'Decidí', 'Diseñé', 'Mi enfoque'",
            })
    else:
        plural_matches = re.findall(r"(?i)\b(?:we decided|we designed|we built|our team|we chose)\b", text)
        if plural_matches:
            plural_voice_detected = True
            violations.append({
                "pattern": f"Corporate plural detected: {list(set(plural_matches))}",
                "snippet": ", ".join(plural_matches[:3]),
                "suggestion": "Use 1st-person singular: 'I decided', 'I designed', 'My approach'",
            })

    # 4. Detección de calificadores débiles / hedging excesivo (Copywriting: Confident over qualified)
    hedging_matches = (
        re.findall(r"(?i)\b(?:casi|muy|bastante|realmente|en gran medida)\b", text)
        if _is_spanish(language)
        else re.findall(r"(?i)\b(?:almost|very|really|basically|somewhat)\b", text)
    )
    hedging_count = len(hedging_matches)
    hedging_budget = max(2, round(word_count / 75))
    if hedging_count > hedging_budget:
        violations.append({
            "pattern": f"Exceso de calificadores débiles ({hedging_count} detectados)",
            "snippet": ", ".join(hedging_matches[:4]),
            "suggestion": "Escribir con convicción y datos concretos (Confident over qualified), eliminando calificadores como 'muy' o 'casi'",
        })

    # 5. Detección de signos de exclamación (Copywriting Rule #79: Remove exclamation points)
    exclamation_count = text.count("!") + text.count("¡")
    exclamation_budget = max(1, round(word_count / 100))
    if exclamation_count > exclamation_budget:
        violations.append({
            "pattern": f"Exceso de signos de exclamación ({exclamation_count} encontrados)",
            "snippet": "Uso reiterado de signos de exclamación",
            "suggestion": "El copywriting técnico no grita: apoyar el impacto en datos, arquitectura y verbos de acción",
        })

    # Cálculo del score: base 5.0, con penalización por DENSIDAD de patrones distintos.
    # Antes se restaba 0.5 por ocurrencia sin normalizar por largo, así que un guion de
    # carrusel siempre terminaba en 1.0 y arrastraba al paquete entero a "reprobado".
    total_violations = len(violations)
    density = total_violations / max(1.0, word_count / 150)
    penalty = min(density * 0.5, 4.0)
    score = round(max(1.0, 5.0 - penalty), 1)
    passed = (score >= 4.0 and not plural_voice_detected)

    return {
        "score": score,
        "passed": passed,
        "violations_count": total_violations,
        "violations": violations,
        "word_count": word_count,
        "em_dash_count": em_dash_count,
        "hedging_count": hedging_count,
        "exclamation_count": exclamation_count,
        "plural_voice_detected": plural_voice_detected,
    }


def audit_full_package_qc(package: Dict[str, str], language: str = "es") -> Dict[str, Any]:
    """Ejecuta el QC de Humanizer sobre todas las partes del paquete: post, primer comentario y guion de carrusel."""
    post_qc = audit_text_humanizer_qc(package.get("post", ""), language)
    comment_qc = audit_text_humanizer_qc(package.get("first_comment", ""), language)
    carousel_qc = audit_text_humanizer_qc(package.get("carousel_script", ""), language)

    overall_score = round(
        (post_qc["score"] * 0.5) + (carousel_qc["score"] * 0.4) + (comment_qc["score"] * 0.1),
        1,
    )
    # El post es el criterio duro. El carrusel y el comentario aportan al score pero no
    # bloquean por sí solos: son textos accesorios y hacían fallar el paquete completo.
    overall_passed = post_qc["passed"] and carousel_qc["score"] >= 3.5
    total_violations = post_qc["violations_count"] + comment_qc["violations_count"] + carousel_qc["violations_count"]

    return {
        "overall_score": overall_score,
        "passed": overall_passed,
        "total_violations": total_violations,
        "sections": {
            "post": post_qc,
            "first_comment": comment_qc,
            "carousel_script": carousel_qc,
        },
    }


# ==============================================================================
# SANITIZADOR DETERMINISTA HEURÍSTICO (PASO 1)
# ==============================================================================

# Saludos y muletillas de apertura, separados por idioma.
GREETINGS_ES = [
    r"^¡?Hola a todos[!\.,\s]*\n*",
    r"^¡?Hola red[!\.,\s]*\n*",
    r"^¡?Hola comunidad[!\.,\s]*\n*",
    r"^Espero que est[eé]n bien[!\.,\s]*\n*",
    r"^Hoy quiero compartir\s*(?:con ustedes)?\s*[:\.]?\s*\n*",
    r"^En el vertiginoso mundo\b.*?[,\.]\s*\n*",
    r"^En un mundo en constante (?:evolución|cambio)\b.*?[,\.]\s*\n*",
]

GREETINGS_EN = [
    r"^Hello network[!\.,\s]*\n*",
    r"^Hello everyone[!\.,\s]*\n*",
    r"^Hi everyone[!\.,\s]*\n*",
    r"^I am thrilled to announce\b.*?[,\.]\s*\n*",
    r"^I'm excited to share\b.*?[,\.]\s*\n*",
    r"^Excited to share\b.*?[,\.]\s*\n*",
    r"^In today's fast-paced\b.*?[,\.]\s*\n*",
]

# Reemplazos de vocabulario. Cada lista mantiene el idioma de destino: aplicar la
# lista española sobre un post en inglés (lo que hacía la versión anterior) producía
# textos mezclados como "this was a cambio relevante for the pipeline".
REPLACEMENTS_ES = [
    (r"(?i)\bun testimonio de\b", "una prueba de"),
    (r"(?i)\bmarca un hito\b", "representa un cambio"),
    (r"(?i)\bmarca un antes y un despu[eé]s\b", "cambió la forma en que lo hacíamos"),
    (r"(?i)\bdesempeña un papel crucial\b", "es necesario"),
    (r"(?i)\bde suma importancia\b", "importante"),
    (r"(?i)\bindeleble\b", "marcado"),
    (r"(?i)\bde manera fluida y sin fisuras\b", "sin bloqueos"),
    (r"(?i)\bsin fisuras\b", "limpio"),
    (r"(?i)\bgame[- ]changer\b", "cambio relevante"),
    (r"(?i)\brevolucionarias\b", "efectivas"),
    (r"(?i)\brevolucionarios\b", "efectivos"),
    (r"(?i)\brevolucionaria\b", "efectiva"),
    (r"(?i)\brevolucionario\b", "efectivo"),
    (r"(?i)\bintuitivas\b", "simples de usar"),
    (r"(?i)\bintuitivos\b", "simples de usar"),
    (r"(?i)\bintuitiva\b", "simple de usar"),
    (r"(?i)\bintuitivo\b", "simple de usar"),
    (r"(?i)\becosistema vibrante\b", "entorno activo"),
    (r"(?i)\belev[ao]r al siguiente nivel\b", "mejorar"),
    (r"(?i)\b(?:¡|!)?guard[aá] este post\b.*?[!\.]?\s*", ""),
    # Copywriting: Simple over complex & transiciones
    (r"(?i)\butilizar\b", "usar"),
    (r"(?i)\butilic[eé]\b", "usé"),
    (r"(?i)\butilizamos\b", "usamos"),
    (r"(?i)\bfacilitar\b", "ayudar"),
    (r"(?i)\bfacilita\b", "ayuda"),
    (r"(?i)\bcabe destacar que\b\s*", ""),
    (r"(?i)\bdicho esto,\s*", ""),
    (r"(?i)\ben conclusión,\s*", ""),
]

REPLACEMENTS_EN = [
    (r"(?i)\ba testament to\b", "proof of"),
    (r"(?i)\bpivotal moment\b", "turning point"),
    (r"(?i)\bplays a vital role\b", "is required"),
    (r"(?i)\bseamlessly\b", "smoothly"),
    (r"(?i)\bseamless\b", "clean"),
    (r"(?i)\bgame[- ]changer\b", "major improvement"),
    (r"(?i)\brevolutionary\b", "effective"),
    (r"(?i)\bdelve into\b", "examine"),
    (r"(?i)\bintuitive\b", "simple to use"),
    (r"(?i)\bvibrant ecosystem\b", "active ecosystem"),
    (r"(?i)\bevolving landscape\b", "tech stack"),
    (r"(?i)\bunlock the potential\b", "enable"),
    (r"(?i)\bsave this post\b.*?[!\.]?\s*", ""),
    # Copywriting: Simple over complex & transitions
    (r"(?i)\butilize\b", "use"),
    (r"(?i)\butilized\b", "used"),
    (r"(?i)\bfacilitate\b", "help"),
    (r"(?i)\bfacilitates\b", "helps"),
    (r"(?i)\bit's worth noting that\b\s*", ""),
    (r"(?i)\bthat being said,\s*", ""),
    (r"(?i)\bin conclusion,\s*", ""),
]


def _is_spanish(language: str) -> bool:
    return (language or "es").lower().startswith("es")


def sanitize_text_humanizer(text: str, language: str = "es") -> str:
    """Aplica transformaciones deterministas para erradicar slop sin alterar el contenido técnico.

    Los reemplazos se eligen según el idioma del texto: la versión anterior calculaba
    `patterns` por idioma y después nunca lo usaba, aplicando siempre una lista mixta.
    """
    if not text:
        return text

    cleaned = text
    spanish = _is_spanish(language)
    greetings = GREETINGS_ES if spanish else GREETINGS_EN
    replacements = REPLACEMENTS_ES if spanish else REPLACEMENTS_EN

    # 1. Eliminar saludos y aperturas de relleno
    for pattern in greetings:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.MULTILINE)

    # 2. Reemplazos de vocabulario en el idioma del texto
    for pattern, repl in replacements:
        cleaned = re.sub(pattern, repl, cleaned)

    # 3. El em-dash en exceso es una firma clásica de texto generado
    if cleaned.count("—") >= 3:
        cleaned = cleaned.replace("—", ",")

    # 4. Reducción de signos de exclamación múltiples o forzados (Copywriting Rule #79)
    cleaned = re.sub(r"[!¡]{2,}", ".", cleaned)

    return cleaned.strip()


# ==============================================================================
# RE-ESCRITURA CON LLM USANDO EL PROMPT DEL SKILL HUMANIZER Y COPYWRITING (PASO 2)
# ==============================================================================

HUMANIZER_REWRITE_SYSTEM = """
Sos un Senior Text Editor y Tech Lead especializado en des-artificializar textos técnicos y aplicar copywriting de conversión según las directrices de Humanizer y Copywriting.

TU MISIÓN:
Reescribir el texto provisto para eliminar cualquier rastro de lenguaje de IA, clichés o tono corporativo vacío, inyectando claridad persuasiva, autoridad técnica y voz humana auténtica.

REGLAS ESTRICTAS DE HUMANIZACIÓN Y COPYWRITING:
1. **CLARIDAD SOBRE INGENIO (CLARITY OVER CLEVERNESS)**: Si el lector tiene que descifrar la frase, se fue. Todo titular y punto clave debe pasar el test "Now you can..." (nombra una capacidad o resultado tangible).
2. **BENEFICIOS SOBRE CARACTERÍSTICAS**: No te limites a describir qué hace el código; explicá qué significa para el desarrollador, el rendimiento o la arquitectura.
3. **ELIMINAR SALUDOS Y MULETILLAS**: Ve directo al grano sin "Hola red", "Hoy quiero compartir...".
4. **ROMPER FÓRMULAS BINARIAS Y TRANSICIONES MECÁNICAS**: Prohibido "No se trata de X, sino de Y", "Cabe destacar que", "Dicho esto", "At its core". Afirma directamente.
5. **CERO TRÍADAS CLICHÉ NI BUZZWORDS**: Prohibido "rápido, escalable y robusto", "sin fisuras" (seamless), "game changer", "revolucionario". Usa datos, latencias o nombres concretos.
6. **VOZ EN PRIMERA PERSONA SINGULAR**: "Decidí", "Diseñé", "Me equivoqué al principio", "Lo que aprendí". Prohibido plurales corporativos ("decidimos") o voz pasiva ("se implementó").
7. **SEGURIDAD SOBRE DUDA (CONFIDENT OVER QUALIFIED)**: Eliminá calificadores débiles ("casi", "muy", "bastante", "realmente"). Los hechos y números hablan por sí solos.
8. **CERO SIGNOS DE EXCLAMACIÓN FORZADOS**: El copywriting profesional no grita. Eliminá los signos de exclamación para sostener tono senior sobrio.
9. **CALL TO ACTION (CTA) DE CONVERSIÓN CON VALOR**: Cero CTAs pasivos ("aprendé más", "hacé clic", "guardá este post"). Cerrá con la fórmula: [Verbo de Acción] + [Qué se debate o analiza] + [Pregunta técnica de trade-offs].
10. **PRESERVAR CONTENIDO TÉCNICO**: Conserva intactos los nombres de librerías, repositorios, números y comandos técnicos.
11. Devuelve ÚNICAMENTE el texto humanizado, sin preámbulos ni notas explicativas.
"""

def humanize_text_with_llm(
    text: str,
    violations_feedback: str = "",
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
    preferred_model: Optional[str] = None,
    language: str = "es",
) -> str:
    """Reescribe un texto utilizando un LLM con el sistema Humanizer cuando el QC detecta violaciones complejas."""
    if not text.strip():
        return text

    prompt = f"""
Por favor humaniza el siguiente texto técnico de LinkedIn. Elimina cualquier cliché de IA y patrones artificiales, asegurando voz en 1ª persona singular y autenticidad:

FEEDBACK ESPECÍFICO DEL CONTROL DE CALIDAD (QC):
{violations_feedback or 'Eliminar cualquier tono artificial o clichés corporativos.'}

TEXTO ORIGINAL A HUMANIZAR:
{text}
"""
    try:
        refined, _ = generate_llm_text(
            prompt=prompt,
            system_instruction=HUMANIZER_REWRITE_SYSTEM,
            temperature=0.25,
            provider=provider,
            model=preferred_model,
            api_key=api_key,
        )
        if refined and len(refined.strip()) > 30:
            return sanitize_text_humanizer(refined.strip(), language)
    except Exception as e:
        print(f"[WARN] Error durante re-escritura con Humanizer LLM: {e}")

    return sanitize_text_humanizer(text, language)


# ==============================================================================
# PIPELINE INTEGRAL: HUMANIZACIÓN OBLIGATORIA + GATE DE CONTROL DE CALIDAD
# ==============================================================================

def process_and_enforce_humanizer_qc(
    package: Dict[str, str],
    language: str = "es",
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
    preferred_model: Optional[str] = None,
) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """Pipeline obligatorio:
    1. Aplica sanitización determinista a cada sección del paquete.
    2. Ejecuta auditoría de QC basada en el skill Humanizer.
    3. Si alguna sección no supera el QC (score < 4.5), ejecuta re-escritura dirigida con LLM.
    4. Re-audita y emite el veredicto final.
    """
    refined_package = dict(package)

    # 1. Sanitización heurística determinista inicial en TODOS los textos
    for key in ["post", "first_comment", "carousel_script"]:
        if refined_package.get(key):
            refined_package[key] = sanitize_text_humanizer(refined_package[key], language)

    # 2. Auditoría de QC inicial
    qc_report = audit_full_package_qc(refined_package, language)
    score = qc_report["overall_score"]
    passed = qc_report["passed"]

    print(f"  • [HUMANIZER QC] Score Inicial: {score:.1f}/5.0 (Passed: {passed}, Violaciones: {qc_report['total_violations']})")

    # 3. Si no pasa el QC, auto-refinamiento con LLM
    if not passed:
        post_qc = qc_report["sections"]["post"]
        if not post_qc["passed"]:
            print("    [QC AUTO-REFINEMENT] Refinando post con Humanizer LLM...")
            feedback = "; ".join([v["pattern"] + " -> " + v["suggestion"] for v in post_qc["violations"]])
            refined_package["post"] = humanize_text_with_llm(
                refined_package["post"],
                violations_feedback=feedback,
                api_key=api_key,
                provider=provider,
                preferred_model=preferred_model,
                language=language,
            )

        # Re-auditar paquete final
        qc_report = audit_full_package_qc(refined_package, language)
        print(f"  • [HUMANIZER QC FINAL] Score: {qc_report['overall_score']:.1f}/5.0 (Passed: {qc_report['passed']})")
    else:
        print(f"    [QC APROBADO] Texto 100% humanizado, libre de AI slop y verificado en 1ª persona.")

    refined_package["humanizer_qc"] = qc_report
    return refined_package, qc_report
