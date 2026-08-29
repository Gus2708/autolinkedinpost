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
from src.theme_manager import get_rotating_theme, get_theme_by_id, DesignTheme


# Versiones PINEADAS de las dependencias de render. Antes Lucide se cargaba como
# '@latest', lo que significaba que un release del paquete podía cambiar el resultado
# de una corrida desatendida sin que nadie tocara el repo. Verificadas contra el
# registry: lucide 1.35.0 conserva los alias de iconos usados en este módulo.
LUCIDE_VERSION = os.getenv("LUCIDE_VERSION", "1.35.0")
SHADERS_VERSION = os.getenv("PAPER_SHADERS_VERSION", "0.0.80")

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


LUCIDE_ICON_ALIASES = {
    "sparkler": "sparkles",
    "sparkle": "sparkles",
    "magic": "sparkles",
    "stars": "sparkles",
    "bulb": "lightbulb",
    "idea": "lightbulb",
    "check-circle": "check-circle-2",
    "check-circle-outline": "check-circle-2",
    "check": "check",
    "gear": "settings",
    "gears": "settings",
    "cog": "settings",
    "warning": "alert-triangle",
    "caution": "alert-triangle",
    "danger": "alert-triangle",
    "error": "alert-circle",
    "bug": "bug",
    "graph": "bar-chart-2",
    "chart": "bar-chart-2",
    "analytics": "activity",
    "chat": "message-square",
    "comment": "message-square",
    "comments": "message-square",
    "dialog": "message-circle",
    "doc": "file-text",
    "document": "file-text",
    "file": "file-text",
    "file-check": "file-check",
    "code-bracket": "code",
    "brackets": "code",
    "terminal-window": "terminal",
    "console": "terminal",
    "magnifier": "search",
    "magnifying-glass": "search",
    "find": "search",
    "cross": "x",
    "close": "x",
    "cancel": "x-circle",
    "phone": "smartphone",
    "mobile": "smartphone",
    "clock": "clock",
    "time": "clock",
    "speed": "gauge",
    "meter": "gauge",
    "database": "database",
    "db": "database",
    "lock": "lock",
    "padlock": "lock",
    "shield": "shield-check",
    "security": "shield-check",
    "key": "key",
    "palette": "palette",
    "design": "palette",
    "shapes": "shapes",
    "icons": "sparkles",
    "icon": "sparkles",
    "iconografia": "sparkles",
    "iconografía": "sparkles",
}


def normalize_lucide_icon(name: Optional[str]) -> str:
    """Normaliza y valida nombres de iconos Lucide, mapeando sinónimos comunes a SVG válidos."""
    if not name:
        return "sparkles"
    clean = name.strip().lower()
    return LUCIDE_ICON_ALIASES.get(clean, clean)


def resolve_lucide_icon(slide: Dict[str, str], idx: int, total_slides: int) -> str:
    """Resuelve dinámicamente el mejor icono Lucide para la diapositiva.
    
    1. Si el agente/guion especificó un icono explícito ([ICON: cpu], [CATEGORIA | database]), lo usa directamente.
    2. Si no, realiza matching semántico contextual sobre categoría, título y cuerpo usando el catálogo completo de Lucide.
    """
    explicit = slide.get("icon", "").strip().lower()
    if explicit:
        return normalize_lucide_icon(explicit)

    is_first = (idx == 1)
    is_last = (idx == total_slides)

    if is_first:
        return "rocket"
    if is_last:
        return "message-square-code"

    text_to_analyze = f"{slide.get('category', '')} {slide.get('title', '')} {slide.get('body', '')}".lower()

    # Mapeo semántico exhaustivo sobre la suite completa de Lucide Icons (https://lucide.dev/icons)
    SEMANTIC_ICON_MAP = [
        # Base de datos y almacenamiento
        (r"\b(postgres|postgresql|database|bd|sql|nosql|mongodb|mongo|prisma|drizzle|sqlite|storage|persistencia|tablas|indices|indexes)\b", "database"),
        # Cache y memoria
        (r"\b(cache|redis|memcached|ram|caching|hit|miss|invalidation|eviction)\b", "zap"),
        # Seguridad, autenticación y criptografía
        (r"\b(auth|jwt|oauth|token|seguridad|security|cifrado|crypto|permisos|roles|rbac|firewall|ssl|tls)\b", "shield-check"),
        # Concurrencia, bloqueos y sincronización
        (r"\b(deadlock|lock|bloqueo|concurrencia|race condition|mutex|semáforo|threads|hilos|async|await)\b", "lock"),
        # Rendimiento, benchmarks y latencia
        (r"\b(benchmark|latencia|latency|throughput|rendimiento|performance|ms|qps|ops|carga|estrés|speed|optimización|optimization)\b", "gauge"),
        # Redes, APIs y endpoints
        (r"\b(api|rest|graphql|grpc|http|https|endpoint|webhook|socket|websocket|networking|ip|dns)\b", "network"),
        # Cloud e infraestructura
        (r"\b(aws|gcp|azure|cloud|serverless|lambda|deploy|deployment|infraestructura|iac|terraform)\b", "cloud"),
        # Contenedores y orquestación
        (r"\b(docker|container|contenedor|kubernetes|k8s|helm|pod|cluster|swarm)\b", "container"),
        # Servidores y Backend
        (r"\b(server|servidor|backend|node|nodejs|fastapi|express|django|spring|rust|golang|go)\b", "server"),
        # Procesamiento, CPU y colas
        (r"\b(cpu|procesador|computo|worker|workers|queue|colas|bullmq|celery|kafka|rabbitmq)\b", "cpu"),
        # Git, ramas y control de versiones
        (r"\b(git|branch|ramas|commit|merge|pr|pull request|diff|rollback|revert|versionado)\b", "git-branch"),
        # Terminal, CLI y scripting
        (r"\b(cli|terminal|bash|powershell|script|comando|shell|stdout|stderr)\b", "terminal"),
        # Métricas, monitoreo y observabilidad
        (r"\b(metricas|metrics|monitoreo|monitoring|grafana|prometheus|telemetria|telemetry|logs|logging|datadog|trace|tracing|apm)\b", "activity"),
        # Testing, QA y aserciones
        (r"\b(test|testing|tdd|unit|e2e|cypress|jest|pytest|qa|qc|cobertura|coverage|assertion)\b", "check-circle-2"),
        # Errores, fallos y depuración
        (r"\b(bug|error|fallo|exception|excepción|crash|leak|overflow|panic|fix|debug)\b", "bug"),
        # Escalabilidad y particionamiento
        (r"\b(scale|escalabilidad|sharding|particionamiento|alta disponibilidad|fault tolerance|distribuido|distributed)\b", "scale"),
        # CI/CD y automatización
        (r"\b(pipeline|ci/cd|automation|automatizacion|github actions|workflow|jobs)\b", "workflow"),
        # Arquitectura, patrones y capas
        (r"\b(arquitectura|architecture|hexagonal|clean arch|modular|capas|layers|patron|pattern|microservicios|microservices)\b", "layers"),
        # Código, tipos y refactoring
        (r"\b(codigo|code|refactor|clean code|types|typescript|interfaces|clases|solid|dry)\b", "code-2"),
        # Problema, tensión o cuello de botella
        (r"\b(problema|problem|tensión|tension|desafío|challenge|fricción|cuello de botella|bottleneck|alerta|riesgo|danger)\b", "alert-triangle"),
        # Solución, ideas y estrategia
        (r"\b(solución|solution|idea|innovación|propuesta|enfoque|estrategia|resolución)\b", "lightbulb"),
        # Búsqueda, consultas e indexación
        (r"\b(search|búsqueda|busqueda|query|indexing|elastic|lucene|filtro)\b", "search"),
    ]

    for pattern, icon_name in SEMANTIC_ICON_MAP:
        if re.search(pattern, text_to_analyze):
            return icon_name

    return "sparkles"


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


def strip_block_markdown(line: str) -> str:
    """Quita los prefijos de bloque de Markdown (encabezados `##` y citas `>`)."""
    if not line:
        return line
    return _MD_BLOCK_PREFIX_RE.sub("", line).strip()


def render_inline_markdown(escaped_text: str) -> str:
    """Convierte el Markdown inline a HTML.

    Debe aplicarse SOBRE TEXTO YA ESCAPADO con `html.escape`: los marcadores de
    Markdown no son caracteres especiales de HTML, así que sobreviven al escape
    intactos y el contenido que envuelven ya viene saneado.
    """
    if not escaped_text:
        return escaped_text

    out = _MD_LINK_RE.sub(r"\1", escaped_text)            # [texto](url) -> texto
    out = _MD_CODE_RE.sub(r"<code>\1</code>", out)
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

        raw_title = cleaned_lines[0]
        title = re.sub(
            r"^(?:PORTADA|SLIDE\s*\d+|TITULO|TÍTULO)\s*:\s*",
            "",
            raw_title,
            flags=re.IGNORECASE,
        ).strip()
        body = "\n".join(cleaned_lines[1:]) if len(cleaned_lines) > 1 else ""

        slides.append({
            "category": category,
            "title": title,
            "body": body,
            "icon": explicit_icon,
        })

    return slides


def build_carousel_html(
    slides: List[Dict[str, str]],
    project_name: str,
    theme: Optional[DesignTheme] = None,
    scale_factor: float = 1.0,
    language: str = "es",
) -> str:
    """Construye el documento HTML5 completo con las 10 láminas en CSS Flexbox para 1080x1350 px."""
    if theme is None:
        theme = get_rotating_theme(seed=project_name)

    strings = get_carousel_strings(language)
    clean_project = project_name.split("/")[-1].replace("-", " ").title()
    total_slides = len(slides) if slides else 10

    slides_html = []
    for idx, slide in enumerate(slides, start=1):
        is_first = (idx == 1)
        is_last = (idx == total_slides)

        cat = slide.get("category", "")
        if is_first or not cat:
            if is_first:
                cat = strings["cover_category"].format(project=clean_project)
            elif is_last:
                cat = strings["last_category"]
            else:
                cat = strings["mid_category"]

        raw_title = slide.get("title", "")
        raw_body = slide.get("body", "")

        words = raw_title.split()
        if len(words) > 2 and is_first:
            title_styled = (
                render_inline_markdown(html.escape(" ".join(words[:-2])))
                + f" <span class='highlight'>{render_inline_markdown(html.escape(' '.join(words[-2:])))}</span>"
            )
        else:
            title_styled = render_inline_markdown(html.escape(raw_title))

        body_lines = [b.strip() for b in raw_body.splitlines() if b.strip()]
        intro_lines = []
        bullet_lines = []
        for l in body_lines:
            if re.match(r"^[-*•\d\.]\s+", l):
                bullet_lines.append(l)
            else:
                if not bullet_lines:
                    intro_lines.append(l)
                else:
                    bullet_lines.append(f"- {l}")

        card_parts = []
        if intro_lines:
            intro_raw = " ".join(intro_lines)
            intro_esc = render_inline_markdown(html.escape(intro_raw))
            intro_styled = _apply_outside_tags(intro_esc, _highlight_keywords)
            card_parts.append(f"<p class='card-intro'>{intro_styled}</p>")

        if bullet_lines:
            items_html = []
            for bl in bullet_lines:
                clean_item = re.sub(r"^[-*•\d\.]\s+", "", bl).strip()
                bullet_icon = "chevron-right"
                b_icon_match = re.search(r"\[(?:ICON|ICONO)\s*:\s*([a-z0-9-]+)\]", clean_item, re.IGNORECASE)
                if b_icon_match:
                    bullet_icon = b_icon_match.group(1).lower().strip()
                    clean_item = re.sub(r"\[(?:ICON|ICONO)\s*:\s*[a-z0-9-]+\]", "", clean_item, flags=re.IGNORECASE).strip()

                item_esc = render_inline_markdown(html.escape(clean_item))
                item_styled = _apply_outside_tags(item_esc, _highlight_keywords)
                items_html.append(f"<li><span class='bullet-icon'><i data-lucide='{bullet_icon}'></i></span><span>{item_styled}</span></li>")
            card_parts.append(f"<ul class='card-list'>{''.join(items_html)}</ul>")

        # Una lámina puede traer sólo título (una portada sin subtítulo, por ejemplo).
        # En ese caso NO se dibuja la tarjeta: `.card` tiene fondo, borde y
        # min-height de 280px, así que un `<p></p>` vacío adentro producía un
        # rectángulo gris hueco en el PDF.
        has_card = bool(card_parts)
        card_content = "".join(card_parts)

        cta_action_html = ""
        if is_last:
            cta_action_html = f"""
                <div class="cta-action-box">
                    <span class="cta-action-icon"><i data-lucide='message-square'></i></span>
                    <span class="cta-action-text">{html.escape(strings["cta_box"])}</span>
                </div>
            """

        swipe_text = strings["swipe_last"] if is_last else strings["swipe"]
        footer_right = f"<div class='swipe-hint'>{html.escape(swipe_text)}</div>"

        badge_icon = resolve_lucide_icon(slide, idx, total_slides)

        # Watermark del usuario con GitHub (Lucide). El owner del repo es la fuente
        # preferida; GH_USERNAME es el respaldo (el resto del proyecto usa esa variable).
        if "/" in project_name:
            github_user = project_name.split("/")[0]
        else:
            github_user = os.getenv("GH_USERNAME") or "github"

        card_header_extra = ""
        if theme.layout_family == "terminal":
            card_header_extra = f"""
            <div class="terminal-bar">
                <span class="term-dot term-dot-red"></span>
                <span class="term-dot term-dot-yellow"></span>
                <span class="term-dot term-dot-green"></span>
                <span class="term-path">~/architecture/{clean_project.lower()}</span>
            </div>
            """

        # Variación de orden y jerarquía de cajas por lámina
        # Lámina 1: Portada Hero
        # Láminas pares (2, 4, 6, 8) no extremas: Cámara Integrada (título adentro de la tarjeta sin badges duplicados)
        # Láminas impares (3, 5, 7, 9): Estándar Clásico (título exterior + tarjeta de contenido)
        # Lámina 10: Debate & CTA con foco centrado
        if is_first:
            # La portada sin subtítulo se queda sólo con el título, centrado y sin caja.
            cover_card = (
                f"""<div class="card cover-card">
                        {card_header_extra}
                        {card_content}
                    </div>"""
                if has_card else ""
            )
            content_html = f"""
            <div class="content layout-cover{'' if has_card else ' is-titleonly'}">
                <div class="cover-hero">
                    <h1 class="title cover-title">{title_styled}</h1>
                    {cover_card}
                </div>
            </div>
            """
        elif is_last:
            # En la última lámina la caja se dibuja si hay contenido o si hay CTA.
            cta_card = (
                f"""<div class="card cta-card">
                    {card_header_extra}
                    {card_content}
                    {cta_action_html}
                </div>"""
                if (has_card or cta_action_html) else ""
            )
            content_html = f"""
            <div class="content layout-cta">
                <h1 class="title cta-title">{title_styled}</h1>
                {cta_card}
            </div>
            """
        elif idx % 2 == 0 and has_card:
            # Layout Integrado: la caja de texto integra el título y las viñetas en un módulo unificado limpio
            content_html = f"""
            <div class="content layout-integrated">
                <div class="card card-integrated">
                    {card_header_extra}
                    <div class="card-title-bar">
                        <h2 class="integrated-title">{title_styled}</h2>
                    </div>
                    <div class="card-body">
                        {card_content}
                    </div>
                    {cta_action_html}
                </div>
            </div>
            """
        else:
            # Layout Estándar: Título prominente arriba y tarjeta de soporte abajo.
            # Sin contenido, la lámina queda sólo con su título en vez de arrastrar
            # una caja hueca.
            standard_card = (
                f"""<div class="card">
                    {card_header_extra}
                    {card_content}
                    {cta_action_html}
                </div>"""
                if (has_card or cta_action_html) else ""
            )
            content_html = f"""
            <div class="content layout-standard{'' if has_card else ' is-titleonly'}">
                <h1 class="title">{title_styled}</h1>
                {standard_card}
            </div>
            """

        slide_class = f"slide theme-{theme.id} layout-{theme.layout_family}"
        if is_first:
            slide_class += " is-cover"
        elif is_last:
            slide_class += " is-cta"


        slide_block = f"""
        <div class="{slide_class}">
            <div class="shader-bg" id="shader-bg-{idx}"></div>
            <div class="content-layer">
                <div class="header">
                    <div class="badge"><i data-lucide='{badge_icon}'></i> {html.escape(cat)}</div>
                    <div class="page-num">{idx:02d} / {total_slides:02d}</div>
                </div>
                
                {content_html}
                
                <div class="footer">
                    <div class="author"><svg class="github-icon" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"></path><path d="M9 18c-4.51 2-5-2-7-2"></path></svg> github/{html.escape(github_user)}</div>
                    {footer_right}
                </div>
            </div>
        </div>
        """
        slides_html.append(slide_block)

    t_size = int(66 * scale_factor)
    t_cover_size = int(84 * scale_factor)
    intro_size = int(33 * scale_factor)
    bullet_size = int(31 * scale_factor)
    card_pad_v = int(44 * scale_factor)
    card_pad_h = int(50 * scale_factor)
    bullet_gap = int(16 * scale_factor)
    content_gap = int(20 * scale_factor)
    integrated_title_size = int(58 * scale_factor)

    shader_palettes_json = json.dumps(theme.shader_palettes)

    return f"""<!DOCTYPE html>
<html lang="{strings["html_lang"]}">
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="{theme.font_import_url}">
<script src="https://unpkg.com/lucide@{LUCIDE_VERSION}/dist/umd/lucide.min.js"></script>
<style>

:root {{
    --bg-color: {theme.bg_color};
    --card-bg: {theme.card_bg};
    --card-border: {theme.card_border};
    --card-border-top: {theme.card_border_top or theme.card_border};
    --card-border-left: {theme.card_border_left or theme.card_border};
    --accent-color: {theme.accent_color};
    --text-primary: {theme.text_primary};
    --text-muted: {theme.text_muted};
    --badge-bg: {theme.badge_bg};
    --badge-border: {theme.badge_border};
    --font-family: {theme.font_family};
    --font-mono: {theme.font_mono};
    --card-radius: {theme.card_radius};

    --title-size: {t_size}px;
    --title-cover-size: {t_cover_size}px;
    --intro-size: {intro_size}px;
    --bullet-size: {bullet_size}px;
    --card-pad-v: {card_pad_v}px;
    --card-pad-h: {card_pad_h}px;
    --bullet-gap: {bullet_gap}px;
    --content-gap: {content_gap}px;
    --integrated-title-size: {integrated_title_size}px;
}}

@page {{
    size: 1080px 1350px;
    margin: 0;
}}

* {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}}

html, body {{
    margin: 0;
    padding: 0;
    width: 1080px;
    font-size: 0;
    line-height: 0;
    background: var(--bg-color);
    font-family: var(--font-family);
    -webkit-font-smoothing: antialiased;
}}

.slide {{
    position: relative;
    width: 1080px;
    height: 1350px;
    overflow: hidden;
    background: var(--bg-color);
    font-size: 16px;
    line-height: 1.5;
}}

.slide:not(:last-child) {{
    page-break-after: always;
    break-after: page;
}}

.shader-bg, .shader-canvas {{
    position: absolute;
    top: 0;
    left: 0;
    width: 1080px;
    height: 1350px;
    z-index: 1;
    pointer-events: none;
}}

.shader-bg canvas, .shader-canvas canvas {{
    width: 1080px !important;
    height: 1350px !important;
    display: block;
}}

.content-layer {{
    position: relative;
    z-index: 2;
    width: 1080px;
    height: 1350px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 70px 70px;
}}

.header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--card-border);
    padding-bottom: 22px;
}}

.badge {{
    display: inline-flex;
    align-items: center;
    gap: 10px;
    background: var(--badge-bg);
    border: 1px solid var(--badge-border);
    color: var(--accent-color);
    padding: 10px 24px;
    border-radius: 100px;
    font-size: 24px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}

.badge svg {{
    width: 24px;
    height: 24px;
    stroke-width: 2.2px;
    flex-shrink: 0;
}}

.page-num {{
    font-family: var(--font-mono);
    font-size: 26px;
    color: var(--text-muted);
    font-weight: 600;
}}

.content {{
    margin-top: auto;
    margin-bottom: auto;
    width: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: var(--content-gap);
}}

.title {{
    font-size: var(--title-size);
    font-weight: 800;
    line-height: 1.14;
    letter-spacing: -1.6px;
    color: var(--text-primary);
    margin-bottom: 4px;
}}

.title span.highlight {{
    color: var(--accent-color);
}}

.slide.is-cover .title {{
    font-size: var(--title-cover-size);
    letter-spacing: -2.2px;
    line-height: 1.1;
    margin-bottom: 22px;
}}

.card {{
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-top: var(--card-border-top);
    border-left: var(--card-border-left);
    border-radius: var(--card-radius);
    padding: var(--card-pad-v) var(--card-pad-h);
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-height: 280px;
    position: relative;
    overflow: hidden;
}}

.card p {{
    font-size: var(--intro-size);
    line-height: 1.5;
    color: var(--text-muted);
    font-weight: 400;
}}

/* Lámina sin cuerpo: el título se queda solo y centrado, en vez de acompañado
   por una tarjeta hueca. */
.content.is-titleonly {{
    justify-content: center;
}}

.content.is-titleonly .title {{
    margin-bottom: 0;
}}

.card-intro {{
    font-size: var(--intro-size);
    line-height: 1.5;
    color: var(--text-muted);
    font-weight: 400;
    margin-bottom: 20px;
}}

.card strong {{
    color: var(--text-primary);
    font-weight: 700;
}}

/* Marcado inline convertido desde Markdown */
.card em, .title em {{
    font-style: italic;
    color: var(--text-primary);
}}

.card code, .title code {{
    font-family: var(--font-mono);
    font-size: 0.92em;
    color: var(--accent-color);
    background: var(--badge-bg);
    border: 1px solid var(--badge-border);
    border-radius: 6px;
    padding: 2px 8px;
    white-space: nowrap;
}}

.card-list {{
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: var(--bullet-gap);
}}

.card-list li {{
    font-size: var(--bullet-size);
    line-height: 1.44;
    color: var(--text-muted);
    display: flex;
    align-items: flex-start;
    gap: 18px;
}}

.card-list .bullet-icon {{
    color: var(--accent-color);
    font-size: 26px;
    line-height: 1.44;
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    margin-top: 5px;
}}

.card-list .bullet-icon svg {{
    width: 26px;
    height: 26px;
    stroke-width: 2.5px;
}}

.card-integrated {{
    padding: var(--card-pad-v) var(--card-pad-h);
}}

.card-title-bar {{
    margin-bottom: 20px;
    padding-bottom: 18px;
    border-bottom: 1px solid var(--card-border);
    display: flex;
    flex-direction: column;
    gap: 10px;
}}

.integrated-badge {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 22px;
    color: var(--accent-color);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

.integrated-badge svg {{
    width: 20px;
    height: 20px;
}}

.integrated-title {{
    font-size: var(--integrated-title-size);
    font-weight: 800;
    line-height: 1.15;
    letter-spacing: -1.4px;
    color: var(--text-primary);
}}

.terminal-bar {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 30px;
    padding-bottom: 20px;
    border-bottom: 1px solid var(--card-border);
}}

.term-dot {{
    width: 16px;
    height: 16px;
    border-radius: 50%;
}}

.term-dot-red {{ background: #EF4444; }}
.term-dot-yellow {{ background: #F59E0B; }}
.term-dot-green {{ background: #10B981; }}

.term-path {{
    font-family: var(--font-mono);
    font-size: 22px;
    color: var(--text-muted);
    margin-left: 12px;
}}

/* Raycast Command Bar */
.raycast-bar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 30px;
    padding-bottom: 18px;
    border-bottom: 1px solid rgba(255, 99, 99, 0.2);
}}

.raycast-chip {{
    font-family: var(--font-mono);
    font-size: 22px;
    background: rgba(255, 99, 99, 0.2);
    color: var(--accent-color);
    padding: 6px 14px;
    border-radius: 8px;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    gap: 8px;
}}

.raycast-chip svg {{
    width: 20px;
    height: 20px;
}}

.raycast-crumb {{
    font-size: 24px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
}}

/* CTA Action Box */
.cta-action-box {{
    margin-top: 22px;
    padding: 20px 24px;
    background: var(--badge-bg);
    border: 1px solid var(--badge-border);
    border-radius: 12px;
    display: flex;
    align-items: center;
    gap: 16px;
}}

.cta-action-icon {{
    display: inline-flex;
    align-items: center;
    color: var(--accent-color);
}}

.cta-action-icon svg {{
    width: 30px;
    height: 30px;
    stroke-width: 2.2px;
}}

.cta-action-text {{
    font-size: 26px;
    font-weight: 700;
    color: var(--accent-color);
}}

/* Modificadores Temáticos Refero */
.theme-wispr-flow .title {{
    font-family: 'EB Garamond', serif;
    font-weight: 500;
    font-size: 78px;
    letter-spacing: -1px;
}}

.theme-apple.layout-theater.is-cover .content,
.theme-apple.layout-theater.is-cta .content {{
    text-align: center;
    align-items: center;
}}

.theme-apple.layout-theater.is-cover .card,
.theme-apple.layout-theater.is-cta .card {{
    text-align: center;
}}

.theme-notion .title {{
    letter-spacing: -1.2px;
}}

.theme-notion .badge {{
    border-radius: 10px;
    text-transform: none;
    letter-spacing: 0;
}}

.footer {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid var(--card-border);
    padding-top: 20px;
}}

.author {{
    font-size: 24px;
    color: var(--text-muted);
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 10px;
}}

.author svg {{
    width: 26px;
    height: 26px;
    stroke-width: 2.2px;
    color: var(--accent-color);
}}

.swipe-hint {{
    font-size: 24px;
    color: var(--accent-color);
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 8px;
}}
</style>
</head>
<body>{"".join(slides_html)}
<script>
// Iconos Lucide: script clásico e independiente del módulo de shaders, para que la
// caída de un CDN no arrastre al otro. Publica banderas que el renderer consulta
// antes de exportar, en lugar de confiar en una espera fija.
window._iconsReady = false;
window._lucideAvailable = (typeof lucide !== 'undefined');
window._iconsRepaired = 0;

// document.fonts.ready resuelve cuando el conjunto de fuentes queda estable. Consultar
// document.fonts.status directamente da 'loaded' también ANTES de que el layout dispare
// las peticiones, así que la espera podía pasar con las fuentes todavía sin cargar.
window._fontsReady = false;
if (document.fonts && document.fonts.ready) {{
    document.fonts.ready.then(function () {{ window._fontsReady = true; }});
}} else {{
    window._fontsReady = true;
}}

if (window._lucideAvailable) {{
    const attrs = {{ attrs: {{ width: 16, height: 16, 'stroke-width': 2 }} }};
    // 1. Renderizar todos los iconos válidos
    lucide.createIcons(attrs);

    // 2. Auto-healing: los que siguen siendo <i> son nombres que Lucide no reconoció
    document.querySelectorAll('i[data-lucide]').forEach(el => {{
        el.setAttribute('data-lucide', 'sparkles');
        window._iconsRepaired++;
    }});
    if (window._iconsRepaired > 0) {{
        lucide.createIcons(attrs);
    }}
}}
window._iconsReady = true;
</script>
<script type="module">
import {{
    ShaderMount,
    meshGradientFragmentShader,
    neuroNoiseFragmentShader,
    getShaderColorFromString,
    ShaderFitOptions
}} from 'https://cdn.jsdelivr.net/npm/@paper-design/shaders@{SHADERS_VERSION}/dist/index.js';

const shaderType = '{theme.shader_type}';
const colorPalettes = {shader_palettes_json};
// UI/UX Consistency (Emil Kowalski & UI UX Pro Max):
// Todas las láminas de una misma publicación deben mantener el mismo lienzo y paleta base armónica
const basePalette = colorPalettes[0] || ['#08090A', '#161718', '#23252A', '#5E6AD2'];

for (let i = 1; i <= {total_slides}; i++) {{
    const container = document.getElementById(`shader-bg-${{i}}`);
    if (!container) continue;

    const palette = basePalette;
    let fragmentShader, uniforms;

    if (shaderType === 'neuroNoise') {{
        fragmentShader = neuroNoiseFragmentShader;
        const colors = palette.map(getShaderColorFromString);
        uniforms = {{
            u_colorBack: colors[0] || [0, 0, 0, 1],
            u_colorMid: colors[1] || [0.2, 0.2, 0.2, 1],
            u_colorFront: colors[2] || [0.4, 0.4, 0.4, 1],
            u_brightness: 0.6,
            u_contrast: 0.5,
            u_fit: ShaderFitOptions['cover'] || 2,
            u_rotation: (i * 3) % 25,
            u_scale: 1.2,
            u_offsetX: 0,
            u_offsetY: 0,
            u_originX: 0.5,
            u_originY: 0.5,
            u_worldWidth: 1,
            u_worldHeight: 1
        }};
    }} else {{
        fragmentShader = meshGradientFragmentShader;
        uniforms = {{
            u_colors: palette.map(getShaderColorFromString),
            u_colorsCount: palette.length,
            u_distortion: 0.75,
            u_swirl: 0.35,
            u_grainMixer: 0.05,
            u_grainOverlay: 0.05,
            u_fit: ShaderFitOptions['cover'] || 2,
            u_rotation: (i * 3) % 25,
            u_scale: 1,
            u_offsetX: 0,
            u_offsetY: 0,
            u_originX: 0.5,
            u_originY: 0.5,
            u_worldWidth: 1,
            u_worldHeight: 1
        }};
    }}

    try {{
        new ShaderMount(
            container,
            fragmentShader,
            uniforms,
            {{}},
            0,
            i * 11
        );
    }} catch (e) {{
        console.warn('Paper shader mount skipped:', e);
    }}
}}
window._shadersMounted = true;
</script>
</body>
</html>
"""


def render_html_carousel_to_pdf(
    html_content: str,
    timeout_ms: int = 45000,
) -> bytes:
    """Compila el HTML a un PDF vectorial de 1080x1350 px con Playwright Chromium y Paper Shaders WebGL.

    Espera señales explícitas de la página (iconos listos, fuentes cargadas, shaders montados)
    en vez de dormir un tiempo fijo, para que el export no dependa de la latencia del CDN.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=[
                "--use-gl=angle",
                "--use-angle=swiftshader",
                "--enable-webgl",
                "--disable-dev-shm-usage",
            ]
        )
        try:
            page = browser.new_page(viewport={"width": 1080, "height": 1350})
            page.set_content(html_content, wait_until="load", timeout=timeout_ms)

            # 1. Iconos: bandera publicada por el script clásico de Lucide.
            try:
                page.wait_for_function("window._iconsReady === true", timeout=15000)
            except PlaywrightTimeoutError:
                print("  • [WARN] El script de Lucide no llegó a inicializar; se exporta sin iconos.")

            if not page.evaluate("window._lucideAvailable === true"):
                print(f"  • [WARN] Lucide {LUCIDE_VERSION} no cargó desde el CDN: las láminas saldrán sin iconos.")
            else:
                repaired = page.evaluate("window._iconsRepaired || 0")
                if repaired:
                    print(f"  • [AUTO-REPARACIÓN] {repaired} nombre(s) de icono no reconocidos por Lucide {LUCIDE_VERSION}; se usó 'sparkles'.")

            # 2. Fuentes: sin esto el PDF puede salir con la tipografía de respaldo.
            try:
                page.wait_for_function("window._fontsReady === true", timeout=15000)
            except PlaywrightTimeoutError:
                print("  • [WARN] Las fuentes no terminaron de cargar; se exporta con la familia de respaldo.")

            # 3. Shaders WebGL: si el módulo no monta, el fondo sólido del tema alcanza.
            try:
                page.wait_for_function("window._shadersMounted === true", timeout=20000)
                # Un frame extra para que el primer draw de WebGL quede en el compositor.
                page.wait_for_timeout(400)
            except PlaywrightTimeoutError:
                print("  • [WARN] Los Paper Shaders no montaron a tiempo; se exporta con el fondo plano del tema.")

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
    empty_qc: Dict[str, Any] = {}
    try:
        slides = parse_carousel_slides(carousel_script)
        if not slides:
            print("[WARN] No se pudieron parsear diapositivas del guion del carrusel.")
            return None, "", "", empty_qc

        if theme_id:
            theme = get_theme_by_id(theme_id)
        else:
            theme = get_rotating_theme(seed=project_name)

        scales_to_try = [1.0, 0.90, 0.82]
        best_pdf_bytes: Optional[bytes] = None
        best_structural: Dict[str, Any] = {}
        best_penalty = float("inf")
        best_theme = theme
        best_scale = 1.0
        current_theme = theme

        for attempt in range(1, max_repair_attempts + 1):
            scale_factor = scales_to_try[min(attempt - 1, len(scales_to_try) - 1)]

            # Los temas claros son los que más artefactos de recorte producen en visores
            # móviles de PDF; si el primer intento falló, mutamos a contraste absoluto.
            if attempt > 1 and current_theme.id in ["notion", "wispr-flow"]:
                print(f"  • [AUTO-REPARACIÓN #{attempt}] Mutando a 'Linear Midnight' para garantizar pureza del lienzo...")
                current_theme = get_theme_by_id("linear")

            if attempt == 1:
                print(f"  • Renderizando {len(slides)} diapositivas con tema Refero '{current_theme.name}' ({current_theme.brand})...")
            else:
                print(f"  • [AUTO-REPARACIÓN #{attempt}] Re-renderizando con escala compensada ({int(scale_factor * 100)}%)...")

            html_content = build_carousel_html(
                slides,
                project_name,
                theme=current_theme,
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
                best_theme = current_theme
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
            return None, "", "", empty_qc

        # Capa 2: auditoría visual multimodal, UNA sola vez sobre el mejor candidato.
        qc_result = audit_carousel_pdf(
            best_pdf_bytes,
            api_key=api_key,
            structural=best_structural,
        )
        qc_result["theme_name"] = best_theme.name
        qc_result["theme_brand"] = best_theme.brand
        qc_result["theme_north_star"] = best_theme.north_star
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
        print(f"[WARN] Error generando carrusel nativo HTML/CSS: {e}")
        return None, "", "", empty_qc

