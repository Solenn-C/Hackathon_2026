"""Agrégation du SWI mensuel par département français.

Charge le fichier silver SWI (coordonnées Lambert 93), télécharge le contour
des départements depuis data.gouv.fr si absent, fait une jointure spatiale
pour affecter chaque point à un département, puis calcule la moyenne mensuelle
du SWI par département.

Produit : data/gold/swi_par_departement.parquet
"""

import logging
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

SILVER_DIR = Path("data/silver")
GOLD_DIR = Path("data/gold")
REF_DIR = Path("data/reference")
OUTPUT_FILE = GOLD_DIR / "swi_par_departement.parquet"

DEPT_GEOJSON_URL = (
    "https://raw.githubusercontent.com/gregoiredavid/france-geojson/"
    "master/departements-version-simplifiee.geojson"
)
DEPT_GEOJSON_PATH = REF_DIR / "departements.geojson"

# CRS Lambert 93 (projection des coordonnées SWI)
CRS_LAMBERT93 = "EPSG:2154"
# CRS WGS84 (utilisé par le GeoJSON des départements)
CRS_WGS84 = "EPSG:4326"


def download_departements() -> gpd.GeoDataFrame:
    """Télécharge et met en cache le GeoJSON des départements français.

    Returns:
        GeoDataFrame des départements en Lambert 93.
    """
    REF_DIR.mkdir(parents=True, exist_ok=True)

    if not DEPT_GEOJSON_PATH.exists():
        logger.info("Téléchargement du GeoJSON des départements…")
        resp = requests.get(DEPT_GEOJSON_URL, timeout=30)
        resp.raise_for_status()
        DEPT_GEOJSON_PATH.write_bytes(resp.content)
        logger.info("Sauvegardé : %s", DEPT_GEOJSON_PATH)
    else:
        logger.info("GeoJSON départements déjà en cache : %s", DEPT_GEOJSON_PATH)

    gdf = gpd.read_file(DEPT_GEOJSON_PATH)
    gdf = gdf.rename(columns={"code": "code_dept", "nom": "nom_dept"})
    return gdf.to_crs(CRS_LAMBERT93)


def build_points_gdf(swi: pd.DataFrame) -> gpd.GeoDataFrame:
    """Construit un GeoDataFrame des points SWI uniques (sans dimension temporelle).

    Args:
        swi: DataFrame silver SWI avec colonnes [numero, lambx, lamby].

    Returns:
        GeoDataFrame avec une ligne par point de grille unique.
    """
    points = swi[["numero", "lambx", "lamby"]].drop_duplicates("numero")
    gdf = gpd.GeoDataFrame(
        points,
        geometry=gpd.points_from_xy(points["lambx"], points["lamby"]),
        crs=CRS_LAMBERT93,
    )
    return gdf


def main() -> None:
    """Charge le SWI silver, joint aux départements et agrège par (dept, date)."""
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    # Chargement SWI
    logger.info("Chargement SWI silver…")
    swi = pd.read_parquet(SILVER_DIR / "swi.parquet")
    logger.info("SWI : %d lignes, %d points", len(swi), swi["numero"].nunique())

    # Contours départements
    depts = download_departements()
    logger.info("Départements chargés : %d", len(depts))

    # Jointure spatiale : chaque point → département
    logger.info("Jointure spatiale points → départements…")
    points_gdf = build_points_gdf(swi)
    points_with_dept = gpd.sjoin(
        points_gdf,
        depts[["code_dept", "nom_dept", "geometry"]],
        how="left",
        predicate="within",
    )

    # Points hors métropole (DOM-TOM ou hors contour)
    n_outside = points_with_dept["code_dept"].isna().sum()
    if n_outside:
        logger.warning("Points sans département (hors métropole) : %d", n_outside)

    # Table de correspondance numero → département
    mapping = points_with_dept[["numero", "code_dept", "nom_dept"]].dropna(
        subset=["code_dept"]
    )
    logger.info("Points mappés : %d / %d", len(mapping), len(points_gdf))

    # Jointure avec les données temporelles
    swi_dept = swi.merge(mapping, on="numero", how="inner")

    # Agrégation : moyenne SWI par (département, date)
    logger.info("Agrégation par département × date…")
    result = swi_dept.groupby(["code_dept", "nom_dept", "date"], as_index=False).agg(
        swi_moyen=("swi", "mean"), nb_points=("swi", "count")
    )
    result = result.sort_values(["code_dept", "date"]).reset_index(drop=True)

    result.to_parquet(OUTPUT_FILE, index=False, engine="pyarrow")

    logger.info("Départements couverts : %d", result["code_dept"].nunique())
    logger.info(
        "Période couverte      : %s → %s",
        result["date"].min().date(),
        result["date"].max().date(),
    )
    logger.info("Lignes totales        : %d", len(result))
    logger.info("Parquet               : %s", OUTPUT_FILE)


if __name__ == "__main__":
    main()
