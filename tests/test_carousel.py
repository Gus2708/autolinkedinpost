"""Tests del renderizador de carruseles: parseo del guion, iconos, i18n y rotación de temas."""

from datetime import date

import pytest

from src.carousel_renderer import (
    get_carousel_strings,
    normalize_lucide_icon,
    parse_carousel_slides,
    resolve_lucide_icon,
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
