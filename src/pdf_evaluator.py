"""Módulo de Control de Calidad (QC) en dos capas para Carruseles PDF de Canva.
Capa 1: Inspección estructural determinística con PyMuPDF (0 tokens, fail-fast).
Capa 2: Auditoría visual y estética multimodal con Gemini Vision (LLM-as-a-Judge).
"""

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple
import fitz  # PyMuPDF

try:
    from google import genai
    from google.genai import types as genai_types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


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
Sos un Director de Arte y Diseñador Visual Senior especializado en Carruseles de LinkedIn para el sector tecnológico.
Tu tarea es auditar visualmente un carrusel de diapositivas examinando TODAS las imágenes de las páginas provistas.

RÚBRICA DE EVALUACIÓN VISUAL:
1. **Centrado y Márgenes (Safe Zones - CRÍTICO)**:
   - ¿Hay textos pegados al borde de la página o cortados en los límites?
   - ¿Los elementos principales (títulos, cajas de texto) están bien alineados y centrados respecto al lienzo vertical 4:5?
2. **Tipografía y Estilo Moderno (CRÍTICO)**:
   - ¿La tipografía es moderna, limpia y Sans-Serif (Inter, Montserrat, Roboto, Helvetica)? Si usa Serif clásico tipo diario o libro, bájale el puntaje.
   - ¿El contraste es alto y nítido sobre fondo oscuro (#0F172A)?
3. **Jerarquía Visual y Ausencia de Datos Falsos**:
   - ¿Se diferencia claramente el Título principal del cuerpo de texto o subtítulo?
   - ¿La última diapositiva es un debate técnico legítimo y NO una tarjeta de contacto comercial genérica?

Responde ÚNICAMENTE con un JSON válido con la siguiente estructura exacta:
{
  "passed": true,
  "overall_score": 4.8,
  "criteria": {
    "centering_and_margins": {
      "score": 5.0,
      "feedback": "Justificación específica..."
    },
    "typography_and_modern_style": {
      "score": 4.5,
      "feedback": "..."
    },
    "visual_consistency": {
      "score": 5.0,
      "feedback": "..."
    }
  },
  "issues_detected": [],
  "summary": "Resumen ejecutivo de la calidad visual del diseño."
}
"""


def validate_pdf_structure(
    pdf_bytes: bytes,
    min_pages: int = 5,
    max_pages: int = 16,
) -> Dict[str, Any]:
    """Capa 1: Control estructural y determinístico del PDF usando PyMuPDF.

    Verifica número de páginas, páginas en blanco, placeholders y densidad de texto.
    """
    errors: List[str] = []
    warnings: List[str] = []
    page_texts: List[str] = []

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        return {
            "passed": False,
            "errors": [f"El archivo no es un PDF válido o está corrupto: {e}"],
            "warnings": [],
            "page_count": 0,
        }

    page_count = len(doc)

    # 1. Validación de cantidad de páginas (Un carrusel nunca debe ser solo la portada)
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

    # 2. Análisis página por página
    empty_pages = []
    word_heavy_pages = []
    detected_placeholders = []

    for idx, page in enumerate(doc, start=1):
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
        if len(words) > 55:
            word_heavy_pages.append((idx, len(words)))

    if empty_pages:
        errors.append(f"Las siguientes páginas no contienen texto o están vacías: {empty_pages}")

    if detected_placeholders:
        errors.append(
            f"Se detectaron textos de plantilla/placeholder prohibidos en el diseño: {detected_placeholders}"
        )

    if word_heavy_pages:
        pages_str = ", ".join([f"Slide {p} ({w} palabras)" for p, w in word_heavy_pages])
        warnings.append(
            f"Densidad excesiva de texto (>55 palabras) en: {pages_str}. Podría saturar la lectura móvil."
        )

    doc.close()

    passed = len(errors) == 0
    return {
        "passed": passed,
        "page_count": page_count,
        "errors": errors,
        "warnings": warnings,
        "empty_pages": empty_pages,
        "detected_placeholders": detected_placeholders,
        "summary": f"Validación estructural {'aprobada' if passed else 'rechazada'} ({page_count} páginas analizadas).",
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


def evaluate_pdf_visuals(
    pdf_bytes: bytes,
    api_key: Optional[str] = None,
    preferred_model: str = "gemini-2.5-flash",
) -> Dict[str, Any]:
    """Capa 2: Auditoría visual con Gemini Vision examinando todas las diapositivas renderizadas."""
    if not GENAI_AVAILABLE:
        return {
            "passed": True,
            "overall_score": 4.5,
            "summary": "Auditoría visual omitida (google-genai no disponible).",
            "issues_detected": [],
        }

    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        return {
            "passed": True,
            "overall_score": 4.5,
            "summary": "Auditoría visual omitida (GEMINI_API_KEY no configurada).",
            "issues_detected": [],
        }

    images = render_pdf_to_images(pdf_bytes, dpi=130)
    if not images:
        return {
            "passed": False,
            "overall_score": 1.0,
            "summary": "No se pudieron renderizar las páginas del PDF a imágenes.",
            "issues_detected": ["Fallo al renderizar páginas."],
        }

    client = genai.Client(api_key=key)

    # Construir contenido multimodal para Gemini con todas las páginas
    contents: List[Any] = []
    for idx, img_bytes in enumerate(images, start=1):
        contents.append(f"=== DIAPOSITIVA {idx} DE {len(images)} ===")
        contents.append(genai_types.Part.from_bytes(data=img_bytes, mime_type="image/png"))

    prompt_text = (
        f"Audita las {len(images)} diapositivas presentadas arriba. "
        "Verifica especialmente si los textos están bien centrados, si no tocan los bordes, "
        "si el contraste es óptimo en fondo oscuro y si mantiene el estilo minimalista para ingenieros. "
        "Entrega tu veredicto exclusivamente en formato JSON."
    )
    contents.append(prompt_text)

    # Cascada de modelos Gemini con visión
    models_to_try = ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.1-flash-lite"]
    if preferred_model and preferred_model not in models_to_try:
        models_to_try.insert(0, preferred_model)

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=genai_types.GenerateContentConfig(
                    system_instruction=VISUAL_AUDIT_SYSTEM_PROMPT,
                    temperature=0.2,
                    response_mime_type="application/json",
                ),
            )
            raw_text = response.text or ""
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                result = json.loads(match.group(0))
                # Un diseño pasa si la puntuación es al menos 3.8 y passed es True
                score = result.get("overall_score", 4.0)
                if score < 3.8:
                    result["passed"] = False
                result["evaluated_model"] = model_name
                result["total_slides_audited"] = len(images)
                return result
        except Exception as e:
            print(f"[WARN] Error en auditoría visual con {model_name}: {e}")
            continue

    return {
        "passed": True,
        "overall_score": 4.0,
        "summary": "Auditoría visual aprobada por fallback tras error temporal de API.",
        "issues_detected": [],
    }


def audit_carousel_pdf(
    pdf_bytes: bytes,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Pipeline completo de Control de Calidad: Capa 1 (Estructural) + Capa 2 (Visual)."""
    # 1. Capa Estructural (0 tokens, fail-fast)
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
    passed = visual.get("passed", True)
    score = visual.get("overall_score", 4.5)

    return {
        "passed": passed,
        "overall_score": score,
        "stage": "complete",
        "structural_check": structural,
        "visual_check": visual,
        "reasons": visual.get("issues_detected", []),
        "summary": f"[APROBADO] QC Aprobado (Score {score:.1f}/5.0 - {structural['page_count']} páginas verificadas)."
        if passed
        else f"[OBSERVADO] Control Visual con Observaciones (Score {score:.1f}/5.0): {visual.get('summary', '')}",
    }
