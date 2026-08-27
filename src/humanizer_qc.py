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
    patterns = SLOP_PATTERNS_ES if language.lower().startswith("es") else SLOP_PATTERNS_EN

    # 1. Detección de patrones de slop
    for regex, pattern_name, suggestion in patterns:
        for match in re.finditer(regex, text):
            start = max(0, match.start() - 25)
            end = min(len(text), match.end() + 25)
            snippet = text[start:end].replace("\n", " ").strip()
            violations.append({
                "pattern": pattern_name,
                "snippet": f"...{snippet}...",
                "suggestion": suggestion,
            })

    # 2. Detección de sobreuso de em-dash (—)
    em_dash_count = text.count("—") + text.count("–")
    if em_dash_count >= 3:
        violations.append({
            "pattern": f"Sobreuso de rayas em-dash ({em_dash_count} encontradas)",
            "snippet": "Uso excesivo de '—' típico de redactores de IA",
            "suggestion": "Reemplazar por comas o separar en oraciones cortas",
        })

    # 3. Detección de plural corporativo / pérdida de primera persona
    plural_voice_detected = False
    if language.lower().startswith("es"):
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

    # Cálculo del score (base 5.0, resta 0.5 por cada patrón crítico)
    total_violations = len(violations)
    penalty = min(total_violations * 0.5, 4.0)
    score = round(max(1.0, 5.0 - penalty), 1)
    passed = (score >= 4.5 and not plural_voice_detected)

    return {
        "score": score,
        "passed": passed,
        "violations_count": total_violations,
        "violations": violations,
        "em_dash_count": em_dash_count,
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
    overall_passed = post_qc["passed"] and carousel_qc["passed"] and (comment_qc["score"] >= 4.0)
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

def sanitize_text_humanizer(text: str, language: str = "es") -> str:
    """Aplica transformaciones deterministas para erradicar slop común sin alterar el contenido técnico."""
    if not text:
        return text

    cleaned = text
    patterns = SLOP_PATTERNS_ES if language.lower().startswith("es") else SLOP_PATTERNS_EN

    # 1. Eliminar saludos iniciales
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

    # 2. Reemplazos directos de vocabulario
    replacements = [
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

    for pattern, repl in replacements:
        cleaned = re.sub(pattern, repl, cleaned)

    if cleaned.count("—") >= 3:
        cleaned = cleaned.replace("—", ",")

    return cleaned.strip()


# ==============================================================================
# RE-ESCRITURA CON LLM USANDO EL PROMPT DEL SKILL HUMANIZER (PASO 2)
# ==============================================================================

HUMANIZER_REWRITE_SYSTEM = """
Sos un Senior Text Editor y Tech Lead especializado en des-artificializar y humanizar textos técnicos generados por IA, siguiendo la guía WikiProject AI Cleanup y el skill Humanizer.

TU MISIÓN:
Reescribir el texto provisto para eliminar cualquier rastro de lenguaje de IA, clichés o tono corporativo vacío, inyectándole voz humana, natural y honesta.

REGLAS ESTRICTAS DE HUMANIZACIÓN:
1. **ELIMINAR SALUDOS Y MULETILLAS**: Ve directo al grano sin "Hola red", "Hoy quiero compartir...".
2. **ROMPER FÓRMULAS BINARIAS**: Prohibido "No se trata de X, sino de Y". Afirma directamente.
3. **CERO TRÍADAS CLICHÉ**: Prohibido "rápido, escalable y robusto". Usa detalles concretos.
4. **CERO VOCABULARIO DE IA**: Prohibido "un testimonio de", "sin fisuras" (seamless), "game changer", "crucial", "fundamental", "vital", "panorama".
5. **VOZ EN PRIMERA PERSONA SINGULAR**: "Decidí", "Diseñé", "Me equivoqué al principio", "Lo que aprendí". Prohibido plurales ("decidimos") o voz pasiva ("se implementó").
6. **RITMO Y MATIZ**: Mezcla frases cortas contundentes con oraciones explicativas. Admite complejidades y trade-offs reales de producción.
7. **PRESERVAR CONTENIDO TÉCNICO**: Conserva intactos los nombres de librerías, repositorios, números y comandos técnicos.
8. Devuelve ÚNICAMENTE el texto humanizado, sin preámbulos ni notas explicativas.
"""

def humanize_text_with_llm(
    text: str,
    violations_feedback: str = "",
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
    preferred_model: Optional[str] = None,
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
            return sanitize_text_humanizer(refined.strip())
    except Exception as e:
        print(f"[WARN] Error durante re-escritura con Humanizer LLM: {e}")

    return sanitize_text_humanizer(text)


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
            )

        # Re-auditar paquete final
        qc_report = audit_full_package_qc(refined_package, language)
        print(f"  • [HUMANIZER QC FINAL] Score: {qc_report['overall_score']:.1f}/5.0 (Passed: {qc_report['passed']})")
    else:
        print(f"    [QC APROBADO] Texto 100% humanizado, libre de AI slop y verificado en 1ª persona.")

    refined_package["humanizer_qc"] = qc_report
    return refined_package, qc_report
