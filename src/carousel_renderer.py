"""Módulo de renderizado nativo HTML/CSS a PDF para carruseles de LinkedIn e Instagram.

Genera carruseles multipágina de altísima calidad visual (1080x1350 px, formato 4:5 vertical)
utilizando HTML5, CSS Flexbox moderno, Google Fonts y Playwright Chromium.
Genera PDFs vectoriales nativos de alto impacto de forma 100% local y determinística.
"""

import html
import io
import json
import os
import re
import traceback
from typing import Any, Dict, List, Optional, Tuple

try:
    import pymupdf as fitz
except ImportError:
    import fitz
from PIL import Image
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

from src.pdf_evaluator import (
    CRITERIA_LABELS,
    audit_carousel_pdf,
    summarize_qc_issues,
    validate_pdf_structure,
)
from src.design_systems import DesignSystem, get_rotating_system, get_system_by_id


# Textos de la plantilla del carrusel por idioma. El renderer los tenía en duro en
# español, así que --lang en producía un post en inglés con un PDF en español.
CAROUSEL_STRINGS = {
    "es": {
        "cover_category": "{project} • Arquitectura",
        "mid_category": "Arquitectura Técnica",
        "last_category": "Conclusiones & Debate",
        "swipe": "Deslizá ➔",
        "swipe_last": "Dejá tu comentario 💬",
        "cta_box": "Dejá tu opinión o caso en comentarios",
        "html_lang": "es",
    },
    "en": {
        "cover_category": "{project} • Architecture",
        "mid_category": "Technical Architecture",
        "last_category": "Takeaways & Discussion",
        "swipe": "Swipe ➔",
        "swipe_last": "Leave a comment 💬",
        "cta_box": "Share your take or your own case in the comments",
        "html_lang": "en",
    },
}


def get_carousel_strings(language: str) -> Dict[str, str]:
    """Devuelve los textos de plantilla del carrusel para el idioma pedido (es por defecto)."""
    key = "en" if (language or "").lower().startswith("en") else "es"
    return CAROUSEL_STRINGS[key]


# ==============================================================================
# LIMPIEZA DE MARKDOWN
# ==============================================================================
# Los modelos devuelven el guion con sintaxis Markdown. Sin este tratamiento, los
# '##', '>', '**' y backticks viajaban crudos hasta el PDF y se imprimían en las
# láminas. En vez de borrarlos, el marcado inline se convierte a HTML real para
# conservar el énfasis que el modelo quiso dar.

# Prefijos de bloque: encabezados y citas, en cualquier combinación.
_MD_BLOCK_PREFIX_RE = re.compile(r"^\s*(?:#{1,6}\s+|>\s*)+")

# Marcado inline. El orden de aplicación importa: negrita antes que cursiva,
# porque '**' contiene '*'.
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_MD_CODE_RE = re.compile(r"`([^`\n]+)`")
_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")
_MD_STRIKE_RE = re.compile(r"~~(.+?)~~")
# La cursiva de Markdown no admite espacios pegados a los delimitadores: sin esa
# guarda, una multiplicación como "3 * 4 * 5" se convertía en "3 <em> 4 </em> 5".
_MD_ITALIC_RE = re.compile(
    r"(?<![\w*])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![\w*])"
    r"|(?<![\w_])_(?!\s)([^_\n]+?)(?<!\s)_(?![\w_])"
)

# Separador de tags para no re-procesar el interior del marcado ya generado.
_HTML_TAG_SPLIT_RE = re.compile(r"(<[^>]+>)")


# Reglas horizontales de Markdown: '---', '***', '___' con tres o más caracteres.
# El modelo las intercala entre secciones y sobrevivían al parseo, imprimiéndose
# como guiones sueltos en la lámina.
_MD_HORIZONTAL_RULE_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")


def is_horizontal_rule(line: str) -> bool:
    """Indica si la línea es sólo un separador de Markdown, sin contenido."""
    return bool(_MD_HORIZONTAL_RULE_RE.match(line or ""))


# Etiquetas de estructura que el modelo emite en línea propia ("TÍTULO:",
# "CONTENIDO:", "SUBTÍTULO:"). No son contenido: rotulan lo que viene después.
# Sin filtrarlas, la primera línea del bloque —que es la etiqueta— terminaba
# impresa como título de la lámina.
_STRUCTURE_LABEL_RE = re.compile(
    r"^\s*\**\s*(?:"
    r"T[ÍI]TULO(?:\s+(?:PORTADA|PRINCIPAL|DE\s+PORTADA))?|SUBT[ÍI]TULO|"
    r"CONTENIDO|CUERPO|TEXTO|DESCRIPCI[ÓO]N|VI[ÑN]ETAS|BULLETS|"
    r"TITLE|SUBTITLE|CONTENT|BODY|"
    r"PORTADA|COVER|CTA|CIERRE|CONCLUSI[ÓO]N"
    r")\s*:\s*\**\s*$",
    re.IGNORECASE,
)


# El mismo vocabulario, para cuando el rótulo llega en mayúsculas y sin dos puntos.
_BARE_LABEL_RE = re.compile(
    r"(?:"
    r"T[ÍI]TULO(?:\s+(?:PORTADA|PRINCIPAL|DE\s+PORTADA))?|SUBT[ÍI]TULO|"
    r"CONTENIDO|CUERPO|TEXTO|DESCRIPCI[ÓO]N|VI[ÑN]ETAS|BULLETS|"
    r"TITLE|SUBTITLE|CONTENT|BODY|"
    r"PORTADA|COVER|CTA|CIERRE|CONCLUSI[ÓO]N"
    r")",
    re.IGNORECASE,
)


def is_structure_label(line: str) -> bool:
    """Indica si la línea es sólo un rótulo de estructura, sin contenido propio.

    Con dos puntos alcanza para reconocerlo ("TÍTULO:"). Sin ellos se exige además
    que venga en mayúsculas: así "PORTADA" se descarta como rótulo mientras que
    "Titulo", que puede ser el título real de una lámina, se conserva.
    """
    limpio = (line or "").strip()
    if not limpio:
        return False
    if _STRUCTURE_LABEL_RE.match(limpio):
        return True
    sin_marcado = limpio.strip("*_ ").rstrip(":").strip()
    return bool(
        sin_marcado
        and sin_marcado.isupper()
        and _BARE_LABEL_RE.fullmatch(sin_marcado)
    )


# El mismo rótulo pero como prefijo de una línea que sí trae texto
# ("TÍTULO PORTADA: Debuggeando un bot" -> "Debuggeando un bot").
_STRUCTURE_LABEL_PREFIX_RE = re.compile(
    r"^\s*\**\s*(?:"
    r"T[ÍI]TULO(?:\s+(?:PORTADA|PRINCIPAL|DE\s+PORTADA))?|SUBT[ÍI]TULO|"
    r"CONTENIDO|CUERPO|TEXTO|DESCRIPCI[ÓO]N|VI[ÑN]ETAS|BULLETS|"
    r"TITLE|SUBTITLE|CONTENT|BODY|"
    r"PORTADA|COVER|CTA|SLIDE\s*\d*|DIAPOSITIVA\s*\d*"
    r")\s*\**\s*:\s*",
    re.IGNORECASE,
)


def strip_block_markdown(line: str) -> str:
    """Quita los prefijos de bloque de Markdown (encabezados `##` y citas `>`)."""
    if not line:
        return line
    return _MD_BLOCK_PREFIX_RE.sub("", line).strip()


_HUGGING_PUNCTUATION = ",.;:!?)]"


def _render_code_chip(match: "re.Match[str]") -> str:
    """Envuelve el código inline, recortando el padding si le sigue puntuación.

    El chip lleva padding horizontal para separarse del texto, pero delante de una
    coma o un punto ese aire se lee como un espacio de más: "cero `ssh` , cero
    `grep` ." La clase `tight` anula sólo el padding derecho en ese caso.
    """
    # `siguiente` viene vacío al final del texto, y "" in "..." es True en Python:
    # sin el chequeo de verdad, el último chip de cada línea perdía su padding.
    siguiente = match.string[match.end():match.end() + 1]
    clase = ' class="tight"' if siguiente and siguiente in _HUGGING_PUNCTUATION else ""
    return f"<code{clase}>{match.group(1)}</code>"


def render_inline_markdown(escaped_text: str) -> str:
    """Convierte el Markdown inline a HTML.

    Debe aplicarse SOBRE TEXTO YA ESCAPADO con `html.escape`: los marcadores de
    Markdown no son caracteres especiales de HTML, así que sobreviven al escape
    intactos y el contenido que envuelven ya viene saneado.
    """
    if not escaped_text:
        return escaped_text

    out = _MD_LINK_RE.sub(r"\1", escaped_text)            # [texto](url) -> texto
    out = _MD_CODE_RE.sub(_render_code_chip, out)
    out = _MD_BOLD_RE.sub(lambda m: f"<strong>{m.group(1) or m.group(2)}</strong>", out)
    out = _MD_STRIKE_RE.sub(r"\1", out)                   # sin tachado en el diseño
    out = _MD_ITALIC_RE.sub(lambda m: f"<em>{m.group(1) or m.group(2)}</em>", out)
    return out


def _apply_outside_tags(text: str, transform) -> str:
    """Aplica `transform` sólo a los segmentos que quedan fuera de un tag HTML."""
    return "".join(
        part if part.startswith("<") else transform(part)
        for part in _HTML_TAG_SPLIT_RE.split(text)
    )


# Vocabulario técnico que se resalta automáticamente en las láminas.
_KEYWORDS_RE = re.compile(
    r"(?i)\b(react native|expo|supabase|postgresql|zustand|tanstack query|cache|realtime|"
    r"rollback|latencia|concurrencia|offline-first|tablet-first|api|docker|python|gemini|"
    r"llm|playwright|webgl|pymupdf|refero|shaders|lucide|chromium)\b"
)


def _highlight_keywords(fragment: str) -> str:
    """Envuelve el vocabulario técnico en <strong>."""
    return _KEYWORDS_RE.sub(r"<strong>\1</strong>", fragment)


def parse_carousel_slides(carousel_script: str) -> List[Dict[str, str]]:
    """Extrae de forma robusta las 10 diapositivas del guion generado con soporte para iconos Lucide."""
    matches = list(
        re.finditer(
            r"---\s*(?:DIAPOSITIVA|SLIDE)\s*(\d+)\s*(?:/|DE)\s*\d+\s*---",
            carousel_script,
            flags=re.IGNORECASE,
        )
    )
    slides: List[Dict[str, str]] = []

    for i in range(len(matches)):
        start = matches[i].end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(carousel_script)
        block = carousel_script[start:end].strip()
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue

        category = ""
        explicit_icon = ""
        cleaned_lines = []
        for l in lines:
            # Un separador de Markdown no es contenido: se descarta antes de todo,
            # incluso antes de mirar si parece viñeta ('---' empieza con guion).
            if is_horizontal_rule(l):
                continue

            # Rótulos de estructura en línea propia: se descartan para que el título
            # sea la línea siguiente, la que realmente lo contiene.
            if is_structure_label(l):
                continue

            is_bullet_line = bool(re.match(r"^[-*•\d\.]\s+", l))

            # Los prefijos de bloque (`##`, `>`) se quitan antes de clasificar la línea,
            # pero sólo si no es viñeta: en una viñeta el guion inicial es el marcador.
            if not is_bullet_line:
                stripped = strip_block_markdown(l)
                if stripped != l:
                    l = stripped
                    if not l:
                        continue

            # Si es tag de cabecera [ICON: name] standalone (no en viñeta)
            standalone_icon = re.match(r"^\[(?:ICON|ICONO)\s*:\s*([a-z0-9-]+)\]$", l, re.IGNORECASE)
            if standalone_icon:
                explicit_icon = standalone_icon.group(1).lower().strip()
                continue

            tag_match = re.match(r"^\[(.*?)\]$", l)
            if tag_match:
                tag_str = tag_match.group(1).strip()
                # Soportar formato [CATEGORIA | icon-name]
                if "|" in tag_str:
                    parts = [p.strip() for p in tag_str.split("|", 1)]
                    cat_part = parts[0]
                    icon_part = parts[1].lower().replace("icon:", "").replace("icono:", "").strip()
                    if icon_part:
                        explicit_icon = icon_part
                    if cat_part.upper() not in ["PORTADA", "COVER", "SLIDE 1", "DIAPOSITIVA 1", "TITULO", "TÍTULO"]:
                        category = cat_part
                else:
                    if tag_str.upper() not in ["PORTADA", "COVER", "SLIDE 1", "DIAPOSITIVA 1", "TITULO", "TÍTULO"]:
                        category = tag_str
                continue

            # Si no es viñeta y tiene un [ICON: xxx] inline en el título
            if not is_bullet_line and not explicit_icon:
                inline_icon = re.search(r"\[(?:ICON|ICONO)\s*:\s*([a-z0-9-]+)\]", l, re.IGNORECASE)
                if inline_icon:
                    explicit_icon = inline_icon.group(1).lower().strip()
                    l = re.sub(r"\[(?:ICON|ICONO)\s*:\s*[a-z0-9-]+\]", "", l, flags=re.IGNORECASE).strip()

            if is_bullet_line:
                cleaned_lines.append(l)
            else:
                cleaned = re.sub(r"\[.*?\]", "", l).strip()
                if cleaned:
                    cleaned_lines.append(cleaned)

        if not cleaned_lines:
            continue

        # El rótulo también puede venir pegado al texto en la misma línea
        # ("TÍTULO PORTADA: Debuggeando un bot"): se le quita el prefijo.
        raw_title = _STRUCTURE_LABEL_PREFIX_RE.sub("", cleaned_lines[0]).strip()
        resto = cleaned_lines[1:]

        # Si tras quitar el rótulo la línea queda vacía, el título es la siguiente.
        while not raw_title and resto:
            raw_title = _STRUCTURE_LABEL_PREFIX_RE.sub("", resto.pop(0)).strip()

        title = raw_title
        body = "\n".join(_STRUCTURE_LABEL_PREFIX_RE.sub("", l).strip() for l in resto) if resto else ""

        slides.append({
            "category": category,
            "title": title,
            "body": body,
            "icon": explicit_icon,
        })

    return slides


# Una métrica es un dato corto y contundente: "400ms", "94%", "3.2x", "60 ms".
# Cuando el título de una lámina es sólo eso, se compone a tamaño display en vez
# de tratarse como un título más.
_METRIC_RE = re.compile(
    r"^\s*[<>~±]?\s*\d[\d.,]*\s*(?:ms|s|seg|min|h|%|x|kb|mb|gb|tb|k|m|req/s|qps|rps|ops|fps|°)?\s*$",
    re.IGNORECASE,
)


def is_metric(text: str) -> bool:
    """Indica si el texto es una cifra suelta que merece componerse en grande."""
    return bool(_METRIC_RE.match(text or "")) and any(c.isdigit() for c in text or "")


def classify_slide(slide: Dict[str, str], idx: int, total: int) -> str:
    """Decide cómo componer la lámina: cover, metric, list o statement.

    El tipo sale del contenido, no de la posición: una lámina cuyo título es una
    cifra se compone distinto de una con viñetas. Antes todas usaban el mismo
    molde de título más tarjeta, y por eso las diez se veían iguales.
    """
    if idx == 1:
        return "cover"
    if is_metric(slide.get("title", "")):
        return "metric"
    if any(re.match(r"^[-*•\d\.]\s+", l) for l in (slide.get("body") or "").splitlines()):
        return "list"
    return "statement"


def split_body(raw_body: str) -> Tuple[List[str], List[str]]:
    """Separa el cuerpo en párrafos introductorios y viñetas."""
    intro: List[str] = []
    bullets: List[str] = []
    for line in [b.strip() for b in (raw_body or "").splitlines() if b.strip()]:
        if re.match(r"^[-*•\d\.]\s+", line):
            bullets.append(re.sub(r"^[-*•\d\.]\s+", "", line).strip())
        elif bullets:
            bullets.append(line)
        else:
            intro.append(line)
    return intro, bullets


def _rich(text: str) -> str:
    """Escapa el texto y le devuelve el marcado inline como HTML real."""
    return _apply_outside_tags(render_inline_markdown(html.escape(text)), _highlight_keywords)


def compose_slide(
    slide: Dict[str, str],
    idx: int,
    total: int,
    system: DesignSystem,
    strings: Dict[str, str],
    project: str,
    github_user: str,
) -> str:
    """Arma el HTML de una lámina con la composición que le corresponde."""
    kind = classify_slide(slide, idx, total)
    is_last = idx == total

    eyebrow = slide.get("category") or (
        strings["cover_category"].format(project=project) if idx == 1
        else strings["last_category"] if is_last
        else strings["mid_category"]
    )

    intro, bullets = split_body(slide.get("body", ""))
    title = slide.get("title", "")

    if kind == "metric":
        cuerpo = f'<div class="metric">{_rich(title)}</div>'
        if intro:
            cuerpo += f'<p class="metric-note">{_rich(" ".join(intro))}</p>'
    else:
        cuerpo = f'<h1 class="title">{_rich(title)}</h1>' if title else ""
        if intro:
            cuerpo += f'<p class="lede">{_rich(" ".join(intro))}</p>'
        if bullets:
            items = "".join(f'<div class="item"><span>{_rich(b)}</span></div>' for b in bullets)
            cuerpo += f'<div class="items">{items}</div>'

    cue = strings["swipe_last"] if is_last else strings["swipe"]
    clases = f"slide sys-{system.id}"
    if kind == "cover":
        clases += " is-cover"
    elif is_last:
        clases += " is-cta"

    return f"""
    <div class="{clases}" data-kind="{kind}">
        <div class="content-layer">
            <div class="header">
                <div class="eyebrow">{html.escape(eyebrow)}</div>
                <div class="folio">{idx:02d} / {total:02d}</div>
            </div>
            <div class="content">{cuerpo}</div>
            <div class="footer">
                <span class="handle">github/{html.escape(github_user)}</span>
                <span class="cue">{html.escape(cue)}</span>
            </div>
        </div>
    </div>"""


def build_carousel_html(
    slides: List[Dict[str, str]],
    project_name: str,
    system: Optional[DesignSystem] = None,
    scale_factor: float = 1.0,
    language: str = "es",
) -> str:
    """Construye el documento HTML de 1080x1350 px con el sistema de diseño activo.

    El sistema define tipografía, color y composición. No hay tarjetas ni fondo
    WebGL: cada lámina se sostiene con jerarquía tipográfica, que es lo que
    distingue una pieza diseñada de una plantilla rellenada.
    """
    if system is None:
        system = get_rotating_system(seed=project_name)

    strings = get_carousel_strings(language)
    project = project_name.split("/")[-1].replace("-", " ").title()
    github_user = project_name.split("/")[0] if "/" in project_name else (os.getenv("GH_USERNAME") or "github")
    total = len(slides) if slides else 10

    cuerpo = "".join(
        compose_slide(s, i, total, system, strings, project, github_user)
        for i, s in enumerate(slides, start=1)
    )

    tokens = "\n".join(f"    --{k}: {v};" for k, v in system.tokens.items())
    # La escala comprime la tipografía cuando el bucle de auto-reparación detecta
    # que el contenido no entra en las safe-zones.
    escala = f"\n    zoom: {scale_factor};" if scale_factor != 1.0 else ""

    return f"""<!DOCTYPE html>
<html lang="{strings["html_lang"]}">
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="{system.fonts_url}">
<style>
:root {{
{tokens}
}}

@page {{ size: 1080px 1350px; margin: 0; }}

* {{ box-sizing: border-box; margin: 0; padding: 0; }}

html, body {{
    width: 1080px;
    background: var(--bg);
    font-size: 0;
    -webkit-font-smoothing: antialiased;
}}

.slide {{
    position: relative;
    width: 1080px;
    height: 1350px;
    overflow: hidden;
    background: var(--bg);
    font-size: 16px;
}}

.slide:not(:last-child) {{
    page-break-after: always;
    break-after: page;
}}

.content-layer {{
    position: relative;
    width: 1080px;
    height: 1350px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;{escala}
}}

.content {{ flex: 1; min-height: 0; }}

{system.css}
</style>
</head>
<body>{cuerpo}</body>
</html>
"""

def render_html_carousel_to_pdf(
    html_content: str,
    timeout_ms: int = 45000,
) -> bytes:
    """Compila el HTML a un PDF vectorial de 1080x1350 px con Playwright Chromium.

    La única dependencia externa que queda son las tipografías: los sistemas de
    diseño usan fondos sólidos, así que ya no hay WebGL ni iconos remotos que
    esperar. Eso saca 35 s de timeouts del camino y elimina dos CDNs del render.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--disable-dev-shm-usage"])
        try:
            page = browser.new_page(viewport={"width": 1080, "height": 1350})
            page.set_content(html_content, wait_until="load", timeout=timeout_ms)

            # Sin esto el PDF puede salir con la tipografía de respaldo del sistema.
            try:
                page.wait_for_function(
                    "document.fonts && document.fonts.status === 'loaded'",
                    timeout=15000,
                )
            except PlaywrightTimeoutError:
                print("  • [WARN] Las fuentes no terminaron de cargar; se exporta con la familia de respaldo.")

            return page.pdf(
                width="1080px",
                height="1350px",
                print_background=True,
                margin={"top": "0px", "right": "0px", "bottom": "0px", "left": "0px"},
            )
        finally:
            browser.close()


def optimize_pdf_webgl_streams(pdf_bytes: bytes) -> bytes:
    """Optimiza el tamaño del PDF recompimiendo los canvas WebGL PNG a JPEG de alta fidelidad.
    
    Reduce el peso de un carrusel de 10 láminas de ~55MB a ~3.5MB, garantizando que cumpla con los
    límites de subida de Telegram (50MB) y se descargue de forma instantánea en móviles.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        optimized_count = 0
        for page in doc:
            for img_info in page.get_images():
                xref = img_info[0]
                extracted = doc.extract_image(xref)
                png_bytes = extracted.get("image")
                if not png_bytes or len(png_bytes) < 300_000:
                    continue
                
                im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
                out_io = io.BytesIO()
                im.save(out_io, format="JPEG", quality=85, optimize=True)
                jpeg_bytes = out_io.getvalue()
                
                # compress=False es vital para evitar doble compresión zlib en streams DCTDecode
                doc.update_stream(xref, jpeg_bytes, compress=False)
                doc.xref_set_key(xref, "Filter", "/DCTDecode")
                doc.xref_set_key(xref, "ColorSpace", "/DeviceRGB")
                optimized_count += 1
        
        optimized_bytes = doc.tobytes(deflate=True, garbage=4, clean=True)
        doc.close()
        orig_mb = len(pdf_bytes) / (1024 * 1024)
        new_mb = len(optimized_bytes) / (1024 * 1024)
        if optimized_count > 0:
            print(f"  • PDF optimizado para Telegram: {orig_mb:.1f} MB -> {new_mb:.1f} MB ({optimized_count} laminas WebGL comprimidas).")
        return optimized_bytes
    except Exception as e:
        print(f"[WARN] No se pudo optimizar el stream del PDF: {e}")
        return pdf_bytes


def _structural_penalty(structural: Dict[str, Any]) -> int:
    """Puntaje de defectos estructurales: cuanto más bajo, mejor el candidato."""
    return (
        len(structural.get("errors", [])) * 10
        + len(structural.get("footer_collisions", []))
        + len(structural.get("color_jumps", [])) * 5
        + len(structural.get("warnings", []))
    )


def generate_native_carousel_pdf(
    carousel_script: str,
    project_name: str,
    theme_id: Optional[str] = None,
    max_repair_attempts: int = 3,
    language: str = "es",
    api_key: Optional[str] = None,
) -> Tuple[Optional[bytes], str, str, Dict[str, Any]]:
    """Punto de entrada principal con bucle de Auto-Reparación (Self-Healing Loop) y QC.

    El bucle de reparación usa SÓLO la capa estructural determinística de PyMuPDF, que
    cuesta 0 tokens y es además la única señal que alimenta las correcciones disponibles
    (escala y elección de tema). La capa visual multimodal corre UNA sola vez, sobre el
    mejor candidato, en vez de una vez por intento: antes cada carrusel mandaba hasta 30
    imágenes al modelo de visión para producir un único PDF.
    """
    # Un fallo del carrusel devolvía un dict vacío, así que el emisor no podía
    # distinguir "no había guion" de "el render reventó" y entregaba el post en
    # silencio, sin PDF ni motivo. El dict ahora viaja con la causa.
    def _failed(reason: str) -> Tuple[Optional[bytes], str, str, Dict[str, Any]]:
        return None, "", "", {"generation_failed": True, "failure_reason": reason}

    try:
        slides = parse_carousel_slides(carousel_script)
        if not slides:
            print("[WARN] No se pudieron parsear diapositivas del guion del carrusel.")
            return _failed("el guion no tiene diapositivas parseables (falta el delimitador --- DIAPOSITIVA N / 10 ---)")

        if theme_id:
            system = get_system_by_id(theme_id)
        else:
            system = get_rotating_system(seed=project_name)

        scales_to_try = [1.0, 0.90, 0.82]
        best_pdf_bytes: Optional[bytes] = None
        best_structural: Dict[str, Any] = {}
        best_penalty = float("inf")
        best_system = system
        best_scale = 1.0
        current_system = system

        for attempt in range(1, max_repair_attempts + 1):
            scale_factor = scales_to_try[min(attempt - 1, len(scales_to_try) - 1)]

            # Los temas claros son los que más artefactos de recorte producen en visores
            # móviles de PDF; si el primer intento falló, mutamos a contraste absoluto.
            if attempt > 1 and current_system.canvas != "solid":
                print(f"  • [AUTO-REPARACIÓN #{attempt}] Mutando a 'Linear Midnight' para garantizar pureza del lienzo...")
                current_system = get_system_by_id("terminal")

            if attempt == 1:
                print(f"  • Renderizando {len(slides)} diapositivas con tema Refero '{current_system.name}' ({current_system.id})...")
            else:
                print(f"  • [AUTO-REPARACIÓN #{attempt}] Re-renderizando con escala compensada ({int(scale_factor * 100)}%)...")

            html_content = build_carousel_html(
                slides,
                project_name,
                system=current_system,
                scale_factor=scale_factor,
                language=language,
            )
            raw_pdf_bytes = render_html_carousel_to_pdf(html_content)
            pdf_bytes = optimize_pdf_webgl_streams(raw_pdf_bytes)

            # Capa 1: estructural, determinística y gratis. Es la que guía la reparación.
            structural = validate_pdf_structure(pdf_bytes)
            penalty = _structural_penalty(structural)
            footer_collisions = structural.get("footer_collisions", [])

            if penalty < best_penalty:
                best_penalty = penalty
                best_pdf_bytes = pdf_bytes
                best_structural = structural
                best_system = current_system
                best_scale = scale_factor

            if structural["passed"] and not footer_collisions:
                label = "APROBADO" if attempt == 1 else f"AUTO-REPARADO en intento {attempt}"
                print(f"    [QC ESTRUCTURAL {label}] {structural['page_count']} páginas, 0 colisiones en safe-zones.")
                break

            print(
                f"    [QC ESTRUCTURAL OBSERVADO - INTENTO {attempt}] "
                f"{len(footer_collisions)} colisión(es), {len(structural.get('errors', []))} error(es)."
            )
            for col in footer_collisions[:2]:
                print(f"      - {col[1]}")

            # Reintentar sólo tiene sentido si hay una acción de reparación aplicable.
            # Las únicas palancas del bucle son la escala y el tema; defectos como
            # "faltan páginas" o "hay placeholders" vienen del guion, no del render,
            # y volver a renderizar sólo quema CPU y tiempo de runner.
            if not structural.get("repair_actions") and not footer_collisions:
                print("    [SIN REPARACIÓN APLICABLE] Los defectos vienen del guion, no del render. Se corta el bucle.")
                break

        if best_pdf_bytes is None:
            return _failed(f"ningún intento de render produjo un PDF ({max_repair_attempts} intentos)")

        # Capa 2: auditoría visual multimodal, UNA sola vez sobre el mejor candidato.
        qc_result = audit_carousel_pdf(
            best_pdf_bytes,
            api_key=api_key,
            structural=best_structural,
        )
        qc_result["theme_name"] = best_system.name
        qc_result["design_system"] = best_system.id
        qc_result["theme_north_star"] = best_system.north_star
        qc_result["scale_factor_applied"] = best_scale

        score = float(qc_result.get("overall_score", 0.0))
        status = "APROBADO" if qc_result.get("passed") else "OBSERVADO"
        print(f"  • [QC FINAL {status}] Score {score:.1f}/5.0 — {qc_result.get('summary', '')}")

        # El juez devuelve un score por criterio y una lista de problemas concretos.
        # Antes se descartaban, así que un score bajo no se podía diagnosticar sin
        # releer el resumen a ojo.
        visual = qc_result.get("visual_check") or {}
        criterios = visual.get("criteria") or {}
        if criterios:
            print("    Detalle por criterio:")
            for nombre, datos in criterios.items():
                if not isinstance(datos, dict):
                    continue
                etiqueta = CRITERIA_LABELS.get(nombre, nombre.replace("_", " "))
                marca = "!" if isinstance(datos.get("score"), (int, float)) and datos["score"] < 4.5 else " "
                print(f"      {marca} {datos.get('score')}  {etiqueta}")

        if not qc_result.get("passed"):
            motivo = summarize_qc_issues(qc_result)
            if motivo:
                print(f"    Motivo: {motivo}")

        return best_pdf_bytes, "", "", qc_result

    except Exception as e:
        # `{e}` solo a secas oculta el tipo y el punto de fallo: un carrusel que no
        # sale queda indistinguible de uno que nunca se pidió. La traza va completa
        # a la consola y el motivo corto viaja hasta Telegram.
        print(f"[WARN] Error generando carrusel nativo HTML/CSS: {type(e).__name__}: {e}")
        traceback.print_exc()
        return _failed(f"{type(e).__name__}: {e}")

