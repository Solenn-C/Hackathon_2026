"""Jointure des fichiers Parquet TN, TX et RR en un unique fichier gold.

Fusionne les trois séries mensuelles homogénéisées (température minimale,
température maximale, précipitations) sur les clés [date, num_poste].
Produit un fichier Parquet dans data/gold/.
"""

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

SILVER_DIR = Path("data/silver")
GOLD_DIR = Path("data/gold")
OUTPUT_FILE = GOLD_DIR / "climat_metropole.parquet"

STATION_COLS = ["num_poste", "nom_usuel", "latitude", "longitude", "altitude"]
JOIN_KEYS = ["date", "num_poste"]


def load(path: Path, value_col: str) -> pd.DataFrame:
    """Charge un fichier Parquet silver et retourne les colonnes utiles.

    Args:
        path: Chemin vers le fichier Parquet.
        value_col: Nom de la colonne de mesure (tn, tx ou rr).

    Returns:
        DataFrame avec les colonnes [date, num_poste, nom_usuel, latitude,
        longitude, altitude, <value_col>, q_hom_<value_col>].
    """
    df = pd.read_parquet(path, engine="pyarrow")
    df = df.rename(columns={"q_hom": f"q_hom_{value_col}"})
    logger.info(
        "Chargé %s — %d lignes, %d stations",
        path.name,
        len(df),
        df["num_poste"].nunique(),
    )
    return df


def coalesce_station_meta(
    merged: pd.DataFrame, suffixes: tuple[str, str]
) -> pd.DataFrame:
    """Fusionne les colonnes de métadonnées dupliquées après un merge.

    Après un outer join, les colonnes station (nom_usuel, lat, lon, alt)
    sont dupliquées avec suffixes. Cette fonction les consolide en prenant
    la première valeur non-nulle.

    Args:
        merged: DataFrame issu d'un pd.merge avec suffixes.
        suffixes: Tuple des deux suffixes utilisés lors du merge.

    Returns:
        DataFrame avec colonnes station dédupliquées.
    """
    for col in ["nom_usuel", "latitude", "longitude", "altitude"]:
        left = f"{col}{suffixes[0]}"
        right = f"{col}{suffixes[1]}"
        if left in merged.columns and right in merged.columns:
            merged[col] = merged[left].combine_first(merged[right])
            cols_to_drop = [c for c in [left, right] if c != col]
            merged = merged.drop(columns=cols_to_drop)
    return merged


def main() -> None:
    """Point d'entrée : fusionne TN, TX et RR en un seul fichier Parquet gold."""
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    tn = load(SILVER_DIR / "tn_metropole.parquet", "tn")
    tx = load(SILVER_DIR / "tx_metropole.parquet", "tx")
    rr = load(SILVER_DIR / "rr_metropole.parquet", "rr")

    # TN + TX
    merged = pd.merge(
        tn,
        tx,
        on=JOIN_KEYS,
        how="outer",
        suffixes=("_tn", "_tx"),
    )
    merged = coalesce_station_meta(merged, ("_tn", "_tx"))

    # + RR
    merged = pd.merge(
        merged,
        rr,
        on=JOIN_KEYS,
        how="outer",
        suffixes=("", "_rr"),
    )
    merged = coalesce_station_meta(merged, ("", "_rr"))

    # Ordre final des colonnes
    merged = merged[
        [
            "date",
            "num_poste",
            "nom_usuel",
            "latitude",
            "longitude",
            "altitude",
            "tn",
            "q_hom_tn",
            "tx",
            "q_hom_tx",
            "rr",
            "q_hom_rr",
        ]
    ]
    merged = merged.sort_values(["num_poste", "date"]).reset_index(drop=True)

    merged.to_parquet(OUTPUT_FILE, index=False, engine="pyarrow")

    logger.info("Stations totales    : %d", merged["num_poste"].nunique())
    logger.info(
        "Période couverte    : %s → %s",
        merged["date"].min().date(),
        merged["date"].max().date(),
    )
    logger.info("Lignes totales      : %d", len(merged))
    logger.info(
        "Couverture TN/TX/RR : %d / %d / %d stations",
        merged["tn"].notna().groupby(merged["num_poste"]).any().sum(),
        merged["tx"].notna().groupby(merged["num_poste"]).any().sum(),
        merged["rr"].notna().groupby(merged["num_poste"]).any().sum(),
    )
    logger.info("Fichier Parquet     : %s", OUTPUT_FILE)


if __name__ == "__main__":
    main()
