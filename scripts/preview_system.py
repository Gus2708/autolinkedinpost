#!/usr/bin/env python
"""Renderiza una muestra de láminas con un sistema de diseño, para verlas.

Herramienta de trabajo: el diseño se juzga mirándolo, no leyendo el CSS.

Uso:
    python scripts/preview_system.py editorial
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import html as html_mod

import pymupdf as fitz
from playwright.sync_api import sync_playwright

from src.design_systems import get_system_by_id

# Contenido de muestra: una portada, una lámina de métrica, una de lista y un cierre.
MUESTRA = [
    {
        "kind": "cover",
        "eyebrow": "Arquitectura",
        "title": "Migré el cache a Redis",
        "lede": "Bajé la latencia p99 de 400 ms a 60 ms sin tocar el modelo de datos.",
    },
    {
        "kind": "metric",
        "eyebrow": "El síntoma",
        "metric": "400ms",
        "metric_note": "El p99 del agregado de facturación bajo carga concurrente. Una consulta por cada workspace del tenant.",
    },
    {
        "kind": "list",
        "eyebrow": "La decisión",
        "title": "Redis sobre memoria local",
        "lede": "El proceso escala horizontal, así que un cache en memoria se duplicaba en cada réplica.",
        "items": [
            "TTL de 300 s con invalidación por evento, no por tiempo.",
            "Lock distribuido corto para el <em>thundering herd</em> al expirar.",
            "Jitter en el TTL para que las réplicas no expiren a la vez.",
        ],
    },
    {
        "kind": "cta",
        "eyebrow": "Tu turno",
        "title": "¿Cache local o distribuido?",
        "lede": "Redis suma un salto de red y una dependencia operativa. ¿Con qué criterio decidís vos?",
    },
]


def render_slide(system, slide, idx, total):
    """Arma el HTML de una lámina según su tipo."""
    eyebrow = html_mod.escape(slide.get("eyebrow", ""))
    folio = f"{idx:02d} / {total:02d}"
    kind = slide.get("kind", "list")

    if kind == "cover":
        cuerpo = f"""
            <h1 class="title">{slide['title']}</h1>
            <p class="lede">{slide['lede']}</p>"""
    elif kind == "metric":
        cuerpo = f"""
            <div class="metric">{slide['metric']}</div>
            <p class="metric-note">{slide['metric_note']}</p>"""
    elif kind == "cta":
        cuerpo = f"""
            <h1 class="title">{slide['title']}</h1>
            <p class="lede">{slide['lede']}</p>"""
    else:
        items = "".join(f'<div class="item"><span>{i}</span></div>' for i in slide.get("items", []))
        cuerpo = f"""
            <h1 class="title">{slide['title']}</h1>
            <p class="lede">{slide['lede']}</p>
            <div class="items">{items}</div>"""

    cue = "Deslizá ➔" if idx < total else "Comentá 💬"
    clase = f"slide sys-{system.id}" + (" is-cover" if kind == "cover" else "")

    return f"""
    <div class="{clase}">
        <div class="content-layer">
            <div class="header">
                <div class="eyebrow">{eyebrow}</div>
                <div class="folio">{folio}</div>
            </div>
            <div class="content">{cuerpo}</div>
            <div class="footer">
                <span>github/Gus2708</span>
                <span class="cue">{cue}</span>
            </div>
        </div>
    </div>"""


def build(system):
    tokens = "\n".join(f"    --{k}: {v};" for k, v in system.tokens.items())
    slides = "".join(render_slide(system, s, i, len(MUESTRA)) for i, s in enumerate(MUESTRA, 1))
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<link rel="stylesheet" href="{system.fonts_url}">
<style>
:root {{
{tokens}
}}
@page {{ size: 1080px 1350px; margin: 0; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ width: 1080px; background: var(--bg); font-size: 0; }}
.slide {{
    position: relative; width: 1080px; height: 1350px;
    overflow: hidden; background: var(--bg); font-size: 16px;
}}
.slide:not(:last-child) {{ page-break-after: always; break-after: page; }}
.content-layer {{
    width: 1080px; height: 1350px;
    display: flex; flex-direction: column; justify-content: space-between;
}}
.content {{ flex: 1; }}
{system.css}
</style></head><body>{slides}</body></html>"""


def main():
    system = get_system_by_id(sys.argv[1] if len(sys.argv) > 1 else "editorial")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1080, "height": 1350})
            page.set_content(build(system), wait_until="load", timeout=45000)
            page.wait_for_function("document.fonts.ready.then(()=>true)", timeout=20000)
            pdf = page.pdf(width="1080px", height="1350px", print_background=True,
                           margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        finally:
            browser.close()

    doc = fitz.open(stream=pdf, filetype="pdf")
    for i, page in enumerate(doc, 1):
        page.get_pixmap(dpi=52).save(f"preview_{system.id}_{i}.png")
    doc.close()
    print(f"{len(MUESTRA)} láminas -> preview_{system.id}_N.png")


if __name__ == "__main__":
    main()
