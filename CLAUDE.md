# Hackathon #26 — Instructions de travail

## Contexte du projet

Sujet Data & IA : **Changement Climatique** — Analyse, Visualisation et Prédiction Multi-Échelle.
Stack principale : Python, Jupyter, Streamlit/Dash, Plotly, scikit-learn, PyTorch/TensorFlow.

---

## Structure du projet

```
hackaton/
├── data/
│   ├── raw/          # Données brutes téléchargées, ne jamais modifier
│   ├── interim/      # Données en cours de transformation
│   └── processed/    # Données propres prêtes à l'usage
├── notebooks/        # Exploration et analyses (nommés 01_, 02_, etc.)
├── src/
│   ├── ingestion/    # Scripts d'ingestion des données
│   ├── processing/   # Nettoyage et transformation
│   ├── models/       # Entraînement et évaluation des modèles IA
│   ├── visualization/# Graphiques et dashboard
│   └── utils/        # Fonctions utilitaires partagées
├── tests/            # Tests unitaires
├── dashboard/        # Application Streamlit ou Dash
├── pyproject.toml    # Configuration centralisée
└── sujet.md          # Cahier des charges
```

---

## Qualité du code

### Règles générales
- Tout le code Python doit respecter **PEP 8**
- Les fonctions et classes doivent avoir des **docstrings Google style**
- Chaque module doit avoir un docstring en en-tête
- Les magic numbers doivent être des constantes nommées
- Pas de `print()` en production — utiliser `logging`
- Pas de secrets ou chemins absolus en dur dans le code

### Formatage automatique
Avant tout commit, exécuter dans l'ordre :

```bash
isort src/ tests/          # Tri des imports
black src/ tests/          # Formatage du code
ruff check src/ tests/     # Linting
```

### Docstrings — style Google

```python
def predict_temperature(
    series: pd.Series,
    horizon: int,
    scenario: str = "median",
) -> pd.DataFrame:
    """Prédit l'évolution de la température sur un horizon donné.

    Args:
        series: Série temporelle de températures historiques indexée par date.
        horizon: Nombre d'années à projeter dans le futur.
        scenario: Scénario climatique parmi 'optimistic', 'median', 'pessimistic'.

    Returns:
        DataFrame avec les colonnes ['date', 'predicted', 'lower_bound', 'upper_bound'].

    Raises:
        ValueError: Si le scénario n'est pas reconnu.
        ValueError: Si la série contient moins de 10 points.

    Example:
        >>> predict_temperature(temps, horizon=25, scenario="pessimistic")
    """
```

---

## Configuration — pyproject.toml

Le fichier `pyproject.toml` est la **source unique de configuration** pour tous les outils.

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "hackathon-climat"
version = "0.1.0"
description = "Analyse, visualisation et prédiction climatique multi-échelle"
requires-python = ">=3.11"
dependencies = [
    "pandas>=2.0",
    "numpy>=1.26",
    "scikit-learn>=1.4",
    "matplotlib>=3.8",
    "plotly>=5.18",
    "streamlit>=1.32",
    "prophet>=1.1",
    "torch>=2.2",
    "mlflow>=2.11",
    "requests>=2.31",
]

[project.optional-dependencies]
dev = [
    "black>=24.0",
    "ruff>=0.3",
    "isort>=5.13",
    "pytest>=8.0",
    "pytest-cov>=5.0",
]

[tool.black]
line-length = 88
target-version = ["py311"]

[tool.isort]
profile = "black"
line_length = 88
known_first_party = ["src"]

[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
    "N",   # pep8-naming
]
ignore = ["E501"]  # line length géré par black

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=src --cov-report=term-missing"

[tool.coverage.report]
fail_under = 70
```

---

## Conventions de nommage

| Élément | Convention | Exemple |
|---------|-----------|---------|
| Fichiers Python | `snake_case` | `load_meteo_data.py` |
| Classes | `PascalCase` | `TemperaturePredictor` |
| Fonctions / variables | `snake_case` | `clean_missing_values()` |
| Constantes | `UPPER_SNAKE_CASE` | `DEFAULT_SCENARIO = "median"` |
| Notebooks | `NN_description.ipynb` | `01_exploration_meteo.ipynb` |

---

## Notebooks Jupyter

- Un notebook = **une étape** du projet (exploration, modélisation, viz...)
- Numéroter les notebooks : `01_`, `02_`, etc.
- Remettre à zéro les outputs avant de commit (`Kernel > Restart & Clear Output`)
- Le code réutilisable doit migrer dans `src/`, pas rester dans un notebook

---

## Gestion des données

- Les données brutes dans `data/raw/` sont **en lecture seule**
- Documenter chaque source dans un fichier `data/raw/README.md`
- Les fichiers > 50 Mo ne doivent pas être commités — utiliser `.gitignore`
- Préférer les formats **Parquet** pour les données tabulaires volumineuses

---

## Modèles IA

- Chaque modèle est entraîné et tracké avec **MLflow**
- Sauvegarder : hyperparamètres, métriques (RMSE, MAE, MAPE), artefacts
- Comparer systématiquement plusieurs modèles avant de choisir
- Les projections couvrent obligatoirement : **2030, 2050, 2100**
- Trois scénarios obligatoires : optimiste, médian, pessimiste

---

## Tests

- Écrire des tests unitaires dans `tests/` pour tout le code dans `src/`
- Nommer les fichiers `test_<module>.py`
- Couverture minimale cible : **70%**
- Lancer les tests : `pytest`

---

## Git

- Commits en français ou anglais, clairs et atomiques
- Format : `type: description courte` (ex: `feat: ajout modèle LSTM températures`)
- Types : `feat`, `fix`, `data`, `model`, `viz`, `docs`, `refactor`, `test`
- Ne jamais commiter de credentials, tokens ou clés API
