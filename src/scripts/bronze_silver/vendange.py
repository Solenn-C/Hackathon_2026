from pathlib import Path

import pandas as pd

# Chargement
df = pd.read_excel("data/bronze/vendange/europe2012ghd.xls", sheet_name=2, skiprows=2)

# Renommer première colonne
df.columns.values[0] = "année"

# Nettoyer : remplacer les non-chiffres par NaN, puis convertir
df["année"] = pd.to_numeric(df["année"], errors="coerce")
df["année"] = df["année"].astype("Int64")

# Filtrer années > 1900 (supprime automatiquement les NaN)
df_filtre = df[df["année"] > 1900]

print(df_filtre.head())

# CORRECTION : Convertir Int64 en int64/float avant parquet + bon nom de fichier
silver_dir = Path("data/silver")
parquet_path = silver_dir / "vendange_europe.parquet"  # Nom corrigé

# Convertir les colonnes problématiques pour PyArrow
df_filtre["année"] = (
    df_filtre["année"].fillna(-1).astype("int64")
)  # Remplacer NaN par -1
df_filtre.to_parquet(parquet_path, index=False)
