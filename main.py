import json
import os

import pandas as pd
from fastapi import FastAPI, Query

app = FastAPI()

# Configuration des chemins selon votre environnement
BASE_PATH = os.getcwd()
DATA_PATH = os.path.join(BASE_PATH, "data_historique_carte.csv")
WEIGHTS_PATH = os.path.join(BASE_PATH, "poids_variables_final.csv")
PROJECTIONS_PATH = os.path.join(BASE_PATH, "climat_data_web.json")

# Chargement initial des données
df_hist = pd.read_csv(DATA_PATH)
# Chargement des poids depuis le CSV
weights_df = pd.read_csv(WEIGHTS_PATH, index_col=0)
weights_dict = weights_df.to_dict()["0"]

# Chargement des projections JSON [cite: 1]
with open(PROJECTIONS_PATH, "r") as f:
    projections_data = json.load(f)


@app.get("/data/historical")
def get_historical_data(year: int = Query(None)):
    if year:
        filtered = df_hist[df_hist["annee"] == year]
        return filtered.to_dict(orient="records")[0] if not filtered.empty else {}
    return df_hist.to_dict(orient="records")


@app.get("/indicators")
def get_indicators():
    return [col for col in df_hist.columns if col != "annee"]


@app.get("/calculate_risk")
def calculate_risk(year: int):
    row = df_hist[df_hist["annee"] == year]
    if row.empty:
        return {"error": "Année non trouvée"}

    score = 0
    for var, weight in weights_dict.items():
        if var in row.columns:
            val = row[var].values[0]
            max_val = df_hist[var].max()
            score += (val / max_val) * weight

    return {"annee": year, "score_risque_global": round(score * 100, 2)}


@app.get("/projections")
def get_projections(scenario: str = "intermediaire"):
    if scenario not in projections_data["projections"]:
        return {"error": "Scénario non trouvé"}
    return {
        "years": projections_data["projections"]["years"],
        "values": projections_data["projections"][scenario],
    }


@app.get("/map_projections")
def get_map_projections(scenario: str, year: int):
    import random
    idx = projections_data["projections"]["years"].index(year)
    temp_val = projections_data["projections"][scenario][idx]

    base_score = min(100, (temp_val / 20) * 100)
    dep_codes = [str(i).zfill(2) for i in range(1, 96)] + ["971", "972", "973", "974", "976"]

    return [
        {"code_dep": dep, "score": round(min(100, base_score * (1 + random.uniform(-0.1, 0.1))), 1)}
        for dep in dep_codes
    ]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8888)
