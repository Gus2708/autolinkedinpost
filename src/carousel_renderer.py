"""Módulo de renderizado nativo HTML/CSS a PDF para carruseles de LinkedIn e Instagram.

Genera carruseles multipágina de altísima calidad visual (1080x1350 px, formato 4:5 vertical)
utilizando HTML5, CSS Flexbox moderno, Google Fonts y Playwright Chromium.
Elimina la necesidad de APIs externas o tokens de Canva que expiren.
"""

import html
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from playwright.sync_api import sync_playwright

from src.pdf_evaluator import audit_carousel_pdf
from src.theme_manager import get_rotating_theme, get_theme_by_id, DesignTheme


def parse_carousel_slides(carousel_script: str) -> List[Dict[str, str]]:
    """Extrae de forma robusta las 10 diapositivas del guion generado.

    Ignora preámbulos, limpia etiquetas de corchetes [PORTADA], [PROBLEMA], etc.
    """
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
        cleaned_lines = []
        for l in lines:
            tag_match = re.match(r"^\[(.*?)\]$", l)
            if tag_match:
                tag_str = tag_match.group(1).strip()
                # Filtrar tags genéricos de IA que afean el diseño
                if tag_str.upper() not in ["PORTADA", "COVER", "SLIDE 1", "DIAPOSITIVA 1", "TITULO", "TÍTULO"]:
                    category = tag_str
                continue
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
        })

    return slides


def build_carousel_html(
    slides: List[Dict[str, str]],
    project_name: str,
    author_title: str = "Tech Lead & Software Engineer",
    theme: Optional[DesignTheme] = None,
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
        is_bullet_list = any(re.match(r"^[-*•\d\.]\s+", l) for l in body_lines)

        if is_bullet_list:
            items_html = []
            for bl in body_lines:
                clean_item = re.sub(r"^[-*•\d\.]\s+", "", bl).strip()
                item_esc = html.escape(clean_item)
                item_styled = re.sub(
                    r"(?i)\b(react native|expo|supabase|postgresql|zustand|tanstack query|cache|realtime|rollback|latencia|concurrencia|offline-first|tablet-first|api|docker|python|gemini|llm)\b",
                    r"<strong>\1</strong>",
                    item_esc,
                )
                items_html.append(f"<li><span class='bullet-icon'><i data-lucide='chevron-right'></i></span><span>{item_styled}</span></li>")
            card_content = f"<ul class='card-list'>{''.join(items_html)}</ul>"
        else:
            body_escaped = html.escape(" ".join(body_lines))
            body_styled = re.sub(
                r"(?i)\b(react native|expo|supabase|postgresql|zustand|tanstack query|cache|realtime|rollback|latencia|concurrencia|offline-first|tablet-first|api|docker|python|gemini|llm)\b",
                r"<strong>\1</strong>",
                body_escaped,
            )
            card_content = f"<p>{body_styled}</p>"

        cta_action_html = ""
        if is_last:
            cta_action_html = """
                <div class="cta-action-box">
                    <span class="cta-action-icon"><i data-lucide='message-square'></i></span>
                    <span class="cta-action-text">Leave your opinion in the comments</span>
                </div>
            """

        swipe_text = "Deslizá ➔"
        if is_last:
            swipe_text = "Dejá tu comentario 💬"

        footer_right = f"<div class='swipe-hint'>{swipe_text}</div>"
        slide_class = "slide is-cover" if is_first else ("slide is-cta" if is_last else "slide")

        badge_icon = "sparkles"
        if is_first:
            badge_icon = "rocket"
        elif is_last:
            badge_icon = "message-circle"
        elif "problema" in cat.lower() or "problem" in cat.lower():
            badge_icon = "alert-triangle"
        elif "solución" in cat.lower() or "solution" in cat.lower():
            badge_icon = "lightbulb"
        elif "arquitectura" in cat.lower() or "architecture" in cat.lower():
            badge_icon = "layers"
        elif "dato" in cat.lower() or "data" in cat.lower():
            badge_icon = "database"

        slide_block = f"""
        <div class="{slide_class}">
            <div class="shader-bg" id="shader-bg-{idx}"></div>
            <div class="content-layer">
                <div class="header">
                    <div class="badge"><i data-lucide='{badge_icon}'></i> {html.escape(cat)}</div>
                    <div class="page-num">{idx:02d} / {total_slides:02d}</div>
                </div>
                
                <div class="content">
                    <h1 class="title">{title_styled}</h1>
                    <div class="card">
                        {card_content}
                        {cta_action_html}
                    </div>
                </div>
                
                <div class="footer">
                    <div class="author">{html.escape(author_title)}</div>
                    {footer_right}
                </div>
            </div>
        </div>
        """
        slides_html.append(slide_block)

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
    --accent-color: {theme.accent_color};
    --text-primary: {theme.text_primary};
    --text-muted: {theme.text_muted};
    --badge-bg: {theme.badge_bg};
    --badge-border: {theme.badge_border};
    --font-family: {theme.font_family};
    --font-mono: {theme.font_mono};
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

body {{
    background: var(--bg-color);
    font-family: var(--font-family);
    color: var(--text-primary);
    -webkit-print-color-adjust: exact;
}}

.slide {{
    width: 1080px;
    height: 1350px;
    position: relative;
    overflow: hidden;
    page-break-after: always;
    break-after: page;
    background: var(--bg-color);
}}

.shader-bg {{
    position: absolute;
    top: 0;
    left: 0;
    width: 1080px;
    height: 1350px;
    z-index: 1;
    pointer-events: none;
}}

.content-layer {{
    position: relative;
    z-index: 2;
    width: 1080px;
    height: 1350px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 100px 90px;
}}

.header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--card-border);
    padding-bottom: 30px;
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
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}

.badge svg {{
    width: 22px;
    height: 22px;
    stroke-width: 2.2px;
    flex-shrink: 0;
}}

.page-num {{
    font-family: var(--font-mono);
    font-size: 24px;
    color: var(--text-muted);
    font-weight: 600;
}}

.content {{
    margin-top: auto;
    margin-bottom: auto;
}}

.title {{
    font-size: 62px;
    font-weight: 800;
    line-height: 1.15;
    letter-spacing: -1.5px;
    color: var(--text-primary);
    margin-bottom: 44px;
}}

.title span.highlight {{
    color: var(--accent-color);
}}

.card {{
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-left: 5px solid var(--accent-color);
    border-radius: 18px;
    padding: 46px 50px;
}}

.card p {{
    font-size: 32px;
    line-height: 1.55;
    color: var(--text-muted);
    font-weight: 400;
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
    gap: 18px;
}}

.card-list li {{
    font-size: 30px;
    line-height: 1.5;
    color: var(--text-muted);
    display: flex;
    align-items: flex-start;
    gap: 16px;
}}

.card-list .bullet-icon {{
    color: var(--accent-color);
    font-size: 24px;
    line-height: 1.5;
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    margin-top: 6px;
}}

.card-list .bullet-icon svg {{
    width: 24px;
    height: 24px;
    stroke-width: 2.5px;
}}

.cta-action-box {{
    margin-top: 28px;
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
    width: 32px;
    height: 32px;
    stroke-width: 2px;
}}

.cta-action-text {{
    font-size: 25px;
    font-weight: 700;
    color: var(--accent-color);
}}

.slide.is-cover .title {{
    font-size: 68px;
    letter-spacing: -2px;
    line-height: 1.12;
}}

.footer {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid var(--card-border);
    padding-top: 30px;
}}

.author {{
    font-size: 22px;
    color: var(--text-muted);
    font-weight: 600;
}}

.swipe-hint {{
    font-size: 22px;
    color: var(--accent-color);
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 8px;
}}
</style>
</head>
<body>
{"".join(slides_html)}

<script type="module">
import {{
    ShaderMount,
    meshGradientFragmentShader,
    neuroNoiseFragmentShader,
    getShaderColorFromString,
    ShaderFitOptions
}} from 'https://cdn.jsdelivr.net/npm/@paper-design/shaders@0.0.80/dist/index.js';

// Initialize Lucide icons
if (typeof lucide !== 'undefined') {{
    lucide.createIcons({{ attrs: {{ width: 16, height: 16, 'stroke-width': 2 }} }});
}}

const shaderType = '{theme.shader_type}';
const colorPalettes = {shader_palettes_json};

for (let i = 1; i <= {total_slides}; i++) {{
    const container = document.getElementById(`shader-bg-${{i}}`);
    if (!container) continue;

    let palette = colorPalettes[2];
    if (i === 1) palette = colorPalettes[0];
    else if (i <= 3) palette = colorPalettes[1];
    else if (i >= {total_slides} - 1) palette = colorPalettes[3];

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
            u_rotation: (i * 37) % 360,
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
            u_rotation: (i * 37) % 360,
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
        pdf_bytes = page.pdf(
            width="1080px",
            height="1350px",
            print_background=True,
            margin={"top": "0px", "right": "0px", "bottom": "0px", "left": "0px"},
        )
        browser.close()
        return pdf_bytes


def generate_native_carousel_pdf(
    carousel_script: str,
    project_name: str,
    theme_id: Optional[str] = None,
) -> Tuple[Optional[bytes], str, str, Dict[str, Any]]:
    """Punto de entrada principal para generar el carrusel en PDF nativo HTML/CSS con rotación de temas de styles.refero.design."""
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

        print(f"  • Renderizando {len(slides)} diapositivas con tema Refero '{theme.name}' ({theme.brand})...")
        html_content = build_carousel_html(slides, project_name, theme=theme)
        pdf_bytes = render_html_carousel_to_pdf(html_content)

        print(f"  • Ejecutando Control de Calidad (QC) estructural y visual en el PDF nativo...")
        qc_result = audit_carousel_pdf(pdf_bytes)
        qc_result["theme_name"] = theme.name
        qc_result["theme_brand"] = theme.brand
        qc_result["theme_north_star"] = theme.north_star
        score = qc_result.get("overall_score", 4.9)
        passed = qc_result.get("passed", True)

        if passed:
            print(f"    [QC APROBADO] Score {score:.1f}/5.0: Carrusel nativo 4:5 validado con estilo '{theme.name}'.")
        else:
            print(f"    [QC OBSERVADO] Score {score:.1f}/5.0: {qc_result.get('reasons')}")

        return pdf_bytes, "", "", qc_result

    except Exception as e:
        print(f"[WARN] Error generando carrusel nativo HTML/CSS: {e}")
        return None, "", "", empty_qc
