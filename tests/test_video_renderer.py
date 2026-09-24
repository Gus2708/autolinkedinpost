"""Pruebas unitarias para el motor de renderizado de videos técnicos con Hyperframes."""

import os
from unittest.mock import MagicMock, patch
import pytest

from src.design_systems import EDITORIAL, SWISS, TERMINAL, get_system_by_id
from src.video_renderer import (
    TechnicalVideoStoryboard,
    extract_technical_storyboard,
    generate_technical_video,
    generate_video_composition_html,
)


def test_extract_technical_storyboard_es():
    """Verifica la extracción de storyboard técnico en español."""
    commits = [
        "perf(db): optimizar consultas n+1 en workspace billing usando eager loading",
        "fix(cache): evitar race condition con redis cluster",
    ]
    storyboard = extract_technical_storyboard(
        project_name="empresa/core-api",
        commits=commits,
        language="es",
        theme_id="terminal",
    )

    assert isinstance(storyboard, TechnicalVideoStoryboard)
    assert storyboard.project_name == "empresa/core-api"
    assert "latencia p99" in storyboard.problem_detail.lower() or "n+1" in storyboard.problem_detail.lower() or "cuello" in storyboard.problem_title.lower()
    assert len(storyboard.architecture_steps) == 3
    assert len(storyboard.metrics) == 3
    assert "github.com/empresa/core-api" in storyboard.repo_url


def test_extract_technical_storyboard_en():
    """Verifica la extracción de storyboard técnico en inglés."""
    commits = [
        "feat(auth): migrate token rotation from memory cache to distributed redis cluster",
    ]
    storyboard = extract_technical_storyboard(
        project_name="sample-project",
        commits=commits,
        language="en",
        theme_id="swiss",
    )

    assert storyboard.project_name == "sample-project"
    assert "The Architecture Bottleneck" in storyboard.problem_title
    assert "System Design & Trade-offs" in storyboard.decision_title
    assert "Measurable Engineering Impact" in storyboard.impact_title
    assert len(storyboard.architecture_steps) == 3


def test_generate_video_composition_html_themes():
    """Verifica que el HTML generado sea válido y aplique los tokens de cada sistema de diseño."""
    storyboard = extract_technical_storyboard(
        project_name="my-service",
        commits=["perf: speed up index"],
        language="es",
    )

    # 1. Probar Terminal
    html_terminal = generate_video_composition_html(storyboard, TERMINAL, duration=20.0)
    assert 'data-composition-id="main"' in html_terminal
    assert 'window.__timelines["main"] = tl;' in html_terminal
    assert "data-duration=\"20.0\"" in html_terminal
    assert "JetBrains Mono" in html_terminal

    # 2. Probar Swiss Grid
    html_swiss = generate_video_composition_html(storyboard, SWISS, duration=18.0)
    assert 'data-composition-id="main"' in html_swiss
    assert "Archivo" in html_swiss
    assert "data-duration=\"18.0\"" in html_swiss

    # 3. Probar Editorial
    html_editorial = generate_video_composition_html(storyboard, EDITORIAL, duration=20.0)
    assert 'data-composition-id="main"' in html_editorial
    assert "Bricolage Grotesque" in html_editorial or "Literata" in html_editorial


def test_generate_technical_video_graceful_failure(tmp_path):
    """Verifica que el renderer maneje fallas externas de herramientas limpiamente sin crashear."""
    with patch("subprocess.run") as mock_run:
        # Simular fallo de ejecución
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = "hyperframes: command failed"
        mock_run.return_value = mock_proc

        result = generate_technical_video(
            project_name="test-repo",
            commits=["feat: test commit"],
            theme_id="terminal",
            output_dir=str(tmp_path / "video_out"),
        )

        assert result["success"] is False
        assert result["error"] is not None
        assert "Fallo al renderizar video" in result["error"]


def test_generate_technical_video_mocked_success(tmp_path):
    """Verifica que cuando los comandos de render y ffmpeg tienen éxito se devuelvan los paths y bytes."""
    out_dir = tmp_path / "video_out"
    raw_video = out_dir / "raw_video.mp4"
    final_video = out_dir / "video.mp4"
    poster_img = out_dir / "poster.jpg"

    def side_effect(cmd, **kwargs):
        # Crear los archivos esperados
        os.makedirs(out_dir, exist_ok=True)
        if "render" in cmd:
            raw_video.write_bytes(b"\x00\x00\x00\x20ftypisom" + b"\x00" * 100)
        elif "poster.jpg" in str(cmd):
            poster_img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 50)
        elif "brag.poster.mp4" in str(cmd) or final_video.name in str(cmd):
            final_video.write_bytes(b"\x00\x00\x00\x20ftypisom" + b"\x00" * 200)

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Success"
        mock_proc.stderr = ""
        return mock_proc

    with patch("subprocess.run", side_effect=side_effect):
        result = generate_technical_video(
            project_name="sample-project",
            commits=["feat: test commit"],
            theme_id="swiss",
            output_dir=str(out_dir),
        )

        assert result["success"] is True
        assert result["theme_id"] == "swiss"
        assert result["theme_name"] == "Swiss Grid"
        assert result["video_bytes"] is not None
        assert len(result["video_bytes"]) > 0
