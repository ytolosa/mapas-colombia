"""Paso 1 del pipeline (`python mapas.py prepare`): shapefiles MGN -> GeoJSON maestro.

Produce, en `build/`, cuatro GeoJSON sin simplificar (capa x variante):

    master_departamentos_real.geojson
    master_departamentos_inset.geojson
    master_municipios_real.geojson
    master_municipios_inset.geojson

Responsabilidades de este paso:

1. Renombrar los atributos del MGN a los campos DIVIPOLA canónicos del proyecto.
2. Construir la variante `inset`, con San Andrés y Providencia acercados al
   continente y ampliados.

La simplificación NO ocurre aquí: la hace `build.py` con mapshaper, que
preserva la topología compartida entre municipios vecinos.
"""

from __future__ import annotations

import geopandas as gpd
from shapely.affinity import scale as shp_scale
from shapely.affinity import translate as shp_translate
from shapely.geometry import MultiPolygon, Polygon

import config as cfg


# --- Normalización de atributos ---------------------------------------------


def load_departamentos() -> gpd.GeoDataFrame:
    """Lee el shapefile departamental y devuelve solo los campos canónicos."""
    gdf = gpd.read_file(cfg.SHP_DPTO, engine="pyogrio")
    out = gpd.GeoDataFrame(
        {
            "divipola_dep": gdf["dpto_ccdgo"].str.zfill(2),
            "dpto_nombre": gdf["dpto_cnmbr"].str.strip(),
            "area_km2": gdf["dpto_narea"].round(4),
        },
        geometry=gdf.geometry,
        crs=gdf.crs,
    )
    out["divipola_dep_n"] = out["divipola_dep"].astype(int)
    return out[list(cfg.FIELDS_DPTO) + ["geometry"]].sort_values("divipola_dep_n")


def load_municipios() -> gpd.GeoDataFrame:
    """Lee el shapefile municipal y devuelve solo los campos canónicos."""
    gdf = gpd.read_file(cfg.SHP_MPIO, engine="pyogrio")
    out = gpd.GeoDataFrame(
        {
            "divipola_mun": gdf["mpio_cdpmp"].str.zfill(5),
            "divipola_dep": gdf["dpto_ccdgo"].str.zfill(2),
            "mpio_nombre": gdf["mpio_cnmbr"].str.strip(),
            "dpto_nombre": gdf["dpto_cnmbr"].str.strip(),
            "area_km2": gdf["mpio_narea"].round(4),
        },
        geometry=gdf.geometry,
        crs=gdf.crs,
    )
    out["divipola_mun_n"] = out["divipola_mun"].astype(int)
    out["divipola_dep_n"] = out["divipola_dep"].astype(int)
    return out[list(cfg.FIELDS_MPIO) + ["geometry"]].sort_values("divipola_mun_n")


def validate(gdf: gpd.GeoDataFrame, layer: str) -> None:
    """Falla ruidosamente si los códigos DIVIPOLA no cumplen el contrato."""
    assert gdf["divipola_dep"].str.fullmatch(r"\d{2}").all(), f"{layer}: divipola_dep inválido"
    assert (gdf["divipola_dep"].astype(int) == gdf["divipola_dep_n"]).all()
    if "divipola_mun" in gdf.columns:
        assert gdf["divipola_mun"].str.fullmatch(r"\d{5}").all(), f"{layer}: divipola_mun inválido"
        assert (gdf["divipola_mun"].astype(int) == gdf["divipola_mun_n"]).all()
        assert gdf["divipola_mun"].str[:2].eq(gdf["divipola_dep"]).all(), (
            f"{layer}: divipola_mun no empieza con su divipola_dep"
        )
        assert gdf["divipola_mun"].is_unique, f"{layer}: divipola_mun duplicado"
    else:
        assert gdf["divipola_dep"].is_unique, f"{layer}: divipola_dep duplicado"
    assert gdf.geometry.is_valid.all(), f"{layer}: geometrías inválidas"


# --- Ampliación del archipiélago --------------------------------------------


def island_transforms(mpios: gpd.GeoDataFrame) -> list[tuple[tuple[float, ...], dict]]:
    """Calcula la transformación afín de cada isla del archipiélago.

    Cada isla (San Andrés y Providencia) se escala sobre su propio centro y se
    reubica. Escalar el archipiélago como un solo bloque no sirve: las islas
    están a ~95 km una de otra, y al ampliar x15 esa separación crecería a más
    de 1.400 km. Tratarlas por separado es también lo que hace el notebook de
    referencia de `jacasta2/colombian_map`, que acerca San Andrés a Providencia
    dejando un espacio fijo entre ambas.

    Las dos islas quedan lado a lado, alineadas por el borde superior y en su
    orden geográfico oeste-este, que es como se dibuja el recuadro del
    archipiélago en los mapas de referencia de uso común.

    Returns:
        Lista de `(bbox_original, params)` ordenada de oeste a este, donde
        `params` tiene las claves `origin`, `scale`, `xoff` y `yoff`.
    """
    islas = mpios[mpios["divipola_dep"] == cfg.DPTO_SAN_ANDRES]
    if islas.empty:
        raise ValueError("No se encontró el departamento 88 en la capa municipal")

    # Oeste a este: San Andrés (81.7W) a la izquierda, Providencia (81.4W) a la
    # derecha, conservando su posición relativa real.
    islas = islas.assign(_left=islas.geometry.bounds["minx"]).sort_values("_left")

    transforms: list[tuple[tuple[float, ...], dict]] = []
    cursor_left = cfg.SA_ANCHOR_LON
    for _, row in islas.iterrows():
        minx, miny, maxx, maxy = row.geometry.bounds
        cx = (minx + maxx) / 2
        cy = (miny + maxy) / 2
        half_w = (maxx - minx) * cfg.SA_SCALE / 2
        half_h = (maxy - miny) * cfg.SA_SCALE / 2

        # Tras escalar sobre el centro, el centro no se mueve: basta trasladarlo
        # al punto donde queremos que quede la isla ampliada.
        target_cx = cursor_left + half_w
        target_cy = cfg.SA_ANCHOR_LAT - half_h

        transforms.append(
            (
                (minx, miny, maxx, maxy),
                {
                    "origin": (cx, cy),
                    "scale": cfg.SA_SCALE,
                    "xoff": target_cx - cx,
                    "yoff": target_cy - cy,
                },
            )
        )
        cursor_left = target_cx + half_w + cfg.SA_GAP

    return transforms


def _apply(geom, params: dict):
    """Escala una parte sobre su origen y la traslada."""
    scaled = shp_scale(geom, xfact=params["scale"], yfact=params["scale"], origin=params["origin"])
    return shp_translate(scaled, xoff=params["xoff"], yoff=params["yoff"])


def _match(geom, transforms) -> dict:
    """Devuelve la transformación de la isla a la que pertenece esta parte.

    Cada polígono se asigna a la isla cuyo bbox original lo contiene; si por
    algún borde no cae dentro de ninguno, gana el bbox más cercano.
    """
    minx, miny, maxx, maxy = geom.bounds
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    best, best_d = None, float("inf")
    for (bminx, bminy, bmaxx, bmaxy), params in transforms:
        if bminx <= cx <= bmaxx and bminy <= cy <= bmaxy:
            return params
        dx = max(bminx - cx, 0, cx - bmaxx)
        dy = max(bminy - cy, 0, cy - bmaxy)
        d = dx * dx + dy * dy
        if d < best_d:
            best, best_d = params, d
    return best


def make_inset(gdf: gpd.GeoDataFrame, transforms) -> gpd.GeoDataFrame:
    """Devuelve una copia con el archipiélago acercado y ampliado.

    Se transforma polígono por polígono (no la geometría completa del
    departamento), porque un MultiPolygon del archipiélago mezcla partes de las
    dos islas y cada una lleva su propia traslación.
    """
    out = gdf.copy()
    mask = out["divipola_dep"] == cfg.DPTO_SAN_ANDRES

    def transform(geom):
        parts = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
        moved = [_apply(p, _match(p, transforms)) for p in parts]
        return MultiPolygon(moved) if isinstance(geom, MultiPolygon) else moved[0]

    out.loc[mask, "geometry"] = out.loc[mask, "geometry"].apply(transform)
    assert isinstance(out.geometry.iloc[0], (Polygon, MultiPolygon))
    check_inset_clearance(out, mask)
    return out


#: Separación mínima aceptable, en grados, entre el archipiélago ampliado y el
#: continente. Por debajo de esto el inset se lee como parte de tierra firme.
MIN_CLEARANCE_DEG = 0.5


def check_inset_clearance(gdf: gpd.GeoDataFrame, mask) -> None:
    """Falla si el archipiélago ampliado invade el continente o queda pegado.

    El inset se ancla dentro del rectángulo continental para minimizar el
    encuadre, así que un cambio de `SA_SCALE` o de los anclajes puede meterlo
    encima de tierra firme sin que ningún otro control lo note.
    """
    islas = gdf.loc[mask].geometry.union_all()
    continente = gdf.loc[~mask].geometry.union_all()
    distancia = islas.distance(continente)
    if distancia < MIN_CLEARANCE_DEG:
        raise ValueError(
            f"El archipiélago ampliado queda a {distancia:.3f}° del continente "
            f"(mínimo {MIN_CLEARANCE_DEG}°). Ajusta SA_SCALE o los anclajes "
            f"SA_ANCHOR_LON / SA_ANCHOR_LAT en config.py."
        )
    print(f"  separación del continente: {distancia:.2f}°")


# --- Escritura ---------------------------------------------------------------


def write(gdf: gpd.GeoDataFrame, layer: str, variant: str) -> None:
    path = cfg.BUILD_DIR / f"master_{layer}_{variant}.geojson"
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(path, driver="GeoJSON", engine="pyogrio")
    size_mb = path.stat().st_size / 1e6
    print(f"  {path.name:44s} {len(gdf):5d} rasgos  {size_mb:7.1f} MB")


def run(layers=cfg.LAYERS) -> None:
    """Genera los GeoJSON maestros de las capas pedidas.

    La capa municipal se lee siempre: de ella salen las transformaciones del
    archipiélago que también usa la capa departamental.
    """
    if not cfg.SHP_MPIO.exists():
        raise SystemExit(
            f"No se encuentran los shapefiles del DANE en «{cfg.RAW_DIR.name}/».\n"
            "Descárgalos del MGN 2025 (ver README) y colócalos ahí."
        )

    print("Leyendo shapefiles MGN 2025...")
    mpios = load_municipios()
    validate(mpios, "municipios")
    transforms = island_transforms(mpios)

    print(
        f"Ampliación del archipiélago: x{cfg.SA_SCALE:g} anclado en "
        f"({cfg.SA_ANCHOR_LON}, {cfg.SA_ANCHOR_LAT})"
    )

    sources = {}
    if "municipios" in layers:
        sources["municipios"] = mpios
    if "departamentos" in layers:
        dptos = load_departamentos()
        validate(dptos, "departamentos")
        sources["departamentos"] = dptos

    print("Escribiendo GeoJSON maestros:")
    for layer, gdf in sources.items():
        write(gdf, layer, "real")
        write(make_inset(gdf, transforms), layer, "inset")
