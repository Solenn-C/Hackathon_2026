"""Pipeline bronze → silver.

Exécute dans l'ordre tous les scripts de transformation du dossier bronze_silver/.

Usage :
    python src/scripts/bronze_silver/pipeline.py
    python src/scripts/bronze_silver/pipeline.py --skip ges_citepa rr_metropole
"""

import argparse
import logging
import runpy
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = Path(__file__).resolve().parent

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

PIPELINE: list[str] = [
    "tmin.py",
    "tx_metropole.py",
    "rr_metropole.py",
    "ges_communes.py",
    "ges_citepa.py",
    "ges_co2e_mt.py",
    "empreinte_carbone.py",
    "incendies.py",
    "swi.py",
]


def run_step(script_path: Path) -> bool:
    """Exécute un script via runpy depuis la racine du projet.

    Args:
        script_path: Chemin absolu vers le script à exécuter.

    Returns:
        True si succès, False sinon.
    """
    try:
        start = time.monotonic()
        runpy.run_path(str(script_path), run_name="__main__")
        logger.info("[OK]   %-30s %.1fs", script_path.name, time.monotonic() - start)
        return True
    except Exception as exc:
        logger.error("[FAIL] %-30s %s", script_path.name, exc)
        return False


def main() -> None:
    """Point d'entrée : exécute tous les scripts bronze → silver."""
    import os

    os.chdir(PROJECT_ROOT)

    parser = argparse.ArgumentParser(description="Pipeline bronze → silver")
    parser.add_argument(
        "--skip",
        nargs="+",
        metavar="SCRIPT",
        default=[],
        help="Noms de fichiers à ignorer (ex: ges_citepa.py rr_metropole.py)",
    )
    args = parser.parse_args()

    skip = set(args.skip)
    steps = [SCRIPTS_DIR / s for s in PIPELINE if s not in skip]

    missing = [s for s in steps if not s.exists()]
    if missing:
        for m in missing:
            logger.error("Script introuvable : %s", m)
        sys.exit(1)

    logger.info("Scripts à exécuter : %d", len(steps))
    total_start = time.monotonic()
    results = {s.name: run_step(s) for s in steps}

    success = sum(results.values())
    failed = len(results) - success
    logger.info("=" * 50)
    logger.info(
        "Résultat : %d/%d OK — %.1fs total",
        success,
        len(results),
        time.monotonic() - total_start,
    )

    if failed:
        logger.error("Échecs : %s", [k for k, v in results.items() if not v])
        sys.exit(1)


if __name__ == "__main__":
    main()
