"""Sistemas de diseño para los carruseles.

Un sistema de diseño no es una paleta: define tipografía, color, espaciado Y la
composición de cada lámina. La versión anterior rotaba entre siete "temas" que
sólo cambiaban colores sobre la misma estructura —título arriba, tarjeta con
viñetas abajo—, así que las diez láminas de un carrusel se veían idénticas entre
sí y todos los carruseles se veían iguales entre ellos.

Acá viven tres sistemas con composición propia. Rotan por publicación, de modo que
dos posts seguidos no comparten ni estructura ni tipografía.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
import hashlib
from typing import Dict, List, Optional


@dataclass
class DesignSystem:
    """Define por completo el aspecto de un carrusel."""

    id: str
    name: str
    north_star: str
    fonts_url: str
    # Tokens que el renderer inyecta como variables CSS.
    tokens: Dict[str, str] = field(default_factory=dict)
    # Hoja de estilos propia del sistema.
    css: str = ""
    # Fondo del lienzo: 'solid' no monta WebGL. El mesh gradient genérico era
    # uno de los rasgos más reconocibles de imagen generada.
    canvas: str = "solid"


# ==============================================================================
# 1. EDITORIAL — papel, tipografía grande, cero contenedores
# ==============================================================================
# Marca: preciso, autoritario, respirado.
# La lámina se sostiene con jerarquía tipográfica: no hay tarjetas ni bordes.
# Fondo claro porque se lee de día, en el feed, entre publicaciones oscuras:
# el contraste con el entorno es lo que frena el scroll.

EDITORIAL = DesignSystem(
    id="editorial",
    name="Editorial Técnico",
    north_star="Página de revista técnica: tipografía enorme, aire y una sola idea por lámina",
    fonts_url=(
        "https://fonts.googleapis.com/css2"
        "?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,800"
        "&family=Literata:ital,opsz,wght@0,7..72,400;0,7..72,600;1,7..72,400"
        "&display=swap"
    ),
    canvas="solid",
    tokens={
        # Papel apenas cálido: el blanco puro no existe en impresión.
        "bg": "oklch(0.968 0.006 85)",
        "ink": "oklch(0.19 0.012 75)",
        "ink-soft": "oklch(0.44 0.014 75)",
        "rule": "oklch(0.86 0.008 80)",
        # Un solo acento, rojo de tinta editorial, usado con cuentagotas.
        "accent": "oklch(0.52 0.19 28)",
        "display": "'Bricolage Grotesque', 'Archivo', sans-serif",
        "body": "'Literata', Georgia, serif",
    },
    css="""
.slide.sys-editorial .content-layer {
    padding: 96px 88px 72px;
}

/* Cabecera: una línea de texto, sin píldoras ni cajas. */
.sys-editorial .header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    border: 0;
    border-bottom: 1px solid var(--rule);
    padding-bottom: 18px;
}

.sys-editorial .eyebrow {
    font-family: var(--body);
    font-size: 25px;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--accent);
}

.sys-editorial .folio {
    font-family: var(--body);
    font-size: 25px;
    color: var(--ink-soft);
    font-variant-numeric: tabular-nums;
}

/* El bloque se apoya en el pie en lugar de flotar centrado: la asimetría
   vertical es lo que le da tensión a la lámina. */
.sys-editorial .content {
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    gap: 30px;
    padding-bottom: 76px;
}

/* La portada respira más: el título sube desde abajo con el aire arriba. */
.sys-editorial .is-cover .content {
    padding-bottom: 120px;
}

/* El título es el elemento gráfico de la lámina. */
.sys-editorial .title {
    font-family: var(--display);
    font-weight: 800;
    font-size: 92px;
    line-height: 0.94;
    letter-spacing: -0.035em;
    color: var(--ink);
    max-width: 15ch;
}

.sys-editorial .is-cover .title {
    font-size: 126px;
    letter-spacing: -0.045em;
}

/* Bajada en serif: contraste real de forma, no sólo de tamaño. */
.sys-editorial .lede {
    font-family: var(--body);
    font-size: 38px;
    line-height: 1.42;
    color: var(--ink-soft);
    max-width: 30ch;
}

/* Las viñetas son párrafos numerados, no una lista dentro de una caja. */
.sys-editorial .items {
    display: flex;
    flex-direction: column;
    gap: 26px;
    margin-top: 8px;
    counter-reset: item;
}

.sys-editorial .item {
    display: grid;
    grid-template-columns: 62px 1fr;
    align-items: start;
    gap: 4px;
    font-family: var(--body);
    font-size: 33px;
    line-height: 1.4;
    color: var(--ink);
    max-width: 34ch;
}

.sys-editorial .item::before {
    counter-increment: item;
    content: counter(item, decimal-leading-zero);
    font-family: var(--display);
    font-weight: 600;
    font-size: 27px;
    color: var(--accent);
    padding-top: 8px;
    font-variant-numeric: tabular-nums;
}

/* Una métrica sola ocupa la lámina entera. */
.sys-editorial .metric {
    font-family: var(--display);
    font-weight: 800;
    font-size: 168px;
    line-height: 0.86;
    letter-spacing: -0.05em;
    color: var(--ink);
    font-variant-numeric: tabular-nums;
}

.sys-editorial .metric-note {
    font-family: var(--body);
    font-size: 34px;
    color: var(--ink-soft);
    max-width: 30ch;
}

.sys-editorial em { font-style: italic; color: var(--ink); }
.sys-editorial strong { font-weight: 600; color: var(--ink); }

.sys-editorial code {
    font-family: var(--body);
    font-size: 0.92em;
    background: oklch(0.93 0.01 82);
    padding: 1px 9px;
    border-radius: 3px;
}
.sys-editorial code.tight { padding-right: 2px; }

.sys-editorial .footer {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    border: 0;
    border-top: 1px solid var(--rule);
    padding-top: 20px;
    font-family: var(--body);
    font-size: 24px;
    color: var(--ink-soft);
}

.sys-editorial .footer .cue { color: var(--accent); font-weight: 600; }
""",
)


# ==============================================================================
# 2. TERMINAL — herramienta de ingeniería, no pieza de diseño
# ==============================================================================
# Marca: crudo, mecánico, sin adornos.
# Todo monoespaciado y alineado a una grilla de caracteres. Cero radios, cero
# degradados: bloques planos y una sola tinta de fósforo. La lámina se lee como
# la salida de un comando, que es la estética nativa de quien la va a leer.

TERMINAL = DesignSystem(
    id="terminal",
    name="Terminal Brutalista",
    north_star="Salida de consola: monoespaciada, plana, sin una sola esquina redondeada",
    fonts_url=(
        "https://fonts.googleapis.com/css2"
        "?family=Martian+Mono:wght@400;700;800"
        "&family=JetBrains+Mono:wght@400;500;700"
        "&display=swap"
    ),
    canvas="solid",
    tokens={
        "bg": "oklch(0.16 0.012 250)",
        "ink": "oklch(0.94 0.008 250)",
        "ink-soft": "oklch(0.66 0.018 250)",
        "rule": "oklch(0.28 0.016 250)",
        "accent": "oklch(0.80 0.17 88)",
        "display": "'Martian Mono', 'JetBrains Mono', monospace",
        "body": "'JetBrains Mono', monospace",
    },
    css="""
.slide.sys-terminal .content-layer { padding: 78px 76px 64px; }

.sys-terminal .header {
    display: flex; justify-content: space-between; align-items: baseline;
    border: 0; border-bottom: 2px solid var(--rule); padding-bottom: 20px;
}

/* La ruta del archivo hace de título de sección. */
.sys-terminal .eyebrow {
    font-family: var(--body); font-size: 26px; font-weight: 500;
    color: var(--ink-soft); letter-spacing: -0.01em;
}
.sys-terminal .eyebrow::before { content: "~/"; color: var(--accent); }

.sys-terminal .folio {
    font-family: var(--body); font-size: 26px; color: var(--ink-soft);
}
.sys-terminal .folio::before { content: "["; }
.sys-terminal .folio::after  { content: "]"; }

.sys-terminal .content {
    display: flex; flex-direction: column; justify-content: flex-end;
    gap: 34px; padding-bottom: 64px;
}

.sys-terminal .title {
    font-family: var(--display); font-weight: 800; font-size: 76px;
    line-height: 1.06; letter-spacing: -0.045em; color: var(--ink);
    max-width: 17ch;
}
.sys-terminal .is-cover .title { font-size: 92px; }

/* El prompt delante del título: marca que esto lo escribió una máquina. */
.sys-terminal .title::before {
    content: "$ "; color: var(--accent); font-weight: 400;
}

.sys-terminal .lede {
    font-family: var(--body); font-size: 33px; line-height: 1.55;
    color: var(--ink-soft); max-width: 40ch;
}

.sys-terminal .items {
    display: flex; flex-direction: column; gap: 18px; margin-top: 6px;
}

/* Cada punto es una línea de salida, con su marcador de estado. */
.sys-terminal .item {
    display: grid; grid-template-columns: 46px 1fr; align-items: start;
    font-family: var(--body); font-size: 31px; line-height: 1.45;
    color: var(--ink); max-width: 42ch;
}
.sys-terminal .item::before {
    content: "->"; color: var(--accent); font-weight: 700;
}

/* La métrica se enmarca en un bloque plano, sin radio ni sombra. */
.sys-terminal .metric {
    font-family: var(--display); font-weight: 800; font-size: 132px;
    line-height: 1; letter-spacing: -0.055em; color: var(--bg);
    background: var(--accent); padding: 26px 38px; align-self: flex-start;
}
.sys-terminal .metric-note {
    font-family: var(--body); font-size: 32px; line-height: 1.5;
    color: var(--ink-soft); max-width: 38ch;
}

.sys-terminal em { font-style: normal; color: var(--accent); }
.sys-terminal strong { font-weight: 700; color: var(--ink); }
.sys-terminal code {
    font-family: var(--body); background: var(--rule);
    color: var(--accent); padding: 2px 10px;
}
.sys-terminal code.tight { padding-right: 2px; }

.sys-terminal .footer {
    display: flex; justify-content: space-between; align-items: baseline;
    border: 0; border-top: 2px solid var(--rule); padding-top: 22px;
    font-family: var(--body); font-size: 25px; color: var(--ink-soft);
}
.sys-terminal .footer .cue { color: var(--accent); font-weight: 700; }
""",
)


# ==============================================================================
# 3. SWISS — grilla, peso tipográfico y un bloque de color que corta la lámina
# ==============================================================================
# Marca: sistemático, tenso, gráfico.
# Una grotesca en peso extremo, alineación estricta a la izquierda y una barra de
# color que rompe la composición en un punto distinto según el tipo de lámina.
# Es el sistema más legible en miniatura, que es como se ve al pasar por el feed.

SWISS = DesignSystem(
    id="swiss",
    name="Swiss Grid",
    north_star="Señalética suiza: grotesca pesada, grilla estricta y un bloque de color por lámina",
    fonts_url=(
        "https://fonts.googleapis.com/css2"
        "?family=Archivo:wght@400;500;700;900"
        "&family=Archivo+Black"
        "&display=swap"
    ),
    canvas="solid",
    tokens={
        "bg": "oklch(0.975 0.003 265)",
        "ink": "oklch(0.16 0.014 265)",
        "ink-soft": "oklch(0.46 0.016 265)",
        "rule": "oklch(0.88 0.006 265)",
        "accent": "oklch(0.58 0.21 255)",
        "display": "'Archivo Black', 'Archivo', sans-serif",
        "body": "'Archivo', sans-serif",
    },
    css="""
.slide.sys-swiss .content-layer { padding: 0; }

/* Barra de color a sangre en el borde superior: el ancho cambia por lámina. */
.sys-swiss .content-layer::before {
    content: ""; position: absolute; top: 0; left: 0;
    height: 22px; width: 38%; background: var(--accent);
}
.sys-swiss .is-cover .content-layer::before { width: 100%; }

.sys-swiss .header {
    display: flex; justify-content: space-between; align-items: baseline;
    border: 0; padding: 74px 80px 0;
}

.sys-swiss .eyebrow {
    font-family: var(--body); font-size: 24px; font-weight: 700;
    letter-spacing: 0.16em; text-transform: uppercase; color: var(--ink);
}

.sys-swiss .folio {
    font-family: var(--body); font-size: 24px; font-weight: 500;
    color: var(--ink-soft); font-variant-numeric: tabular-nums;
}

.sys-swiss .content {
    display: flex; flex-direction: column; justify-content: flex-end;
    gap: 32px; padding: 0 80px 78px;
}

.sys-swiss .title {
    font-family: var(--display); font-size: 96px; line-height: 0.92;
    letter-spacing: -0.03em; color: var(--ink); text-transform: uppercase;
    max-width: 13ch;
}
.sys-swiss .is-cover .title { font-size: 118px; }

.sys-swiss .lede {
    font-family: var(--body); font-size: 35px; font-weight: 400;
    line-height: 1.38; color: var(--ink-soft); max-width: 32ch;
}

/* Las viñetas se separan con reglas finas: la grilla se ve. */
.sys-swiss .items { display: flex; flex-direction: column; margin-top: 10px; }

.sys-swiss .item {
    font-family: var(--body); font-size: 32px; font-weight: 500;
    line-height: 1.36; color: var(--ink); max-width: 36ch;
    padding: 22px 0; border-top: 1px solid var(--rule);
}
.sys-swiss .item:last-child { border-bottom: 1px solid var(--rule); }

.sys-swiss .metric {
    font-family: var(--display); font-size: 184px; line-height: 0.84;
    letter-spacing: -0.05em; color: var(--accent);
    font-variant-numeric: tabular-nums;
}
.sys-swiss .metric-note {
    font-family: var(--body); font-size: 33px; line-height: 1.4;
    color: var(--ink-soft); max-width: 30ch;
}

.sys-swiss em { font-style: normal; color: var(--accent); font-weight: 700; }
.sys-swiss strong { font-weight: 700; color: var(--ink); }
.sys-swiss code {
    font-family: var(--body); font-weight: 500;
    background: var(--rule); padding: 1px 8px;
}
.sys-swiss code.tight { padding-right: 2px; }

.sys-swiss .footer {
    display: flex; justify-content: space-between; align-items: baseline;
    border: 0; border-top: 3px solid var(--ink); margin: 0 80px;
    padding: 20px 0 62px;
    font-family: var(--body); font-size: 24px; font-weight: 500;
    color: var(--ink);
}
.sys-swiss .footer .cue { color: var(--accent); font-weight: 700; }
""",
)


DESIGN_SYSTEMS: List[DesignSystem] = [EDITORIAL, TERMINAL, SWISS]


def get_system_by_id(system_id: str) -> DesignSystem:
    """Busca un sistema por su id; devuelve el primero si no existe."""
    clean = (system_id or "").strip().lower()
    for system in DESIGN_SYSTEMS:
        if system.id == clean:
            return system
    return DESIGN_SYSTEMS[0]


def _stable_hash(value: str) -> int:
    """Hash reproducible entre procesos.

    El hash() nativo está aleatorizado por PYTHONHASHSEED y daría un sistema
    distinto en cada corrida sobre el mismo repositorio.
    """
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def get_rotating_system(
    seed: Optional[str] = None,
    today: Optional[date] = None,
) -> DesignSystem:
    """Elige el sistema de diseño de la publicación, de forma determinista.

    Combina la fecha UTC con el repositorio: días distintos rotan el sistema y dos
    repos del mismo día no salen iguales. Sin estado en disco, así que un runner de
    CI efímero también rota.
    """
    current_day = today or datetime.now(timezone.utc).date()
    index = (current_day.toordinal() + (_stable_hash(seed) if seed else 0)) % len(DESIGN_SYSTEMS)
    return DESIGN_SYSTEMS[index]
