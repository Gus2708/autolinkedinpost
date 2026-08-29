"""Módulo de Control de Calidad (QC) en dos capas para Carruseles PDF Nativos.
Capa 1: Inspección estructural determinística con PyMuPDF (0 tokens, fail-fast).
Capa 2: Auditoría visual y estética multimodal con Gemini Vision (LLM-as-a-Judge).
"""

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple
try:
    import pymupdf as fitz
except ImportError:
    import fitz

try:
    from google import genai  # noqa: F401  (sólo para detectar disponibilidad)
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from src.llm_client import (
    PROVIDER_API_KEY_ENV,
    detect_provider,
    extract_json_object,
    generate_llm_vision,
)


FORBIDDEN_PLACEHOLDERS = [
    "reallygreatsite.com",
    "really great site",
    "lorem ipsum",
    "dolor sit amet",
    "yourwebsite.com",
    "sample text",
    "placeholder",
]

VISUAL_AUDIT_SYSTEM_PROMPT = """
Sos un Director de Arte y Lead Design Engineer con el estándar de calidad de Emil Kowalski (Vercel, Linear) y las directrices de UI UX Pro Max.
Tu tarea es auditar visualmente un carrusel de diapositivas de LinkedIn examinando rigurosamente TODAS las imágenes provistas.

RÚBRICA DE EVALUACIÓN VISUAL Y DE INGENIERÍA:
1. **Respiración Visual y Safe Zones (CRÍTICO - Emil Kowalski Craft)**:
   - ¿El contenido respira con elegancia o se ve apretado/hacinado?
   - ¿Hay textos o cajas pegadas o invadiendo el pie de página ("Deslizá ➔") o el encabezado?
   - El contenido debe ocupar entre el 65% y el 75% del alto útil, dejando márgenes seguros y limpios.
2. **Coherencia Cromática del Lienzo (CRÍTICO - UI UX Pro Max)**:
   - ¿Todas las diapositivas del carrusel comparten el MISMO color de fondo y atmósfera visual?
   - PROHIBIDO saltar de fondo blanco a rosa, durazno o azul entre láminas de la misma publicación.
   - Contraste accesible WCAG mínimo 4.5:1 en todos los textos sobre sus tarjetas y fondos.
3. **Jerarquía Tipográfica y Sutileza de Materiales**:
   - Título dominante con tracking negativo compacto (-0.03em a -0.04em) e interlineado ceñido.
   - Distinción nítida entre Título > Párrafo contextual > Viñetas técnicas.
   - Tarjetas con bordes sutiles semi-translúcidos y sombras multicapa suaves (sin bordes toscos opacos).
4. **Autonomía del Contenido (Micro-ensayo Autosuficiente)**:
   - ¿El carrusel habla por sí solo? ¿Las láminas ofrecen contexto y sustancia técnica real o parecen notas telegráficas de una charla oral?
5. **Ausencia de Marcos Toscos y Cuadros de Color (CRÍTICO - Craft Emil Kowalski)**:
   - ¿Las tarjetas tienen marcos o bordes gruesos de colores llamativos (ej: cuadros azules, cyan, verdes o halos saturados alrededor del texto)?
   - REPRUEBA INMEDIATAMENTE cualquier diseño con bordes gruesos o cuadros de color estilo alerta/callout. Las tarjetas deben ser sutiles, con bordes ultra-delgados (hairline 1px) semi-traslúcidos y sombras neutras.
6. **Integridad de Iconos Lucide (CRÍTICO)**:
   - ¿Cada diapositiva tiene su icono correspondiente y visible en el badge superior y en las viñetas?
   - Si algún badge o viñeta carece de icono o muestra un hueco vacío: REPRUEBA INMEDIATAMENTE ("passed": false, score <= 3.0, "issues_detected": ["Icono ausente"]).
7. **Cajas Vacías o Contenedores sin Contenido (CRÍTICO - TOLERANCIA CERO)**:
   - ¿Alguna lámina muestra una tarjeta, caja o contenedor rectangular SIN texto adentro?
   - Un rectángulo de fondo distinto al lienzo, sin una sola palabra dentro, es un defecto de render, no una decisión de diseño: delata un contenedor que se dibujó sin contenido.
   - Revisá especialmente la portada y la lámina de cierre, donde el guion suele traer sólo un título.
   - Si detectás una sola caja vacía: REPRUEBA INMEDIATAMENTE ("passed": false, score <= 2.5, "issues_detected": ["Tarjeta vacía sin contenido en la lámina N"]).

8. **Limpieza del Lienzo y Ausencia Total de Sombras/Cajas Parásitas (TOLERANCIA CERO)**:
   - ¿Se observa cualquier línea horizontal o vertical divisoria, halo rectangular, o caja opaca/sombra detrás o alrededor de las tarjetas de contenido?
   - Los visores móviles de PDF (iOS PDFKit y Android) revelan artefactos de recorte rectangular cuando hay sombras o backdrop-filter.
   - Si se detecta el menor indicio de caja parásita, corte de fondo o halo rectangular alrededor de la tarjeta: REPRUEBA INMEDIATAMENTE ("passed": false, score <= 2.5, "issues_detected": ["Artefacto de sombra o caja rectangular parásita"]).

Responde ÚNICAMENTE con un JSON válido con la siguiente estructura exacta:
{
  "passed": true,
  "overall_score": 4.9,
  "criteria": {
    "breathing_room_and_safe_zones": {
      "score": 5.0,
      "feedback": "Justificación específica..."
    },
    "canvas_color_cohesion": {
      "score": 5.0,
      "feedback": "..."
    },
    "typography_and_materials": {
      "score": 4.8,
      "feedback": "..."
    },
    "content_autonomy": {
      "score": 4.9,
      "feedback": "..."
    }
  },
  "summary": "Resumen ejecutivo del veredicto visual y craft.",
  "issues_detected": [],
  "needs_repair": false,
  "suggested_repair": null
}
"""


def validate_pdf_structure(
    pdf_bytes: bytes,
    min_pages: int = 5,
    max_pages: int = 16,
) -> Dict[str, Any]:
    """Capa 1: Control estructural determinístico avanzado con PyMuPDF (0 tokens).

    Verifica número de páginas, relación de aspecto 4:5, páginas vacías, placeholders prohibidos,
    safe-zones y colisiones contra header/footer, consistencia de color de fondo y densidad tipográfica.
    """
    errors: List[str] = []
    warnings: List[str] = []
    page_texts: List[str] = []
    repair_actions: List[str] = []

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        return {
            "passed": False,
            "errors": [f"El archivo no es un PDF válido o está corrupto: {e}"],
            "warnings": [],
            "page_count": 0,
            "needs_repair": False,
            "repair_actions": [],
        }

    page_count = len(doc)

    # 1. Validación de cantidad de páginas
    if page_count < min_pages:
        errors.append(
            f"El carrusel tiene solo {page_count} página(s). Se requieren al menos {min_pages} páginas completas."
        )
    elif page_count > max_pages:
        warnings.append(
            f"El carrusel tiene {page_count} páginas, lo que excede el rango óptimo de {max_pages} slides."
        )

    # 2. Comprobación de relación de aspecto (Debe ser vertical 4:5 ~ 0.80, no apaisado)
    if page_count > 0:
        first_page = doc[0]
        w, h = first_page.rect.width, first_page.rect.height
        if h > 0:
            aspect_ratio = w / h
            if aspect_ratio > 0.95:
                warnings.append(
                    f"El formato del carrusel es horizontal ({w:.0f}x{h:.0f}, ratio {aspect_ratio:.2f}) en vez de vertical 4:5 (~0.80) para consumo móvil."
                )

    # 3. Análisis página por página
    empty_pages = []
    word_heavy_pages = []
    telegraphic_pages = []
    detected_placeholders = []
    footer_collisions = []
    header_collisions = []
    bg_colors = []

    for idx, page in enumerate(doc, start=1):
        h = page.rect.height
        text = page.get_text().strip()
        page_texts.append(text)

        if not text:
            empty_pages.append(idx)
            continue

        text_lower = text.lower()
        for placeholder in FORBIDDEN_PLACEHOLDERS:
            if placeholder in text_lower and placeholder not in detected_placeholders:
                detected_placeholders.append(placeholder)

        words = text.split()
        if len(words) > 85:
            word_heavy_pages.append((idx, len(words)))
        elif 1 < idx < page_count and len(words) < 16:
            telegraphic_pages.append((idx, len(words)))

        # Safe-Zones y colisiones con header y footer (Craft Emil Kowalski / Apple Design)
        blocks = page.get_text("blocks")
        for b in blocks:
            x0, y0, x1, y1, b_text = b[0], b[1], b[2], b[3], b[4].strip()
            if not b_text:
                continue
            b_lower = b_text.lower()
            is_footer = any(w in b_lower for w in ["tech lead", "desliz", "comentario", "opinión", "software engineer", "github/"])
            is_header = bool(re.search(r"\b\d{1,2}\s*/\s*\d{1,2}\b", b_text))

            # Colisión con pie de página inferior (Safe threshold: 88.5% de altura)
            if not is_footer and y1 > 0.885 * h:
                footer_collisions.append((idx, f"Slide {idx}: Texto termina a {y1/h*100:.1f}% de la altura, invadiendo el footer"))

            # Colisión con encabezado superior (Safe threshold: 11% de altura)
            if not is_header and y0 < 0.11 * h:
                header_collisions.append((idx, f"Slide {idx}: Texto inicia a {y0/h*100:.1f}% de la altura, colisionando con el header"))

        # Muestreo de color de fondo en esquina para validar coherencia cromática
        try:
            pix = page.get_pixmap(dpi=36)
            pixel_corner = pix.pixel(10, 10)
            bg_colors.append(pixel_corner[:3])
        except Exception:
            pass

    if empty_pages:
        errors.append(f"Las siguientes páginas no contienen texto o están vacías: {empty_pages}")

    if detected_placeholders:
        errors.append(
            f"Se detectaron textos de plantilla/placeholder prohibidos en el diseño: {detected_placeholders}"
        )

    if footer_collisions:
        errors.append(
            f"Desborde tipográfico detectado en {len(footer_collisions)} lámina(s) que colisiona con el pie de página: "
            + "; ".join([c[1] for c in footer_collisions[:3]])
        )
        repair_actions.append("reduce_scale")

    if header_collisions:
        warnings.append(
            f"Proximidad excesiva con el encabezado en {len(header_collisions)} lámina(s)."
        )

    # Comprobación de coherencia cromática de fondo entre láminas (UI UX Pro Max)
    # Detecta saltos discordantes (ej: blanco a rosa o claro a oscuro) sin penalizar gradientes orgánicos WebGL
    color_jumps = []
    if len(bg_colors) > 1:
        base_rgb = bg_colors[0]
        base_lum = 0.299 * base_rgb[0] + 0.587 * base_rgb[1] + 0.114 * base_rgb[2]
        for i, c in enumerate(bg_colors[1:], start=2):
            c_lum = 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
            lum_diff = abs(base_lum - c_lum)
            total_diff = abs(base_rgb[0] - c[0]) + abs(base_rgb[1] - c[1]) + abs(base_rgb[2] - c[2])
            if lum_diff > 85 or total_diff > 200:
                color_jumps.append((i, f"Slide {i} salta de RGB{base_rgb} a RGB{c} (diferencia {total_diff:.0f})"))

    if color_jumps:
        errors.append(
            f"Inconsistencia cromática en el fondo: diapositivas alternan colores no armónicos ({'; '.join([c[1] for c in color_jumps[:2]])})."
        )
        repair_actions.append("unify_palette")

    if word_heavy_pages:
        pages_str = ", ".join([f"Slide {p} ({w} palabras)" for p, w in word_heavy_pages])
        warnings.append(
            f"Hacinamiento excesivo (>85 palabras) en: {pages_str}. Podría saturar la lectura móvil."
        )

    if telegraphic_pages:
        pages_str = ", ".join([f"Slide {p} ({w} palabras)" for p, w in telegraphic_pages])
        warnings.append(
            f"Contenido telegráfico insuficiente (<16 palabras) en: {pages_str}. Las láminas deben ser autónomas."
        )

    doc.close()

    passed = len(errors) == 0
    needs_repair = len(repair_actions) > 0 or not passed

    return {
        "passed": passed,
        "page_count": page_count,
        "errors": errors,
        "warnings": warnings,
        "empty_pages": empty_pages,
        "detected_placeholders": detected_placeholders,
        "footer_collisions": footer_collisions,
        "color_jumps": color_jumps,
        "needs_repair": needs_repair,
        "repair_actions": repair_actions,
        "summary": f"Validación estructural {'aprobada' if passed else 'rechazada'} ({page_count} páginas analizadas, {len(footer_collisions)} colisiones, {len(color_jumps)} saltos cromáticos).",
    }


# DPI de las imágenes que se mandan al juez visual. Las láminas son de 1080x1350 px:
# 100 DPI alcanza de sobra para juzgar composición, contraste y safe-zones, y recorta
# el peso de cada request frente a los 130 anteriores.
VISUAL_AUDIT_DPI = 100


def _skipped_visual_audit(reason: str) -> Dict[str, Any]:
    """Resultado para cuando la capa visual no puede correr.

    Marca 'evaluated: False' para que el llamador distinga "el diseño está bien" de
    "nadie lo miró", en lugar de propagar un aprobado sintético.
    """
    print(f"[WARN] Auditoría visual del carrusel omitida: {reason}.")
    return {
        "passed": True,
        "evaluated": False,
        "overall_score": 0.0,
        "summary": f"Auditoría visual omitida ({reason}). Sólo se validó la capa estructural.",
        "issues_detected": [],
    }


def render_pdf_to_images(
    pdf_bytes: bytes,
    dpi: int = 150,
) -> List[bytes]:
    """Renderiza todas las páginas de un PDF en bytes a imágenes PNG en memoria."""
    images = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        images.append(pix.tobytes("png"))
    doc.close()
    return images


def _has_vision_credentials(provider: str) -> Tuple[bool, str]:
    """Comprueba que el proveedor tenga con qué correr la auditoría visual."""
    prov = (provider or "").strip().lower()
    if prov == "gemini":
        if not GENAI_AVAILABLE:
            return False, "google-genai no está instalado"
        if not os.getenv("GEMINI_API_KEY"):
            return False, "GEMINI_API_KEY no está configurada"
        return True, ""

    env_var = PROVIDER_API_KEY_ENV.get(prov)
    if env_var and not os.getenv(env_var):
        return False, f"{env_var} no está configurada para el proveedor '{prov}'"
    return True, ""


def evaluate_pdf_visuals(
    pdf_bytes: bytes,
    api_key: Optional[str] = None,
    preferred_model: Optional[str] = None,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Capa 2: auditoría visual multimodal de todas las diapositivas renderizadas.

    Corre sobre el cliente unificado, así que funciona con cualquier proveedor que
    exponga un endpoint multimodal compatible con OpenAI (OpenRouter, OpenAI) además
    del SDK nativo de Gemini. Antes estaba atada a Google: con otro proveedor
    configurado, esta capa sencillamente no se ejecutaba.
    """
    prov = (provider or detect_provider()).strip().lower()

    ok, motivo = _has_vision_credentials(prov)
    if not ok:
        return _skipped_visual_audit(motivo)

    images = render_pdf_to_images(pdf_bytes, dpi=VISUAL_AUDIT_DPI)
    if not images:
        return {
            "passed": False,
            "evaluated": True,
            "overall_score": 1.0,
            "summary": "No se pudieron renderizar las páginas del PDF a imágenes.",
            "issues_detected": ["Fallo al renderizar páginas."],
        }

    prompt_text = (
        f"Audita las {len(images)} diapositivas presentadas arriba. "
        "Verifica especialmente si los textos están bien centrados, si no tocan los bordes, "
        "si el contraste es óptimo sobre el fondo y si mantiene el estilo minimalista para ingenieros. "
        "Entrega tu veredicto exclusivamente en formato JSON."
    )

    raw_text, used_model = generate_llm_vision(
        prompt=prompt_text,
        images=images,
        system_instruction=VISUAL_AUDIT_SYSTEM_PROMPT,
        temperature=0.2,
        provider=prov,
        model=preferred_model,
        api_key=api_key,
        json_response=True,
    )

    if not raw_text:
        return {
            "passed": False,
            "evaluated": False,
            "overall_score": 0.0,
            "summary": "Auditoría visual no completada: ningún modelo de visión respondió.",
            "issues_detected": [f"Sin respuesta del proveedor '{prov}'"],
        }

    result = extract_json_object(raw_text)
    if result is None:
        preview = raw_text[:120].replace("\n", " ")
        print(f"[WARN] El juez visual no devolvió JSON parseable. Respuesta: {preview!r}")
        return {
            "passed": False,
            "evaluated": False,
            "overall_score": 0.0,
            "summary": "Auditoría visual no completada: el veredicto no vino en JSON válido.",
            "issues_detected": ["Respuesta del juez visual sin JSON"],
        }

    # Un diseño pasa rigurosamente si la puntuación es al menos 4.5.
    try:
        score = float(result.get("overall_score", 0.0))
    except (TypeError, ValueError):
        score = 0.0
    result["overall_score"] = score
    if score < 4.5:
        result["passed"] = False
    result.setdefault("passed", True)

    result["evaluated"] = True
    result["evaluated_model"] = used_model
    result["total_slides_audited"] = len(images)
    return result


def summarize_qc_issues(qc_result: Dict[str, Any], max_len: int = 200) -> str:
    """Construye un motivo legible de por qué el QC quedó observado.

    El juez devuelve cuatro scores por criterio y una lista de problemas detectados,
    pero el pipeline sólo propagaba el número agregado. Un badge "⚠️ 3.8/5.0" sin
    explicación no es accionable: el lector no sabe si mirar el texto, los márgenes
    o los iconos.

    Prioriza lo más concreto: errores estructurales, después problemas visuales
    puntuales, después el criterio peor puntuado y por último el resumen.
    """
    if not qc_result:
        return ""

    # 1. Errores estructurales: son deterministas y muy específicos.
    errores = (qc_result.get("structural_check") or {}).get("errors") or []
    if errores:
        return _truncate("; ".join(errores), max_len)

    visual = qc_result.get("visual_check") or {}

    # 2. Problemas concretos que enumeró el juez visual.
    issues = [str(i).strip() for i in (visual.get("issues_detected") or []) if str(i).strip()]
    if issues:
        return _truncate("; ".join(issues), max_len)

    # 3. El criterio peor puntuado, con su justificación.
    criterios = visual.get("criteria") or {}
    peores = [
        (v.get("score"), k, v.get("feedback") or "")
        for k, v in criterios.items()
        if isinstance(v, dict) and isinstance(v.get("score"), (int, float))
    ]
    if peores:
        score, nombre, feedback = min(peores, key=lambda x: x[0])
        etiqueta = CRITERIA_LABELS.get(nombre, nombre.replace("_", " "))
        detalle = f"{etiqueta} ({score}/5.0)"
        if feedback:
            detalle += f": {feedback}"
        return _truncate(detalle, max_len)

    # 4. Último recurso: el resumen ejecutivo.
    return _truncate(visual.get("summary") or qc_result.get("summary") or "", max_len)


def _truncate(texto: str, max_len: int) -> str:
    """Recorta en el límite de palabra para no cortar a mitad de una."""
    texto = " ".join(texto.split())
    if len(texto) <= max_len:
        return texto
    corte = texto[:max_len].rsplit(" ", 1)[0]
    return corte + "…"


# Nombres legibles de los criterios de la rúbrica visual.
CRITERIA_LABELS = {
    "breathing_room_and_safe_zones": "Respiración y safe-zones",
    "canvas_color_cohesion": "Coherencia cromática",
    "typography_and_materials": "Tipografía y materiales",
    "content_autonomy": "Autonomía del contenido",
}


def audit_carousel_pdf(
    pdf_bytes: bytes,
    api_key: Optional[str] = None,
    structural: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Pipeline completo de Control de Calidad: Capa 1 (Estructural) + Capa 2 (Visual).

    `structural` permite reutilizar un análisis ya hecho por el llamador y evitar
    volver a abrir y recorrer el PDF entero.
    """
    # 1. Capa Estructural (0 tokens, fail-fast)
    if structural is None:
        structural = validate_pdf_structure(pdf_bytes)
    if not structural["passed"]:
        return {
            "passed": False,
            "overall_score": 2.0,
            "stage": "structural",
            "structural_check": structural,
            "visual_check": None,
            "reasons": structural["errors"],
            "summary": f"[RECHAZADO] Control Estructural Fallido: {'; '.join(structural['errors'])}",
        }

    # 2. Capa Visual con Gemini Multimodal (Audita TODAS las páginas)
    visual = evaluate_pdf_visuals(pdf_bytes, api_key=api_key)
    visual_ran = visual.get("evaluated", True)
    passed = visual.get("passed", True)
    score = visual.get("overall_score", 0.0)
    pages = structural["page_count"]

    if not visual_ran:
        # Sin auditoría visual sólo podemos afirmar lo que verificó la capa estructural.
        return {
            "passed": True,
            "overall_score": 0.0,
            "visual_audited": False,
            "stage": "structural_only",
            "structural_check": structural,
            "visual_check": visual,
            "reasons": [],
            "summary": f"[ESTRUCTURAL] {pages} páginas validadas sin auditoría visual: {visual.get('summary', '')}",
        }

    return {
        "passed": passed,
        "overall_score": score,
        "visual_audited": True,
        "stage": "complete",
        "structural_check": structural,
        "visual_check": visual,
        "reasons": visual.get("issues_detected", []),
        "summary": f"[APROBADO] QC Aprobado (Score {score:.1f}/5.0 - {pages} páginas verificadas)."
        if passed
        else f"[OBSERVADO] Control Visual con Observaciones (Score {score:.1f}/5.0): {visual.get('summary', '')}",
    }
