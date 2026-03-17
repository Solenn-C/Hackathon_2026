"""Extraction des émissions GES par secteur depuis le fichier CITEPA 2025.

Lit la feuille CO2e-MT du fichier Citepa Secten-GES 2025, extrait les lignes
6 (Industrie de l'énergie) et 17 (Hors total) année par année jusqu'en 2024,
et produit un fichier Parquet dans data/silver/.
"""

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

BRONZE_FILE = Path(
    "data/bronze/ges/01-Citepa_Emissions-par-substance_Secten-GES_2025-d.xlsx"
)
SILVER_DIR = Path("data/silver")
OUTPUT_FILE = SILVER_DIR / "ges_par_secteur.parquet"

SHEET_NAME = "CO2e-MT"

# Indices de lignes (0-based)
ROW_YEARS = 5
ROW_INDUSTRIE_ENERGIE = 6
ROW_HORS_TOTAL = 17

YEAR_MAX = 2024


def extract(path: Path) -> pd.DataFrame:
    """Extrait les séries annuelles des lignes 6 et 17 de la feuille CO2e-MT.

    Construit le mapping année→colonne depuis la ligne d'en-tête, filtre les
    années jusqu'à YEAR_MAX, puis extrait les valeurs numériques.

    Args:
        path: Chemin vers le fichier Excel CITEPA.

    Returns:
        DataFrame avec les colonnes [annee, industrie_energie_mtco2e,
        hors_total_mtco2e].

    Raises:
        ValueError: Si aucune colonne d'année valide n'est trouvée.
    """
    raw = pd.read_excel(path, sheet_name=SHEET_NAME, header=None)
    logger.info("Feuille lue — %d lignes × %d colonnes", *raw.shape)

    # Construire le mapping colonne → année depuis la ligne d'en-tête
    years_row = raw.iloc[ROW_YEARS]
    year_cols = {}
    for col_idx, val in years_row.items():
        try:
            year = int(val)
            if 1900 <= year <= YEAR_MAX:
                year_cols[col_idx] = year
        except (TypeError, ValueError):
            continue

    if not year_cols:
        raise ValueError("Aucune colonne d'année trouvée dans la ligne d'en-tête.")

    logger.info(
        "Années détectées : %d → %d (%d colonnes)",
        min(year_cols.values()),
        max(year_cols.values()),
        len(year_cols),
    )

    def extract_series(row_idx: int) -> list[float]:
        row = raw.iloc[row_idx]
        return [pd.to_numeric(row[col], errors="coerce") for col in year_cols]

    df = pd.DataFrame(
        {
            "annee": list(year_cols.values()),
            "industrie_energie_mtco2e": extract_series(ROW_INDUSTRIE_ENERGIE),
            "hors_total_mtco2e": extract_series(ROW_HORS_TOTAL),
        }
    )
    df = df.sort_values("annee").reset_index(drop=True)
    return df


def main() -> None:
    """Point d'entrée : extrait et sauvegarde les séries GES par secteur."""
    SILVER_DIR.mkdir(parents=True, exist_ok=True)

    df = extract(BRONZE_FILE)
    df.to_parquet(OUTPUT_FILE, index=False, engine="pyarrow")

    logger.info("Période couverte : %d → %d", df["annee"].min(), df["annee"].max())
    logger.info("Lignes totales   : %d", len(df))
    logger.info("Fichier Parquet  : %s", OUTPUT_FILE)
    logger.info("\n%s", df.to_string(index=False))


if __name__ == "__main__":
    main()
