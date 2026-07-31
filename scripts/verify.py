"""Paso 4 (`python mapas.py verify`): comprueba que las salidas cumplan el contrato.

Comprueba, para las 12 combinaciones de capa, variante y nivel:

- Existen el GeoJSON, el TopoJSON y los previews (PNG y SVG) de cada ámbito
  aplicable a la capa.
- El conjunto de campos es exactamente el declarado en `config.py`.
- El número de rasgos se conserva tras simplificar (33 y 1.122): ningún
  municipio ni departamento se pierde por más que se baje el detalle.
- `divipola_dep` sigue siendo texto de 2 caracteres y `divipola_mun` de 5, con
  sus ceros a la izquierda intactos.
- Los `_n` corresponden al mismo código casteado a entero.
- El TopoJSON es una topología válida.

Esto atrapa regresiones de atributos y de conteo. Lo que NO atrapa son los
errores geométricos: huecos entre municipios vecinos, islas perdidas o
polígonos colapsados. Para eso hay que mirar los PNG de `output/previews/`.
"""

from __future__ import annotations

import json

import config as cfg

EXPECTED_COUNT = {"departamentos": 33, "municipios": 1122}


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def verify_geojson(path, layer: str, base: str, failures: list[str]) -> None:
    data = json.loads(path.read_text())
    features = data["features"]
    fields = set(cfg.FIELDS_MPIO if layer == "municipios" else cfg.FIELDS_DPTO)

    check(
        len(features) == EXPECTED_COUNT[layer],
        f"{base}: {len(features)} rasgos, se esperaban {EXPECTED_COUNT[layer]}",
        failures,
    )

    props = set(features[0]["properties"])
    check(props == fields, f"{base}: campos inesperados {props ^ fields}", failures)

    for feature in features:
        p = feature["properties"]
        dep = p.get("divipola_dep")
        if not (isinstance(dep, str) and len(dep) == 2 and dep.isdigit()):
            failures.append(f"{base}: divipola_dep inválido ({dep!r})")
            break
        if int(dep) != p.get("divipola_dep_n"):
            failures.append(f"{base}: divipola_dep_n no coincide con {dep!r}")
            break
        if layer == "municipios":
            mun = p.get("divipola_mun")
            if not (isinstance(mun, str) and len(mun) == 5 and mun.isdigit()):
                failures.append(f"{base}: divipola_mun inválido ({mun!r})")
                break
            if int(mun) != p.get("divipola_mun_n"):
                failures.append(f"{base}: divipola_mun_n no coincide con {mun!r}")
                break


def run(layers=cfg.LAYERS, variants=cfg.VARIANTS, level_names=None) -> None:
    names = level_names or [lv.name for lv in cfg.QUALITY_LEVELS]
    failures: list[str] = []
    checked = 0

    for layer in layers:
        fields = cfg.FIELDS_MPIO if layer == "municipios" else cfg.FIELDS_DPTO
        for variant in variants:
            for level_name in names:
                base = cfg.stem(layer, variant, level_name)

                gj = cfg.GEOJSON_DIR / f"{base}.geojson"
                tj = cfg.TOPOJSON_DIR / f"{base}.topojson"
                if not gj.exists():
                    failures.append(f"falta {gj}")
                    continue
                if not tj.exists():
                    failures.append(f"falta {tj}")
                else:
                    topo = json.loads(tj.read_text())
                    check(topo.get("type") == "Topology", f"{base}: TopoJSON inválido", failures)
                    checked += 1

                verify_geojson(gj, layer, base, failures)
                checked += 1

                for scope in cfg.PREVIEW_SCOPES:
                    if variant not in scope.variants:
                        continue  # p. ej. no hay preview `inset` de Boyacá
                    if scope.field is not None and scope.field not in fields:
                        continue  # p. ej. no hay preview municipal de departamentos
                    for ext in ("png", "svg"):
                        preview = cfg.PREVIEW_DIR / scope.name / f"{base}_{scope.name}.{ext}"
                        if preview.exists():
                            checked += 1
                        else:
                            failures.append(f"falta {preview}")

    if failures:
        print(f"{len(failures)} problema(s):")
        for f in failures:
            print(f"  - {f}")
        raise SystemExit(1)

    print(f"OK — {checked} archivos verificados")
