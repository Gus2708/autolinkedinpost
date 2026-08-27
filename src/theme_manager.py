"""Gestor de Temas de Diseño y Paletas Refero (styles.refero.design).
Permite rotar dinámicamente entre los mejores Design Systems reales (Linear, Supabase, Apple, Raycast, Cyber Navy).
Inyecta tokens de color, tipografía y paletas de WebGL Paper Shaders de forma determinista y modular.
"""

from dataclasses import dataclass, field
import json
import os
from typing import Dict, List, Optional


@dataclass
class DesignTheme:
    id: str
    name: str
    brand: str
    north_star: str
    bg_color: str
    card_bg: str
    card_border: str
    text_primary: str
    text_muted: str
    accent_color: str
    badge_bg: str
    badge_border: str
    font_family: str
    font_mono: str
    font_import_url: str
    shader_palettes: List[List[str]] = field(default_factory=list)


# Catálogo curado de temas basados estrictamente en styles.refero.design
REFERO_THEMES: List[DesignTheme] = [
    # 1. Linear (Dark) - Midnight precision instrument
    DesignTheme(
        id="linear",
        name="Linear Midnight",
        brand="Linear",
        north_star="Midnight precision instrument — graphite depths with indigo accents",
        bg_color="#08090A",
        card_bg="#121316",
        card_border="#23252A",
        text_primary="#F7F8F8",
        text_muted="#8A8F98",
        accent_color="#5E6AD2",
        badge_bg="#161718",
        badge_border="#383B3F",
        font_family="'Inter', -apple-system, sans-serif",
        font_mono="'JetBrains Mono', monospace",
        font_import_url="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap",
        shader_palettes=[
            ["#08090A", "#0F1011", "#1B1C26", "#5E6AD2"],  # Cover
            ["#08090A", "#161718", "#23252A", "#383B3F"],  # Problem
            ["#08090A", "#121316", "#252736", "#6E7AE6"],  # Architecture
            ["#08090A", "#1B1C26", "#4752B2", "#8B95F6"],  # Synthesis / CTA
        ],
    ),
    # 2. Supabase (Dark) - Phosphor green on midnight emerald
    DesignTheme(
        id="supabase",
        name="Supabase Phosphor",
        brand="Supabase",
        north_star="Midnight code editor with phosphor green caret",
        bg_color="#0C0E12",
        card_bg="#14181F",
        card_border="#1F2633",
        text_primary="#FAFAFA",
        text_muted="#94A3B8",
        accent_color="#3ECF8E",
        badge_bg="#0D281E",
        badge_border="#1F4B37",
        font_family="'Plus Jakarta Sans', -apple-system, sans-serif",
        font_mono="'JetBrains Mono', monospace",
        font_import_url="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap",
        shader_palettes=[
            ["#0C0E12", "#0D281E", "#163829", "#3ECF8E"],  # Cover
            ["#0C0E12", "#14181F", "#1F2633", "#22C55E"],  # Problem
            ["#0C0E12", "#0F261D", "#164E35", "#3ECF8E"],  # Architecture
            ["#0C0E12", "#103826", "#15803D", "#4ADE80"],  # Synthesis / CTA
        ],
    ),
    # 3. Raycast (Dark) - Midnight command center with neon coral
    DesignTheme(
        id="raycast",
        name="Raycast Coral",
        brand="Raycast",
        north_star="Midnight command center with vibrant coral neon",
        bg_color="#07080A",
        card_bg="#111214",
        card_border="#1F2024",
        text_primary="#FFFFFF",
        text_muted="#9C9C9D",
        accent_color="#FF6363",
        badge_bg="#231215",
        badge_border="#521E24",
        font_family="'Inter', -apple-system, sans-serif",
        font_mono="'JetBrains Mono', monospace",
        font_import_url="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap",
        shader_palettes=[
            ["#07080A", "#1C0D10", "#3B141B", "#FF6363"],  # Cover
            ["#07080A", "#151619", "#1F2024", "#FF7F7F"],  # Problem
            ["#07080A", "#241014", "#4D1621", "#FF6363"],  # Architecture
            ["#07080A", "#331218", "#661B29", "#FF8F8F"],  # Synthesis / CTA
        ],
    ),
    # 4. Apple Pro (Dark) - Black theater with luminous hardware
    DesignTheme(
        id="apple",
        name="Apple Pro Dark",
        brand="Apple",
        north_star="Black theater with titanium minimalism and platinum contrast",
        bg_color="#000000",
        card_bg="#111113",
        card_border="#222226",
        text_primary="#FFFFFF",
        text_muted="#86868B",
        accent_color="#F5F5F7",
        badge_bg="#1D1D1F",
        badge_border="#424245",
        font_family="'Plus Jakarta Sans', -apple-system, sans-serif",
        font_mono="'JetBrains Mono', monospace",
        font_import_url="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap",
        shader_palettes=[
            ["#000000", "#111113", "#222226", "#424245"],  # Cover
            ["#000000", "#0D0D0F", "#1A1A1E", "#333336"],  # Problem
            ["#000000", "#161619", "#2E2E33", "#55555C"],  # Architecture
            ["#000000", "#1F1F24", "#3D3D45", "#70707A"],  # Synthesis / CTA
        ],
    ),
    # 5. Cyber Navy (Dark) - Deep oceanic cyber terminal
    DesignTheme(
        id="cyber-navy",
        name="Cyber Navy",
        brand="Antigravity",
        north_star="Deep oceanic cyber terminal with electric cyan pulse",
        bg_color="#070B14",
        card_bg="#0F172A",
        card_border="#1E293B",
        text_primary="#F8FAFC",
        text_muted="#94A3B8",
        accent_color="#38BDF8",
        badge_bg="#0F2038",
        badge_border="#1E3A8A",
        font_family="'Plus Jakarta Sans', -apple-system, sans-serif",
        font_mono="'JetBrains Mono', monospace",
        font_import_url="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap",
        shader_palettes=[
            ["#070B14", "#0D1B33", "#162C5B", "#0284C7"],  # Cover
            ["#070B14", "#0F172A", "#1E293B", "#0EA5E9"],  # Problem
            ["#070B14", "#111827", "#1E293B", "#38BDF8"],  # Architecture
            ["#070B14", "#0E1E38", "#1D4ED8", "#38BDF8"],  # Synthesis / CTA
        ],
    ),
]

_STATE_FILE = os.path.join(os.path.dirname(__file__), "..", ".theme_rotation_state.json")


def _read_rotation_index() -> int:
    """Lee el índice de rotación persistente."""
    try:
        if os.path.exists(_STATE_FILE):
            with open(_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return int(data.get("index", 0))
    except Exception:
        pass
    return 0


def _write_rotation_index(idx: int) -> None:
    """Guarda el siguiente índice de rotación."""
    try:
        with open(_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"index": idx}, f)
    except Exception:
        pass


def get_theme_by_id(theme_id: str) -> DesignTheme:
    """Busca un tema específico por su ID."""
    clean_id = theme_id.lower().strip()
    for theme in REFERO_THEMES:
        if theme.id == clean_id or clean_id in theme.name.lower():
            return theme
    return REFERO_THEMES[0]


def get_rotating_theme(seed: Optional[str] = None) -> DesignTheme:
    """Obtiene el siguiente tema del catálogo Refero rotando automáticamente.
    
    Si se proporciona un seed (ej: nombre de repo), lo usa para dar variedad determinista
    o avanza el índice persistente.
    """
    current_idx = _read_rotation_index()
    theme = REFERO_THEMES[current_idx % len(REFERO_THEMES)]
    
    # Avanzar rotador para la próxima generación
    _write_rotation_index(current_idx + 1)
    
    return theme
