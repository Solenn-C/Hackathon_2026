"""Extraction des séries annuelles d'empreinte carbone (data_2).

Lit la feuille data_2 du fichier SDES empreinte carbone 2024, extrait les
lignes 6, 7 et 8 (empreinte par personne, empreinte totale, émissions directes
ménages) et produit un fichier Parquet annuel dans data/silver/.
"""

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

BRONZE_FILE = Path(
    "data/bronze/ges/"
    "statistiques_sdes_empreinte_carbone_2024_donnees_graphiques_octobre2025.xlsx"
)
SILVER_DIR = Path("data/silver")
OUTPUT_FILE = SILVER_DIR / "empreinte_carbone.parquet"

SHEET_NAME = "data_2"

# Indices de lignes dans la feuille (0-based)
ROW_YEARS = 5
ROW_PAR_PERSONNE = 6
ROW_TOTALE = 7
ROW_DIRECTES_MENAGES = 8

OUTPUT_COLS = [
    "annee",
    "empreinte_par_personne_tco2eq",
    "empreinte_totale_mtco2eq",
    "emissions_directes_menages_mtco2eq",
]


def extract(path: Path) -> pd.DataFrame:
    """Extrait les trois séries annuelles depuis la feuille data_2.

    Args:
        path: Chemin vers le fichier Excel SDES.

    Returns:
        DataFrame avec les colonnes [annee, empreinte_par_personne_tco2eq,
        empreinte_totale_mtco2eq, emissions_directes_menages_mtco2eq].

    Raises:
        ValueError: Si les lignes attendues sont absentes.
    """
    raw = pd.read_excel(path, sheet_name=SHEET_NAME, header=None)
    logger.info("Feuille lue — %d lignes × %d colonnes", *raw.shape)

    years = pd.to_numeric(raw.iloc[ROW_YEARS, 1:], errors="coerce")
    valid = years.notna()
    years = years[valid].astype(int)

    def series(row_idx: int) -> pd.Series:
        vals = pd.to_numeric(raw.iloc[row_idx, 1:], errors="coerce")
        return vals[valid].values

    df = pd.DataFrame(
        {
            "annee": years.values,
            "empreinte_par_personne_tco2eq": series(ROW_PAR_PERSONNE),
            "empreinte_totale_mtco2eq": series(ROW_TOTALE),
            "emissions_directes_menages_mtco2eq": series(ROW_DIRECTES_MENAGES),
        }
    )
    df = df.sort_values("annee").reset_index(drop=True)
    return df


def main() -> None:
    """Point d'entrée : extrait et sauvegarde les séries d'empreinte carbone."""
    SILVER_DIR.mkdir(parents=True, exist_ok=True)

    df = extract(BRONZE_FILE)
    df.to_parquet(OUTPUT_FILE, index=False, engine="pyarrow")

    logger.info("Période couverte : %d → %d", df["annee"].min(), df["annee"].max())
    logger.info("Lignes totales   : %d", len(df))
    logger.info("Fichier Parquet  : %s", OUTPUT_FILE)
    logger.info("\n%s", df.to_string(index=False))


if __name__ == "__main__":
    main()
