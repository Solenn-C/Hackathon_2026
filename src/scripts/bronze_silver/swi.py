"""Consolidation des fichiers CSV d'indice d'humidité des sols (SWI).

Le SWI (Soil Wetness Index) est un indice mensuel d'humidité des sols,
compris entre 0 (sol très sec) et >1 (sol saturé).

Source : data/bronze/swi/swi.*.csv
Format : NUMERO;LAMBX;LAMBY;DATE;SWI_UNIF_MENS (décimale = virgule)
Produit : data/silver/swi.parquet
"""

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

BRONZE_DIR = Path("data/bronze/swi")
SILVER_DIR = Path("data/silver")
OUTPUT_FILE = SILVER_DIR / "swi.parquet"


def parse_csv(path: Path) -> pd.DataFrame | None:
    """Parse un fichier CSV SWI et retourne un DataFrame normalisé.

    Args:
        path: Chemin vers le fichier CSV.

    Returns:
        DataFrame avec colonnes [date, numero, lambx, lamby, swi],
        ou None si le fichier est invalide.
    """
    try:
        df = pd.read_csv(path, sep=";", decimal=",", encoding="utf-8")
    except Exception as exc:
        logger.warning("Impossible de parser %s : %s", path.name, exc)
        return None

    df.columns = df.columns.str.strip().str.lower()

    expected = {"numero", "lambx", "lamby", "date", "swi_unif_mens"}
    if not expected.issubset(df.columns):
        logger.warning(
            "Colonnes inattendues dans %s : %s", path.name, df.columns.tolist()
        )
        return None

    df = df.rename(columns={"swi_unif_mens": "swi"})
    df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y%m")
    df["swi"] = pd.to_numeric(df["swi"], errors="coerce")

    return df[["date", "numero", "lambx", "lamby", "swi"]]


def main() -> None:
    """Point d'entrée : consolide tous les CSV SWI en un seul Parquet."""
    SILVER_DIR.mkdir(parents=True, exist_ok=True)

    # Ignorer les fichiers .Zone.Identifier (métadonnées Windows)
    csv_files = sorted(
        f for f in BRONZE_DIR.glob("*.csv") if ".Zone.Identifier" not in f.name
    )
    logger.info("Fichiers CSV trouvés : %d", len(csv_files))

    frames = []
    errors = 0

    for path in csv_files:
        df = parse_csv(path)
        if df is not None:
            frames.append(df)
        else:
            errors += 1

    if not frames:
        logger.error("Aucune donnée valide. Abandon.")
        return

    combined = pd.concat(frames, ignore_index=True)

    # Doublons
    n_dupes = combined.duplicated(subset=["numero", "date"]).sum()
    if n_dupes:
        logger.warning("Doublons supprimés : %d", n_dupes)
        combined = combined.drop_duplicates(subset=["numero", "date"])

    # Nulls
    n_nulls = combined["swi"].isna().sum()
    if n_nulls:
        logger.warning("Nulls supprimés : %d", n_nulls)
        combined = combined.dropna(subset=["swi"])

    combined = combined.sort_values(["numero", "date"]).reset_index(drop=True)

    combined.to_parquet(OUTPUT_FILE, index=False, engine="pyarrow")

    logger.info("Points (NUMERO)  : %d", combined["numero"].nunique())
    logger.info(
        "Période couverte : %s → %s",
        combined["date"].min().date(),
        combined["date"].max().date(),
    )
    logger.info("Lignes totales   : %d", len(combined))
    logger.info("Erreurs / skips  : %d", errors)
    logger.info("Parquet          : %s", OUTPUT_FILE)


if __name__ == "__main__":
    main()
