"""Paso 3 (`python mapas.py render`): previews PNG y SVG de cada archivo generado.

Para cada combinación de capa, variante y nivel de calidad dibuja las tres
escalas que dan nombre a los niveles: Colombia completa, un departamento
(Boyacá) y un municipio (Bogotá D.C.). Sirven para dos cosas:

- Comparar visualmente cuánto detalle sobrevive en cada nivel a la escala a la
  que ese nivel se usa, que es la base de `docs/guia-calidad.md`.
- Detectar de un vistazo si la simplificación rompió algo (islas perdidas,
  municipios colapsados, huecos entre vecinos).

El PNG es el que se mira; el SVG es vectorial y sirve para llevar el mapa a
Illustrator, Inkscape o Figma.
"""

from __future__ import annotations

import math

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import config as cfg  # noqa: E402

FILL = "#dbe4ee"
EDGE = "#2f4858"
BACKGROUND = "#ffffff"

#: Grosor del borde según qué se dibuja. Un mapa nacional de 1.122 municipios
#: necesita líneas mucho más finas que un departamento solo, o el relleno
#: desaparece bajo los bordes.
LINEWIDTH = {
    ("municipios", "colombia"): 0.12,
    ("municipios", "boyaca"): 0.35,
    ("municipios", "bogota"): 1.0,
    ("departamentos", "colombia"): 0.45,
    ("departamentos", "boyaca"): 0.8,
}


def figure_size(bounds, width_in: float) -> tuple[float, float]:
    """Alto proporcional a la extensión geográfica, corrigiendo la latitud."""
    minx, miny, maxx, maxy = bounds
    lat_mid = math.radians((miny + maxy) / 2)
    w = (maxx - minx) * math.cos(lat_mid)
    h = maxy - miny
    return width_in, max(width_in * h / w, 1.0)


def render(gdf: gpd.GeoDataFrame, out_base, title: str, key: tuple[str, str]) -> None:
    bounds = gdf.total_bounds
    fig, ax = plt.subplots(figsize=figure_size(bounds, cfg.PREVIEW_WIDTH_IN))
    fig.patch.set_facecolor(BACKGROUND)
    gdf.plot(ax=ax, facecolor=FILL, edgecolor=EDGE, linewidth=LINEWIDTH[key])
    ax.set_axis_off()
    ax.margins(0.01)
    ax.set_title(title, fontsize=8, color="#4a5a68", loc="left", pad=6)
    fig.tight_layout(pad=0.4)

    out_base.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_base.with_suffix(".png"), dpi=cfg.PREVIEW_DPI, facecolor=BACKGROUND)
    fig.savefig(out_base.with_suffix(".svg"), facecolor=BACKGROUND)
    plt.close(fig)


def subset(gdf: gpd.GeoDataFrame, field: str | None, code: str | None):
    """Recorta el GeoDataFrame al ámbito del preview, o None si no aplica.

    La capa departamental no tiene `divipola_mun`, así que el preview municipal
    simplemente no existe para ella.
    """
    if field is None:
        return gdf
    if field not in gdf.columns:
        return None
    out = gdf[gdf[field] == code]
    return None if out.empty else out


def run(layers=cfg.LAYERS, variants=cfg.VARIANTS, level_names=None) -> None:
    names = level_names or [lv.name for lv in cfg.QUALITY_LEVELS]

    for layer in layers:
        for variant in variants:
            for level_name in names:
                base = cfg.stem(layer, variant, level_name)
                src = cfg.GEOJSON_DIR / f"{base}.geojson"
                if not src.exists():
                    print(f"  (falta {src.name}, se omite)")
                    continue

                gdf = gpd.read_file(src, engine="pyogrio")
                size_mb = src.stat().st_size / 1e6

                for scope in cfg.PREVIEW_SCOPES:
                    if variant not in scope.variants:
                        continue  # el archipiélago no entra en este recorte
                    parte = subset(gdf, scope.field, scope.code)
                    if parte is None:
                        continue
                    title = (
                        f"{layer} · {variant} · nivel {level_name} · {scope.name} · "
                        f"{len(parte)} rasgos · GeoJSON {size_mb:.2f} MB"
                    )
                    out = cfg.PREVIEW_DIR / scope.name / f"{base}_{scope.name}"
                    render(parte, out, title, (layer, scope.name))
                    print(f"  {out.relative_to(cfg.OUTPUT_DIR)}.png/.svg")
