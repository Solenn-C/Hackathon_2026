"""Extraction des émissions nationales de GES par substance (Citepa / Secten 2025).

Source : 01-Citepa_Emissions-par-substance_Secten-GES_2025-d.xlsx, onglet Récapitulatif
Extrait les deux blocs annuels (lignes Excel 7–14 et 18–25) :
  - Bloc 1 (lignes 7–14)  : GES hors UTCATF
  - Bloc 2 (lignes 18–25) : GES UTCATF inclus
Pivote le format large (colonnes = années 1960–2024) en format long.
Produit : data/silver/ges_citepa.parquet
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
OUTPUT_FILE = SILVER_DIR / "ges_citepa.parquet"

SHEET = "Récapitulatif"

# Indices 0-based dans la feuille (= ligne Excel - 1)
ROW_YEARS_BLOC1 = 5  # Excel 6  : "Emissions (ktCO2e/an...) | 1960 | 1961 | ..."
ROW_DATA_START1 = 6  # Excel 7  : Dioxyde de carbone (CO2) hors UTCATF
ROW_DATA_END1 = 13  # Excel 14 : Total GES hors UTCATF (inclus)

ROW_YEARS_BLOC2 = 16  # Excel 17 : header années pour UTCATF inclus
ROW_DATA_START2 = 17  # Excel 18 : Dioxyde de carbone (CO2) UTCATF inclus
ROW_DATA_END2 = 24  # Excel 25 : Total GES UTCATF inclus (inclus)

# Unités par substance (hors Total)
UNITE_MAP = {
    "Dioxyde de carbone (CO2)": "Mt CO2/an",
    "Méthane (CH4)": "kt CO2e/an",
    "Protoxyde d'azote (N2O)": "kt CO2e/an",
    "Hydrofluorocarbures (HFC)": "kt CO2e/an",
    "Perfluorocarbures (PFC)": "kt CO2e/an",
    "Hexafluorure de soufre (SF6)": "kt CO2e/an",
    "Trifluorure d'azote (NF3)": "kt CO2e/an",
    "Total gaz à effet de serre (CO2e)": "Mt CO2e/an",
}


def extract_bloc(
    raw: pd.DataFrame,
    row_years: int,
    row_start: int,
    row_end: int,
    utcatf: bool,
) -> pd.DataFrame:
    """Extrait un bloc de données annuelles depuis la feuille Récapitulatif.

    Args:
        raw: DataFrame brut de la feuille (header=None).
        row_years: Indice de la ligne contenant les années (0-based).
        row_start: Première ligne de données (0-based, incluse).
        row_end: Dernière ligne de données (0-based, incluse).
        utcatf: True si le bloc inclut l'UTCATF.

    Returns:
        DataFrame long avec colonnes [annee, substance, valeur, unite, utcatf_inclus].
    """
    # Récupération des années (colonne 2 onward)
    years_raw = raw.iloc[row_years, 2:]
    years = pd.to_numeric(years_raw, errors="coerce").dropna().astype(int)
    year_indices = years.index  # indices de colonnes dans le DataFrame brut

    frames = []
    for row_idx in range(row_start, row_end + 1):
        substance = raw.iloc[row_idx, 1]
        if pd.isna(substance):
            continue

        substance = str(substance).strip()
        valeurs = pd.to_numeric(raw.iloc[row_idx, year_indices], errors="coerce")

        df_row = pd.DataFrame(
            {
                "annee": years.values,
                "substance": substance,
                "valeur": valeurs.values,
                "unite": UNITE_MAP.get(substance, "kt CO2e/an"),
                "utcatf_inclus": utcatf,
            }
        )
        frames.append(df_row)

    bloc = pd.concat(frames, ignore_index=True)
    logger.info(
        "Bloc UTCATF=%s : %d substances, %d lignes",
        utcatf,
        bloc["substance"].nunique(),
        len(bloc),
    )
    return bloc


def main() -> None:
    """Charge, extrait et exporte les deux blocs GES en Parquet."""
    SILVER_DIR.mkdir(parents=True, exist_ok=True)

    raw = pd.read_excel(BRONZE_FILE, sheet_name=SHEET, header=None, engine="openpyxl")
    logger.info("Feuille '%s' lue : %d lignes × %d colonnes", SHEET, *raw.shape)

    bloc1 = extract_bloc(
        raw, ROW_YEARS_BLOC1, ROW_DATA_START1, ROW_DATA_END1, utcatf=False
    )
    bloc2 = extract_bloc(
        raw, ROW_YEARS_BLOC2, ROW_DATA_START2, ROW_DATA_END2, utcatf=True
    )

    df = pd.concat([bloc1, bloc2], ignore_index=True)

    # Suppression des NaN (années sans données)
    n_nulls = df["valeur"].isna().sum()
    logger.info("Nulls supprimés : %d (années sans données)", n_nulls)
    df = df.dropna(subset=["valeur"])

    # Valeurs négatives conservées (puits UTCATF)
    n_neg = (df["valeur"] < 0).sum()
    if n_neg:
        logger.info("Valeurs négatives conservées (puits UTCATF) : %d", n_neg)

    df = df.sort_values(["utcatf_inclus", "substance", "annee"]).reset_index(drop=True)

    df.to_parquet(OUTPUT_FILE, index=False, engine="pyarrow")

    logger.info("Substances  : %s", sorted(df["substance"].unique()))
    logger.info("Années      : %d → %d", df["annee"].min(), df["annee"].max())
    logger.info("Lignes      : %d", len(df))
    logger.info("Parquet     : %s", OUTPUT_FILE)


if __name__ == "__main__":
    main()
