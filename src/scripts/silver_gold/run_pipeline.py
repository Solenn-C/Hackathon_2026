"""Pipeline complet bronze → silver → gold.

Exécute dans l'ordre tous les scripts d'ingestion et de transformation :
  1. Bronze → Silver : TN, TX, RR, GES communes, GES Citepa, empreinte carbone, incendies
  2. Silver → Gold   : nettoyage et jointure climat

Usage :
    python src/scripts/run_pipeline.py
    python src/scripts/run_pipeline.py --only bronze
    python src/scripts/run_pipeline.py --only gold
    python src/scripts/run_pipeline.py --skip ges_citepa rr_metropole
"""

import argparse
import logging
import runpy
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# Racine du projet = trois niveaux au-dessus de ce fichier
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BRONZE_SILVER_DIR = PROJECT_ROOT / "src" / "scripts" / "bronze_silver"
SILVER_GOLD_DIR = PROJECT_ROOT / "src" / "scripts" / "silver_gold"

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger(__name__)


SILVER_DIR = PROJECT_ROOT / "data" / "silver"
GOLD_DIR = PROJECT_ROOT / "data" / "gold"

# Fichiers silver passés directement en gold (déjà nettoyés)
SILVER_TO_GOLD_COPIES: list[str] = [
    "ges_communes.parquet",
    "ges_citepa.parquet",
    "empreinte_carbone.parquet",
    "incendies.parquet",
    "cata.parquet",
]


@dataclass
class Step:
    """Représente une étape du pipeline."""

    name: str
    path: Path
    stage: str  # "bronze" ou "gold"
    deps: list[str] = field(default_factory=list)


def _b(script: str) -> Path:
    return BRONZE_SILVER_DIR / script


def _g(script: str) -> Path:
    return SILVER_GOLD_DIR / script


PIPELINE: list[Step] = [
    # Bronze → Silver
    Step("tn_metropole", _b("tmin.py"), stage="bronze"),
    Step("tx_metropole", _b("tx_metropole.py"), stage="bronze"),
    Step("rr_metropole", _b("rr_metropole.py"), stage="bronze"),
    Step("ges_communes", _b("ges_communes.py"), stage="bronze"),
    Step("ges_citepa", _b("ges_citepa.py"), stage="bronze"),
    Step("empreinte_carbone", _b("empreinte_carbone.py"), stage="bronze"),
    Step("incendies", _b("incendies.py"), stage="bronze"),
    Step("swi", _b("swi.py"), stage="bronze"),
    Step("cata", _b("cata.py"), stage="bronze"),
    # Silver → Gold
    Step(
        "silver_to_gold",
        _g("silver_to_gold.py"),
        stage="gold",
        deps=["tn_metropole", "tx_metropole", "rr_metropole"],
    ),
    Step(
        "swi_par_departement",
        _g("swi_par_departement.py"),
        stage="gold",
        deps=["swi"],
    ),
]


def copy_silver_to_gold() -> None:
    """Copie les fichiers silver nettoyés directement dans gold.

    Utilisé pour les datasets (GES, empreinte, incendies) qui n'ont pas
    besoin de jointure et sont déjà propres après l'étape silver.
    """
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    for filename in SILVER_TO_GOLD_COPIES:
        src = SILVER_DIR / filename
        dst = GOLD_DIR / filename
        if src.exists():
            shutil.copy2(src, dst)
            logger.info("[COPY] %s → gold/", filename)
        else:
            logger.warning("[MISSING] %s introuvable dans silver/", filename)


def run_step(step: Step) -> bool:
    """Exécute un script via runpy depuis la racine du projet.

    Args:
        step: Étape du pipeline à exécuter.

    Returns:
        True si succès, False si erreur.
    """
    script_path = step.path
    try:
        start = time.monotonic()
        # runpy exécute le script avec __name__ == '__main__'
        runpy.run_path(str(script_path), run_name="__main__")
        elapsed = time.monotonic() - start
        logger.info("[OK] %-22s %.1fs", step.name, elapsed)
        return True
    except Exception as exc:
        logger.error("[FAIL] %-20s %s", step.name, exc)
        return False


def parse_args() -> argparse.Namespace:
    """Parse les arguments de la ligne de commande.

    Returns:
        Namespace avec les champs only et skip.
    """
    parser = argparse.ArgumentParser(description="Pipeline bronze → silver → gold")
    parser.add_argument(
        "--only",
        choices=["bronze", "gold"],
        help="Exécuter uniquement une étape du pipeline",
    )
    parser.add_argument(
        "--skip",
        nargs="+",
        metavar="STEP",
        default=[],
        help="Noms des étapes à ignorer",
    )
    return parser.parse_args()


def main() -> None:
    """Point d'entrée : exécute le pipeline complet ou partiel."""
    import os

    os.chdir(PROJECT_ROOT)
    logger.info("Répertoire de travail : %s", PROJECT_ROOT)

    args = parse_args()

    steps = PIPELINE
    if args.only:
        steps = [s for s in steps if s.stage == args.only]
    if args.skip:
        skipped = set(args.skip)
        steps = [s for s in steps if s.name not in skipped]

    logger.info("Pipeline : %d étape(s) à exécuter", len(steps))
    logger.info("Étapes   : %s", [s.name for s in steps])

    results: dict[str, bool] = {}
    total_start = time.monotonic()

    for step in steps:
        # Vérification des dépendances
        failed_deps = [d for d in step.deps if results.get(d) is False]
        if failed_deps:
            logger.error(
                "[SKIP] %-20s dépendances échouées : %s", step.name, failed_deps
            )
            results[step.name] = False
            continue

        logger.info(">>> %s", step.name)
        results[step.name] = run_step(step)

    # Résumé
    total = time.monotonic() - total_start
    success = sum(v for v in results.values())
    failed = len(results) - success

    logger.info("=" * 50)
    logger.info(
        "Résultat : %d/%d étapes OK — %.1fs total", success, len(results), total
    )

    # Copie silver → gold pour les datasets sans jointure
    if not args.only or args.only == "gold":
        copy_silver_to_gold()

    if failed:
        failed_steps = [k for k, v in results.items() if not v]
        logger.error("Échecs : %s", failed_steps)
        sys.exit(1)


if __name__ == "__main__":
    main()
