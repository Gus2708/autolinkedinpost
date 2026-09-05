"""Tests específicos para la integración de los patrones de no-ai-slop (petergyang/no-ai-slop).
Verifica detección de vocabulario prohibido, patrones estructurales y sanitización determinista.
"""

import pytest
from src.humanizer_qc import audit_text_humanizer_qc, sanitize_text_humanizer


class TestNoAiSlopBannedVocabulary:
    """Task 1.1: Vocabulario prohibido y frases vacías de no-ai-slop."""

    @pytest.mark.parametrize(
        "word,phrase",
        [
            ("delve", "Let's delve into the indexing mechanism."),
            ("leverage", "We leverage Redis for sub-millisecond caching."),
            ("foster", "This helps foster better engineering practices."),
            ("streamline", "We streamline the deployment workflow."),
            ("cutting-edge", "Built with cutting-edge microservices."),
            ("supercharge", "A proxy to supercharge query throughput."),
            ("paradigm shift", "This architecture represents a paradigm shift."),
            ("tapestry", "Part of a rich tapestry of services."),
            ("transformative", "A transformative tool for devops."),
            ("harness", "Designed to harness raw CPU power."),
        ],
    )
    def test_english_banned_words_detected(self, word, phrase):
        res = audit_text_humanizer_qc(phrase, "en")
        assert res["violations_count"] > 0
        patterns = [v["pattern"].lower() for v in res["violations"]]
        assert any(word in p for p in patterns)

    @pytest.mark.parametrize(
        "word,phrase",
        [
            ("apalancar", "Decidí apalancar Redis para la capa de lectura."),
            ("fomentar", "Buscamos fomentar buenas prácticas en el stack."),
            ("vanguardista", "Implementé una solución vanguardista en Rust."),
            ("cambio de paradigma", "Este enfoque supone un cambio de paradigma total."),
            ("empoderar", "La CLI busca empoderar a cada dev en el equipo."),
            ("tapiz", "Parte de un rico tapiz de dependencias."),
            ("al fin y al cabo", "Al fin y al cabo, lo que cuenta es la latencia."),
        ],
    )
    def test_spanish_banned_words_detected(self, word, phrase):
        res = audit_text_humanizer_qc(phrase, "es")
        assert res["violations_count"] > 0
        patterns = [v["pattern"].lower() for v in res["violations"]]
        assert any(word in p for p in patterns)

    @pytest.mark.parametrize(
        "expected_sub,phrase,lang",
        [
            ("leverage", "LEVERAGING our existing Kafka cluster!", "en"),
            ("supercharge", "A tool that SUPERCHARGED the response time.", "en"),
            ("apalancar", "APALANCAMOS la base de datos distribuida.", "es"),
            ("vanguardista", "Nuestras soluciones VANGUARDISTAS.", "es"),
        ],
    )
    def test_casing_and_inflections_triangulation(self, expected_sub, phrase, lang):
        res = audit_text_humanizer_qc(phrase, lang)
        assert res["violations_count"] > 0
        patterns = [v["pattern"].lower() for v in res["violations"]]
        assert any(expected_sub in p for p in patterns)


class TestNoAiSlopStructuralPatterns:
    """Task 1.2: Patrones estructurales de no-ai-slop."""

    @pytest.mark.parametrize(
        "expected_label,phrase,lang",
        [
            ("faux-insight", "Here's what nobody tells you about database locks.", "en"),
            ("faux-insight", "What most people get wrong about distributed tracing.", "en"),
            ("faux-insight", "The part everyone misses when scaling WebSocket.", "en"),
            ("faux-insight", "Lo que nadie te cuenta sobre los índices en PostgreSQL.", "es"),
            ("faux-insight", "La parte que todos ignoran al migrar a microservicios.", "es"),
            ("colon reveal", "The secret: it runs completely on SQLite without servers.", "en"),
            ("colon reveal", "The detail that makes it work: a separate worker grades it.", "en"),
            ("colon reveal", "El secreto: corre completamente en memoria local.", "es"),
            ("superficial analysis", "We integrated Redis, highlighting our dedication to performance.", "en"),
            ("superficial analysis", "The patch reduces memory usage, underscoring the team's discipline.", "en"),
            ("superficial analysis", "Agregamos sharding, destacando nuestro foco en escalabilidad.", "es"),
            ("superficial analysis", "Refactorizamos el ORM, subrayando la importancia del código limpio.", "es"),
            ("interpretive metadiscourse", "That last part matters more than it sounds.", "en"),
            ("interpretive metadiscourse", "This distinction matters when building high-concurrency systems.", "en"),
            ("interpretive metadiscourse", "Esa última parte importa más de lo que parece.", "es"),
            ("weasel attribution", "Experts agree that monolithic architectures are returning.", "en"),
            ("weasel attribution", "Industry reports suggest that Rust adoption is accelerating.", "en"),
            ("weasel attribution", "Estudios demuestran que el 80% de los microservicios son innecesarios.", "es"),
            ("rhetorical setup", "What if I told you that you don't need Kubernetes?", "en"),
            ("rhetorical setup", "Think about it: how many microservices do you actually call?", "en"),
            ("rhetorical setup", "¿Qué pasaría si te dijera que tu base de datos no está indexada?", "es"),
            ("rhetorical setup", "Pensalo bien: nunca mediste la latencia en p99.", "es"),
        ],
    )
    def test_structural_patterns_detected(self, expected_label, phrase, lang):
        res = audit_text_humanizer_qc(phrase, lang)
        assert res["violations_count"] > 0
        patterns = [v["pattern"].lower() for v in res["violations"]]
        assert any(expected_label in p for p in patterns)

    @pytest.mark.parametrize(
        "phrase,lang",
        [
            ("Stack: FastAPI, PostgreSQL 16 y Redis 7.2.", "es"),
            ("curl -H 'Authorization: Bearer mytoken' http://localhost:8000", "en"),
            ("Building a distributed cache requires careful invalidation.", "en"),
            ("Construyendo un pipeline de CI con GitHub Actions y Docker.", "es"),
        ],
    )
    def test_legitimate_technical_syntax_not_flagged_as_slop(self, phrase, lang):
        res = audit_text_humanizer_qc(phrase, lang)
        patterns = [v["pattern"].lower() for v in res["violations"]]
        assert not any("colon reveal" in p for p in patterns)
        assert not any("superficial analysis" in p for p in patterns)


class TestNoAiSlopSanitizer:
    """Task 1.3: Sanitizador determinista con vocabulario y rellenos de no-ai-slop."""

    def test_clean_banned_words_english(self):
        raw = "We leverage Redis in order to streamline our deployment. At the end of the day, it's cutting-edge."
        cleaned = sanitize_text_humanizer(raw, "en")
        assert "leverage" not in cleaned.lower()
        assert "streamline" not in cleaned.lower()
        assert "cutting-edge" not in cleaned.lower()
        assert "at the end of the day" not in cleaned.lower()
        assert "Redis" in cleaned  # technical entity preserved

    def test_clean_banned_words_spanish(self):
        raw = "Decidí apalancar Redis para potenciar el throughput. Al fin y al cabo, es vanguardista."
        cleaned = sanitize_text_humanizer(raw, "es")
        assert "apalancar" not in cleaned.lower()
        assert "potenciar" not in cleaned.lower()
        assert "vanguardista" not in cleaned.lower()
        assert "al fin y al cabo" not in cleaned.lower()
        assert "Redis" in cleaned
        assert "throughput" in cleaned

    def test_triangulation_preserves_code_identifiers(self):
        raw = "from utils import streamline_data\nredis_stream = leverage_cache()"
        cleaned = sanitize_text_humanizer(raw, "en")
        # identifiers with underscores shouldn't be blindly broken by word boundaries
        assert "streamline_data" in cleaned
        assert "leverage_cache" in cleaned


class TestNoAiSlopLlmPrompt:
    """Task 3.1: Prompt del sistema para re-escritura con LLM (No-AI-Slop)."""

    def test_humanizer_rewrite_system_incorporates_no_ai_slop(self):
        from src.humanizer_qc import HUMANIZER_REWRITE_SYSTEM

        assert "MÍNIMA EDICIÓN EFECTIVA" in HUMANIZER_REWRITE_SYSTEM or "MINIMUM EFFECTIVE EDIT" in HUMANIZER_REWRITE_SYSTEM
        assert "VOZ" in HUMANIZER_REWRITE_SYSTEM
        assert "PORTABILIDAD" in HUMANIZER_REWRITE_SYSTEM or "PORTABILITY" in HUMANIZER_REWRITE_SYSTEM
        assert "FAUX-INSIGHT" in HUMANIZER_REWRITE_SYSTEM
        assert "COLON REVEAL" in HUMANIZER_REWRITE_SYSTEM

    def test_humanize_text_with_llm_formatting_triangulation(self, monkeypatch):
        from src.humanizer_qc import humanize_text_with_llm

        captured = {}

        def mock_generate(prompt, system_instruction, **kwargs):
            captured["prompt"] = prompt
            captured["system"] = system_instruction
            return "Decidí implementar Redis 7.2 para el cache.", "mock-model"

        monkeypatch.setattr("src.humanizer_qc.generate_llm_text", mock_generate)
        res = humanize_text_with_llm(
            text="Decidimos apalancar Redis.",
            violations_feedback="Eliminar plural corporativo y 'apalancar'.",
            language="es",
        )
        assert "Eliminar plural corporativo" in captured["prompt"]
        assert "Decidimos apalancar Redis." in captured["prompt"]
        assert "NO-AI-SLOP" in captured["system"]
        assert "Decidí implementar Redis" in res


class TestHumanizerQcEndToEndIntegration:
    """Task 3.3: Verificación end-to-end de process_and_enforce_humanizer_qc."""

    def test_pipeline_enforce_humanizer_qc_cleans_package(self, monkeypatch):
        from src.humanizer_qc import process_and_enforce_humanizer_qc

        package = {
            "post": "Decidimos apalancar PostgreSQL en el vertiginoso mundo digital. Lo que nadie te cuenta: colapsó.",
            "hook": "Lo que nadie te cuenta: Redis es rápido.",
            "first_comment": "En conclusión, dejamos el repo.",
        }

        def mock_generate(prompt, system_instruction, **kwargs):
            return "Decidí usar PostgreSQL. Redis es rápido. Dejamos el repo.", "mock-model"

        monkeypatch.setattr("src.humanizer_qc.generate_llm_text", mock_generate)

        clean_pkg, qc_meta = process_and_enforce_humanizer_qc(package, language="es")
        assert "apalancar" not in clean_pkg["post"].lower()
        assert "vertiginoso mundo" not in clean_pkg["post"].lower()
        assert "En conclusión," not in clean_pkg["first_comment"]
        assert "total_violations" in qc_meta
        assert "overall_score" in qc_meta






