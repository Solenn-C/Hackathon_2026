"""Nettoyage des données de bilan massique glaciaire WGMS.

Source : data/bronze/glacier/glacier_WGMS.csv
Format : BADC-CSV avec 24 lignes d'en-tête, puis colonnes time/year/data.
         time = jours depuis 1800-01-01, data = bilan massique cumulatif (mwe).

Produit : data/silver/glacier_wgms.parquet
Colonnes :
  annee                         — année calendaire
  bilan_massique_cumulatif_mwe  — bilan cumulatif en mètres eau équivalent (1970 = 0)
  bilan_annuel_mwe              — variation annuelle (différence vs année précédente)
"""

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

BRONZE_FILE = Path("data/bronze/glacier/glacier_WGMS.csv")
SILVER_DIR = Path("data/silver")
OUTPUT_FILE = SILVER_DIR / "glacier_wgms.parquet"

# Marqueur de début des données dans le format BADC-CSV
DATA_MARKER = "data"


def find_data_start(path: Path) -> int:
    """Retourne le numéro de ligne (0-indexé) du marqueur 'data'.

    Args:
        path: Chemin vers le fichier BADC-CSV.

    Returns:
        Index de la ligne contenant uniquement 'data'.
    """
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if line.strip().lower() == DATA_MARKER:
                return i
    raise ValueError(f"Marqueur '{DATA_MARKER}' introuvable dans {path}")


def main() -> None:
    """Charge, nettoie et exporte le bilan massique glaciaire WGMS en Parquet."""
    SILVER_DIR.mkdir(parents=True, exist_ok=True)

    data_line = find_data_start(BRONZE_FILE)
    logger.info("Données démarrent à la ligne %d", data_line + 1)

    # Lecture des données (ligne header + données après le marqueur)
    df = pd.read_csv(
        BRONZE_FILE,
        skiprows=data_line + 1,  # +1 pour sauter le marqueur lui-même
        header=0,
        names=["time_days", "annee", "bilan_massique_cumulatif_mwe"],
    )

    # Supprimer la ligne de fin "end data" si présente
    df = df[pd.to_numeric(df["annee"], errors="coerce").notna()].copy()
    df["annee"] = df["annee"].astype(int)
    df["bilan_massique_cumulatif_mwe"] = pd.to_numeric(
        df["bilan_massique_cumulatif_mwe"], errors="coerce"
    )
    df = df.drop(columns=["time_days"])

    logger.info("Chargé : %d lignes", len(df))

    # Nulls
    n_nulls = df["bilan_massique_cumulatif_mwe"].isna().sum()
    if n_nulls:
        logger.warning("Valeurs nulles supprimées : %d", n_nulls)
        df = df.dropna(subset=["bilan_massique_cumulatif_mwe"])

    # Doublons
    n_dupes = df.duplicated(subset=["annee"]).sum()
    if n_dupes:
        logger.warning("Doublons supprimés : %d", n_dupes)
        df = df.drop_duplicates(subset=["annee"])

    df = df.sort_values("annee").reset_index(drop=True)

    # Variation annuelle (différence de bilan cumulatif)
    df["bilan_annuel_mwe"] = df["bilan_massique_cumulatif_mwe"].diff()

    df.to_parquet(OUTPUT_FILE, index=False, engine="pyarrow")

    logger.info("Période   : %d → %d", df["annee"].min(), df["annee"].max())
    logger.info(
        "Bilan min : %.3f mwe (an %d)",
        df["bilan_massique_cumulatif_mwe"].min(),
        df.loc[df["bilan_massique_cumulatif_mwe"].idxmin(), "annee"],
    )
    logger.info("Lignes    : %d", len(df))
    logger.info("Parquet   : %s", OUTPUT_FILE)


if __name__ == "__main__":
    main()
