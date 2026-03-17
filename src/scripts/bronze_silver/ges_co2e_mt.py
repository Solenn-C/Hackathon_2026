"""Extraction des émissions CO2e par grand secteur (Citepa / Secten 2025).

Source : 01-Citepa_Emissions-par-substance_Secten-GES_2025-d.xlsx, onglet CO2e-MT
Extrait les lignes Excel 7 à 17 (pandas rows 6–16) :
  - Industrie de l'énergie
  - Industrie manufacturière et construction
  - Traitement centralisé des déchets
  - Usage des bâtiments et activités résidentiels/tertiaires
  - Agriculture / sylviculture
  - Transports
  - Transport hors total
  - TOTAL national hors UTCATF
  - UTCATF
  - Emissions naturelles hors total
  - TOTAL national avec UTCATF

Chaque ligne est pivotée année par année (1960–2024).
Produit : data/silver/ges_co2e_mt.parquet
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
OUTPUT_FILE = SILVER_DIR / "ges_co2e_mt.parquet"

SHEET = "CO2e-MT"
ROW_YEARS = 5  # Excel row 6  : header années (1960 → 2024)
ROW_START = 6  # Excel row 7  : premier secteur
ROW_END = 16  # Excel row 17 : dernier secteur (inclus)
UNITE = "MtCO2e/an"


def main() -> None:
    """Charge, pivote et exporte les émissions CO2e par secteur en Parquet."""
    SILVER_DIR.mkdir(parents=True, exist_ok=True)

    raw = pd.read_excel(BRONZE_FILE, sheet_name=SHEET, header=None, engine="openpyxl")
    logger.info("Feuille '%s' lue : %d lignes × %d colonnes", SHEET, *raw.shape)

    # Récupération des années depuis la ligne de header
    years_raw = pd.to_numeric(raw.iloc[ROW_YEARS, 2:], errors="coerce")
    years = years_raw.dropna().astype(int)
    year_indices = years.index
    logger.info(
        "Années : %d → %d (%d points)", years.iloc[0], years.iloc[-1], len(years)
    )

    # Extraction ligne par ligne
    frames = []
    for row_idx in range(ROW_START, ROW_END + 1):
        secteur = raw.iloc[row_idx, 1]
        if pd.isna(secteur):
            logger.warning("Ligne %d (Excel %d) vide — ignorée", row_idx, row_idx + 1)
            continue

        valeurs = pd.to_numeric(raw.iloc[row_idx, year_indices], errors="coerce")

        frames.append(
            pd.DataFrame(
                {
                    "annee": years.values,
                    "secteur": str(secteur).strip(),
                    "valeur": valeurs.values,
                    "unite": UNITE,
                }
            )
        )

    df = pd.concat(frames, ignore_index=True)
    logger.info("Lignes après extraction : %d", len(df))

    # Nulls (années sans données pour les premières décennies)
    n_nulls = df["valeur"].isna().sum()
    logger.info("Nulls supprimés : %d", n_nulls)
    df = df.dropna(subset=["valeur"])

    # Valeurs négatives conservées (UTCATF = puits de carbone)
    n_neg = (df["valeur"] < 0).sum()
    if n_neg:
        logger.info("Valeurs négatives conservées (UTCATF) : %d", n_neg)

    df = df.sort_values(["secteur", "annee"]).reset_index(drop=True)

    df.to_parquet(OUTPUT_FILE, index=False, engine="pyarrow")

    logger.info("Secteurs    : %d", df["secteur"].nunique())
    for s in df["secteur"].unique():
        n = df[df["secteur"] == s]["valeur"].count()
        logger.info("  %-55s %d pts", s, n)
    logger.info("Années      : %d → %d", df["annee"].min(), df["annee"].max())
    logger.info("Lignes      : %d", len(df))
    logger.info("Parquet     : %s", OUTPUT_FILE)


if __name__ == "__main__":
    main()
