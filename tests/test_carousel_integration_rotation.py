import os
import pytest
from unittest.mock import patch
from src.design_systems import DESIGN_SYSTEMS

def test_renderer_cycles_persistent_themes_when_no_theme_specified(tmp_path):
    from src.carousel_renderer import generate_native_carousel_pdf

    script = '---\\s*DIAPOSITIVA 1 / 1 ---\\n[PORTADA]\\nTitulo\\nCuerpo.\\n'

    with patch('src.carousel_renderer.get_next_rotating_theme') as mock_rot:
        mock_rot.side_effect = [DESIGN_SYSTEMS[0], DESIGN_SYSTEMS[1]]
        with patch('src.carousel_renderer.render_html_carousel_to_pdf') as mock_render, \
             patch('src.carousel_renderer.optimize_pdf_webgl_streams') as mock_opt, \
             patch('src.carousel_renderer.validate_pdf_structure') as mock_val, \
             patch('src.carousel_renderer.audit_carousel_pdf') as mock_aud:

            mock_render.return_value = b'%PDF'
            mock_opt.return_value = b'%PDF'
            mock_val.return_value = {'passed': True, 'page_count': 1, 'footer_collisions': [], 'errors': []}
            mock_aud.return_value = {'overall_score': 5.0}

            # First generation
            _, _, _, qc1 = generate_native_carousel_pdf('--- DIAPOSITIVA 1 / 1 ---\n[PORTADA]\nTitulo\nCuerpo.\n', 'user/repo')
            assert qc1.get('theme_name') == DESIGN_SYSTEMS[0].name

            # Second generation
            _, _, _, qc2 = generate_native_carousel_pdf('--- DIAPOSITIVA 1 / 1 ---\n[PORTADA]\nTitulo\nCuerpo.\n', 'user/repo')
            assert qc2.get('theme_name') == DESIGN_SYSTEMS[1].name

            assert mock_rot.call_count == 2

def test_renderer_explicit_theme_does_not_call_rotation():
    from src.carousel_renderer import generate_native_carousel_pdf
    from src.design_systems import get_system_by_id

    with patch('src.carousel_renderer.get_next_rotating_theme') as mock_rot, \
         patch('src.carousel_renderer.render_html_carousel_to_pdf') as mock_render, \
         patch('src.carousel_renderer.optimize_pdf_webgl_streams') as mock_opt, \
         patch('src.carousel_renderer.validate_pdf_structure') as mock_val, \
         patch('src.carousel_renderer.audit_carousel_pdf') as mock_aud:

        mock_render.return_value = b'%PDF'
        mock_opt.return_value = b'%PDF'
        mock_val.return_value = {'passed': True, 'page_count': 1, 'footer_collisions': [], 'errors': []}
        mock_aud.return_value = {'overall_score': 5.0}

        _, _, _, qc = generate_native_carousel_pdf('--- DIAPOSITIVA 1 / 1 ---\n[PORTADA]\nTitulo\nCuerpo.\n', 'user/repo', theme_id='terminal')
        assert qc.get('theme_name') == get_system_by_id('terminal').name
        mock_rot.assert_not_called()
