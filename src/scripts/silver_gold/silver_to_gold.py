"""Nettoyage et consolidation des données silver vers gold.

Pipeline de qualité appliqué à chaque série (TN, TX, RR) avant jointure :
  - Suppression des doublons sur [num_poste, date]
  - Suppression des lignes avec valeur nulle
  - Validation des plages de valeurs physiquement plausibles
  - Validation des coordonnées géographiques (métropole)
  - Cohérence TN < TX pour les stations communes
Produit data/gold/climat_metropole.parquet.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

SILVER_DIR = Path("data/silver")
GOLD_DIR = Path("data/gold")
OUTPUT_FILE = GOLD_DIR / "climat_metropole.parquet"

LAT_BOUNDS = (41.0, 51.5)
LON_BOUNDS = (-5.5, 9.7)
VALUE_BOUNDS = {
    "tn": (-30.0, 30.0),
    "tx": (-30.0, 60.0),
    "rr": (0.0, 2000.0),
}


@dataclass
class CleaningReport:
    """Rapport de nettoyage pour une série."""

    name: str
    initial: int
    after_dedup: int
    after_nulls: int
    after_range: int
    after_coords: int

    def log(self) -> None:
        """Affiche le rapport dans les logs."""
        logger.info("--- Nettoyage %s ---", self.name.upper())
        logger.info("  Initial              : %d lignes", self.initial)
        logger.info(
            "  Après déduplication  : %d  (-%d)",
            self.after_dedup,
            self.initial - self.after_dedup,
        )
        logger.info(
            "  Après nulls          : %d  (-%d)",
            self.after_nulls,
            self.after_dedup - self.after_nulls,
        )
        logger.info(
            "  Après plages         : %d  (-%d)",
            self.after_range,
            self.after_nulls - self.after_range,
        )
        logger.info(
            "  Après coordonnées    : %d  (-%d)",
            self.after_coords,
            self.after_range - self.after_coords,
        )
        logger.info(
            "  Taux de rétention    : %.1f%%", 100 * self.after_coords / self.initial
        )


def clean(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Nettoie une série climatique mensuelle.

    Args:
        df: DataFrame silver avec colonnes [date, num_poste, nom_usuel,
            latitude, longitude, altitude, <value_col>, q_hom].
        value_col: Nom de la colonne de mesure ('tn', 'tx' ou 'rr').

    Returns:
        DataFrame nettoyé.
    """
    report = CleaningReport(
        name=value_col,
        initial=len(df),
        after_dedup=0,
        after_nulls=0,
        after_range=0,
        after_coords=0,
    )

    df = df.drop_duplicates(subset=["num_poste", "date"])
    report.after_dedup = len(df)

    df = df.dropna(subset=[value_col])
    report.after_nulls = len(df)

    low, high = VALUE_BOUNDS[value_col]
    df = df[df[value_col].between(low, high)]
    report.after_range = len(df)

    df = df[df["latitude"].between(*LAT_BOUNDS) & df["longitude"].between(*LON_BOUNDS)]
    report.after_coords = len(df)

    report.log()
    return df.reset_index(drop=True)


def coalesce_meta(merged: pd.DataFrame, suffixes: tuple[str, str]) -> pd.DataFrame:
    """Consolide les colonnes de métadonnées dupliquées après un outer merge.

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
            merged = merged.drop(columns=[c for c in [left, right] if c != col])
    return merged


def main() -> None:
    """Point d'entrée : nettoie les données silver et produit le fichier gold."""
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    tn = pd.read_parquet(SILVER_DIR / "tn_metropole.parquet")
    tx = pd.read_parquet(SILVER_DIR / "tx_metropole.parquet")
    rr = pd.read_parquet(SILVER_DIR / "rr_metropole.parquet")

    tn = clean(tn, "tn")
    tx = clean(tx, "tx")
    rr = clean(rr, "rr")

    tn = tn.rename(columns={"q_hom": "q_hom_tn"})
    tx = tx.rename(columns={"q_hom": "q_hom_tx"})
    rr = rr.rename(columns={"q_hom": "q_hom_rr"})

    merged = pd.merge(
        tn, tx, on=["date", "num_poste"], how="outer", suffixes=("_tn", "_tx")
    )
    merged = coalesce_meta(merged, ("_tn", "_tx"))

    merged = pd.merge(
        merged, rr, on=["date", "num_poste"], how="outer", suffixes=("", "_rr")
    )
    merged = coalesce_meta(merged, ("", "_rr"))

    # Suppression des lignes où TN >= TX
    both = merged["tn"].notna() & merged["tx"].notna()
    invalid = both & (merged["tn"] >= merged["tx"])
    if invalid.sum():
        logger.info("Incohérences TN >= TX supprimées : %d", invalid.sum())
        merged = merged[~invalid]

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

    logger.info("=== Résultat final ===")
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
