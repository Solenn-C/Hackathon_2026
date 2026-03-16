"""Nettoyage des émissions de GES annuelles par secteur et par commune.

Source : emissions-de-gaz-a-effet-de-serre-annuelles-par-secteur-commune.csv
Produit : data/silver/ges_communes.parquet
"""

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

BRONZE_FILE = Path(
    "data/bronze/ges/emissions-de-gaz-a-effet-de-serre-annuelles-par-secteur-commune.csv"
)
SILVER_DIR = Path("data/silver")
OUTPUT_FILE = SILVER_DIR / "ges_communes.parquet"

VALID_SECTEURS = {
    "Industrie hors Energie",
    "Agriculture",
    "Tertiaire",
    "Résidentiel",
    "Déchets",
    "Transports",
    "Energie",
}


def main() -> None:
    """Charge, nettoie et exporte les émissions GES par commune en Parquet."""
    SILVER_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(BRONZE_FILE, sep=None, engine="python")
    logger.info("Chargé : %d lignes", len(df))

    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
    )

    # Parsing de la date (format ISO avec timestamp)
    df["annee"] = pd.to_datetime(df["date_mesure"], errors="coerce").dt.year
    n_bad_dates = df["annee"].isna().sum()
    if n_bad_dates:
        logger.warning("Dates non parsables supprimées : %d", n_bad_dates)
    df = df.dropna(subset=["annee"])
    df["annee"] = df["annee"].astype(int)
    df = df.drop(columns=["date_mesure"])

    # Doublons
    n_dupes = df.duplicated(subset=["annee", "geocode_commune", "secteur"]).sum()
    if n_dupes:
        logger.warning("Doublons supprimés : %d", n_dupes)
        df = df.drop_duplicates(subset=["annee", "geocode_commune", "secteur"])

    # Nulls sur la valeur
    n_nulls = df["valeur"].isna().sum()
    if n_nulls:
        logger.warning("Nulls sur valeur supprimés : %d", n_nulls)
        df = df.dropna(subset=["valeur"])

    # Valeurs négatives (émissions ne peuvent pas être négatives)
    n_neg = (df["valeur"] < 0).sum()
    if n_neg:
        logger.warning("Valeurs négatives supprimées : %d", n_neg)
        df = df[df["valeur"] >= 0]

    # Secteurs inconnus
    unknown = ~df["secteur"].isin(VALID_SECTEURS)
    if unknown.sum():
        logger.warning(
            "Secteurs inconnus supprimés : %d — %s",
            unknown.sum(),
            df.loc[unknown, "secteur"].unique(),
        )
        df = df[~unknown]

    df = df[["annee", "geocode_commune", "libelle_commune", "secteur", "valeur"]]
    df = df.sort_values(["annee", "geocode_commune", "secteur"]).reset_index(drop=True)

    df.to_parquet(OUTPUT_FILE, index=False, engine="pyarrow")

    logger.info("Communes    : %d", df["geocode_commune"].nunique())
    logger.info("Années      : %s", sorted(df["annee"].unique()))
    logger.info("Secteurs    : %d", df["secteur"].nunique())
    logger.info("Lignes      : %d", len(df))
    logger.info("Parquet     : %s", OUTPUT_FILE)


if __name__ == "__main__":
    main()
