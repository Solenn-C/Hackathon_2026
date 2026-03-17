# Hackathon #26 — Sujet Data & IA : Changement Climatique
**16 & 17 Mars 2026 — SUP²VINCI / Open Data University**

---

## Contexte

Le changement climatique constitue un enjeu majeur du XXIe siècle :
- Température mondiale : +1,1°C depuis le XIXe siècle
- Scénario optimiste : +1,4°C d'ici 2100
- Scénario pessimiste : +4,4°C d'ici 2100
- CO₂ : 423 ppm en 2024 (record)

**Objectif global** : Concevoir une solution complète allant de l'ingestion de données massives jusqu'à la production de prédictions climatiques et de recommandations citoyennes actionnables.

---

## Problématiques

**Scientifique** : Comment caractériser et prévoir l'évolution du climat sur un territoire donné afin d'éclairer les décisions d'adaptation et d'atténuation ?

**Citoyenne** : Quelles données climatiques mettre en avant pour sensibiliser les citoyens au réchauffement et les inciter à agir concrètement ?

**Territoire d'étude** (au choix, à justifier) :
- France entière
- Une région
- Une commune

---

## Tâches à réaliser

### ETAPE 1 — Définition du territoire d'étude
- [ ] Choisir le territoire (France / région / commune)
- [ ] Justifier ce choix (granularité, disponibilité des données)
- [ ] Analyser la disponibilité des données sur ce territoire

---

### ETAPE 2 — Sélection des indicateurs climatiques (min. 8)

Critères d'évaluation de chaque indicateur :
- Potentiel narratif
- Lisibilité
- Pertinence pour la sensibilisation citoyenne

**Indicateurs d'évolution climatique disponibles :**
- [ ] Température moyenne annuelle depuis 1900
- [ ] Nombre de jours > 30°C / jours de gel
- [ ] Précipitations / sécheresse
- [ ] Niveau des mers
- [ ] Surface des glaciers
- [ ] Fréquence des feux de forêt

**Indicateurs de pressions humaines :**
- [ ] Émissions GES par secteur
- [ ] Empreinte carbone individuelle
- [ ] Émissions importées vs émissions produites

**Indicateurs d'impacts visibles :**
- [ ] Départ des vendanges (indicateur fort)
- [ ] Déplacements liés aux catastrophes climatiques
- [ ] Coût économique des catastrophes

---

### ETAPE 3 — Pipeline de données (Big Data)
- [ ] Ingestion des données brutes (sources listées ci-dessous)
- [ ] Nettoyage et transformation des données
- [ ] Stockage distribué (HDFS / S3 / Data Lakehouse)
- [ ] Déployer une architecture data scalable

---

### ETAPE 4 — Modélisation IA et prédictions long terme
- [ ] Construire plusieurs modèles prédictifs sur séries temporelles :
  - ARIMA / SARIMA
  - Prophet
  - LSTM / GRU / Transformers temporels
  - Random Forest Regressor
  - Gradient Boosting
- [ ] Comparer les performances des modèles (RMSE, MAE, MAPE)
- [ ] Sélectionner le meilleur modèle
- [ ] Générer des projections pour **2030 / 2050 / 2100** selon 3 scénarios :
  - Optimiste (+1,4°C)
  - Intermédiaire
  - Pessimiste (+4,4°C)

---

### ETAPE 5 — Data Visualisation (Dashboard interactif)
- [ ] Cartographie interactive multi-niveaux (France / régions / communes)
- [ ] Graphiques comparant passé / présent / futur
- [ ] Indicateurs clés (jauges, alertes)
- [ ] Simulations personnalisables (slider temporel)
- [ ] Section actions citoyennes

**Outils recommandés** : Streamlit, Dash, Power BI, Leaflet, Mapbox, Kepler.gl, Plotly

---

### ETAPE 6 — Préconisations citoyennes

Transformer les résultats en actions concrètes selon les risques identifiés :

| Risque | Actions |
|--------|---------|
| Feux accrus | Débroussaillage, aménagement anti-incendie, procédures d'urgence |
| Sécheresse | Réduction conso eau, plantes résistantes, récupération d'eau |
| Canicules | Végétalisation, comportements individuels, rafraîchissement urbain |
| Empreinte carbone | Mobilité douce, alimentation bas carbone, rénovation énergétique |

> Alignement requis avec : **PNACC 3**, **Earth Action Report 2025**, **Objectifs neutralité carbone**

---

## Livrables attendus

### 1. Rapport analytique
- [ ] Analyse historique du territoire
- [ ] Sélection et justification des indicateurs
- [ ] Méthodologie de modélisation IA
- [ ] Projections 2030 / 2050 / 2100
- [ ] Recommandations climat-territoire

### 2. Dashboard interactif
- [ ] Cartes interactives multi-échelles
- [ ] Graphiques passé / présent / futur
- [ ] Simulations personnalisables
- [ ] Section actions citoyennes

### 3. Modèles IA & Pipeline
- [ ] Notebook(s) commenté(s)
- [ ] Artefacts modèles (MLflow)
- [ ] Documentation technique complète

### 4. Pitch final
- [ ] Démonstration du Dashboard
- [ ] Narration Data-Driven
- [ ] Recommandations finales et impact citoyen

---

## Sources de données

### Sources obligatoires
| Source | Contenu |
|--------|---------|
| meteo.data.gouv.fr (Météo France) | Données climatiques historiques par station |
| Secten – CITEPA | Émissions de GES par secteur depuis 1990 |
| DRIAS | Projections climatiques (scénarios RCP/SSP) |
| NOAA | Concentrations CO₂ / CH₄ |
| Données événements extrêmes | Feux, sécheresses, niveau de la mer |
| Insee / SDES | Empreinte carbone française |

### Sources optionnelles
- ERA5 (Copernicus) — données satellitaires
- IGN, ONF — données rurales/forestières
- Biodiversité, surfaces brûlées
- Données socio-économiques (Insee)

---

## Ressources documentaires

- Chiffres clés du climat 2024 — Ministère des Territoires, Écologie, Logement
- Earth Action Report 2025 — KPMG / ChangeNOW
- Rapport GIEC / Climate Change 2023 Synthesis Report — IPCC
- Rapport annuel 2025 — Haut Conseil pour le Climat
- PNACC 3 — La France s'adapte (France Stratégie 2025)
- defis.data.gouv.fr — Défi Changement climatique

---

## Rôles dans l'équipe

### Rôle Data (Data Scientists / Ingénieurs)
- [ ] Définition du territoire d'études
- [ ] Sélection des indicateurs climatiques
- [ ] Modélisation IA
- [ ] Datavisualisation

### Rôle Chef de Projet IT
- [ ] Définir un MVP réaliste (indicateurs + modèles + niveau de précision)
- [ ] Prioriser les fonctionnalités (pipeline → modèles → dashboard → recommandations)
- [ ] Découper le projet en lots et répartir les tâches
- [ ] Arbitrer entre ambition scientifique et contraintes de temps
- [ ] Estimer les ressources (stockage, calcul, hébergement)
- [ ] Identifier les limites du projet
- [ ] Définir les canaux de diffusion (site web, data.gouv.fr)
- [ ] Définir les publics cibles (citoyens, collectivités, décideurs)

---

## Valorisation (optionnel)

- [ ] Publier une réutilisation sur data.gouv.fr

> Point d'attention : La principale difficulté identifiée est **le choix et l'utilisation des modèles de prédiction climatique**.
