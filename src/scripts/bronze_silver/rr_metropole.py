"""Consolidation des séries mensuelles homogénéisées de précipitations (RR).

Lit tous les CSV du dossier SH_RR_metropole, extrait les métadonnées de l'en-tête,
et produit un unique fichier Parquet dans data/silver/.
"""

import logging
import re
from io import StringIO
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

BRONZE_DIR = Path("data/bronze/SH_RR_metropole")
SILVER_DIR = Path("data/silver")
OUTPUT_FILE = SILVER_DIR / "rr_metropole.parquet"

METADATA_PATTERNS = {
    "num_poste": re.compile(r"# NUM_POSTE=\s*(.+)"),
    "nom_usuel": re.compile(r"# NOM_USUEL=\s*(.+)"),
    "latitude": re.compile(r"# LATITUDE \(°\) =\s*(.+)"),
    "longitude": re.compile(r"# LONGITUDE\(°\)=\s*(.+)"),
    "altitude": re.compile(r"# ALTITUDE \(m\) =\s*(.+)"),
}


def parse_csv(path: Path) -> pd.DataFrame | None:
    """Parse un fichier CSV homogénéisé de RR et retourne un DataFrame enrichi.

    Lit l'en-tête commenté pour extraire les métadonnées de la station,
    puis parse les données tabulaires `YYYYMM;VALEUR;Q_HOM`.

    Args:
        path: Chemin vers le fichier CSV à parser.

    Returns:
        DataFrame avec les colonnes [date, rr, q_hom, num_poste, nom_usuel,
        latitude, longitude, altitude], ou None si le fichier est invalide.
    """
    header_lines = []
    data_lines = []

    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                header_lines.append(line)
            else:
                data_lines.append(line)

    meta = {}
    header_text = "".join(header_lines)
    for key, pattern in METADATA_PATTERNS.items():
        match = pattern.search(header_text)
        meta[key] = match.group(1).strip() if match else None

    if not data_lines:
        logger.warning("Fichier vide : %s", path.name)
        return None

    try:
        df = pd.read_csv(StringIO("".join(data_lines)), sep=";")
    except Exception:
        logger.warning("Impossible de parser : %s", path.name)
        return None

    df.columns = df.columns.str.strip().str.lower()

    if "yyyymm" not in df.columns or "valeur" not in df.columns:
        logger.warning(
            "Colonnes inattendues dans %s : %s", path.name, df.columns.tolist()
        )
        return None

    df = df.rename(columns={"yyyymm": "date_ym", "valeur": "rr", "q_hom": "q_hom"})
    df["date"] = pd.to_datetime(df["date_ym"].astype(str), format="%Y%m")
    df = df.drop(columns=["date_ym"])
    df["rr"] = pd.to_numeric(df["rr"], errors="coerce")

    for key, value in meta.items():
        df[key] = value

    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["altitude"] = pd.to_numeric(df["altitude"], errors="coerce")

    return df


def main() -> None:
    """Point d'entrée : consolide tous les CSV RR en un seul fichier Parquet."""
    SILVER_DIR.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(BRONZE_DIR.glob("*.csv"))
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
        logger.error("Aucune donnée valide trouvée. Abandon.")
        return

    combined = pd.concat(frames, ignore_index=True)
    combined = combined[
        [
            "date",
            "num_poste",
            "nom_usuel",
            "latitude",
            "longitude",
            "altitude",
            "rr",
            "q_hom",
        ]
    ]
    combined = combined.sort_values(["num_poste", "date"]).reset_index(drop=True)

    combined.to_parquet(OUTPUT_FILE, index=False, engine="pyarrow")

    logger.info("Stations consolidées : %d", combined["num_poste"].nunique())
    logger.info(
        "Période couverte    : %s → %s",
        combined["date"].min().date(),
        combined["date"].max().date(),
    )
    logger.info("Lignes totales      : %d", len(combined))
    logger.info("Erreurs / skippés   : %d", errors)
    logger.info("Fichier Parquet     : %s", OUTPUT_FILE)


if __name__ == "__main__":
    main()
