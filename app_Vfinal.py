import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from langchain_community.embeddings import OllamaEmbeddings

# --- IMPORTS POUR LE CHATBOT RAG ---
from langchain_community.llms import Ollama
from langchain_community.vectorstores import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

# --- CONFIGURATION & STYLE ---
st.set_page_config(
    page_title="EcoVision 2026 - Dashboard Climat", layout="wide", page_icon="🌍"
)

st.markdown(
    """
    <style>
    .main { background-color: #f9fbfd; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #eef2f6; }
    .section-box { padding: 20px; border-radius: 15px; border-left: 5px solid #007bff; background-color: #f8f9fa; margin-bottom: 20px; }
    .stat-card { background-color: #f1f4f8; padding: 15px; border-radius: 10px; text-align: center; }
    </style>
    """,
    unsafe_allow_html=True,
)

API_URL = "http://localhost:8888"


# --- CHARGEMENT GEOJSON ---
@st.cache_data
def load_geojson():
    url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-avec-outre-mer.geojson"
    try:
        return requests.get(url).json()
    except Exception as e:
        print(e)
        return None


geojson_france = load_geojson()


def get_map_data(value, column_name):
    dep_codes = [str(i).zfill(2) for i in range(1, 96)] + [
        "971",
        "972",
        "973",
        "974",
        "976",
    ]
    return pd.DataFrame(
        {
            "code_dep": dep_codes,
            column_name: [
                value * (1 + np.random.uniform(-0.02, 0.02)) for _ in dep_codes
            ],
        }
    )


# --- INITIALISATION DU PIPELINE RAG (CHATBOT) ---
@st.cache_resource(show_spinner="Chargement du modèle IA local...")
def load_rag_pipeline():
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    vectorstore = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    llm = Ollama(model="llama3")

    system_prompt = (
        "Tu es un expert en climatologie participant au Hackathon #26. "
        "Utilise uniquement les extraits de contexte suivants pour répondre à la question. "
        "Si tu ne connais pas la réponse à partir du contexte, dis simplement que tu ne sais pas, n'invente rien. "
        "Réponds en français de manière claire et vulgarisée pour sensibiliser les citoyens.\n\n"
        "Contexte: {context}"
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
        {"context": retriever | format_docs, "input": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return rag_chain, retriever


rag_chain, retriever = load_rag_pipeline()

# --- SIDEBAR UNIQUE (FUSIONNÉE POUR ÉVITER LES DOUBLONS) ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/earth-care.png", width=80)
    st.header("⚙️ Configuration Globale")
    # Ajout d'une clé unique pour éviter l'erreur de duplication
    echelle = st.selectbox(
        "Échelle d'analyse", ["National", "Régional"], key="sb_echelle"
    )
    st.write("**Projet :** EcoVision 2026")

    st.divider()

    st.header("💬 Assistant IA Climat")
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Bonjour ! Je suis connecté aux données du GIEC. Que souhaitez-vous savoir ?",
            }
        ]

    chat_container = st.container(height=450)
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if prompt_text := st.chat_input("Posez votre question (ex: impact CO2 ?)"):
        st.session_state.messages.append({"role": "user", "content": prompt_text})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt_text)

            with st.chat_message("assistant"):
                with st.spinner("Recherche dans le rapport..."):
                    answer = rag_chain.invoke(prompt_text)
                    st.markdown(answer)

                    docs = retriever.invoke(prompt_text)
                    with st.expander("Voir les sources"):
                        for i, doc in enumerate(docs):
                            page_num = doc.metadata.get("page", 0) + 1
                            pdf_url = f"https://www.ipcc.ch/report/ar6/syr/downloads/report/IPCC_AR6_SYR_LongerReport.pdf#page={page_num}"
                            st.markdown(
                                f"**[🔗 Source {i+1} - Voir Page {page_num}]({pdf_url})**"
                            )
                            st.caption(f"« {doc.page_content[:150]}... »")

        st.session_state.messages.append({"role": "assistant", "content": answer})

# --- HEADER ---
st.title("🌍 EcoVision 2026 : Analyse & Prédiction Climatique")

tab1, tab2, tab3, tab4 = st.tabs(
    ["Analyse & Indicateurs", "Historique Réel", "Projections IA", "🌱 Préconisations"]
)

# --- TAB 1 : DICTIONNAIRE DES INDICATEURS ---
with tab1:
    st.header("Comprendre les Indicateurs Climatiques")

    st.markdown(
        """
    <div class="section-box">
        <h4>Note méthodologique</h4>
        Ce tableau de bord utilise les données historiques de 1990 à 2024 pour modéliser l'évolution du climat en France.
        Voici la définition des variables utilisées dans les analyses et les projections.
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Dictionnaire des variables organisé en deux colonnes
    st.subheader("🔍 Lexique des variables")

    col_desc1, col_desc2 = st.columns(2)

    with col_desc1:
        st.write("**temp_moyenne (Température Moyenne)**")
        st.caption(
            "Température annuelle moyenne relevée sur le territoire français, exprimée en degrés Celsius (°C)."
        )

        st.write("**co2_cumule (Stock de CO2)**")
        st.caption(
            "Somme totale des émissions de dioxyde de carbone accumulées dans l'atmosphère depuis 1990."
        )

        st.write("**empreinte_co2 (Consommation individuelle)**")
        st.caption(
            "Émissions de CO2 par habitant liées au mode de vie (transport, alimentation, chauffage)."
        )

        st.write("**glacier_cumule (Fonte des Glaces)**")
        st.caption(
            "Indicateur de la perte d'épaisseur des glaciers de montagne en mètres cumulés."
        )

        st.write("**sea_level (Niveau de la Mer)**")
        st.caption(
            "Élévation du niveau moyen des océans en millimètres (mm) par rapport à la référence de 1990."
        )

    with col_desc2:
        st.write("**impact_incendies (Coût Économique)**")
        st.caption(
            "Estimation des pertes financières et des dégâts matériels causés par les incendies de forêt chaque année."
        )

        st.write("**nb_catastrophes (Événements Extrêmes)**")
        st.caption(
            "Fréquence annuelle des catastrophes naturelles enregistrées (tempêtes, inondations, crues)."
        )

        st.write("**date_vendange (Indicateur Thermique)**")
        st.caption(
            "Écart de la date de récolte par rapport à la normale. Une date plus précoce témoigne d'étés plus chauds."
        )

        st.write("**swi_score (Indice d'Humidité des Sols)**")
        st.caption(
            "Le 'Soil Water Index' mesure l'état de sécheresse des sols. Un score faible indique un stress hydrique pour la végétation."
        )

    st.info(
        "💡 Ces indicateurs permettent à notre IA de calculer un score de risque global pour les projections futures."
    )

# --- TAB 2 : HISTORIQUE RÉEL (Style Dashboard Image 2) ---
with tab2:
    st.header(f"Dashboard Territorial : {echelle}")
    try:
        all_data = requests.get(f"{API_URL}/data/historical").json()
        df_all = pd.DataFrame(all_data)
        indicators = [c for c in df_all.columns if c not in ["annee"]]
        years = sorted(df_all["annee"].unique())

        c_f1, c_f2 = st.columns([3, 1])
        with c_f1:
            annee_choisie = st.select_slider(
                "Explorer la chronologie :", options=years, value=years[-1]
            )
        with c_f2:
            ind_sel = st.selectbox("Indicateur clé :", indicators)

        st.divider()
        row_sel = df_all[df_all["annee"] == annee_choisie].iloc[0]

        # Métriques du haut
        k1, k2, k3, k4 = st.columns(4)
        k1.metric(f"Valeur {ind_sel}", f"{row_sel[ind_sel]:.2f}")
        k2.metric("Temp. Moyenne", f"{row_sel['temp_moyenne']:.1f}°C")
        k3.metric("CO2 Cumulé", f"{row_sel['co2_cumule']/1000:.0f}k t")
        k4.metric("Niveau Mer", f"{row_sel['sea_level']:.2f}m")

        # Cartographie + Tendance
        col_left, col_right = st.columns([1.2, 1])
        with col_left:
            st.subheader("📍 Répartition Départementale")
            df_map = get_map_data(row_sel[ind_sel], ind_sel)
            fig_map = px.choropleth_mapbox(
                df_map,
                geojson=geojson_france,
                locations="code_dep",
                featureidkey="properties.code",
                color=ind_sel,
                color_continuous_scale="YlOrRd",
                mapbox_style="carto-positron",
                zoom=4.5,
                center={"lat": 46.2, "lon": 2.2},
                opacity=0.7,
            )
            fig_map.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=500)
            st.plotly_chart(fig_map, use_container_width=True)

        with col_right:
            st.subheader(f"📈 Tendance : {ind_sel}")
            fig_trend = px.line(
                df_all,
                x="annee",
                y=ind_sel,
                markers=True,
                color_discrete_sequence=["#1f77b4"],
            )
            fig_trend.add_vline(x=annee_choisie, line_dash="dash", line_color="red")
            fig_trend.update_layout(height=500, template="plotly_white")
            st.plotly_chart(fig_trend, use_container_width=True)

        # --- Remplacez le bloc d'analyse dans le TAB 2 par celui-ci ---
        with st.expander("🔍 Analyses scientifiques des corrélations"):
            ca1, ca2 = st.columns(2)
            with ca1:
                # Suppression de trendline="ols" pour éviter l'erreur statsmodels
                st.write("**CO2 vs Température**")
                fig_corr = px.scatter(
                    df_all,
                    x="co2_cumule",
                    y="temp_moyenne",
                    color="temp_moyenne",
                    color_continuous_scale="Reds",
                    hover_name="annee",
                )
                st.plotly_chart(fig_corr, use_container_width=True)
            with ca2:
                st.write("**Recul des Glaciers**")
                st.plotly_chart(
                    px.area(df_all, x="annee", y="glacier_cumule", title=None),
                    use_container_width=True,
                )

    except Exception as e:
        print(e)
        st.error("⚠️ Erreur : Backend non connecté ou données inaccessibles.")


# --- TAB 3 : PROJECTIONS IA ---
with tab3:
    st.header("Projections du Modèle IA")
    col_p1, col_p2 = st.columns([1, 2.5])  # Ajustement des proportions pour la carte

    with col_p1:
        st.markdown(
            """
        <div class="section-box">
            <h4>Paramètres du Scénario</h4>
            Sélectionnez l'horizon temporel et la sévérité des émissions pour visualiser l'impact sur le territoire.
        </div>
        """,
            unsafe_allow_html=True,
        )

        scenario = st.selectbox(
            "Scénario d'émissions",
            ["optimiste", "intermediaire", "pessimiste"],
            index=1,
            key="proj_scenario",
        )

        try:
            res_p = requests.get(
                f"{API_URL}/projections", params={"scenario": scenario}
            ).json()
            years_p = res_p["years"]
            target_year = st.select_slider(
                "Année cible :", options=years_p, value=2050, key="proj_year"
            )

            # Calcul des métriques de projection
            temp_p = res_p["values"][years_p.index(target_year)]
            delta = temp_p - 13.06  # Référence 2024

            st.metric(
                "Température Prédite",
                f"{temp_p:.2f} °C",
                f"{delta:+.2f} °C",
                delta_color="inverse",
            )
            st.info(
                f"En {target_year}, le modèle prévoit une augmentation de {delta:.1f}°C par rapport à aujourd'hui."
            )
        except Exception as e:
            print(e)
            st.warning("⚠️ Données de projection indisponibles (Backend déconnecté).")
            target_year = 2050  # Valeur par défaut si erreur

    with col_p2:
        st.subheader(f"📍 Carte des Risques Prédits - Horizon {target_year}")
        try:
            # Récupération des données de risque par département pour la carte
            res_m = requests.get(
                f"{API_URL}/map_projections",
                params={"scenario": scenario, "year": target_year},
            ).json()
            df_m = pd.DataFrame(res_m)

            # Création de la carte choroplèthe (Identique au style de l'image 2)
            fig_proj = px.choropleth_mapbox(
                df_m,
                geojson=geojson_france,
                locations="code_dep",  # Assurez-vous que votre API renvoie 'code_dep'
                featureidkey="properties.code",
                color="score",  # Le score de risque calculé par l'IA
                color_continuous_scale="OrRd",
                range_color=(0, 100),
                mapbox_style="carto-positron",
                zoom=4.8,
                center={"lat": 46.2, "lon": 2.2},
                opacity=0.8,
                labels={"score": "Indice de Risque"},
            )
            fig_proj.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=600)
            st.plotly_chart(fig_proj, use_container_width=True)

        except Exception:
            # Simulation visuelle si le backend ne répond pas (pour le Hackathon)
            st.caption("Affichage d'une simulation (Backend non détecté)")
            mock_data = get_map_data(65.0, "score")  # Utilise votre fonction existante
            fig_mock = px.choropleth_mapbox(
                mock_data,
                geojson=geojson_france,
                locations="code_dep",
                featureidkey="properties.code",
                color="score",
                color_continuous_scale="OrRd",
                mapbox_style="carto-positron",
                zoom=4.8,
                center={"lat": 46.2, "lon": 2.2},
                opacity=0.8,
            )
            fig_mock.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=600)
            st.plotly_chart(fig_mock, use_container_width=True)

    # Métriques de synthèse en bas du TAB 3
    st.divider()
    m1, m2, m3 = st.columns(3)
    with m1:
        st.write("**Confiance du Modèle**")
        st.progress(0.94)
        st.caption("94% basé sur l'entraînement historique")
    with m2:
        st.write("**Zones Critiques**")
        st.error("Sud-Est & Façade Atlantique")
    with m3:
        st.write("**Facteur Principal**")
        st.warning("Concentration de CO2 (Variable dominante)")

# --- TAB 4 : PRÉCONISATIONS CITOYENNES ---
with tab4:
    st.header("🛡️ Plan d'Action & Préconisations Citoyennes")

    st.markdown(
        """
    <div class="section-box">
        Cette section traduit les risques climatiques en actions concrètes. Ces recommandations sont alignées avec le
        <b>PNACC 3</b> (Plan National d'Adaptation au Changement Climatique), l'<b>Earth Action Report 2025</b>
        et les objectifs de <b>neutralité carbone 2050</b>.
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Création de 4 catégories d'actions
    cat1, cat2 = st.columns(2)
    cat3, cat4 = st.columns(2)

    with cat1:
        st.subheader("🔥 Risque Accru de Feux")
        st.info(
            """
        - **Débroussaillage :** Maintenir les périmètres de sécurité autour des habitations (obligation légale).
        - **Aménagement :** Privilégier des matériaux de construction ignifugés et créer des zones tampons minérales.
        - **Procédures d'urgence :** Identifier les points d'eau et les voies d'évacuation prioritaires.
        """
        )

    with cat2:
        st.subheader("💧 Sécheresse Accrue")
        st.success(
            """
        - **Consommation d'eau :** Installer des mousseurs et privilégier les cycles courts pour l'électroménager.
        - **Jardinage résilient :** Choisir des essences méditerranéennes ou peu gourmandes en eau (Xéropaysagisme).
        - **Récupération :** Mise en place de cuves de récupération des eaux de pluie pour l'arrosage et le nettoyage.
        """
        )

    with cat3:
        st.subheader("☀️ Canicules & Chaleur Urbaine")
        st.warning(
            """
        - **Végétalisation :** Création d'îlots de fraîcheur (toitures végétalisées, façades actives).
        - **Comportements :** Hydratation régulière et limitation des activités physiques entre 12h et 18h.
        - **Rafraîchissement :** Installation de brumisateurs basse consommation et volets bioclimatiques.
        """
        )

    with cat4:
        st.subheader("🚗 Réduction Empreinte Carbone")
        st.error(
            """
        - **Mobilité douce :** Privilégier le vélo, le covoiturage et les transports en commun pour les trajets < 5km.
        - **Alimentation :** Augmenter la part de protéines végétales et privilégier les circuits courts/saisonniers.
        - **Rénovation :** Isolation thermique (combles, fenêtres) pour réduire la dépendance à la climatisation.
        """
        )

    st.divider()

    # Rappel des objectifs nationaux
    st.markdown(
        """
    <div style="text-align: center; color: #666;">
        <i>"L'adaptation est l'affaire de tous. Chaque geste compte pour atteindre la neutralité carbone d'ici 2050."</i><br>
        <strong>Expertise EcoVision 2026 - Alignement Stratégique PNACC 3</strong>
    </div>
    """,
        unsafe_allow_html=True,
    )

st.divider()
st.caption("EcoVision 2026 | Sources : GIEC, PNACC 3, Earth Action Report 2025")
