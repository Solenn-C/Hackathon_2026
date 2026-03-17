import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from xgboost import XGBRegressor
from web_climat_data import export_web_data, export_historique_carte

# --- 1. CONFIGURATION ---
gold_path = r"C:\Users\Xachi\Documents\Sup_de_Vinci\Mastere_2\Hackathon_2026\Hackathon_2026\data\gold"

def load_p(name):
    path = os.path.join(gold_path, name)
    return pd.read_parquet(path) if os.path.exists(path) else None

def get_col(df, keywords):
    for k in keywords:
        cols = [c for c in df.columns if k.lower() in c.lower()]
        if cols: return cols[0]
    return None

def safe_merge(base_df, file_name, keywords_ann, keywords_val, new_name):
    target_df = load_p(file_name)
    if target_df is None: 
        print(f"⚠️ Fichier manquant : {file_name}")
        return base_df
    
    # --- DIAGNOSTIC SEA_LEVEL ---
    if 'sea_level' in file_name:
        print(f"🔎 DIAGNOSTIC {file_name} :")
        print(f"   - Colonnes trouvées : {list(target_df.columns)}")

    c_ann = get_col(target_df, keywords_ann)
    c_val = get_col(target_df, keywords_val)
    
    if c_ann and not c_val:
        num_cols = target_df.select_dtypes(include=[np.number]).columns
        num_cols = [c for c in num_cols if c != c_ann]
        if len(num_cols) > 0:
            target_df[new_name] = target_df[num_cols].mean(axis=1)
            c_val = new_name
            
    if c_ann and not c_val and 'cata' in file_name:
        target_df[new_name] = 1
        c_val = new_name

    if c_ann and c_val:
        if not np.issubdtype(target_df[c_ann].dtype, np.number):
            target_df[c_ann] = pd.to_datetime(target_df[c_ann], errors='coerce').dt.year
        
        agg_type = 'sum' if 'incendies' in file_name else 'mean'
        res = target_df.groupby(c_ann)[c_val].agg(agg_type).reset_index()
        res.columns = ['annee_merge', new_name]
        
        merged = pd.merge(base_df, res, left_on='annee', right_on='annee_merge', how='left').drop(columns=['annee_merge'])
        if 'sea_level' in file_name:
            print(f"   - Succès de la fusion pour {new_name} ✅")
        return merged
    
    if 'sea_level' in file_name:
        print(f"   - ÉCHEC de détection des colonnes (Année: {c_ann}, Valeur: {c_val}) ❌")
    return base_df

# --- 2. PRÉPARATION DE LA CIBLE ---
print("\n🌡️ Préparation des données thermiques moyennes...")
df_clim = load_p('climat_metropole.parquet')
if df_clim is not None:
    df_clim['date'] = pd.to_datetime(df_clim['date'])
    df_clim['t_moy'] = (df_clim['tn'] + df_clim['tx']) / 2
    df = df_clim[df_clim['date'].dt.year >= 1990].groupby(df_clim['date'].dt.year)['t_moy'].mean().reset_index()
    df.columns = ['annee', 'temp_moyenne']
else:
    print("❌ Erreur : climat_metropole.parquet introuvable.")
    exit()

# --- 3. FUSION DES 8 VARIABLES ---
# Elargissement des mots-clés pour sea_level
sources = [
    ('ges_citepa.parquet', ['annee'], ['valeur'], 'co2_total'),
    ('empreinte_carbone.parquet', ['annee'], ['empreinte'], 'empreinte_co2'),
    ('glacier_wgms.parquet', ['annee'], ['bilan'], 'glacier_loss'),
    ('sea_level.parquet', ['annee', 'date', 'year', 'time'], ['level', 'gmsl', 'height', 'valeur'], 'sea_level'),
    ('incendies.parquet', ['annee'], ['surface'], 'impact_incendies'),
    ('cata.parquet', ['date', 'annee'], ['id'], 'nb_catastrophes'),
    ('vendange_europe.parquet', ['ann', 'year'], ['value'], 'date_vendange'),
    ('swi_par_departement.parquet', ['date', 'annee'], ['swi'], 'swi_score')
]

for file, k_ann, k_val, name in sources:
    df = safe_merge(df, file, k_ann, k_val, name)

df = df.sort_values('annee').interpolate(method='linear').bfill().fillna(0)

# --- 4. FEATURE ENGINEERING ---
if 'co2_total' in df.columns: df['co2_cumule'] = df['co2_total'].cumsum()
if 'glacier_loss' in df.columns: df['glacier_cumule'] = df['glacier_loss'].abs().cumsum()

logic_map = {
    'co2_cumule': 1, 'empreinte_co2': 1, 'glacier_cumule': 1, 
    'sea_level': 1, 'impact_incendies': 1, 'nb_catastrophes': 1, 
    'date_vendange': -1, 'swi_score': 0
}

features = [f for f in logic_map.keys() if f in df.columns]
constraints = tuple(logic_map[f] for f in features)

print(f"\n✅ Variables finales : {features}")

# --- 5. MODÈLE ---
X, y = df[features], df['temp_moyenne']
model = XGBRegressor(n_estimators=500, learning_rate=0.02, monotone_constraints=constraints, colsample_bytree=0.8)
model.fit(X, y)

# --- 6. VISUALISATION CORRÉLATION ---
plt.figure(figsize=(11, 9))
sns.heatmap(df[['temp_moyenne'] + features].corr(), annot=True, cmap='RdYlBu_r', center=0, fmt=".2f")
plt.title("Matrice de Corrélation Corrigée")
plt.show()

# --- 7. PROJECTIONS 2100 ---
years_proj = np.arange(2025, 2101)
physics_trend = 0.041 

def predict_scenario(scenario_name):
    future = pd.DataFrame({'annee': years_proj})
    last_vals = df[features].iloc[-1]
    hist_slopes = df[features].diff().mean()
    
    for col in features:
        m = 2.0 if scenario_name == "pessimiste" else (0.8 if scenario_name == "intermediaire" else -1.5)
        future[col] = last_vals[col] + (np.arange(1, len(years_proj)+1) * hist_slopes[col] * m)
    
    base_preds = model.predict(future[features])
    years_ahead = np.arange(1, len(years_proj) + 1)
    
    if scenario_name == "pessimiste": return base_preds + (years_ahead * physics_trend * 1.6)
    elif scenario_name == "intermediaire": return base_preds + (years_ahead * physics_trend * 0.7)
    else: return base_preds - (years_ahead * physics_trend * 0.3)

p_opt, p_int, p_pes = predict_scenario("optimiste"), predict_scenario("intermediaire"), predict_scenario("pessimiste")

# --- 8. GRAPHES ---
plt.figure(figsize=(12, 6))
plt.plot(df['annee'], df['temp_moyenne'], 'k', label='Historique', lw=2)
plt.plot(years_proj, p_pes, 'r--', label='Pessimiste (+4.5°C)')
plt.plot(years_proj, p_int, 'b--', label='Intermédiaire (+2.4°C)')
plt.plot(years_proj, p_opt, 'g--', label='Optimiste (+1.2°C)')
plt.legend()
plt.title("Projections Climatiques 2100")
plt.show()

# Export final
poids = pd.Series(model.feature_importances_, index=features).sort_values(ascending=False)
print("\n📊 POIDS DES VARIABLES :")
print(poids.apply(lambda x: f"{x:.2%}"))

# Export poids variables :
export_web_data(poids, years_proj, p_opt, p_int, p_pes)

# Export pour l'historique de la carte
export_historique_carte(df, features)