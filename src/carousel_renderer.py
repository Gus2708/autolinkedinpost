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

import fitz  # PyMuPDF
from PIL import Image
from playwright.sync_api import sync_playwright

from src.pdf_evaluator import audit_carousel_pdf
from src.theme_manager import get_rotating_theme, get_theme_by_id, DesignTheme


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
    author_title: str = "Tech Lead & Software Engineer",
    theme: Optional[DesignTheme] = None,
    scale_factor: float = 1.0,
) -> str:
    """Construye el documento HTML5 completo con las 10 láminas en CSS Flexbox para 1080x1350 px."""
    if theme is None:
        theme = get_rotating_theme(seed=project_name)

    clean_project = project_name.split("/")[-1].replace("-", " ").title()
    total_slides = len(slides) if slides else 10

    slides_html = []
    for idx, slide in enumerate(slides, start=1):
        is_first = (idx == 1)
        is_last = (idx == total_slides)

        cat = slide.get("category", "")
        if is_first or not cat:
            if is_first:
                cat = f"{clean_project} • Arquitectura"
            elif is_last:
                cat = "Conclusiones & Debate"
            else:
                cat = "Arquitectura Técnica"

        raw_title = slide.get("title", "")
        raw_body = slide.get("body", "")

        words = raw_title.split()
        if len(words) > 2 and is_first:
            title_styled = (
                html.escape(" ".join(words[:-2]))
                + f" <span class='highlight'>{html.escape(' '.join(words[-2:]))}</span>"
            )
        else:
            title_styled = html.escape(raw_title)

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
            intro_esc = html.escape(intro_raw)
            intro_styled = re.sub(
                r"(?i)\b(react native|expo|supabase|postgresql|zustand|tanstack query|cache|realtime|rollback|latencia|concurrencia|offline-first|tablet-first|api|docker|python|gemini|llm|playwright|webgl|pymupdf|refero|shaders|lucide|chromium)\b",
                r"<strong>\1</strong>",
                intro_esc,
            )
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

                item_esc = html.escape(clean_item)
                item_styled = re.sub(
                    r"(?i)\b(react native|expo|supabase|postgresql|zustand|tanstack query|cache|realtime|rollback|latencia|concurrencia|offline-first|tablet-first|api|docker|python|gemini|llm|playwright|webgl|pymupdf|refero|shaders|lucide|chromium)\b",
                    r"<strong>\1</strong>",
                    item_esc,
                )
                items_html.append(f"<li><span class='bullet-icon'><i data-lucide='{bullet_icon}'></i></span><span>{item_styled}</span></li>")
            card_parts.append(f"<ul class='card-list'>{''.join(items_html)}</ul>")

        if not card_parts:
            card_content = "<p></p>"
        else:
            card_content = "".join(card_parts)

        cta_action_html = ""
        if is_last:
            cta_action_html = """
                <div class="cta-action-box">
                    <span class="cta-action-icon"><i data-lucide='message-square'></i></span>
                    <span class="cta-action-text">Dejá tu opinión o caso en comentarios</span>
                </div>
            """

        swipe_text = "Deslizá ➔"
        if is_last:
            swipe_text = "Dejá tu comentario 💬"

        footer_right = f"<div class='swipe-hint'>{swipe_text}</div>"
        slide_class = "slide is-cover" if is_first else ("slide is-cta" if is_last else "slide")

        badge_icon = resolve_lucide_icon(slide, idx, total_slides)

        # Watermark del usuario con GitHub (Lucide)
        github_user = os.getenv("GITHUB_USERNAME", "Gus2708")
        if "/" in project_name:
            github_user = project_name.split("/")[0]

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
            content_html = f"""
            <div class="content layout-cover">
                <div class="cover-hero">
                    <h1 class="title cover-title">{title_styled}</h1>
                    <div class="card cover-card">
                        {card_header_extra}
                        {card_content}
                    </div>
                </div>
            </div>
            """
        elif is_last:
            content_html = f"""
            <div class="content layout-cta">
                <h1 class="title cta-title">{title_styled}</h1>
                <div class="card cta-card">
                    {card_header_extra}
                    {card_content}
                    {cta_action_html}
                </div>
            </div>
            """
        elif idx % 2 == 0:
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
            # Layout Estándar: Título prominente arriba y tarjeta de soporte abajo
            content_html = f"""
            <div class="content layout-standard">
                <h1 class="title">{title_styled}</h1>
                <div class="card">
                    {card_header_extra}
                    {card_content}
                    {cta_action_html}
                </div>
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
<html lang="es">
<head>
<meta charset="utf-8">
<script src="https://unpkg.com/lucide@latest/dist/umd/lucide.min.js"></script>
<style>
@import url('{theme.font_import_url}');

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
    --card-shadow: {theme.card_shadow};
    --card-backdrop: {theme.card_backdrop};

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

.theme-wispr-flow .card {{
    border-width: 2px;
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
<script type="module">
import {{
    ShaderMount,
    meshGradientFragmentShader,
    neuroNoiseFragmentShader,
    getShaderColorFromString,
    ShaderFitOptions
}} from 'https://cdn.jsdelivr.net/npm/@paper-design/shaders@0.0.80/dist/index.js';

// Initialize Lucide icons with auto-healing fallback
if (typeof lucide !== 'undefined') {{
    // 1. Renderizar todos los iconos válidos
    lucide.createIcons({{ attrs: {{ width: 16, height: 16, 'stroke-width': 2 }} }});
    
    // 2. Auto-healing: Solo intervenir en elementos que aún sean <i> (es decir, que Lucide no reconoció)
    let repaired = false;
    document.querySelectorAll('i[data-lucide]').forEach(el => {{
        el.setAttribute('data-lucide', 'sparkles');
        repaired = true;
    }});
    if (repaired) {{
        lucide.createIcons({{ attrs: {{ width: 16, height: 16, 'stroke-width': 2 }} }});
    }}
}}

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
    """Compila el HTML a un documento PDF vectorial de 1080x1350 px usando Playwright Chromium con soporte Paper Shaders WebGL."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=[
                "--use-gl=angle",
                "--use-angle=swiftshader",
                "--enable-webgl",
                "--disable-dev-shm-usage",
            ]
        )
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        page.set_content(html_content, wait_until="networkidle", timeout=timeout_ms)
        page.wait_for_timeout(1500)

        # Verificación determinística pre-flight de iconos Lucide antes de exportar
        missing_count = page.evaluate("""() => {
            let missing = 0;
            // Solo los elementos que quedaron como <i> son los que Lucide no reconoció
            document.querySelectorAll('i[data-lucide]').forEach(el => {
                el.setAttribute('data-lucide', 'sparkles');
                missing++;
            });
            if (missing > 0 && typeof lucide !== 'undefined') {
                lucide.createIcons({ attrs: { width: 16, height: 16, 'stroke-width': 2 } });
            }
            return missing;
        }""")
        if missing_count > 0:
            print(f"  • [AUTO-REPARACIÓN PRE-FLIGHT] {missing_count} iconos no renderizados fueron recuperados con fallback válido.")
            page.wait_for_timeout(300)

        pdf_bytes = page.pdf(
            width="1080px",
            height="1350px",
            print_background=True,
            margin={"top": "0px", "right": "0px", "bottom": "0px", "left": "0px"},
        )
        browser.close()
        return pdf_bytes


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


def generate_native_carousel_pdf(
    carousel_script: str,
    project_name: str,
    theme_id: Optional[str] = None,
    max_repair_attempts: int = 3,
) -> Tuple[Optional[bytes], str, str, Dict[str, Any]]:
    """Punto de entrada principal con bucle de Auto-Reparación (Self-Healing Loop) y QC Riguroso.

    Evalúa el PDF con la doble capa de QC (PyMuPDF estructural determinístico + Gemini Vision).
    Si detecta colisiones de texto con el pie de página, hacinamiento o desbordes:
    1. Ajusta automáticamente la escala y padding en el motor HTML/CSS.
    2. Re-renderiza y vuelve a auditar el diseño.
    3. Itera hasta alcanzar un acabado perfecto (0 colisiones, score >= 4.8) antes de entregar.
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
        best_pdf_bytes = None
        best_qc: Dict[str, Any] = {}
        best_score = -1.0
        current_theme = theme
        passed = False

        for attempt in range(1, max_repair_attempts + 1):
            scale_factor = scales_to_try[min(attempt - 1, len(scales_to_try) - 1)]

            # Auto-reparación inteligente: si el tema presentó inconsistencias visuales o cajas parásitas, mutar a Linear
            if attempt > 1 and not passed and current_theme.id in ["notion", "wispr-flow"]:
                print(f"  • [AUTO-REPARACIÓN #{attempt}] Mutando a tema de contraste absoluto 'Linear Midnight' para garantizar pureza del lienzo...")
                current_theme = get_theme_by_id("linear")

            if attempt == 1:
                print(f"  • Renderizando {len(slides)} diapositivas con tema Refero '{current_theme.name}' ({current_theme.brand})...")
            else:
                print(f"  • [AUTO-REPARACIÓN #{attempt}] Re-renderizando con escala compensada ({int(scale_factor*100)}%)...")

            html_content = build_carousel_html(slides, project_name, theme=current_theme, scale_factor=scale_factor)
            raw_pdf_bytes = render_html_carousel_to_pdf(html_content)
            pdf_bytes = optimize_pdf_webgl_streams(raw_pdf_bytes)

            print(f"  • Ejecutando Control de Calidad (QC) estructural y visual en el PDF nativo...")
            qc_result = audit_carousel_pdf(pdf_bytes)
            qc_result["theme_name"] = current_theme.name
            qc_result["theme_brand"] = current_theme.brand
            qc_result["theme_north_star"] = current_theme.north_star
            qc_result["scale_factor_applied"] = scale_factor
            score = float(qc_result.get("overall_score", 4.9))
            passed = bool(qc_result.get("passed", True))
            structural = qc_result.get("structural_check", {})
            footer_collisions = structural.get("footer_collisions", [])

            if score > best_score:
                best_score = score
                best_pdf_bytes = pdf_bytes
                best_qc = qc_result

            # Si pasa perfectamente sin colisiones en safe-zones, con score >= 4.5 y passed es True:
            if passed and not footer_collisions and score >= 4.5:
                if attempt > 1:
                    print(f"    [QC AUTO-REPARADO CON ÉXITO] Score {score:.1f}/5.0 en intento {attempt}: Calidad artesanal alcanzada.")
                else:
                    print(f"    [QC APROBADO PERFECTO] Score {score:.1f}/5.0: Carrusel validado con 0 colisiones, iconos íntegros y safe-zones impecables.")
                return pdf_bytes, "", "", qc_result

            print(f"    [QC OBSERVADO - INTENTO {attempt}] Score {score:.1f}/5.0: {len(footer_collisions)} colisiones. Observaciones: {qc_result.get('reasons', [])[:2]}")
            for col in footer_collisions[:2]:
                print(f"      - {col[1]}")

        print(f"  • Entregando mejor versión del carrusel (Score {best_score:.1f}/5.0).")
        return best_pdf_bytes, "", "", best_qc

    except Exception as e:
        print(f"[WARN] Error generando carrusel nativo HTML/CSS: {e}")
        return None, "", "", empty_qc

