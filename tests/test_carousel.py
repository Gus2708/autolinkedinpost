"""Tests del renderizador de carruseles: parseo del guion, iconos, i18n y rotación de temas."""

from datetime import date
import re

import pytest

from src.carousel_renderer import (
    build_carousel_html,
    get_carousel_strings,
    normalize_lucide_icon,
    parse_carousel_slides,
    render_inline_markdown,
    resolve_lucide_icon,
    strip_block_markdown,
)
from src.pdf_evaluator import (
    _text_belongs_to_box,
    find_empty_containers,
    summarize_qc_issues,
    validate_pdf_structure,
)
from src.theme_manager import REFERO_THEMES, get_rotating_theme, get_theme_by_id


class TestParseCarouselSlides:
    def test_parses_spanish_delimiters(self):
        script = """
--- DIAPOSITIVA 1 / 3 ---
[PORTADA | rocket]
Migrando el cache a Redis
Bajamos la latencia de 400ms a 60ms.

--- DIAPOSITIVA 2 / 3 ---
[PROBLEMA | alert-triangle]
El cuello de botella
- [ICON: database] Consultas N+1 en el agregado
- Sin indice compuesto

--- DIAPOSITIVA 3 / 3 ---
[CTA | message-square]
Que harias vos?
"""
        slides = parse_carousel_slides(script)
        assert len(slides) == 3
        assert slides[0]["title"] == "Migrando el cache a Redis"
        assert slides[0]["icon"] == "rocket"
        assert slides[1]["category"] == "PROBLEMA"
        assert "Consultas N+1" in slides[1]["body"]

    def test_parses_english_delimiters(self):
        script = """
--- SLIDE 1 / 2 ---
[COVER | rocket]
Cutting p99 latency

--- SLIDE 2 / 2 ---
[CTA | message-square]
Your take?
"""
        slides = parse_carousel_slides(script)
        assert len(slides) == 2
        assert slides[0]["title"] == "Cutting p99 latency"

    def test_returns_empty_without_delimiters(self):
        assert parse_carousel_slides("Un texto cualquiera sin estructura") == []

    def test_inline_icon_is_stripped_from_title(self):
        script = "--- DIAPOSITIVA 1 / 1 ---\n[ICON: database] El titulo real"
        slides = parse_carousel_slides(script)
        assert slides[0]["icon"] == "database"
        assert "[ICON" not in slides[0]["title"]


class TestMarkdownCleanup:
    """Regresión detectada por la auditoría visual del run 33224143511: los modelos
    devuelven el guion con Markdown y los '##', '>', '**' y backticks se imprimían
    crudos en el PDF final."""

    def test_strips_heading_prefix(self):
        assert strip_block_markdown("## El cuello de botella") == "El cuello de botella"
        assert strip_block_markdown("###### Titulo") == "Titulo"

    def test_strips_blockquote_prefix(self):
        assert strip_block_markdown("> Una cita del analisis") == "Una cita del analisis"
        assert strip_block_markdown("> > Anidada") == "Anidada"

    def test_leaves_plain_text_untouched(self):
        assert strip_block_markdown("Un titulo normal") == "Un titulo normal"
        assert strip_block_markdown("") == ""

    def test_hash_inside_text_is_preserved(self):
        """Un '#' que no es prefijo de encabezado no debe tocarse."""
        assert strip_block_markdown("Issue #42 resuelto") == "Issue #42 resuelto"

    def test_bold_becomes_strong(self):
        assert render_inline_markdown("un **cambio** importante") == "un <strong>cambio</strong> importante"
        assert render_inline_markdown("un __cambio__ importante") == "un <strong>cambio</strong> importante"

    def test_code_becomes_code_tag(self):
        assert render_inline_markdown("usa `redis.get()` aca") == "usa <code>redis.get()</code> aca"

    def test_italic_becomes_em(self):
        assert render_inline_markdown("es *muy* rapido") == "es <em>muy</em> rapido"

    def test_link_keeps_only_the_text(self):
        assert render_inline_markdown("ver [la doc](https://x.com/y)") == "ver la doc"

    def test_strikethrough_is_removed(self):
        assert render_inline_markdown("~~viejo~~ nuevo") == "viejo nuevo"

    def test_bold_wins_over_italic(self):
        """'**' contiene '*': el orden de aplicacion importa."""
        assert render_inline_markdown("**doble**") == "<strong>doble</strong>"

    def test_multiplication_is_not_italic(self):
        assert render_inline_markdown("3 * 4 * 5") == "3 * 4 * 5"

    def test_snake_case_is_not_italic(self):
        assert render_inline_markdown("la var some_long_name aca") == "la var some_long_name aca"

    def test_empty_input(self):
        assert render_inline_markdown("") == ""

    def test_no_raw_markdown_reaches_the_slides(self):
        """Prueba de extremo a extremo sobre el HTML renderizado."""
        script = """--- DIAPOSITIVA 1 / 2 ---
[PROBLEMA | bug]
## El cuello de botella
> El agregado hacia una consulta por workspace.
- **N+1**: consultas sobre la tabla
* Sin `indice compuesto` en la query
- Ver [la doc](https://ejemplo.com) para el detalle
--- DIAPOSITIVA 2 / 2 ---
[CTA | message-square]
Y vos?
"""
        html = build_carousel_html(parse_carousel_slides(script), "user/repo", language="es")
        # Excluir script y style: los template literals de JS usan backticks legitimos.
        visible = re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S)

        assert "&gt;" not in visible, "blockquote crudo en la lamina"
        assert "**" not in visible, "negrita cruda en la lamina"
        assert "##" not in visible, "encabezado crudo en la lamina"
        assert "`" not in visible, "backtick crudo en la lamina"
        assert "](http" not in visible, "link markdown crudo en la lamina"

        # Y el enfasis se conserva convertido a HTML real.
        assert "<strong>N+1</strong>" in visible
        assert "<code>indice compuesto</code>" in visible
        assert "la doc" in visible

    def test_title_loses_its_heading_prefix(self):
        slides = parse_carousel_slides("--- DIAPOSITIVA 1 / 1 ---\n## Un titulo\nCuerpo.")
        assert slides[0]["title"] == "Un titulo"

    def test_bullet_dash_is_not_treated_as_heading(self):
        """El guion inicial de una vineta es su marcador, no Markdown de bloque."""
        slides = parse_carousel_slides("--- DIAPOSITIVA 1 / 1 ---\nTitulo\n- Primera\n- Segunda")
        assert "- Primera" in slides[0]["body"]


class TestResolveLucideIcon:
    def test_explicit_icon_wins(self):
        slide = {"icon": "database", "title": "algo", "body": ""}
        assert resolve_lucide_icon(slide, 3, 10) == "database"

    def test_first_and_last_have_fixed_icons(self):
        blank = {"icon": "", "title": "", "body": ""}
        assert resolve_lucide_icon(blank, 1, 10) == "rocket"
        assert resolve_lucide_icon(blank, 10, 10) == "message-square-code"

    def test_semantic_match_from_body(self):
        slide = {"icon": "", "category": "", "title": "Optimizando queries", "body": "indices en postgres"}
        assert resolve_lucide_icon(slide, 4, 10) == "database"

    def test_unknown_content_falls_back(self):
        slide = {"icon": "", "category": "", "title": "zzz", "body": "qqq"}
        assert resolve_lucide_icon(slide, 4, 10) == "sparkles"

    def test_aliases_normalize(self):
        assert normalize_lucide_icon("gear") == "settings"
        assert normalize_lucide_icon("WARNING") == "alert-triangle"
        assert normalize_lucide_icon(None) == "sparkles"


class TestCarouselStrings:
    """El renderer tenía los textos en duro en español: --lang en daba un PDF en español."""

    def test_english_strings(self):
        s = get_carousel_strings("en")
        assert s["swipe"] == "Swipe ➔"
        assert s["html_lang"] == "en"

    def test_spanish_is_default(self):
        assert get_carousel_strings("es")["swipe"] == "Deslizá ➔"
        assert get_carousel_strings("")["html_lang"] == "es"

    def test_both_languages_define_the_same_keys(self):
        assert set(get_carousel_strings("es")) == set(get_carousel_strings("en"))


class TestThemeRotation:
    """El índice vivía en un archivo gitignoreado: en CI siempre arrancaba en 0."""

    def test_rotates_across_consecutive_days(self):
        names = {
            get_rotating_theme(seed="user/repo", today=date(2026, 9, day)).name
            for day in range(1, len(REFERO_THEMES) + 1)
        }
        assert len(names) == len(REFERO_THEMES)

    def test_deterministic_for_same_inputs(self):
        a = get_rotating_theme(seed="user/repo", today=date(2026, 9, 1))
        b = get_rotating_theme(seed="user/repo", today=date(2026, 9, 1))
        assert a.id == b.id

    def test_no_disk_state_required(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert get_rotating_theme(seed="user/repo", today=date(2026, 9, 1)) is not None

    def test_get_theme_by_id(self):
        assert get_theme_by_id("linear").id == "linear"
        assert get_theme_by_id("no-existe").id == REFERO_THEMES[0].id


class TestSummarizeQcIssues:
    """Un badge "⚠️ 3.8/5.0" sin explicación no es accionable: el lector no sabe si
    mirar el texto, los márgenes o los iconos."""

    def test_structural_errors_have_priority(self):
        qc = {
            "structural_check": {"errors": ["El carrusel tiene solo 3 página(s)."]},
            "visual_check": {"issues_detected": ["algo visual"]},
        }
        assert "solo 3 página(s)" in summarize_qc_issues(qc)

    def test_falls_back_to_visual_issues(self):
        qc = {
            "structural_check": {"errors": []},
            "visual_check": {"issues_detected": ["Icono ausente", "Texto cortado"]},
        }
        motivo = summarize_qc_issues(qc)
        assert "Icono ausente" in motivo and "Texto cortado" in motivo

    def test_falls_back_to_worst_criterion(self):
        qc = {
            "structural_check": {"errors": []},
            "visual_check": {
                "issues_detected": [],
                "criteria": {
                    "canvas_color_cohesion": {"score": 5.0, "feedback": "perfecta"},
                    "typography_and_materials": {"score": 2.5, "feedback": "markdown crudo visible"},
                },
            },
        }
        motivo = summarize_qc_issues(qc)
        assert "Tipografía y materiales" in motivo
        assert "2.5" in motivo
        assert "markdown crudo" in motivo

    def test_falls_back_to_summary(self):
        qc = {"structural_check": {"errors": []}, "visual_check": {"summary": "Resumen del veredicto."}}
        assert summarize_qc_issues(qc) == "Resumen del veredicto."

    def test_truncates_on_word_boundary(self):
        largo = " ".join(["palabra"] * 80)
        qc = {"structural_check": {"errors": []}, "visual_check": {"summary": largo}}
        motivo = summarize_qc_issues(qc, max_len=50)
        assert len(motivo) <= 51           # 50 + el carácter de elipsis
        assert motivo.endswith("…")
        assert not motivo.replace("…", "").endswith("palabr")  # no corta a mitad

    def test_empty_input(self):
        assert summarize_qc_issues({}) == ""
        assert summarize_qc_issues(None) == ""

    def test_ignores_non_numeric_scores(self):
        qc = {
            "structural_check": {"errors": []},
            "visual_check": {"issues_detected": [], "criteria": {"x": {"score": None}, "y": "texto"}},
        }
        assert summarize_qc_issues(qc) == ""

    def test_real_case_markdown_leak(self):
        """El veredicto real que dejó el carrusel del 2026-08-29 en 3.8/5.0."""
        qc = {
            "structural_check": {"errors": []},
            "visual_check": {
                "issues_detected": ["Guiones de listas y símbolos de blockquote de Markdown visibles en el diseño"],
            },
        }
        motivo = summarize_qc_issues(qc)
        assert "Markdown" in motivo
        assert len(motivo) < 200


class TestEmptyCards:
    """Regresión visible en el carrusel del run 33227942657: la portada traía sólo
    título y se dibujaba una tarjeta gris de 280px sin una palabra adentro."""

    @staticmethod
    def _cajas_vacias(html_str: str) -> int:
        sin_contenido = re.findall(
            r'<div class="card[^"]*">\s*(?:<div class="terminal-bar".*?</div>)?\s*</div>',
            html_str,
            re.S,
        )
        return len(sin_contenido) + html_str.count("<p></p>")

    def test_cover_with_only_title_has_no_empty_card(self):
        script = "--- DIAPOSITIVA 1 / 2 ---\n[PORTADA | rocket]\nSolo un titulo\n--- DIAPOSITIVA 2 / 2 ---\n[CTA | message-square]\nCierre\n"
        html_str = build_carousel_html(parse_carousel_slides(script), "u/r", language="es")
        assert self._cajas_vacias(html_str) == 0

    def test_middle_slide_with_only_title_has_no_empty_card(self):
        script = (
            "--- DIAPOSITIVA 1 / 3 ---\n[P | rocket]\nTitulo\nSub.\n"
            "--- DIAPOSITIVA 2 / 3 ---\n[X | bug]\nSolo titulo aca\n"
            "--- DIAPOSITIVA 3 / 3 ---\n[CTA | message-square]\nCierre\n"
        )
        html_str = build_carousel_html(parse_carousel_slides(script), "u/r", language="es")
        assert self._cajas_vacias(html_str) == 0

    def test_cover_with_body_still_renders_its_card(self):
        script = "--- DIAPOSITIVA 1 / 2 ---\n[P | rocket]\nTitulo\nUn subtitulo real.\n--- DIAPOSITIVA 2 / 2 ---\n[CTA | message-square]\nCierre\n"
        html_str = build_carousel_html(parse_carousel_slides(script), "u/r", language="es")
        assert "cover-card" in html_str
        assert "Un subtitulo real" in html_str

    def test_cta_keeps_its_action_box_without_body(self):
        """La última lámina conserva su caja porque el CTA es contenido real."""
        script = "--- DIAPOSITIVA 1 / 2 ---\n[P | rocket]\nT\nSub.\n--- DIAPOSITIVA 2 / 2 ---\n[CTA | message-square]\nY vos?\n"
        html_str = build_carousel_html(parse_carousel_slides(script), "u/r", language="es")
        assert "cta-action-box" in html_str
        assert self._cajas_vacias(html_str) == 0

    def test_titleonly_slides_are_marked_for_centering(self):
        script = "--- DIAPOSITIVA 1 / 2 ---\n[P | rocket]\nSolo titulo\n--- DIAPOSITIVA 2 / 2 ---\n[CTA | message-square]\nCierre\n"
        html_str = build_carousel_html(parse_carousel_slides(script), "u/r", language="es")
        assert "is-titleonly" in html_str


class TestEmptyContainerDetection:
    """La capa estructural no veía cajas huecas: contaba palabras por página y la
    portada tenía suficientes. Ahora cruza geometría de formas contra bloques de texto."""

    @staticmethod
    def _pdf(con_texto_en_caja: bool) -> bytes:
        import pymupdf as fitz

        doc = fitz.open()
        page = doc.new_page(width=810, height=1012)
        page.draw_rect(fitz.Rect(0, 0, 810, 1012), color=None, fill=(0.04, 0.04, 0.04))
        page.insert_text((60, 80), "Titulo de la lamina", fontsize=28, color=(1, 1, 1))
        caja = fitz.Rect(60, 300, 750, 560)
        page.draw_rect(caja, color=None, fill=(0.09, 0.09, 0.10))
        if con_texto_en_caja:
            page.insert_text((90, 400), "Contenido real adentro", fontsize=18, color=(1, 1, 1))
        page.insert_text((60, 960), "github/usuario", fontsize=14, color=(0.6, 0.6, 0.6))
        data = doc.tobytes()
        doc.close()
        return data

    def _pagina(self, pdf_bytes):
        import pymupdf as fitz

        return fitz.open(stream=pdf_bytes, filetype="pdf")[0]

    def test_detects_container_without_content(self):
        assert len(find_empty_containers(self._pagina(self._pdf(False)))) == 1

    def test_ignores_container_with_content(self):
        assert find_empty_containers(self._pagina(self._pdf(True))) == []

    def test_adjacent_text_does_not_count_as_content(self):
        """Regresión: un título que arranca justo en el borde inferior de la caja
        hacía que `Rect.intersects` la diera por llena estando vacía."""
        import pymupdf as fitz

        caja = fitz.Rect(52, 376, 757, 586)
        titulo_pegado = fitz.Rect(52, 586, 400, 656)   # empieza donde termina la caja
        assert _text_belongs_to_box(titulo_pegado, caja) is False

    def test_text_inside_counts_as_content(self):
        import pymupdf as fitz

        caja = fitz.Rect(52, 376, 757, 586)
        adentro = fitz.Rect(90, 420, 500, 470)
        assert _text_belongs_to_box(adentro, caja) is True

    def test_page_background_is_not_flagged(self):
        """El lienzo de la lámina es un rectángulo relleno enorme: no es una tarjeta."""
        import pymupdf as fitz

        doc = fitz.open()
        page = doc.new_page(width=810, height=1012)
        page.draw_rect(fitz.Rect(0, 0, 810, 1012), color=None, fill=(0.04, 0.04, 0.04))
        page.insert_text((60, 500), "Solo un titulo centrado", fontsize=28, color=(1, 1, 1))
        data = doc.tobytes()
        doc.close()
        assert find_empty_containers(fitz.open(stream=data, filetype="pdf")[0]) == []

    def test_small_decorations_are_not_flagged(self):
        """Badges y viñetas son rectángulos chicos, no contenedores de contenido."""
        import pymupdf as fitz

        doc = fitz.open()
        page = doc.new_page(width=810, height=1012)
        page.draw_rect(fitz.Rect(0, 0, 810, 1012), color=None, fill=(0.04, 0.04, 0.04))
        page.draw_rect(fitz.Rect(53, 53, 331, 96), color=None, fill=(0.09, 0.09, 0.10))
        page.insert_text((60, 500), "Titulo", fontsize=28, color=(1, 1, 1))
        data = doc.tobytes()
        doc.close()
        assert find_empty_containers(fitz.open(stream=data, filetype="pdf")[0]) == []

    def test_reported_as_structural_error(self):
        result = validate_pdf_structure(self._pdf(False), min_pages=1)
        assert result["passed"] is False
        assert result["empty_containers"]
        assert any("sin contenido" in e for e in result["errors"])
