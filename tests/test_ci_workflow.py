import os
from pathlib import Path
import pytest

def test_ci_workflow_exists_and_valid():
    wf_path = Path('.github/workflows/ci.yml')
    assert wf_path.exists(), 'El archivo .github/workflows/ci.yml debe existir'
    content = wf_path.read_text(encoding='utf-8')
    assert len(content) > 50

    # Validar que no hay tabs accidentales en YAML
    assert '\t' not in content, 'YAML no debe contener tabulaciones'

    # Validar contenido y estructura
    assert 'name:' in content
    assert 'concurrency:' in content
    assert 'cancel-in-progress: true' in content

    # Matriz Python 3.11 y 3.12
    assert '3.11' in content
    assert '3.12' in content
    assert 'matrix:' in content

    # Pasos de calidad requeridos
    assert 'compileall' in content, 'CI debe verificar compilacion de sintaxis bytecode'
    assert 'ruff' in content, 'CI debe ejecutar linter ruff'
    assert 'pytest' in content, 'CI debe ejecutar suite pytest'

def test_requirements_dev_includes_quality_tools():
    req_dev = Path('requirements-dev.txt').read_text(encoding='utf-8')
    assert 'pytest' in req_dev
    assert 'ruff' in req_dev, 'requirements-dev.txt debe incluir ruff para linting'

def test_readme_contains_ci_badge():
    readme = Path('README.md').read_text(encoding='utf-8')
    assert '.github/workflows/ci.yml/badge.svg' in readme or 'actions/workflows/ci.yml/badge.svg' in readme, 'README.md debe contener el badge de status del workflow ci.yml'
