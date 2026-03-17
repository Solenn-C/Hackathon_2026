import json

def export_web_data(poids, years_proj, p_opt, p_int, p_pes):
    data_export = {
        "weights": poids.to_dict(),
        "projections": {
            "years": years_proj.tolist(),
            "optimiste": p_opt.tolist(),
            "intermediaire": p_int.tolist(),
            "pessimiste": p_pes.tolist()
        }
    }
    
    with open('climat_data_web.json', 'w') as f:
        json.dump(data_export, f, indent=4)
    print("✅ Fichier 'climat_data_web.json' généré pour le site.")


def export_historique_carte(df, features_list):
    """
    Exporte les données historiques nettoyées pour la carte.
    Inclus la température moyenne et les 8 indicateurs.
    """
    # Sélection des colonnes nécessaires
    cols_a_garder = ['annee', 'temp_moyenne'] + [f for f in features_list if f in df.columns]
    df_map = df[cols_a_garder].copy()
    
    # Export en CSV (souvent plus simple pour Leaflet/Mapbox/D3.js)
    df_map.to_csv('data_historique_carte.csv', index=False, encoding='utf-8')
    
    # Export en JSON (format 'records' pour faire un tableau d'objets JS)
    df_map.to_json('data_historique_carte.json', orient='records', indent=4)
    
    print("\n🌍 DONNÉES CARTE EXPORTÉES :")
    print(f"   - Fichier : 'data_historique_carte.csv'")
    print(f"   - Indicateurs inclus : {len(cols_a_garder) - 2}")
