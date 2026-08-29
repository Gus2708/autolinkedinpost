"""Tests de los controles de calidad de texto: juez LLM, humanizer y parseo del paquete.

El foco está en que los gates fallen CERRADOS y en que el scoring no dependa del largo.
"""

import pytest

from src.evaluator import _unevaluated_verdict, evaluate_linkedin_post
from src.llm_client import extract_json_object
from src.humanizer_qc import (
    audit_full_package_qc,
    audit_text_humanizer_qc,
    sanitize_text_humanizer,
)
from src.post_generator import _extract_refined_post, parse_publication_sections


class TestExtractJsonObject:
    def test_plain_json(self):
        assert extract_json_object('{"passed": true}') == {"passed": True}

    def test_json_inside_markdown_fence(self):
        raw = 'Aca va mi veredicto:\n```json\n{"passed": false, "overall_score": 2.0}\n```\nFin.'
        assert extract_json_object(raw)["passed"] is False

    def test_nested_objects(self):
        raw = '{"evaluations": {"hook_strength": {"score": 4.0}}, "passed": true}'
        assert extract_json_object(raw)["evaluations"]["hook_strength"]["score"] == 4.0

    def test_braces_inside_strings_do_not_break_parsing(self):
        raw = '{"feedback": "usa {placeholder} en el texto", "passed": true}'
        assert extract_json_object(raw)["passed"] is True

    @pytest.mark.parametrize("raw", ["", "sin json aca", "{roto", None])
    def test_invalid_returns_none(self, raw):
        assert extract_json_object(raw) is None


class TestJudgeFailsClosed:
    """Antes cualquier excepción devolvía passed=True con score 4.8."""

    def test_unevaluated_verdict_is_not_passed(self):
        verdict = _unevaluated_verdict("timeout")
        assert verdict["passed"] is False
        assert verdict["evaluated"] is False
        assert verdict["overall_score"] == 0.0

    def test_provider_exception_does_not_approve(self, monkeypatch):
        def boom(**kwargs):
            raise RuntimeError("connection reset")

        monkeypatch.setattr("src.evaluator.generate_llm_text", boom)
        result = evaluate_linkedin_post("un post cualquiera")
        assert result["passed"] is False
        assert result["evaluated"] is False

    def test_unparseable_response_does_not_approve(self, monkeypatch):
        monkeypatch.setattr(
            "src.evaluator.generate_llm_text",
            lambda **kwargs: ("el modelo divago sin json", "modelo-x"),
        )
        result = evaluate_linkedin_post("un post cualquiera")
        assert result["passed"] is False
        assert result["evaluated"] is False

    def test_low_grounding_forces_failure(self, monkeypatch):
        payload = '{"evaluations": {"factual_grounding": {"score": 2.0}}, "overall_score": 4.9, "passed": true}'
        monkeypatch.setattr("src.evaluator.generate_llm_text", lambda **kwargs: (payload, "modelo-x"))
        assert evaluate_linkedin_post("post con metricas inventadas")["passed"] is False

    def test_valid_verdict_passes_through(self, monkeypatch):
        payload = '{"evaluations": {"factual_grounding": {"score": 5.0}}, "overall_score": 4.7, "passed": true}'
        monkeypatch.setattr("src.evaluator.generate_llm_text", lambda **kwargs: (payload, "modelo-x"))
        result = evaluate_linkedin_post("un post correcto")
        assert result["passed"] is True
        assert result["evaluated"] is True
        assert result["overall_score"] == 4.7


class TestJudgeToleratesMalformedShapes:
    """Regresión: el post-procesado quedó fuera del try y un JSON válido pero mal
    tipado subía la excepción hasta main(), abortando todos los repos del día."""

    @pytest.mark.parametrize(
        "payload,description",
        [
            ('{"evaluations": {"factual_grounding": {"score": 5}}, "overall_score": null}', "overall_score null"),
            ('{"evaluations": [1, 2], "overall_score": 4.5, "passed": true}', "evaluations como lista"),
            ('{"evaluations": "texto", "overall_score": 4.5}', "evaluations como string"),
            ('{"evaluations": {"hook": {"score": "4.5"}}, "passed": true}', "score como string"),
            ('{"evaluations": {}, "overall_score": 4.9, "passed": "si"}', "passed no booleano"),
            ('{"evaluations": {"hook": null}, "overall_score": 4.0}', "criterio null"),
            ("{}", "objeto vacio"),
        ],
    )
    def test_does_not_raise(self, payload, description, monkeypatch):
        monkeypatch.setattr("src.evaluator.generate_llm_text", lambda **kwargs: (payload, "modelo-x"))
        result = evaluate_linkedin_post("un post")
        assert isinstance(result["passed"], bool), description
        assert isinstance(result["overall_score"], float), description

    def test_missing_overall_score_is_averaged(self, monkeypatch):
        payload = '{"evaluations": {"a": {"score": 4}, "b": {"score": 5}}}'
        monkeypatch.setattr("src.evaluator.generate_llm_text", lambda **kwargs: (payload, "modelo-x"))
        assert evaluate_linkedin_post("post")["overall_score"] == 4.5

    def test_low_grounding_still_fails_with_odd_types(self, monkeypatch):
        payload = '{"evaluations": {"factual_grounding": {"score": "2"}}, "overall_score": 4.9, "passed": true}'
        monkeypatch.setattr("src.evaluator.generate_llm_text", lambda **kwargs: (payload, "modelo-x"))
        assert evaluate_linkedin_post("post")["passed"] is False

    def test_booleans_are_not_treated_as_scores(self, monkeypatch):
        """En Python True es instancia de int y se colaría como un puntaje de 1.0."""
        payload = '{"evaluations": {"a": {"score": true}, "b": {"score": 4}}}'
        monkeypatch.setattr("src.evaluator.generate_llm_text", lambda **kwargs: (payload, "modelo-x"))
        assert evaluate_linkedin_post("post")["overall_score"] == 4.0


class TestSanitizerRespectsLanguage:
    """La versión anterior calculaba la lista por idioma y después nunca la usaba."""

    def test_english_stays_english(self):
        out = sanitize_text_humanizer("The rollout was seamless and revolutionary.", "en")
        assert "cambio relevante" not in out
        assert "clean" in out and "effective" in out

    def test_spanish_stays_spanish(self):
        out = sanitize_text_humanizer("El despliegue fue revolucionario y sin fisuras.", "es")
        assert "efectivo" in out and "limpio" in out

    def test_spanish_gender_agreement(self):
        assert "efectivas" in sanitize_text_humanizer("Son decisiones revolucionarias.", "es")

    def test_greetings_are_removed(self):
        assert not sanitize_text_humanizer("Hola a todos! Migre el cache.", "es").startswith("Hola")
        assert not sanitize_text_humanizer("Hello network! I migrated the cache.", "en").startswith("Hello")

    def test_technical_content_is_preserved(self):
        text = "Use Redis 7.2 con un TTL de 300s y baje la latencia a 60ms."
        assert sanitize_text_humanizer(text, "es") == text

    def test_empty_input(self):
        assert sanitize_text_humanizer("", "es") == ""


class TestHumanizerScoring:
    def test_repeated_pattern_counts_once(self):
        result = audit_text_humanizer_qc("seamless " * 5 + "pipeline across the stack", "en")
        assert result["violations_count"] == 1
        assert result["violations"][0]["occurrences"] == 5

    def test_long_clean_text_is_not_penalised(self):
        """Un guion de carrusel limpio caía a 1.0 sólo por ser largo."""
        clean = "Decidi mover el cache a Redis y la latencia bajo a 60ms. " * 30
        assert audit_text_humanizer_qc(clean, "es")["score"] == 5.0

    def test_dense_slop_still_fails(self):
        slop = "Fue revolucionario y sin fisuras. Un testimonio de nuestro ecosistema vibrante."
        assert audit_text_humanizer_qc(slop, "es")["score"] < 4.0

    def test_corporate_plural_always_fails(self):
        result = audit_text_humanizer_qc("Decidimos migrar. Nuestro equipo lo diseno.", "es")
        assert result["plural_voice_detected"] is True
        assert result["passed"] is False

    def test_em_dash_budget_scales_with_length(self):
        short = "Uno — dos — tres — cuatro."
        long_text = ("Una oracion tecnica normal sin adornos. " * 60) + "Uno — dos — tres — cuatro."
        assert any("em-dash" in v["pattern"] for v in audit_text_humanizer_qc(short, "es")["violations"])
        assert not any("em-dash" in v["pattern"] for v in audit_text_humanizer_qc(long_text, "es")["violations"])

    def test_empty_text_passes(self):
        result = audit_text_humanizer_qc("", "es")
        assert result["passed"] is True and result["score"] == 5.0


class TestPackageQC:
    def test_carousel_alone_does_not_block_package(self):
        """El carrusel hacía reprobar el paquete entero por ser el texto más largo."""
        package = {
            "post": "Decidi migrar el cache a Redis. La latencia bajo a 60ms.",
            "first_comment": "https://github.com/user/repo",
            "carousel_script": "Una lamina con contenido tecnico concreto. " * 20,
        }
        assert audit_full_package_qc(package, "es")["passed"] is True

    def test_bad_post_blocks_package(self):
        package = {
            "post": "Decidimos migrar. Nuestro equipo lo diseno.",
            "first_comment": "https://github.com/user/repo",
            "carousel_script": "Contenido tecnico normal.",
        }
        assert audit_full_package_qc(package, "es")["passed"] is False


class TestParsePublicationSections:
    def test_extracts_all_sections(self):
        raw = """
=== LINKEDIN_POST ===
El post principal.

=== PRIMER_COMENTARIO ===
https://github.com/user/repo

=== GUION_CARRUSEL_PDF ===
--- DIAPOSITIVA 1 / 1 ---
Titulo

"""
        result = parse_publication_sections(raw, "user/repo")
        assert result["post"] == "El post principal."
        assert "github.com/user/repo" in result["first_comment"]
        assert "DIAPOSITIVA" in result["carousel_script"]

    def test_order_independent(self):
        raw = "=== PRIMER_COMENTARIO ===\nEl comentario\n\n=== LINKEDIN_POST ===\nEl post"
        result = parse_publication_sections(raw, "user/repo")
        assert result["post"] == "El post"
        assert result["first_comment"] == "El comentario"

    def test_falls_back_to_full_text_without_delimiters(self):
        """Sin delimitadores el paquete quedaba vacío y el draft se descartaba en silencio."""
        result = parse_publication_sections("Un post sin ningun delimitador", "user/repo")
        assert result["post"] == "Un post sin ningun delimitador"

    def test_defaults_fill_missing_sections(self):
        result = parse_publication_sections("=== LINKEDIN_POST ===\nSolo el post", "user/repo")
        assert "github.com/user/repo" in result["first_comment"]


class TestExtractRefinedPost:
    def test_stops_at_next_section(self):
        """El .replace() anterior pegaba las secciones siguientes dentro del post."""
        raw = "=== LINKEDIN_POST ===\nEl post corregido.\n\n=== PRIMER_COMENTARIO ===\nNo deberia entrar."
        assert _extract_refined_post(raw) == "El post corregido."

    def test_returns_empty_without_marker(self):
        assert _extract_refined_post("Texto suelto sin marcador") == ""
        assert _extract_refined_post("") == ""
