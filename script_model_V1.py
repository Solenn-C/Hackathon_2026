import os
import pandas as pd
import numpy as np
from prophet import Prophet
from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Input

# Configuration
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
base_path = r"C:\Users\Xachi\Documents\Sup_de_Vinci\Mastere_2\Hackathon_2026\Hackathon_2026"
gold_path = os.path.join(base_path, "data", "gold")

def load_p(name):
    path = os.path.join(gold_path, name)
    return pd.read_parquet(path) if os.path.exists(path) else None

def get_col(df, keywords):
    """Trouve une colonne contenant l'un des mots-clés (insensible à la casse)"""
    for k in keywords:
        cols = [c for c in df.columns if k.lower() in c.lower()]
        if cols: return cols[0]
    return None

print("🚀 Analyse finale : Fusion des 8 variables stratégiques...")

# 1. BASE : Température (Cible)
df_clim = load_p('climat_metropole.parquet')
df_clim['date'] = pd.to_datetime(df_clim['date'])
df = df_clim[df_clim['date'].dt.year >= 1990].groupby(df_clim['date'].dt.year)['tn'].mean().reset_index()
df.columns = ['annee', 'tn']

# --- FUSION DES 8 VARIABLES ---

# V1. CO2 Total (ges_citepa)
df_ges = load_p('ges_citepa.parquet')
if df_ges is not None:
    c_ann = get_col(df_ges, ['annee', 'year', 'ann'])
    c_val = get_col(df_ges, ['valeur', 'total'])
    if c_ann and c_val:
        co2 = df_ges[df_ges['substance'].str.contains('Total|CO2', case=False, na=False)]
        co2 = co2.groupby(c_ann)[c_val].sum().reset_index(name='co2_total')
        df = pd.merge(df, co2, left_on='annee', right_on=c_ann, how='left').drop(columns=[c_ann] if c_ann != 'annee' else [])

# V2. Empreinte Carbone (empreinte_carbone)
df_emp = load_p('empreinte_carbone.parquet')
if df_emp is not None:
    c_ann = get_col(df_emp, ['annee', 'year', 'ann'])
    c_val = get_col(df_emp, ['empreinte_par_personne', 'tco2eq'])
    if c_ann and c_val:
        emp = df_emp.groupby(c_ann)[c_val].mean().reset_index(name='empreinte_co2')
        df = pd.merge(df, emp, left_on='annee', right_on=c_ann, how='left').drop(columns=[c_ann] if c_ann != 'annee' else [])

# V3. Glaciers (glacier_wgms)
df_glac = load_p('glacier_wgms.parquet')
if df_glac is not None:
    c_ann = get_col(df_glac, ['annee', 'year', 'ann'])
    c_val = get_col(df_glac, ['bilan', 'mwe', 'glacier'])
    if c_ann and c_val:
        glac = df_glac.groupby(c_ann)[c_val].mean().reset_index(name='glacier_loss')
        df = pd.merge(df, glac, left_on='annee', right_on=c_ann, how='left').drop(columns=[c_ann] if c_ann != 'annee' else [])

# V4. Niveau de la mer (sea_level)
df_sl = load_p('sea_level.parquet')
if df_sl is not None:
    c_ann = get_col(df_sl, ['annee', 'year', 'date', 'time'])
    c_val = get_col(df_sl, ['level', 'anomaly', 'sla', 'msl'])
    if c_ann and c_val:
        if df_sl[c_ann].dtype == 'object' or df_sl[c_ann].dtype == 'datetime64[ns]':
            df_sl[c_ann] = pd.to_datetime(df_sl[c_ann]).dt.year
        sl = df_sl.groupby(c_ann)[c_val].mean().reset_index(name='sea_level')
        df = pd.merge(df, sl, left_on='annee', right_on=c_ann, how='left').drop(columns=[c_ann] if c_ann != 'annee' else [])

# V5. Incendies (incendies)
df_inc = load_p('incendies.parquet')
if df_inc is not None:
    c_ann = get_col(df_inc, ['annee', 'year', 'commune'])
    c_val = get_col(df_inc, ['surface', 'm2', 'area'])
    if c_ann and c_val:
        inc = df_inc.groupby(c_ann)[c_val].sum().reset_index(name='incendies_surf')
        df = pd.merge(df, inc, left_on='annee', right_on=c_ann, how='left').drop(columns=[c_ann] if c_ann != 'annee' else [])

# V6. Catastrophes Naturelles (cata)
df_cata = load_p('cata.parquet')
if df_cata is not None:
    c_date = get_col(df_cata, ['date_debut', 'date', 'annee'])
    if c_date:
        df_cata['annee_tmp'] = pd.to_datetime(df_cata[c_date]).dt.year
        cata = df_cata.groupby('annee_tmp').size().reset_index(name='nb_catastrophes')
        df = pd.merge(df, cata, left_on='annee', right_on='annee_tmp', how='left').drop(columns=['annee_tmp'])

# V7. Vendanges (vendange_europe)
df_ve = load_p('vendange_europe.parquet')
if df_ve is not None:
    c_ann = get_col(df_ve, ['ann', 'year'])
    if c_ann:
        cols_v = [c for c in df_ve.columns if c != c_ann]
        df_ve['date_vendange'] = df_ve[cols_v].mean(axis=1)
        vend = df_ve[[c_ann, 'date_vendange']]
        df = pd.merge(df, vend, left_on='annee', right_on=c_ann, how='left').drop(columns=[c_ann] if c_ann != 'annee' else [])

# V8. Humidité des sols (swi_par_departement)
df_swi = load_p('swi_par_departement.parquet')
if df_swi is not None:
    c_date = get_col(df_swi, ['date', 'annee'])
    c_swi = get_col(df_swi, ['swi', 'valeur'])
    if c_date and c_swi:
        df_swi['annee_tmp'] = pd.to_datetime(df_swi[c_date]).dt.year
        swi = df_swi.groupby('annee_tmp')[c_swi].mean().reset_index(name='swi_score')
        df = pd.merge(df, swi, left_on='annee', right_on='annee_tmp', how='left').drop(columns=['annee_tmp'])

# --- NETTOYAGE & MODELING ---
df = df.sort_values('annee').interpolate(method='linear').fillna(method='bfill').fillna(0)
features = [c for c in df.columns if c not in ['annee', 'tn']]

# SPLIT & SCORES
split = int(len(df) * 0.8)
train, test = df.iloc[:split], df.iloc[split:]
scores = {}

# Prophet
df_p = train[['annee', 'tn']].rename(columns={'annee': 'ds', 'tn': 'y'})
df_p['ds'] = pd.to_datetime(df_p['ds'], format='%Y')
m_p = Prophet(yearly_seasonality=False).fit(df_p)
pred_p = m_p.predict(pd.DataFrame({'ds': pd.to_datetime(test['annee'], format='%Y')}))['yhat'].values
scores['Prophet'] = np.sqrt(mean_squared_error(test['tn'], pred_p))

# XGBoost
m_x = XGBRegressor(n_estimators=100, learning_rate=0.05).fit(train[features], train['tn'])
pred_x = m_x.predict(test[features])
scores['XGBoost'] = np.sqrt(mean_squared_error(test['tn'], pred_x))

# LSTM
scaler = MinMaxScaler()
scaled = scaler.fit_transform(df[['tn'] + features])
win = 1
X_s, y_s = [], []
for i in range(len(scaled)-win):
    X_s.append(scaled[i:i+win]); y_s.append(scaled[i+win, 0])
X_s, y_s = np.array(X_s), np.array(y_s)
m_l = Sequential([Input(shape=(win, len(features)+1)), LSTM(16, activation='relu'), Dense(1)])
m_l.compile(optimizer='adam', loss='mse')
m_l.fit(X_s[:split-win], y_s[:split-win], epochs=100, verbose=0)
pred_l_sc = m_l.predict(X_s[split-win:], verbose=0).flatten()
tn_min, tn_max = df['tn'].min(), df['tn'].max()
pred_l = pred_l_sc * (tn_max - tn_min) + tn_min
scores['LSTM'] = np.sqrt(mean_squared_error(df['tn'].iloc[-len(pred_l):], pred_l))

# --- AFFICHAGE ---
print("\n" + "="*60)
print(f"{'MODÈLE':<15} | {'RMSE (Précision)':<20}")
print("-"*60)
for mod, rmse in scores.items():
    print(f"{mod:<15} | {rmse:.4f} °C")
print("="*60)
print(f"Variables utilisées ({len(features)}) : {features}")