#!/usr/bin/env python3
"""Mapas de Colombia (MGN 2025) — punto de entrada único del pipeline.

    python mapas.py setup     # instala dependencias (solo la primera vez)
    python mapas.py           # pipeline completo: prepare + build + render + verify
    python mapas.py build --layers departamentos --levels nacional

No hace falta activar el entorno virtual ni tener `make`: si existe `.venv/`, el
script se vuelve a lanzar solo con ese intérprete.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"

PASOS = ("prepare", "build", "render", "verify")
COMANDOS = ("all", *PASOS, "setup", "clean")


def venv_python() -> Path:
    """Ruta del intérprete del entorno virtual del proyecto."""
    if os.name == "nt":
        return ROOT / ".venv" / "Scripts" / "python.exe"
    return ROOT / ".venv" / "bin" / "python"


def usar_venv() -> None:
    """Se vuelve a lanzar dentro de `.venv` si el usuario invocó otro Python."""
    py = venv_python()
    if py.exists() and Path(sys.executable).resolve() != py.resolve():
        os.execv(str(py), [str(py), str(Path(__file__).resolve()), *sys.argv[1:]])


def ejecutar(cmd: list[str]) -> None:
    print("$", " ".join(cmd), flush=True)  # flush: si no, el eco sale tras la salida del comando
    subprocess.run(cmd, check=True, cwd=ROOT)


def setup() -> None:
    """Crea `.venv`, instala las dependencias de Python y mapshaper (npm)."""
    py = venv_python()
    uv = shutil.which("uv")

    if not py.exists():
        if uv:
            ejecutar([uv, "venv", "--python", "3.12", ".venv"])
        else:
            ejecutar([sys.executable, "-m", "venv", ".venv"])

    if uv:
        ejecutar([uv, "pip", "install", "--python", str(py), "-r", "requirements.txt"])
    else:
        ejecutar([str(py), "-m", "pip", "install", "-r", "requirements.txt"])

    npm = shutil.which("npm")
    if npm is None:
        sys.exit(
            "Falta npm. mapshaper (Node) es quien simplifica preservando la "
            "topología entre municipios vecinos.\n"
            "Instala Node 18+ desde https://nodejs.org y vuelve a ejecutar: "
            "python mapas.py setup"
        )
    ejecutar([npm, "install"])

    print("\nListo. Ahora: python mapas.py")


def cargar_pasos():
    """Importa los módulos del pipeline con un error legible si falta algo."""
    try:
        import build, prepare, render, verify  # noqa: E401
    except ImportError as exc:
        sys.exit(
            f"Falta la dependencia de Python «{exc.name}».\n"
            "Ejecuta primero: python mapas.py setup"
        )
    return {"prepare": prepare, "build": build, "render": render, "verify": verify}


def main() -> None:
    sys.path.insert(0, str(SCRIPTS))
    import config as cfg

    niveles = [lv.name for lv in cfg.QUALITY_LEVELS]
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("comando", nargs="?", default="all", choices=COMANDOS)
    parser.add_argument("--layers", nargs="*", default=list(cfg.LAYERS), choices=cfg.LAYERS,
                        help="Capas (por defecto ambas). Los municipios tardan mucho más.")
    parser.add_argument("--variants", nargs="*", default=list(cfg.VARIANTS), choices=cfg.VARIANTS,
                        help="Variantes: posición real del archipiélago o inset ampliado.")
    parser.add_argument("--levels", nargs="*", default=niveles, choices=niveles,
                        help="Niveles de calidad, nombrados por la escala a la que se usan.")
    args = parser.parse_args()

    if args.comando == "clean":
        shutil.rmtree(cfg.BUILD_DIR, ignore_errors=True)
        print(f"Borrado {cfg.BUILD_DIR.relative_to(ROOT)}/")
        return

    pasos = cargar_pasos()
    a_ejecutar = PASOS if args.comando == "all" else (args.comando,)

    for nombre in a_ejecutar:
        print(f"\n=== {nombre} ===")
        if nombre == "prepare":
            pasos[nombre].run(args.layers)          # prepare no simplifica: no usa niveles
        else:
            pasos[nombre].run(args.layers, args.variants, args.levels)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup()
    else:
        usar_venv()
        main()
