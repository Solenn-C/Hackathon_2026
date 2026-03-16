"""Consolidation des fichiers CSV d'incendies de forêt en un unique Parquet.

Lit tous les fichiers CSV du dossier data/bronze/incendies/, détecte
automatiquement la ligne d'en-tête (variable selon les fichiers), et produit
un unique fichier Parquet dans data/silver/.
"""

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

BRONZE_DIR = Path("data/bronze/incendies")
SILVER_DIR = Path("data/silver")
OUTPUT_FILE = SILVER_DIR / "incendies.parquet"

SEP = ";"
HEADER_MARKER = "Année"

COLUMN_RENAME = {
    "Année": "annee",
    "Numéro": "numero",
    "Département": "departement",
    "Code INSEE": "code_insee",
    "Nom de la commune": "commune",
    "Date de première alerte": "date_alerte",
    "Surface parcourue (m2)": "surface_totale_m2",
    "Surface forêt (m2)": "surface_foret_m2",
    "Surface maquis garrigues (m2)": "surface_maquis_m2",
    "Autres surfaces naturelles hors forêt (m2)": "surface_autres_naturelles_m2",
    "Surfaces agricoles (m2)": "surface_agricole_m2",
    "Autres surfaces (m2)": "surface_autres_m2",
    "Surface autres terres boisées (m2)": "surface_autres_boisees_m2",
    "Surfaces non boisées naturelles (m2)": "surface_non_boisee_naturelle_m2",
    "Surfaces non boisées artificialisées (m2)": "surface_non_boisee_artificielle_m2",
    "Surfaces non boisées (m2)": "surface_non_boisee_m2",
    "Précision des surfaces": "precision_surfaces",
    "Type de peuplement": "type_peuplement",
    "Nature": "nature",
    "Décès ou bâtiments touchés": "deces_ou_batiments",
    "Nombre de décès": "nb_deces",
    "Nombre de bâtiments totalement détruits": "nb_batiments_detruits",
    "Nombre de bâtiments partiellement détruits": "nb_batiments_partiels",
    "Précision de la donnée": "precision_donnee",
}


def find_header_row(path: Path) -> int:
    """Détecte l'index (0-based) de la ligne d'en-tête dans un fichier CSV.

    Cherche la première ligne commençant par HEADER_MARKER.

    Args:
        path: Chemin vers le fichier CSV.

    Returns:
        Index 0-based de la ligne d'en-tête.

    Raises:
        ValueError: Si aucune ligne d'en-tête n'est trouvée.
    """
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f):
            if line.startswith(HEADER_MARKER):
                return i
    raise ValueError(f"En-tête '{HEADER_MARKER}' introuvable dans {path.name}")


def parse_csv(path: Path) -> pd.DataFrame:
    """Parse un fichier CSV d'incendies et retourne un DataFrame normalisé.

    Args:
        path: Chemin vers le fichier CSV.

    Returns:
        DataFrame avec colonnes renommées et types castrés.
    """
    skiprows = find_header_row(path)
    df = pd.read_csv(path, sep=SEP, skiprows=skiprows, encoding="utf-8")

    df.columns = df.columns.str.strip().str.strip('"')
    df = df.rename(columns=COLUMN_RENAME)

    df["date_alerte"] = pd.to_datetime(df["date_alerte"], errors="coerce")

    surface_cols = [c for c in df.columns if c.startswith("surface_")]
    for col in surface_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    logger.info(
        "%-40s %6d lignes  (%d–%d)",
        path.name,
        len(df),
        df["annee"].min(),
        df["annee"].max(),
    )
    return df


def main() -> None:
    """Point d'entrée : consolide tous les CSV incendies en un Parquet silver."""
    SILVER_DIR.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(BRONZE_DIR.glob("*.csv"))
    logger.info("Fichiers CSV trouvés : %d", len(csv_files))

    frames = []
    errors = 0

    for path in csv_files:
        try:
            frames.append(parse_csv(path))
        except Exception as exc:
            logger.warning("Erreur sur %s : %s", path.name, exc)
            errors += 1

    if not frames:
        logger.error("Aucune donnée valide trouvée. Abandon.")
        return

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(["annee", "date_alerte"]).reset_index(drop=True)

    combined.to_parquet(OUTPUT_FILE, index=False, engine="pyarrow")

    logger.info(
        "Période couverte : %d → %d", combined["annee"].min(), combined["annee"].max()
    )
    logger.info("Lignes totales   : %d", len(combined))
    logger.info("Départements     : %d", combined["departement"].nunique())
    logger.info("Erreurs / skips  : %d", errors)
    logger.info("Fichier Parquet  : %s", OUTPUT_FILE)


if __name__ == "__main__":
    main()
