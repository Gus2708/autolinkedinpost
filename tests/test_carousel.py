"""Tests del renderizador: parseo del guion, composición por sistema de diseño e i18n."""

import os
import re
from datetime import date

import pytest

from src.carousel_renderer import (
    build_carousel_html,
    classify_slide,
    is_metric,
    split_body,
    get_carousel_strings,
    parse_carousel_slides,
    is_horizontal_rule,
    is_structure_label,
    render_inline_markdown,
    strip_block_markdown,
    title_scale,
)
from src.design_systems import DESIGN_SYSTEMS, get_rotating_system, get_system_by_id
from src.pdf_evaluator import (
    _text_belongs_to_box,
    find_text_overlaps,
    find_empty_containers,
    summarize_qc_issues,
    validate_pdf_structure,
)


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


class TestHorizontalRules:
    """El juez visual reportó "contenido incompleto, múltiples '---' truncados":
    un separador de Markdown sobrevivía al parseo y se imprimía en la lámina."""

    @pytest.mark.parametrize("linea", ["---", "----", "***", "___", "  ---  ", "-----------"])
    def test_detects_separators(self, linea):
        assert is_horizontal_rule(linea) is True

    @pytest.mark.parametrize("linea", ["- Una viñeta", "-- texto", "texto --- mas texto", "", "Titulo"])
    def test_ignores_real_content(self, linea):
        assert is_horizontal_rule(linea) is False

    def test_separator_never_reaches_the_slide(self):
        script = (
            "--- DIAPOSITIVA 1 / 2 ---\n[P | rocket]\nTitulo\nCuerpo real.\n---\n"
            "--- DIAPOSITIVA 2 / 2 ---\n[CTA | message-square]\nCierre\nTexto.\n"
        )
        for slide in parse_carousel_slides(script):
            assert "---" not in slide["title"]
            assert "---" not in slide["body"]

    def test_bullet_dash_survives(self):
        """Un guion de viñeta no es un separador."""
        script = "--- DIAPOSITIVA 1 / 1 ---\nTitulo\n- Primera viñeta\n- Segunda\n"
        assert "- Primera" in parse_carousel_slides(script)[0]["body"]


class TestStructureLabels:
    """Regresión del carrusel del 2026-08-29: las diez láminas mostraban la etiqueta
    'TÍTULO:' como título, porque el modelo la emite en línea propia y el parser
    tomaba la primera línea del bloque tal cual."""

    @pytest.mark.parametrize(
        "linea",
        ["TÍTULO:", "TITULO:", "TÍTULO PORTADA:", "SUBTÍTULO:", "CONTENIDO:",
         "CUERPO:", "TITLE:", "CONTENT:", "**TÍTULO:**", "  CONTENIDO:  ", "VIÑETAS:"],
    )
    def test_detects_labels(self, linea):
        assert is_structure_label(linea) is True

    @pytest.mark.parametrize(
        "linea",
        ["El Sintoma Silencioso", "Titulo real de la lamina", "- Una viñeta",
         "El contenido tecnico del post", "Contenido que sigue en la frase"],
    )
    def test_ignores_real_content(self, linea):
        assert is_structure_label(linea) is False

    def test_label_on_its_own_line(self):
        script = "--- DIAPOSITIVA 1 / 1 ---\nTÍTULO:\nEl Sintoma Silencioso\nCONTENIDO:\nEl cuerpo real.\n"
        slide = parse_carousel_slides(script)[0]
        assert slide["title"] == "El Sintoma Silencioso"
        assert "CONTENIDO" not in slide["body"]
        assert "El cuerpo real." in slide["body"]

    def test_label_inline_with_text(self):
        script = "--- DIAPOSITIVA 1 / 1 ---\nTÍTULO: Tu Turno\nCONTENIDO: Que estrategia usas?\n"
        slide = parse_carousel_slides(script)[0]
        assert slide["title"] == "Tu Turno"
        assert slide["body"] == "Que estrategia usas?"

    def test_cover_label_variant(self):
        script = "--- DIAPOSITIVA 1 / 1 ---\nTÍTULO PORTADA:\nDebuggeando un Bot\nSUBTÍTULO:\nEl subtitulo.\n"
        slide = parse_carousel_slides(script)[0]
        assert slide["title"] == "Debuggeando un Bot"
        assert slide["body"] == "El subtitulo."

    def test_no_label_still_works(self):
        """El formato sin rótulos, que ya funcionaba, no debe cambiar."""
        script = "--- DIAPOSITIVA 1 / 1 ---\nTitulo directo\nCuerpo directo.\n- Una viñeta\n"
        slide = parse_carousel_slides(script)[0]
        assert slide["title"] == "Titulo directo"
        assert "Cuerpo directo." in slide["body"]

    def test_labels_never_reach_the_rendered_slide(self):
        script = (
            "--- DIAPOSITIVA 1 / 2 ---\n[P | rocket]\nTÍTULO PORTADA:\nMi Titulo\nSUBTÍTULO:\nMi subtitulo.\n"
            "--- DIAPOSITIVA 2 / 2 ---\n[CTA | message-square]\nTÍTULO:\nCierre\nCONTENIDO:\nTexto final.\n"
        )
        html_str = build_carousel_html(parse_carousel_slides(script), "u/r", language="es")
        visible = re.sub(r"<script.*?</script>|<style.*?</style>", "", html_str, flags=re.S)
        for etiqueta in ("TÍTULO", "SUBTÍTULO", "CONTENIDO"):
            assert etiqueta not in visible, f"la etiqueta {etiqueta} llegó a la lámina"
        assert "Mi Titulo" in visible and "Cierre" in visible


class TestSlideClassification:
    """El tipo de lámina sale del contenido, no de la posición: antes todas usaban
    el mismo molde de título más tarjeta y las diez se veían iguales."""

    @pytest.mark.parametrize("texto", ["400ms", "94%", "3.2x", "60 ms", "1.5s", "12k", "<100ms"])
    def test_detects_metrics(self, texto):
        assert is_metric(texto) is True

    @pytest.mark.parametrize(
        "texto",
        ["El cuello de botella", "Redis sobre memoria local", "", "Bajé a 60ms la latencia p99"],
    )
    def test_ignores_prose(self, texto):
        assert is_metric(texto) is False

    def test_first_slide_is_cover(self):
        assert classify_slide({"title": "Lo que sea"}, 1, 5) == "cover"

    def test_metric_title_gets_its_own_composition(self):
        assert classify_slide({"title": "400ms", "body": "El p99."}, 2, 5) == "metric"

    def test_bullets_make_a_list(self):
        assert classify_slide({"title": "T", "body": "Intro.\n- Uno\n- Dos"}, 3, 5) == "list"

    def test_plain_text_is_a_statement(self):
        assert classify_slide({"title": "T", "body": "Sólo un párrafo."}, 3, 5) == "statement"


class TestBodySplit:
    def test_separates_intro_from_bullets(self):
        intro, bullets = split_body("Un párrafo.\nOtro más.\n- Primera\n- Segunda")
        assert intro == ["Un párrafo.", "Otro más."]
        assert bullets == ["Primera", "Segunda"]

    def test_handles_only_intro(self):
        intro, bullets = split_body("Sólo texto corrido.")
        assert intro == ["Sólo texto corrido."] and bullets == []

    def test_empty_body(self):
        assert split_body("") == ([], [])


class TestDesignSystemRendering:
    SCRIPT = (
        "--- DIAPOSITIVA 1 / 3 ---\n[PORTADA | rocket]\nMigré el cache\nBajé el p99.\n"
        "--- DIAPOSITIVA 2 / 3 ---\n[SÍNTOMA | bug]\n400ms\nEl p99 bajo carga.\n"
        "--- DIAPOSITIVA 3 / 3 ---\n[CIERRE | message-square]\n¿Y vos?\nContame tu caso.\n"
    )

    @pytest.mark.parametrize("sid", ["editorial", "terminal", "swiss", "blueprint", "monograph", "linear"])
    def test_every_system_renders(self, sid):
        html_str = build_carousel_html(
            parse_carousel_slides(self.SCRIPT), "user/repo",
            system=get_system_by_id(sid), language="es",
        )
        assert f"sys-{sid}" in html_str
        # El vocabulario técnico se resalta con <strong>, así que se compara el texto plano.
        plano = re.sub(r"<[^>]+>", "", html_str)
        assert "Migré el cache" in plano and "400ms" in plano

    def test_no_cards_are_rendered(self):
        """El diseño se sostiene con tipografía: ya no hay contenedores."""
        for sid in ["editorial", "terminal", "swiss", "blueprint", "monograph", "linear"]:
            html_str = build_carousel_html(
                parse_carousel_slides(self.SCRIPT), "user/repo",
                system=get_system_by_id(sid), language="es",
            )
            assert 'class="card' not in html_str

    def test_no_webgl_canvas(self):
        """El mesh gradient genérico era el rasgo más reconocible de imagen de IA."""
        for sid in ["editorial", "terminal", "swiss", "blueprint", "monograph", "linear"]:
            html_str = build_carousel_html(
                parse_carousel_slides(self.SCRIPT), "user/repo",
                system=get_system_by_id(sid), language="es",
            )
            assert "shader" not in html_str.lower()
            assert "ShaderMount" not in html_str

    @pytest.mark.parametrize("sid", ["editorial", "terminal", "swiss", "blueprint", "monograph", "linear"])
    def test_metric_slide_uses_metric_markup(self, sid):
        html_str = build_carousel_html(
            parse_carousel_slides(self.SCRIPT), "user/repo",
            system=get_system_by_id(sid), language="es",
        )
        assert 'class="metric"' in html_str

    def test_systems_rotate_across_days(self):
        nombres = {
            get_rotating_system(seed="user/repo", today=date(2026, 9, d)).id
            for d in range(1, len(DESIGN_SYSTEMS) + 1)
        }
        assert len(nombres) == len(DESIGN_SYSTEMS)
        assert len(DESIGN_SYSTEMS) == 6

    def test_batch_rotation_avoids_collisions(self):
        """Múltiples proyectos en el mismo día no deben colisionar."""
        repos = [
            "user/repo-1", "user/repo-2", "user/repo-3",
            "user/repo-4", "user/repo-5", "user/repo-6"
        ]
        sistemas_en_lote = [
            get_rotating_system(seed=r, today=date(2026, 9, 1), index_offset=i).id
            for i, r in enumerate(repos)
        ]
        # Con index_offset, un lote de 6 proyectos cubre los 6 sistemas sin repetir
        assert len(set(sistemas_en_lote)) == 6

    def test_rotation_is_deterministic(self):
        a = get_rotating_system(seed="user/repo", today=date(2026, 9, 1))
        b = get_rotating_system(seed="user/repo", today=date(2026, 9, 1))
        assert a.id == b.id

    def test_fonts_avoid_the_ai_defaults(self):
        """Inter y Plus Jakarta Sans son las dos tipografías más usadas por
        interfaces generadas con IA: ningún sistema debe recurrir a ellas."""
        for system in DESIGN_SYSTEMS:
            tipografias = (system.fonts_url + str(system.tokens)).lower()
            for prohibida in ("inter:", "plus+jakarta", "dm+sans", "space+grotesk"):
                assert prohibida not in tipografias, f"{system.id} usa {prohibida}"


class TestBareUppercaseLabels:
    """Regresión del carrusel de WhatsApp Agent: el modelo emitió 'PORTADA' sin dos
    puntos y esa palabra terminó impresa como título de la lámina."""

    @pytest.mark.parametrize(
        "linea", ["PORTADA", "CIERRE", "TÍTULO", "CONTENIDO", "SUBTÍTULO", "CTA", "**PORTADA**", "COVER"]
    )
    def test_uppercase_labels_are_detected(self, linea):
        assert is_structure_label(linea) is True

    @pytest.mark.parametrize(
        "linea",
        ["Titulo", "Portada", "El bug silencioso", "Redis sobre memoria local",
         "400ms", "CACHE DISTRIBUIDO", "MIGRÉ EL CACHE"],
    )
    def test_real_content_survives(self, linea):
        """Un título legítimo en mayúsculas no debe confundirse con un rótulo."""
        assert is_structure_label(linea) is False

    def test_bare_label_yields_the_real_title(self):
        script = (
            "--- DIAPOSITIVA 1 / 2 ---\nPORTADA\nEl bug silencioso que rompió mi RAG\n"
            "Escribía ok true con cero vectores.\n"
            "--- DIAPOSITIVA 2 / 2 ---\nCIERRE\n¿Y vos qué harías?\n"
        )
        slides = parse_carousel_slides(script)
        assert slides[0]["title"] == "El bug silencioso que rompió mi RAG"
        assert slides[1]["title"] == "¿Y vos qué harías?"


class TestPromptFormat:
    """El prompt describía la estructura con etiquetas y el modelo las copiaba
    literalmente al guion en vez de escribir el contenido."""

    def test_prompts_show_an_explicit_example(self):
        from src.post_generator import (
            PROJECT_PROMPT_TEMPLATE_ES,
            PROJECT_PROMPT_TEMPLATE_EN,
            SHOWCASE_PROMPT_TEMPLATE_ES,
            SHOWCASE_PROMPT_TEMPLATE_EN,
        )
        for plantilla in (PROJECT_PROMPT_TEMPLATE_ES, SHOWCASE_PROMPT_TEMPLATE_ES):
            assert "FORMATO EXACTO DE CADA LÁMINA" in plantilla
            assert "PROHIBIDO describir el diseño" in plantilla
        for plantilla in (PROJECT_PROMPT_TEMPLATE_EN, SHOWCASE_PROMPT_TEMPLATE_EN):
            assert "EXACT SLIDE FORMAT" in plantilla
            assert "NEVER describe the design" in plantilla

    def test_prompts_no_longer_ask_for_icons(self):
        """El diseño nuevo no dibuja iconos: pedirlos sólo ensucia el guion."""
        from src import post_generator
        fuente = open(post_generator.__file__, encoding="utf-8").read()
        assert "lucide" not in fuente.lower()
        assert "[ICON:" not in fuente


class TestInlineCodeHuggesPunctuation:
    """Un chip de código seguido de puntuación no debe abrir un hueco antes del signo.

    El `<code>` lleva padding horizontal para que el chip respire, pero cuando lo
    sigue una coma o un punto ese padding se lee como un espacio tipográfico:
    "cero `ssh` , cero `unzip` ." El padding derecho se recorta sólo en ese caso.
    """

    def test_code_before_comma_is_marked_tight(self):
        salida = render_inline_markdown("cero `ssh`, cero `unzip`.")
        assert salida.count('<code class="tight">') == 2
        assert "</code>," in salida
        assert "</code>." in salida

    def test_code_before_a_word_keeps_its_padding(self):
        salida = render_inline_markdown("el archivo `servers.json` guarda la config")
        assert "<code>servers.json</code>" in salida
        assert "tight" not in salida

    def test_code_at_end_of_line_keeps_its_padding(self):
        assert render_inline_markdown("corré `pytest`") == "corré <code>pytest</code>"

    def test_closing_bracket_also_hugs(self):
        salida = render_inline_markdown("(ver `AGENTS.md`) y listo")
        assert '<code class="tight">AGENTS.md</code>)' in salida

    def test_code_content_is_untouched(self):
        salida = render_inline_markdown("usá `max-players=40`, nada más")
        assert ">max-players=40</code>," in salida


def _pdf_con_cabecera_invadida(invadir: bool) -> bytes:
    """Arma un carrusel 4:5 mínimo; en `invadir`, el título se encima sobre la cabecera."""
    import fitz

    doc = fitz.open()
    for i in range(6):
        page = doc.new_page(width=810, height=1013)
        if invadir and i == 2:
            # El título se monta sobre el eyebrow: mismas coordenadas, tamaños muy
            # distintos. Es el defecto real que llegó publicado en el carrusel de
            # sftp-manager, con el título tapando "BACKUPS AUTOMÁTICOS" y el folio.
            page.insert_text((66, 80), "BACKUPS AUTOMATICOS", fontsize=20)
            page.insert_text((600, 80), f"0{i + 1} / 06", fontsize=20)
            page.insert_text((66, 88), "Toda escritura guarda", fontsize=52)
        else:
            page.insert_text((66, 90), "SECCION", fontsize=20)
            page.insert_text((600, 90), f"0{i + 1} / 06", fontsize=20)
            page.insert_text((66, 400), "Titulo normal de la lamina", fontsize=44)
        user_handle = os.getenv("GITHUB_ACTOR") or os.getenv("GITHUB_USER") or "author"
        page.insert_text((66, 950), f"github/{user_handle}  Desliza", fontsize=16)
    datos = doc.tobytes()
    doc.close()
    return datos


class TestHeaderCollisionIsRepairable:
    """Invadir la cabecera debe pesar lo mismo que invadir el pie.

    Un texto que se mete en el footer generaba error y disparaba `reduce_scale`;
    el mismo desborde contra el header sólo dejaba un warning, así que el bucle de
    auto-reparación no se enteraba y la lámina encimada se publicaba igual.
    """

    def test_invaded_header_asks_for_a_scale_reduction(self):
        r = validate_pdf_structure(_pdf_con_cabecera_invadida(True))
        assert "reduce_scale" in r.get("repair_actions", [])

    def test_invaded_header_is_reported_as_an_error(self):
        r = validate_pdf_structure(_pdf_con_cabecera_invadida(True))
        assert any("encimado" in e.lower() for e in r.get("errors", []))

    def test_collisions_travel_in_the_result(self):
        r = validate_pdf_structure(_pdf_con_cabecera_invadida(True))
        assert len(r.get("header_collisions") or []) == 1

    def test_a_clean_carousel_asks_for_nothing(self):
        r = validate_pdf_structure(_pdf_con_cabecera_invadida(False))
        assert not (r.get("header_collisions") or [])
        assert "reduce_scale" not in r.get("repair_actions", [])


class TestTitleScalesWithLength:
    """Un título largo debe achicarse, no desbordar sobre la cabecera.

    El título tenía tamaño fijo por sistema (92px en editorial). A tres líneas no
    entraba entre la cabecera y el resto del contenido, y como el contenedor usa
    `justify-content: flex-end`, el excedente salía por arriba y se montaba sobre
    el eyebrow y el folio. El bucle de reparación no lo salvaba: aplicaba `zoom`
    sobre una caja de altura fija, que escala contenedor y contenido por igual.
    """

    def test_short_title_keeps_full_size(self):
        assert title_scale("Sandboxing") == 1.0

    def test_long_title_is_reduced(self):
        # el título real que se montó sobre la cabecera
        assert title_scale("Toda escritura guarda una copia timestamped") < 1.0

    def test_scale_never_collapses_the_title(self):
        assert title_scale("x" * 400) >= 0.6

    def test_scale_is_monotonic(self):
        escalas = [title_scale("x" * n) for n in (10, 30, 50, 80, 120)]
        assert escalas == sorted(escalas, reverse=True)

    def test_empty_title_is_safe(self):
        assert title_scale("") == 1.0

    def test_markup_does_not_count_toward_length(self):
        # el peso visual lo da el texto, no los asteriscos de Markdown
        assert title_scale("**Sandboxing**") == title_scale("Sandboxing")


class TestTextOverlapDetection:
    """Un texto encimado sobre otro se detecta midiendo, no adivinando.

    El chequeo anterior marcaba "colisión con el header" si un bloque empezaba muy
    arriba, y exceptuaba a cualquier bloque que contuviera el folio. Cuando el
    título se montaba sobre la cabecera, PyMuPDF fusionaba ambos en un bloque con
    folio y la excepción tapaba justo el caso a detectar. Ahora se comparan los
    rectángulos de cada línea: se solapan de verdad o no.
    """

    def _pagina(self, trazos):
        import fitz

        doc = fitz.open()
        page = doc.new_page(width=810, height=1013)
        for x, y, texto, size in trazos:
            page.insert_text((x, y), texto, fontsize=size)
        datos = doc.tobytes()
        doc.close()
        return fitz.open(stream=datos, filetype="pdf")[0]

    def test_eyebrow_under_a_title_is_a_collision(self):
        pagina = self._pagina([
            (66, 80, "BACKUPS AUTOMATICOS", 19),
            (66, 88, "Toda escritura guarda", 69),
        ])
        assert find_text_overlaps(pagina)

    def test_title_lines_with_tight_leading_are_not_a_collision(self):
        # line-height 0.94: las cajas se tocan, las letras no. Es diseño, no un bug.
        pagina = self._pagina([
            (66, 120, "Hablarle al servidor", 69),
            (66, 185, "en lenguaje natural", 69),
        ])
        assert not find_text_overlaps(pagina)

    def test_separated_text_is_clean(self):
        pagina = self._pagina([
            (66, 90, "SECCION", 19),
            (66, 400, "Titulo de la lamina", 69),
        ])
        assert not find_text_overlaps(pagina)

    def test_overlap_reports_both_texts(self):
        pagina = self._pagina([
            (66, 80, "EDICION QUIRURGICA", 19),
            (66, 88, "Sin descargar 50MB", 69),
        ])
        primero = find_text_overlaps(pagina)[0]
        assert "EDICION" in primero[0] and "descargar" in primero[1]

    def test_an_empty_page_has_no_overlaps(self):
        assert find_text_overlaps(self._pagina([])) == []
