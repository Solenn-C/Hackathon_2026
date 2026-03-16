# Hackathon #26 — Changement Climatique

Analyse, Visualisation et Prédiction Climatique Multi-Échelle & Sensibilisation Citoyenne.

---

## Prérequis

Installer [uv](https://docs.astral.sh/uv/getting-started/installation/) puis :

```bash
uv sync
source .venv/bin/activate  # Windows : .venv\Scripts\activate
```

---

## Structure des données

```
data/
├── bronze/          # Données brutes, ne pas modifier
│   ├── SH_TN_metropole/   # Températures minimales (CSV Météo France)
│   ├── SH_TX_metropole/   # Températures maximales (CSV Météo France)
│   ├── SH_RR_metropole/   # Précipitations (CSV Météo France)
│   ├── ges/               # Émissions GES, empreinte carbone (XLSX/CSV)
│   └── incendies/         # Incendies de forêt 1973–2024 (CSV)
├── silver/          # Données nettoyées, un fichier par source
└── gold/            # Données finales prêtes pour l'analyse
```

---

## Lancer le pipeline ETL

### Pipeline complet (bronze → silver → gold)

```bash
make get-data
```

### Étape bronze → silver uniquement

```bash
make bronze
# ou
python src/scripts/bronze_silver/pipeline.py
```

### Étape silver → gold uniquement

```bash
make silver
# ou
python src/scripts/silver_gold/run_pipeline.py
```

### Options

```bash
# Ignorer certains scripts
python src/scripts/bronze_silver/pipeline.py --skip ges_citepa.py rr_metropole.py

# Exécuter uniquement la partie gold
python src/scripts/silver_gold/run_pipeline.py --only gold

# Ignorer certaines étapes
python src/scripts/silver_gold/run_pipeline.py --skip ges_communes empreinte_carbone
```

---

## Fichiers gold produits

| Fichier | Contenu | Période |
|---------|---------|---------|
| `climat_metropole.parquet` | TN + TX + RR par station météo (jointure nettoyée) | 1945–2024 |
| `ges_communes.parquet` | Émissions GES annuelles par commune et secteur | 2016, 2018, 2021 |
| `ges_citepa.parquet` | Émissions GES nationales par substance (Secten) | 1990–2024 |
| `ges_co2e_mt.parquet` | Émissions CO2e par grand secteur (Métropole) | 1990–2024 |
| `empreinte_carbone.parquet` | Empreinte carbone française par personne et totale | 1990–2024 |
| `incendies.parquet` | Incendies de forêt (surface, localisation, date) | 1973–2024 |

---

## Structure du projet

```
src/scripts/
├── bronze_silver/   # Scripts bronze → silver (un par source)
│   ├── pipeline.py          # Lance tous les scripts bronze → silver
│   ├── tmin.py              # Températures minimales TN
│   ├── tx_metropole.py      # Températures maximales TX
│   ├── rr_metropole.py      # Précipitations RR
│   ├── ges_communes.py      # GES par commune
│   ├── ges_citepa.py        # GES par substance (Secten)
│   ├── ges_co2e_mt.py       # CO2e par secteur
│   ├── empreinte_carbone.py # Empreinte carbone SDES
│   └── incendies.py         # Incendies de forêt
└── silver_gold/     # Scripts silver → gold
    ├── run_pipeline.py      # Lance le pipeline complet ou partiel
    └── silver_to_gold.py    # Nettoyage et jointure climat (TN+TX+RR)
```
