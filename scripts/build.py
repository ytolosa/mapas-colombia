"""Paso 2 (`python mapas.py build`): maestro -> GeoJSON y TopoJSON en cada nivel.

Usa mapshaper porque simplifica preservando la topología: las fronteras que dos
municipios comparten se simplifican una sola vez, así que nunca aparecen huecos
ni solapes entre vecinos por más que se baje el detalle.

Los niveles de una misma capa se producen en una sola invocación de mapshaper,
encadenando `-simplify` de mayor a menor porcentaje. Además de ser mucho más
rápido (el archivo se lee una vez), garantiza que los niveles queden anidados:
los vértices de `nacional` son un subconjunto de los de `departamental`, y así
sucesivamente.
"""

from __future__ import annotations

import subprocess
import sys

import config as cfg

MAPSHAPER = cfg.ROOT / "node_modules" / "mapshaper" / "bin" / "mapshaper"

#: El GeoJSON municipal sin simplificar ronda los 273 MB; el heap por defecto de
#: Node no alcanza para cargarlo junto con la topología derivada.
NODE_HEAP_MB = 8192


def mapshaper_args(layer: str, variant: str, levels: tuple[cfg.QualityLevel, ...]) -> list[str]:
    """Construye la cadena de comandos de mapshaper para una capa y variante."""
    master = cfg.BUILD_DIR / f"master_{layer}_{variant}.geojson"
    if not master.exists():
        sys.exit(f"Falta {master}. Ejecuta antes: python mapas.py prepare")

    args = ["-i", str(master), "-clean"]

    for level in sorted(levels, key=lambda lv: -lv.simplify):
        # `weighted` (Visvalingam ponderado) conserva mejor la forma reconocible
        # de los polígonos que el Visvalingam plano. `keep-shapes` impide que
        # islas y municipios diminutos se borren.
        args += ["-simplify", "weighted", "keep-shapes", f"percentage={level.simplify}%"]

        base = cfg.stem(layer, variant, level.name)
        args += [
            "-o",
            str(cfg.GEOJSON_DIR / f"{base}.geojson"),
            "format=geojson",
            f"precision={level.precision}",
            "-o",
            str(cfg.TOPOJSON_DIR / f"{base}.topojson"),
            "format=topojson",
            f"quantization={level.quantization}",
        ]

    return args


def simplify(layer: str, variant: str, levels: tuple[cfg.QualityLevel, ...]) -> None:
    cmd = ["node", f"--max-old-space-size={NODE_HEAP_MB}", str(MAPSHAPER)]
    cmd += mapshaper_args(layer, variant, levels)
    print(f"\n== {layer} / {variant} ==")
    subprocess.run(cmd, check=True)


def report(layers, variants, levels: tuple[cfg.QualityLevel, ...]) -> None:
    """Imprime el tamaño de cada archivo generado."""
    print(f"\n{'archivo':44s} {'GeoJSON':>10s} {'TopoJSON':>10s}")
    for layer in layers:
        for variant in variants:
            for level in levels:
                base = cfg.stem(layer, variant, level.name)
                gj = cfg.GEOJSON_DIR / f"{base}.geojson"
                tj = cfg.TOPOJSON_DIR / f"{base}.topojson"
                if not gj.exists():
                    continue
                print(
                    f"{base:44s} {gj.stat().st_size / 1e6:9.2f}M {tj.stat().st_size / 1e6:9.2f}M"
                )


def run(layers=cfg.LAYERS, variants=cfg.VARIANTS, level_names=None) -> None:
    if not MAPSHAPER.exists():
        raise SystemExit("Falta mapshaper. Ejecuta: python mapas.py setup")

    names = level_names or [lv.name for lv in cfg.QUALITY_LEVELS]
    levels = tuple(cfg.LEVEL_BY_NAME[n] for n in names)
    cfg.GEOJSON_DIR.mkdir(parents=True, exist_ok=True)
    cfg.TOPOJSON_DIR.mkdir(parents=True, exist_ok=True)

    for layer in layers:
        for variant in variants:
            simplify(layer, variant, levels)

    report(layers, variants, levels)
