"""Nettoyage des arrêtés de catastrophes naturelles (CataNat).

Source : data/bronze/cata/cata.xlsx
Colonnes : INSEE, Departement, Commune, Périls, Date début, Date fin
Produit : data/silver/cata.parquet
"""

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

BRONZE_FILE = Path("data/bronze/cata/cata.xlsx")
SILVER_DIR = Path("data/silver")
OUTPUT_FILE = SILVER_DIR / "cata.parquet"

SHEET = "Données complètes"

COLUMN_RENAME = {
    "INSEE": "code_insee",
    "Departement": "code_dept",
    "Commune": "commune",
    "Périls": "peril",
    "Date début": "date_debut",
    "Date fin": "date_fin",
}


def main() -> None:
    """Charge, nettoie et exporte les catastrophes naturelles en Parquet."""
    SILVER_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(BRONZE_FILE, sheet_name=SHEET, engine="openpyxl")
    logger.info("Chargé : %d lignes", len(df))

    df = df.rename(columns=COLUMN_RENAME)

    # Dates
    df["date_debut"] = pd.to_datetime(df["date_debut"], errors="coerce")
    df["date_fin"] = pd.to_datetime(df["date_fin"], errors="coerce")
    n_bad_dates = df["date_debut"].isna().sum()
    if n_bad_dates:
        logger.warning("Dates de début invalides supprimées : %d", n_bad_dates)
        df = df.dropna(subset=["date_debut"])

    # Nulls sur péril
    n_null_peril = df["peril"].isna().sum()
    if n_null_peril:
        logger.warning("Lignes sans péril supprimées : %d", n_null_peril)
        df = df.dropna(subset=["peril"])

    # Doublons
    n_dupes = df.duplicated().sum()
    if n_dupes:
        logger.warning("Doublons supprimés : %d", n_dupes)
        df = df.drop_duplicates()

    # Nettoyage des chaînes
    df["peril"] = df["peril"].str.strip()
    df["commune"] = df["commune"].str.strip()
    df["code_dept"] = df["code_dept"].astype(str).str.strip()
    df["code_insee"] = df["code_insee"].astype(str).str.strip()

    # Durée de l'événement
    df["duree_jours"] = (df["date_fin"] - df["date_debut"]).dt.days

    df = df[
        [
            "code_insee",
            "code_dept",
            "commune",
            "peril",
            "date_debut",
            "date_fin",
            "duree_jours",
        ]
    ]
    df = df.sort_values(["code_dept", "date_debut"]).reset_index(drop=True)

    df.to_parquet(OUTPUT_FILE, index=False, engine="pyarrow")

    logger.info("Communes     : %d", df["code_insee"].nunique())
    logger.info("Départements : %d", df["code_dept"].nunique())
    logger.info(
        "Périls       : %d — %s",
        df["peril"].nunique(),
        sorted(df["peril"].unique())[:5],
    )
    logger.info(
        "Période      : %s → %s",
        df["date_debut"].min().date(),
        df["date_debut"].max().date(),
    )
    logger.info("Lignes       : %d", len(df))
    logger.info("Parquet      : %s", OUTPUT_FILE)


if __name__ == "__main__":
    main()
