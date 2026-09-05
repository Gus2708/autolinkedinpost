import os
import pytest
from src.post_generator import (
    SYSTEM_INSTRUCTION_ES,
    SYSTEM_INSTRUCTION_EN,
    PROJECT_PROMPT_TEMPLATE_ES,
    PROJECT_PROMPT_TEMPLATE_EN,
)

TEST_REPO = os.getenv("TEST_REPO_NAME") or os.getenv("GITHUB_REPOSITORY") or "example-org/sample-repo"



class TestPostGeneratorNoAiSlopInstructions:
    """Task 2.1: Directrices No-AI-Slop en las instrucciones del sistema."""

    def test_system_instruction_es_contains_no_ai_slop_rules(self):
        assert "FAUX-INSIGHT" in SYSTEM_INSTRUCTION_ES or "Lo que nadie te cuenta" in SYSTEM_INSTRUCTION_ES
        assert "COLON REVEALS" in SYSTEM_INSTRUCTION_ES or "dos puntos" in SYSTEM_INSTRUCTION_ES
        assert "ANÁLISIS SUPERFICIAL" in SYSTEM_INSTRUCTION_ES or "gerundios" in SYSTEM_INSTRUCTION_ES
        assert "apalancar" in SYSTEM_INSTRUCTION_ES.lower()
        assert "vanguardista" in SYSTEM_INSTRUCTION_ES.lower()
        assert "REMATE" in SYSTEM_INSTRUCTION_ES or "kicker" in SYSTEM_INSTRUCTION_ES.lower()

    def test_system_instruction_en_contains_no_ai_slop_rules(self):
        assert "FAUX-INSIGHT" in SYSTEM_INSTRUCTION_EN or "What nobody tells you" in SYSTEM_INSTRUCTION_EN
        assert "COLON REVEALS" in SYSTEM_INSTRUCTION_EN or "colon reveal" in SYSTEM_INSTRUCTION_EN.lower()
        assert "SUPERFICIAL ANALYSIS" in SYSTEM_INSTRUCTION_EN or "trailing" in SYSTEM_INSTRUCTION_EN.lower()
        assert "leverage" in SYSTEM_INSTRUCTION_EN.lower()
        assert "delve" in SYSTEM_INSTRUCTION_EN.lower()
        assert "streamline" in SYSTEM_INSTRUCTION_EN.lower()
        assert "FAKE-PROFOUND" in SYSTEM_INSTRUCTION_EN or "kicker" in SYSTEM_INSTRUCTION_EN.lower()


class TestPostGeneratorPromptTemplates:
    """Task 2.2: Portability Test y restricciones en los templates de prompts."""

    def test_prompt_template_es_enforces_portability_test(self):
        assert "PORTABILIDAD" in PROJECT_PROMPT_TEMPLATE_ES or "portabilidad" in PROJECT_PROMPT_TEMPLATE_ES
        assert "empresa" in PROJECT_PROMPT_TEMPLATE_ES or "proyecto" in PROJECT_PROMPT_TEMPLATE_ES

    def test_prompt_template_en_enforces_portability_test(self):
        assert "PORTABILITY" in PROJECT_PROMPT_TEMPLATE_EN or "portability" in PROJECT_PROMPT_TEMPLATE_EN
        assert "company" in PROJECT_PROMPT_TEMPLATE_EN or "stack" in PROJECT_PROMPT_TEMPLATE_EN

    def test_template_rendering_triangulation(self):
        rendered_es = PROJECT_PROMPT_TEMPLATE_ES.format(
            repo_name=TEST_REPO,
            commits_text="feat: integrate no-ai-slop",
        )
        assert TEST_REPO in rendered_es
        assert "feat: integrate no-ai-slop" in rendered_es
        assert "TEST DE PORTABILIDAD" in rendered_es

        rendered_en = PROJECT_PROMPT_TEMPLATE_EN.format(
            repo_name=TEST_REPO,
            commits_text="feat: integrate no-ai-slop",
        )
        assert TEST_REPO in rendered_en
        assert "feat: integrate no-ai-slop" in rendered_en
        assert "PORTABILITY TEST" in rendered_en


class TestPostGeneratorEndToEndIntegration:
    """Task 3.3: Verificación end-to-end del pipeline de post-generator y QC."""

    def test_refine_post_pipeline_cleans_ai_slop_spanish(self, monkeypatch):
        from src.post_generator import refine_post_with_feedback

        def mock_generate(prompt, **kwargs):
            return "Decidí apalancar Redis para potenciar el throughput.", "mock-model"

        monkeypatch.setattr("src.post_generator.generate_llm_text", mock_generate)
        result = refine_post_with_feedback(
            original_post="Texto previo",
            user_feedback="Hacelo más conciso",
            repo_name=TEST_REPO,
            language="es",
        )
        post_text = result["post"]
        assert "apalancar" not in post_text.lower()
        assert "potenciar" not in post_text.lower()
        assert "Redis" in post_text
        assert result["repo_name"] == TEST_REPO

    def test_refine_post_pipeline_cleans_ai_slop_english(self, monkeypatch):
        from src.post_generator import refine_post_with_feedback

        def mock_generate(prompt, **kwargs):
            return "I decided to leverage Redis to streamline cache hits.", "mock-model"

        monkeypatch.setattr("src.post_generator.generate_llm_text", mock_generate)
        result = refine_post_with_feedback(
            original_post="Previous text",
            user_feedback="Make it direct",
            repo_name=TEST_REPO,
            language="en",
        )
        post_text = result["post"]
        assert "leverage" not in post_text.lower()
        assert "streamline" not in post_text.lower()
        assert "Redis" in post_text
        assert result["repo_name"] == TEST_REPO


