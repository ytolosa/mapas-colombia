"""Configuración central del pipeline de mapas de Colombia (MGN 2025).

Todos los scripts (`prepare.py`, `build.py`, `render.py`) importan de aquí para
que la definición de niveles de calidad y rutas viva en un solo lugar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# --- Entrada -----------------------------------------------------------------

RAW_DIR = ROOT / "shapefiles MGN"
SHP_DPTO = RAW_DIR / "MGN2025_DPTO_POLITICO" / "MGN_ADM_DPTO_POLITICO.shp"
SHP_MPIO = RAW_DIR / "MGN2025_MPIO_GRAFICO" / "MGN_ADM_MPIO_GRAFICO.shp"

# --- Salida ------------------------------------------------------------------

BUILD_DIR = ROOT / "build"          # intermedios (no versionados)
OUTPUT_DIR = ROOT / "output"
GEOJSON_DIR = OUTPUT_DIR / "geojson"
TOPOJSON_DIR = OUTPUT_DIR / "topojson"
PREVIEW_DIR = OUTPUT_DIR / "previews"

# --- Capas y variantes -------------------------------------------------------

LAYERS = ("departamentos", "municipios")

#: `real` conserva la posición geográfica verdadera del archipiélago.
#: `inset` lo acerca al continente y lo amplía para que sea visible en un mapa
#: nacional (deja de ser geográficamente exacto: es una ampliación cartográfica).
VARIANTS = ("real", "inset")

# --- Ampliación (inset) de San Andrés y Providencia --------------------------

DPTO_SAN_ANDRES = "88"

#: Factor de ampliación del archipiélago en la variante `inset`. Con 1.0 el
#: archipiélago solo se acerca; con valores mayores además se agranda.
#: Con 15, San Andrés ocupa ~10 % de la altura del mapa nacional, que es el
#: tamaño al que se dibuja el archipiélago en los mapas de referencia de uso
#: común. Con valores mucho menores las islas quedan invisibles.
SA_SCALE = 15.0

#: Esquina superior izquierda (lon, lat) del bloque ampliado.
#:
#: Está elegida para que el archipiélago quepa DENTRO del rectángulo que ocupa
#: el continente (-79,01 a -66,85 en longitud; -4,23 a 12,46 en latitud), no
#: fuera. En la franja de latitud 10,5-13,4 el continente más occidental está
#: en -75,5, así que el mar Caribe del noroeste deja unos 3,5° libres: espacio
#: de sobra para el bloque, que mide 1,6° de ancho.
#:
#: El resultado es que la variante `inset` tiene exactamente el mismo encuadre
#: que el continente solo. Comparada con `real`, el mapa es 18 % más estrecho y
#: 5 % más bajo, que es lo máximo que se puede ganar sin recortar territorio.
SA_ANCHOR_LON = -78.95
SA_ANCHOR_LAT = 12.40

#: Separación horizontal, en grados ya escalados, entre las dos islas. Van lado
#: a lado (San Andrés al oeste, Providencia al este) y no apiladas: ampliadas
#: x15 el bloque apilado mediría más de 3° de alto.
SA_GAP = 0.15


@dataclass(frozen=True)
class QualityLevel:
    """Un nivel de calidad del pipeline.

    Cada nivel lleva el nombre de la escala a la que deja de notarse la
    simplificación. No hay más niveles porque no se ven: comparando los previews
    a las tres escalas, `municipal` es indistinguible del dato sin simplificar, y
    entre estos tres cada salto sí se aprecia (ver `docs/guia-calidad.md`).

    Attributes:
        name: identificador usado en nombres de archivo.
        simplify: porcentaje de vértices que mapshaper conserva (`None` = sin
            simplificar).
        precision: redondeo de coordenadas en grados decimales para el GeoJSON.
        quantization: rejilla de cuantización del TopoJSON.
        purpose: para qué sirve este nivel (se usa en la documentación).
    """

    name: str
    simplify: float | None
    precision: float
    quantization: int
    purpose: str


#: Niveles ordenados de mayor a menor detalle.
QUALITY_LEVELS: tuple[QualityLevel, ...] = (
    QualityLevel(
        name="municipal",
        simplify=25.0,
        precision=0.00001,
        quantization=1_000_000,
        purpose="Zoom a un municipio o zona urbana, impresión, trabajo vectorial.",
    ),
    QualityLevel(
        name="departamental",
        simplify=8.0,
        precision=0.0001,
        quantization=100_000,
        purpose="Un departamento en pantalla; tableros donde el usuario puede acercarse.",
    ),
    QualityLevel(
        name="nacional",
        simplify=2.0,
        precision=0.0005,
        quantization=20_000,
        purpose="Colombia completa: herramientas de BI (Power BI, Tableau, Looker) y web.",
    ),
)

LEVEL_BY_NAME = {lvl.name: lvl for lvl in QUALITY_LEVELS}

# --- Campos ------------------------------------------------------------------

#: Campos de la capa municipal, en orden.
FIELDS_MPIO = (
    "divipola_mun",
    "divipola_mun_n",
    "divipola_dep",
    "divipola_dep_n",
    "mpio_nombre",
    "dpto_nombre",
    "area_km2",
)

#: Campos de la capa departamental, en orden.
FIELDS_DPTO = (
    "divipola_dep",
    "divipola_dep_n",
    "dpto_nombre",
    "area_km2",
)

# --- Previews ----------------------------------------------------------------

@dataclass(frozen=True)
class PreviewScope:
    """Un ámbito de preview: qué recorte del mapa se dibuja y para qué variantes.

    Attributes:
        name: aparece en la ruta y en el nombre del archivo.
        field: campo por el que se filtra, o `None` para todo el país.
        code: valor que debe tener ese campo.
        variants: variantes que tiene sentido dibujar aquí. Solo el ámbito
            nacional necesita las dos: el archipiélago no entra en el recorte
            de Boyacá ni en el de Bogotá, así que `real` e `inset` darían dos
            imágenes idénticas.
    """

    name: str
    field: str | None
    code: str | None
    variants: tuple[str, ...]


#: Una escala por nivel de calidad: el país entero, un departamento y un
#: municipio. Comparar los tres previews es lo que justifica que haya tres
#: niveles y no más.
PREVIEW_SCOPES: tuple[PreviewScope, ...] = (
    PreviewScope("colombia", None, None, VARIANTS),
    PreviewScope("boyaca", "divipola_dep", "15", ("real",)),
    PreviewScope("bogota", "divipola_mun", "11001", ("real",)),
)

PREVIEW_DPI = 200
PREVIEW_WIDTH_IN = 8.0


def stem(layer: str, variant: str, level: str) -> str:
    """Nombre base canónico de un archivo de salida."""
    return f"col_{layer}_{variant}_{level}"
