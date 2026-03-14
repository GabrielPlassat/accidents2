"""
app.py – Sécurité Routière en France  v4.0
==========================================
Tableau de bord de l'accidentologie routière française 2005-2024.
Déployé sur Streamlit Cloud — aucune installation requise.

5 onglets fonctionnent immédiatement (données intégrées).
L'onglet Analyse détaillée se déverrouille après dépôt de fichiers CSV.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io, os, sys

st.set_page_config(
    page_title="Sécurité Routière France 2005–2024",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded",
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import (
    build_historical_df, build_summary_stats_2010_2017,
    build_vehicle_trend_2010_2024, build_correlation_dataset,
    load_radars_csv, load_normes_csv,
    get_monthly_trend, get_dept_stats,
    GRAV_LABELS, LUM_LABELS, ATM_LABELS, COL_LABELS,
    CATV_LABELS, SAFETY_MILESTONES, ADAS_DATA,
)

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

C_RED    = "#E63946"
C_ORANGE = "#F4A261"
C_BLUE   = "#457B9D"
C_GREEN  = "#2A9D8F"
C_PURPLE = "#7B2D8B"


# ─────────────────────────────────────────────────────────────
# CACHE — données toujours disponibles (intégrées dans le code)
# ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def charger_historique():
    return build_historical_df(years=range(2005, 2025), data_dir=DATA_DIR)

@st.cache_data(show_spinner=False)
def charger_vehicules():
    return build_vehicle_trend_2010_2024(data_dir=DATA_DIR)

@st.cache_data(show_spinner=False)
def charger_correlations():
    return build_correlation_dataset(data_dir=DATA_DIR)

@st.cache_data(show_spinner=False)
def charger_resume_gravite():
    return build_summary_stats_2010_2017(data_dir=DATA_DIR)

@st.cache_data(show_spinner=False)
def charger_radars():
    return load_radars_csv(DATA_DIR)

@st.cache_data(show_spinner=False)
def charger_normes():
    return load_normes_csv(DATA_DIR)


# ─────────────────────────────────────────────────────────────
# CHARGEMENT DES FICHIERS DÉTAILLÉS (upload utilisateur)
# ─────────────────────────────────────────────────────────────
def lire_csv_accident(uploaded_file):
    """Lit un fichier CSV d'accidents selon son nom (gère les différents encodages)."""
    name = uploaded_file.name.lower()
    enc = "iso-8859-1" if ("caract" in name and "2018" in name) else "utf-8"
    sep = "," if ("caract" in name and "2018" in name) else ";"
    df = pd.read_csv(io.BytesIO(uploaded_file.read()), sep=sep, encoding=enc, low_memory=False)
    df = df.rename(columns={"Accident_Id": "Num_Acc"})
    digits = "".join(filter(str.isdigit, uploaded_file.name))
    df["annee"] = int(digits[-4:]) if len(digits) >= 4 else 0
    return df

def classer_fichier(nom):
    """Retourne le type d'un fichier CSV selon son nom."""
    n = nom.lower()
    if "caract" in n:  return "caract"
    if "usager" in n:  return "usagers"
    if "vehic"  in n:  return "vehicules"
    if "lieu"   in n:  return "lieux"
    return None


# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛣️ Sécurité Routière France")
    st.caption("Données 2005–2024")
    st.markdown("---")

    # ── Upload des fichiers détaillés ────────────────────────
    with st.expander("📂 Charger les données détaillées", expanded=False):
        st.markdown(
            "Pour l'onglet **Analyse détaillée**, chargez les fichiers CSV "
            "de la [base nationale des accidents](https://www.data.gouv.fr/datasets/"
            "bases-de-donnees-annuelles-des-accidents-corporels-de-la-circulation-"
            "routiere-annees-de-2005-a-2024).\n\n"
            "Sélectionnez plusieurs fichiers d'un coup (Ctrl+clic)."
        )
        uploaded = st.file_uploader(
            "Fichiers CSV accidents",
            type=["csv"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )

    # État des fichiers chargés
    fichiers_charges = {"caract": [], "usagers": [], "vehicules": [], "lieux": []}
    if uploaded:
        for f in uploaded:
            t = classer_fichier(f.name)
            if t:
                fichiers_charges[t].append(f)
        n_total = sum(len(v) for v in fichiers_charges.values())
        annees_det = set()
        for lst in fichiers_charges.values():
            for f in lst:
                digits = "".join(filter(str.isdigit, f.name))
                if len(digits) >= 4:
                    annees_det.add(int(digits[-4:]))
        if fichiers_charges["caract"]:
            st.success(f"✅ {n_total} fichier(s) chargé(s)\nAnnées : {', '.join(map(str, sorted(annees_det)))}")
        else:
            st.warning("⚠️ Aucun fichier de caractéristiques reconnu.")

    analyse_disponible = bool(fichiers_charges["caract"])

    st.markdown("---")
    onglet = st.radio("Navigation", [
        "🏠 Bilan national",
        "📈 Évolution historique",
        "🚗 Véhicules & usagers",
        "🔬 Analyse détaillée",
        "🚦 Radars & Technologies",
    ])
    st.markdown("---")
    st.caption("Sources : ONISR · data.gouv.fr · ANTAI · ACEA")
    st.caption("v4.0 — 2025")


# ─────────────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────────────
def ajouter_jalons(fig, types_actifs, annees=(2005, 2024)):
    couleurs = {"radar": C_ORANGE, "reglementation": C_BLUE,
                "securite_active": C_GREEN, "evenement": C_RED}
    for m in SAFETY_MILESTONES:
        if m["type"] not in types_actifs:
            continue
        if not (annees[0] <= m["annee"] <= annees[1]):
            continue
        fig.add_vline(x=m["annee"], line_dash="dot",
                      line_color=couleurs.get(m["type"], "gray"), line_width=1.5,
                      annotation_text=m["label"], annotation_position="top right",
                      annotation_font_size=8)
    return fig


# ══════════════════════════════════════════════════════════════
# ONGLET 1 — BILAN NATIONAL
# ══════════════════════════════════════════════════════════════
if onglet == "🏠 Bilan national":
    st.title("🛣️ Sécurité Routière en France — Bilan 2024")

    df = charger_historique()
    last = df[df["annee"] == 2024].iloc[0]
    prev = df[df["annee"] == 2023].iloc[0]
    ref  = df[df["annee"] == 2005].iloc[0]

    # ── KPIs ──────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Accidents corporels", f"{int(last['accidents']):,}",
              f"{int(last['accidents']-prev['accidents']):+,} vs 2023")
    c2.metric("Personnes tuées", f"{int(last['tues']):,}",
              f"{int(last['tues']-prev['tues']):+,} vs 2023")
    c3.metric("Hospitalisés", f"{int(last['hospitalises']):,}",
              f"{int(last['hospitalises']-prev['hospitalises']):+,} vs 2023")
    c4.metric("Blessés légers", f"{int(last['blesses_legers']):,}",
              f"{int(last['blesses_legers']-prev['blesses_legers']):+,} vs 2023")
    pct = (last["tues"] - ref["tues"]) / ref["tues"] * 100
    c5.metric("Baisse mortalité vs 2005", f"{pct:.0f}%",
              f"de {int(ref['tues']):,} à {int(last['tues']):,} tués")

    st.markdown("---")
    col_g, col_d = st.columns([3, 2])

    with col_g:
        st.markdown("#### Évolution 2005–2024")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df["annee"], y=df["accidents"],
                             name="Accidents", marker_color=C_BLUE,
                             opacity=0.35, yaxis="y2"))
        fig.add_trace(go.Scatter(x=df["annee"], y=df["tues"],
                                 name="Personnes tuées", mode="lines+markers",
                                 line=dict(color=C_RED, width=3), marker=dict(size=7)))
        fig.add_trace(go.Scatter(x=df["annee"], y=df["hospitalises"],
                                 name="Hospitalisés", mode="lines",
                                 line=dict(color=C_ORANGE, width=2, dash="dash")))
        fig.add_vrect(x0=2019.5, x1=2020.5,
                      fillcolor="rgba(230,57,70,0.08)", line_width=0,
                      annotation_text="COVID", annotation_position="top left")
        fig.add_vline(x=2018, line_dash="dot", line_color=C_GREEN,
                      annotation_text="80 km/h", annotation_font_size=9)
        fig.update_layout(
            height=380, plot_bgcolor="white",
            yaxis=dict(title="Personnes tuées / hospitalisées"),
            yaxis2=dict(title="Nb accidents", overlaying="y", side="right", showgrid=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            xaxis=dict(tickmode="linear", dtick=1),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_d:
        st.markdown("#### Répartition 2024")
        grav = {
            "Tué": int(last["tues"]),
            "Hospitalisé": int(last["hospitalises"]),
            "Blessé léger": int(last["blesses_legers"]),
            "Indemne": int(last["accidents"]) * 2 - int(last["tues"]) - int(last["hospitalises"]) - int(last["blesses_legers"]),
        }
        fig2 = px.pie(values=list(grav.values()), names=list(grav.keys()),
                      color_discrete_sequence=[C_RED, C_ORANGE, C_BLUE, C_GREEN],
                      hole=0.45)
        fig2.update_traces(textposition="inside", textinfo="percent+label")
        fig2.update_layout(height=380, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("Estimation : ~2 personnes impliquées par accident en moyenne")

    # ── Progression depuis 2005 ─────────────────────────────
    st.markdown("#### Progression depuis 2005 (indice 100 = niveau 2005)")
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=df["annee"], y=df["idx_acc"],
                              name="Accidents", mode="lines+markers",
                              line=dict(color=C_BLUE, width=2)))
    fig3.add_trace(go.Scatter(x=df["annee"], y=df["idx_tues"],
                              name="Personnes tuées", mode="lines+markers",
                              line=dict(color=C_RED, width=3)))
    fig3.add_hline(y=100, line_dash="dot", line_color="gray",
                   annotation_text="Niveau 2005", annotation_position="right")
    fig3.add_hrect(y0=0, y1=65, fillcolor="rgba(42,157,143,0.06)", line_width=0)
    fig3.update_layout(height=220, plot_bgcolor="white",
                       legend=dict(orientation="h"),
                       xaxis=dict(tickmode="linear", dtick=1),
                       yaxis=dict(title="Indice"))
    st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════════════
# ONGLET 2 — ÉVOLUTION HISTORIQUE
# ══════════════════════════════════════════════════════════════
elif onglet == "📈 Évolution historique":
    st.title("📈 Évolution de la Sécurité Routière 2005–2024")

    df = charger_historique()
    df_grav = charger_resume_gravite()

    col_f1, col_f2 = st.columns([2, 2])
    with col_f1:
        yr = st.slider("Période analysée", 2005, 2024, (2005, 2024))
    with col_f2:
        show_ev = st.multiselect(
            "Afficher sur le graphe",
            ["Radars", "Réglementations", "Technologies de sécurité", "Événements"],
            default=["Réglementations", "Événements"]
        )
    type_map = {"Radars": "radar", "Réglementations": "reglementation",
                "Technologies de sécurité": "securite_active", "Événements": "evenement"}
    actifs = [type_map[s] for s in show_ev]
    df_f = df[(df["annee"] >= yr[0]) & (df["annee"] <= yr[1])]

    # ── Graphe principal ──────────────────────────────────────
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=df_f["annee"], y=df_f["accidents"],
                         name="Accidents", marker_color=C_BLUE, opacity=0.35),
                  secondary_y=True)
    fig.add_trace(go.Scatter(x=df_f["annee"], y=df_f["tues"],
                             name="Personnes tuées", mode="lines+markers",
                             line=dict(color=C_RED, width=3), marker=dict(size=9)),
                  secondary_y=False)
    if df_f["hospitalises"].notna().any():
        fig.add_trace(go.Scatter(x=df_f["annee"], y=df_f["hospitalises"],
                                 name="Hospitalisés", mode="lines",
                                 line=dict(color=C_ORANGE, width=2, dash="dash")),
                      secondary_y=False)
    ajouter_jalons(fig, actifs, yr)
    fig.update_layout(height=460, plot_bgcolor="white",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02),
                      xaxis=dict(tickmode="linear", dtick=1))
    fig.update_yaxes(title_text="Personnes", secondary_y=False)
    fig.update_yaxes(title_text="Accidents", secondary_y=True, showgrid=False)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Légende des jalons"):
        c = st.columns(4)
        c[0].markdown("🟠 **Radars / contrôles**")
        c[1].markdown("🔵 **Réglementations**")
        c[2].markdown("🟢 **Technologies de sécurité**")
        c[3].markdown("🔴 **Événements exceptionnels**")

    st.markdown("---")
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### Mortalité relative (tués pour 100 accidents)")
        fig2 = px.line(df_f.dropna(subset=["taux_tue_par_acc"]),
                       x="annee", y="taux_tue_par_acc", markers=True,
                       color_discrete_sequence=[C_RED])
        fig2.update_traces(line=dict(width=3), marker=dict(size=9))
        fig2.update_layout(height=260, plot_bgcolor="white",
                           xaxis=dict(tickmode="linear", dtick=1),
                           yaxis=dict(title="Tués / 100 accidents"))
        st.plotly_chart(fig2, use_container_width=True)

    with col_b:
        st.markdown("#### Gravité des accidents 2010–2017")
        if len(df_grav) > 0:
            df_s = df_grav[["annee","acc_mortels","acc_graves","acc_legers"]].copy()
            df_s.columns = ["Année","Mortels","Graves","Légers"]
            df_melt = df_s.melt(id_vars="Année", var_name="Gravité", value_name="Nb")
            fig3 = px.bar(df_melt, x="Année", y="Nb", color="Gravité",
                          barmode="stack",
                          color_discrete_map={"Mortels": C_RED, "Graves": C_ORANGE, "Légers": C_BLUE})
            fig3.update_layout(height=260, plot_bgcolor="white",
                               legend=dict(orientation="h"))
            st.plotly_chart(fig3, use_container_width=True)

    st.markdown("#### Tableau des données")
    df_tab = df_f[["annee","accidents","tues","hospitalises","blesses_legers",
                   "taux_tue_par_acc","source"]].copy()
    df_tab.columns = ["Année","Accidents","Tués","Hospitalisés","Blessés légers",
                      "Taux mortalité (%)","Source"]
    st.dataframe(df_tab.sort_values("Année", ascending=False).reset_index(drop=True),
                 use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════
# ONGLET 3 — VÉHICULES & USAGERS
# ══════════════════════════════════════════════════════════════
elif onglet == "🚗 Véhicules & usagers":
    st.title("🚗 Véhicules Impliqués dans les Accidents 2009–2024")

    df_veh = charger_vehicules()
    all_cats = sorted(df_veh["categorie"].unique())
    # Catégories principales affichées par défaut
    cats_defaut = [
        "Voiture (VP)", "Piéton", "Vélo", "Moto >125cm³",
        "Cyclomoteur ≤50cm³", "Trottinette / EDP motorisé",
        "VAE (vélo assisté)", "Utilitaire (VUL)",
    ]
    sel = st.multiselect(
        "Types de véhicules / usagers",
        all_cats,
        default=[c for c in cats_defaut if c in all_cats],
        help="Les piétons sont comptés depuis le fichier usagers (disponible avec les données BAAC 2018-2024)"
    )
    if not sel:
        sel = all_cats
    df_f = df_veh[df_veh["categorie"].isin(sel)]

    st.markdown("### Évolution 2009–2024")
    fig = px.line(df_f, x="annee", y="nb", color="categorie", markers=True,
                  labels={"nb": "Véhicules impliqués", "annee": "Année", "categorie": ""},
                  color_discrete_sequence=px.colors.qualitative.Safe)
    fig.add_vline(x=2017.5, line_dash="dash", line_color="gray",
                  annotation_text="↑ Données détaillées disponibles",
                  annotation_position="top right", annotation_font_size=9)
    fig.update_layout(height=380, plot_bgcolor="white",
                      xaxis=dict(tickmode="linear", dtick=1),
                      legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)

    # ── Variation relative : chaque catégorie indexée sur 2018 = 100 ──
    st.markdown("### Variation depuis 2018 (indice 100 = niveau 2018)")
    df_f18 = df_veh[df_veh["categorie"].isin(sel)].copy()
    base_2018 = df_f18[df_f18["annee"] == 2018].set_index("categorie")["nb"]
    df_f18["idx"] = df_f18.apply(
        lambda r: r["nb"] / base_2018.get(r["categorie"], np.nan) * 100
        if r["categorie"] in base_2018.index else np.nan, axis=1)
    df_f18 = df_f18.dropna(subset=["idx"])
    fig2 = px.line(df_f18, x="annee", y="idx", color="categorie",
                   markers=True,
                   color_discrete_sequence=px.colors.qualitative.Safe,
                   labels={"idx": "Indice (2018 = 100)", "annee": "Année", "categorie": ""})
    fig2.add_hline(y=100, line_dash="dot", line_color="gray",
                   annotation_text="Niveau 2018", annotation_position="right")
    fig2.update_layout(height=340, plot_bgcolor="white",
                       xaxis=dict(tickmode="linear", dtick=1),
                       legend=dict(orientation="h"))
    st.plotly_chart(fig2, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        # Comparaison 2018 vs 2024 : barres côte à côte, année en légende textuelle
        st.markdown("### Comparaison 2018 vs 2024")
        df_comp = df_veh[df_veh["annee"].isin([2018, 2024]) & df_veh["categorie"].isin(sel)].copy()
        df_comp["Année"] = df_comp["annee"].astype(str)
        fig3 = px.bar(df_comp, x="categorie", y="nb", color="Année",
                      barmode="group",
                      color_discrete_map={"2018": C_BLUE, "2024": C_RED},
                      labels={"nb": "Véhicules impliqués", "categorie": ""})
        fig3.update_xaxes(tickangle=35)
        fig3.update_layout(height=340, plot_bgcolor="white",
                           legend=dict(orientation="h"))
        st.plotly_chart(fig3, use_container_width=True)

    with col_b:
        st.markdown("### Nouvelles mobilités (trottinettes, VAE)")
        df_nm = df_veh[df_veh["categorie"].isin(["EDP motorisé","EDP non motorisé","VAE/Vélo"])
                       & (df_veh["annee"] >= 2018)]
        if len(df_nm) > 0:
            fig4 = px.line(df_nm, x="annee", y="nb", color="categorie",
                           markers=True,
                           color_discrete_map={"EDP motorisé": C_GREEN,
                                               "EDP non motorisé": C_ORANGE,
                                               "VAE/Vélo": C_PURPLE},
                           labels={"nb": "Véhicules impliqués", "annee": "Année", "categorie": ""})
            fig4.update_layout(height=340, plot_bgcolor="white",
                               xaxis=dict(tickmode="linear", dtick=1),
                               legend=dict(orientation="h"))
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Données EDP/VAE disponibles à partir de 2019.")


# ══════════════════════════════════════════════════════════════
# ONGLET 4 — ANALYSE DÉTAILLÉE (upload)
# ══════════════════════════════════════════════════════════════
elif onglet == "🔬 Analyse détaillée":
    st.title("🔬 Analyse Détaillée des Accidents")

    if not analyse_disponible:
        # ── Écran d'invitation à charger les fichiers ─────────
        st.markdown("### Comment obtenir les données détaillées ?")
        st.info(
            "Cette analyse utilise la base nationale des accidents de la route, "
            "publiée chaque année par le gouvernement français sur data.gouv.fr. "
            "Ces fichiers sont trop volumineux pour être hébergés directement sur le site."
        )

        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("""
            **Étape 1 — Téléchargez les fichiers**

            Rendez-vous sur [data.gouv.fr](https://www.data.gouv.fr/datasets/bases-de-donnees-annuelles-des-accidents-corporels-de-la-circulation-routiere-annees-de-2005-a-2024)
            et téléchargez les fichiers de l'année qui vous intéresse.

            Pour chaque année (2018–2024), il y a **4 fichiers** :

            | Fichier | Contenu |
            |---------|---------|
            | `caract{année}.csv` | Date, heure, lieu, météo |
            | `lieux{année}.csv` | Type de route, infrastructure |
            | `usagers{année}.csv` | Gravité, âge, sexe de chaque personne |
            | `vehicules{année}.csv` | Type et manœuvre de chaque véhicule |
            """)
        with col2:
            st.markdown("""
            **Étape 2 — Chargez-les dans l'application**

            Dans la barre latérale à gauche, cliquez sur
            **📂 Charger les données détaillées** et déposez vos fichiers.

            Vous pouvez charger une seule année ou plusieurs à la fois.
            L'analyse se lance automatiquement.

            ✅ Vos fichiers ne quittent jamais votre navigateur.
            """)

        st.markdown("---")
        st.markdown("#### Ce qui est déjà disponible sans chargement")
        c1, c2, c3 = st.columns(3)
        c1.success("**🏠 Bilan national**\nKPIs 2024, graphe 2005-2024")
        c2.success("**📈 Évolution historique**\nTendances, jalons, taux mortalité")
        c3.success("**🚗 Véhicules & usagers**\nÉvolution par type 2009-2024")
        st.stop()

    # ── Analyse effective ─────────────────────────────────────
    with st.spinner("Chargement des fichiers déposés…"):
        caracts, usagers_l, vehicules_l, lieux_l = [], [], [], []
        erreurs = []
        tous_fichiers = (fichiers_charges["caract"] + fichiers_charges["usagers"]
                         + fichiers_charges["vehicules"] + fichiers_charges["lieux"])
        for i, f in enumerate(tous_fichiers):
            try:
                df_tmp = lire_csv_accident(f)
                t = classer_fichier(f.name)
                if t == "caract":     caracts.append(df_tmp)
                elif t == "usagers":  usagers_l.append(df_tmp)
                elif t == "vehicules":vehicules_l.append(df_tmp)
                elif t == "lieux":    lieux_l.append(df_tmp)
            except Exception as e:
                erreurs.append(f"{f.name} : {e}")

    if erreurs:
        with st.expander("⚠️ Fichiers non lisibles"):
            for e in erreurs:
                st.write(e)

    df_c = pd.concat(caracts,     ignore_index=True) if caracts     else pd.DataFrame()
    df_u = pd.concat(usagers_l,   ignore_index=True) if usagers_l   else pd.DataFrame()
    df_v = pd.concat(vehicules_l, ignore_index=True) if vehicules_l else pd.DataFrame()
    df_l = pd.concat(lieux_l,     ignore_index=True) if lieux_l     else pd.DataFrame()

    annees_dispo = sorted(df_c["annee"].unique()) if len(df_c) else []
    if not annees_dispo:
        st.error("Aucun fichier de caractéristiques lu. Vérifiez les noms de fichiers.")
        st.stop()

    # ── Sélecteur d'année unique ─────────────────────────────
    col_sel, col_info = st.columns([2, 3])
    with col_sel:
        annee_sel = st.selectbox(
            "Année analysée",
            annees_dispo,
            index=len(annees_dispo) - 1,   # dernière année par défaut
            format_func=str
        )
    with col_info:
        if len(annees_dispo) > 1:
            st.info(f"Vous avez chargé {len(annees_dispo)} années ({', '.join(map(str, annees_dispo))}). "
                    f"Sélectionnez celle à analyser ci-contre.")

    df_c = df_c[df_c["annee"] == annee_sel]
    df_u = df_u[df_u["annee"] == annee_sel] if len(df_u) else df_u
    df_v = df_v[df_v["annee"] == annee_sel] if len(df_v) else df_v
    df_l = df_l[df_l["annee"] == annee_sel] if len(df_l) else df_l

    # Résumé
    n_acc = df_c["Num_Acc"].nunique()
    n_tue = int((df_u["grav"] == 2).sum()) if len(df_u) else 0
    n_bls = int((df_u["grav"] >= 3).sum()) if len(df_u) else 0
    kc = st.columns(4)
    kc[0].metric("Accidents analysés", f"{n_acc:,}")
    kc[1].metric("Personnes tuées", f"{n_tue:,}")
    kc[2].metric("Blessés (hospit. + légers)", f"{n_bls:,}")
    kc[3].metric("Année analysée", annee_sel)
    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs(["📅 Temporel", "🚗 Véhicules", "🗺️ Géographie", "🌦️ Conditions"])

    with tab1:
        if len(df_u) == 0:
            st.info("Chargez les fichiers `usagers{année}.csv` pour cette analyse.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                # Recalculer sur TOUTES les années chargées (pas seulement annee_sel)
                df_c_all = pd.concat(caracts, ignore_index=True) if caracts else df_c
                df_u_all = pd.concat(usagers_l, ignore_index=True) if usagers_l else df_u
                monthly_all = get_monthly_trend(df_c_all, df_u_all)
                mois_labels = {1:"Jan",2:"Fév",3:"Mar",4:"Avr",5:"Mai",6:"Jun",
                               7:"Jul",8:"Aoû",9:"Sep",10:"Oct",11:"Nov",12:"Déc"}
                fig = px.line(monthly_all, x="mois", y="accidents", color="annee",
                              title="Accidents par mois — toutes les années chargées",
                              markers=True,
                              color_discrete_sequence=px.colors.qualitative.Set2,
                              labels={"mois": "Mois", "accidents": "Nb accidents", "annee": "Année"})
                fig.update_xaxes(tickvals=list(range(1,13)),
                                 ticktext=list(mois_labels.values()))
                fig.update_layout(height=300, plot_bgcolor="white",
                                  legend=dict(orientation="h"))
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                try:
                    # hrmn est au format "HH:MM" — extraire uniquement l'heure 0-23
                    heure_series = pd.to_numeric(
                        df_c["hrmn"].astype(str).str.split(":").str[0], errors="coerce")
                    hourly = (df_c.assign(heure=heure_series)
                              .dropna(subset=["heure"])
                              .query("0 <= heure <= 23")
                              .groupby("heure").size().reset_index(name="nb"))
                    hourly["heure"] = hourly["heure"].astype(int)
                    fig2 = px.bar(hourly, x="heure", y="nb",
                                  title=f"Accidents par heure de la journee — {annee_sel}",
                                  color_discrete_sequence=[C_BLUE],
                                  labels={"heure": "Heure", "nb": "Nb accidents"})
                    fig2.update_xaxes(tickvals=list(range(0, 24)),
                                      ticktext=[f"{h}h" for h in range(0, 24)])
                    fig2.update_layout(height=300, plot_bgcolor="white")
                    st.plotly_chart(fig2, use_container_width=True)
                except Exception:
                    st.info("Données horaires non disponibles.")

            jours = {1:"Lun",2:"Mar",3:"Mer",4:"Jeu",5:"Ven",6:"Sam",7:"Dim"}
            daily = df_c.assign(jour=pd.to_numeric(df_c["jour"], errors="coerce")).groupby("jour").size().reset_index(name="nb")
            daily["jour_label"] = daily["jour"].map(jours)
            # Normaliser par nb d'années pour comparer
            daily["jour_label"] = daily["jour"].map(jours)
            daily["pct"] = daily["nb"] / daily["nb"].sum() * 100
            fig3 = px.bar(daily.dropna(subset=["jour_label"]),
                          x="jour_label", y="pct",
                          title=f"Répartition par jour de la semaine — {annee_sel} (%)",
                          category_orders={"jour_label": list(jours.values())},
                          color="pct",
                          color_continuous_scale=["#A8DADC","#457B9D","#1D3557"],
                          labels={"pct": "%", "jour_label": ""})
            fig3.update_layout(height=280, plot_bgcolor="white", showlegend=False,
                               coloraxis_showscale=False)
            st.plotly_chart(fig3, use_container_width=True)

    with tab2:
        if len(df_v) == 0:
            st.info("Chargez les fichiers `vehicules{année}.csv` pour cette analyse.")
        else:
            df_v2 = df_v.copy()
            df_v2["catv"] = pd.to_numeric(df_v2["catv"], errors="coerce")
            df_v2["type_vehicule"] = df_v2["catv"].map(CATV_LABELS).fillna("Autre")
            top10 = df_v2["type_vehicule"].value_counts().head(10).index
            c1, c2 = st.columns(2)
            with c1:
                agg = (df_v2[df_v2["type_vehicule"].isin(top10)]
                       .groupby(["annee","type_vehicule"]).size().reset_index(name="nb"))
                agg_bar = (df_v2[df_v2["type_vehicule"].isin(top10)]
                             .groupby("type_vehicule").size().reset_index(name="nb")
                             .sort_values("nb", ascending=True))
                fig = px.bar(agg_bar, x="nb", y="type_vehicule", orientation="h",
                             title=f"Véhicules impliqués par type — {annee_sel}",
                             color="nb",
                             color_continuous_scale=["#A8DADC","#457B9D","#1D3557"],
                             labels={"nb": "Nb véhicules", "type_vehicule": ""})
                fig.update_layout(height=360, plot_bgcolor="white", showlegend=False,
                                  coloraxis_showscale=False)
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                if len(df_u) > 0:
                    merged = df_v2.merge(
                        df_u[["Num_Acc","grav"]].groupby("Num_Acc")["grav"]
                        .apply(lambda x: (x==2).sum())
                        .reset_index(name="tues"), on="Num_Acc", how="left")
                    cat_g = (merged[merged["type_vehicule"].isin(top10)]
                             .groupby("type_vehicule")
                             .agg(tues=("tues","sum"), nb=("Num_Acc","count"))
                             .reset_index())
                    cat_g["taux"] = cat_g["tues"] / cat_g["nb"] * 100
                    fig2 = px.bar(cat_g.sort_values("taux", ascending=True),
                                  x="taux", y="type_vehicule", orientation="h",
                                  title="Taux de mortalité par type de véhicule (%)",
                                  color="taux",
                                  color_continuous_scale=["#2A9D8F","#F4A261","#E63946"])
                    fig2.update_layout(height=360, plot_bgcolor="white", showlegend=False)
                    st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        dept_stats = get_dept_stats(df_c, df_u) if len(df_u) > 0 else pd.DataFrame()
        if len(dept_stats) == 0:
            st.info("Chargez les fichiers `usagers{année}.csv` pour cette analyse.")
        else:
            dept_f = dept_stats.groupby("dep").agg(
                accidents=("accidents","sum"), tues=("tues","sum")).reset_index()
            c1, c2 = st.columns(2)
            with c1:
                top_acc = (dept_f.nlargest(15,"accidents")
                           .sort_values("accidents", ascending=True))
                # Formater les codes département (75 → "75 - Paris", etc.)
                top_acc["dep_label"] = top_acc["dep"].astype(str).str.lstrip("0").str.zfill(2)
                fig = px.bar(top_acc, x="accidents", y="dep_label",
                             orientation="h",
                             title=f"Top 15 départements — Accidents ({annee_sel})",
                             color="accidents",
                             color_continuous_scale=["#A8DADC","#457B9D","#1D3557"],
                             labels={"accidents": "Nb accidents", "dep_label": "Département"})
                fig.update_layout(height=400, plot_bgcolor="white", showlegend=False,
                                  coloraxis_showscale=False)
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                top_tue = (dept_f.nlargest(15,"tues")
                           .sort_values("tues", ascending=True))
                top_tue["dep_label"] = top_tue["dep"].astype(str).str.lstrip("0").str.zfill(2)
                fig2 = px.bar(top_tue, x="tues", y="dep_label",
                              orientation="h",
                              title=f"Top 15 départements — Tués ({annee_sel})",
                              color="tues",
                              color_continuous_scale=["#F4A261","#E63946","#9B2226"],
                              labels={"tues": "Nb tués", "dep_label": "Département"})
                fig2.update_layout(height=400, plot_bgcolor="white", showlegend=False,
                                   coloraxis_showscale=False)
                st.plotly_chart(fig2, use_container_width=True)

            if "lat" in df_c.columns and "long" in df_c.columns:
                df_map = df_c[["Num_Acc","lat","long","annee"]].copy()
                df_map["lat"] = pd.to_numeric(
                    df_map["lat"].astype(str).str.replace(",","."), errors="coerce")
                df_map["long"] = pd.to_numeric(
                    df_map["long"].astype(str).str.replace(",","."), errors="coerce")
                df_map = df_map.dropna(subset=["lat","long"])
                df_map = df_map[(df_map["lat"].between(41,52)) &
                                (df_map["long"].between(-5,10))]
                sample = df_map.sample(min(5000, len(df_map)), random_state=42)
                fig_map = px.scatter_mapbox(
                    sample, lat="lat", lon="long", color="annee",
                    zoom=5, height=440, mapbox_style="carto-positron",
                    title="Localisation des accidents (échantillon 5 000)",
                    opacity=0.4, color_discrete_sequence=px.colors.qualitative.Set2)
                fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
                st.plotly_chart(fig_map, use_container_width=True)

    with tab4:
        c1, c2 = st.columns(2)
        with c1:
            lum_series = pd.to_numeric(df_c["lum"], errors="coerce").map(LUM_LABELS).fillna("Inconnu")
            lum_agg = df_c.assign(luminosite=lum_series).groupby("luminosite").size().reset_index(name="nb")
            lum_agg["pct"] = lum_agg["nb"] / lum_agg["nb"].sum() * 100
            fig = px.bar(lum_agg.sort_values("pct", ascending=True),
                         x="pct", y="luminosite", orientation="h",
                         title=f"Luminosité au moment de l'accident — {annee_sel}",
                         color="pct",
                         color_continuous_scale=["#A8DADC","#457B9D","#1D3557"],
                         labels={"pct": "%", "luminosite": ""})
            fig.update_layout(height=300, plot_bgcolor="white", showlegend=False,
                              coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            atm_series = pd.to_numeric(df_c["atm"], errors="coerce").map(ATM_LABELS).fillna("Inconnu")
            atm_agg = df_c.assign(meteo=atm_series).groupby("meteo").size().reset_index(name="nb")
            atm_agg["pct"] = atm_agg["nb"] / atm_agg["nb"].sum() * 100
            fig2 = px.bar(atm_agg.sort_values("pct", ascending=True),
                          x="pct", y="meteo", orientation="h",
                          title=f"Conditions météo — {annee_sel}",
                          color="pct",
                          color_continuous_scale=["#A8DADC","#457B9D","#1D3557"],
                          labels={"pct": "%", "meteo": ""})
            fig2.update_layout(height=300, plot_bgcolor="white", showlegend=False,
                               coloraxis_showscale=False)
            st.plotly_chart(fig2, use_container_width=True)

        col_series = pd.to_numeric(df_c["col"], errors="coerce").map(COL_LABELS).fillna("Inconnu")
        col_agg = df_c.assign(type_collision=col_series).groupby("type_collision").size().reset_index(name="nb")
        fig3 = px.pie(col_agg, values="nb", names="type_collision",
                      title="Types de collision",
                      color_discrete_sequence=px.colors.qualitative.Set3, hole=0.3)
        fig3.update_layout(height=320)
        st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════════════
# ONGLET 5 — RADARS & TECHNOLOGIES
# ══════════════════════════════════════════════════════════════
elif onglet == "🚦 Radars & Technologies":
    st.title("🚦 Radars, Technologies & Sécurité Routière")
    st.markdown("Analyse des corrélations entre déploiement des radars, équipements de sécurité et évolution de la mortalité.")

    df = charger_correlations()
    df_normes = charger_normes()

    sous_onglet = st.tabs(["📡 Radars", "🛡️ Équipements de sécurité", "📊 Corrélations", "📋 Réglementations"])

    with sous_onglet[0]:
        st.markdown("### Déploiement des radars automatiques vs mortalité")
        st.caption("Sources : ANTAI · fiches-auto.fr · Cour des Comptes — données officielles")

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        if "total_radars" in df.columns:
            fig.add_trace(go.Bar(x=df["annee"], y=df["total_radars"],
                                 name="Total radars", marker_color=C_ORANGE,
                                 opacity=0.55), secondary_y=True)
        fig.add_trace(go.Scatter(x=df["annee"], y=df["tues"],
                                 name="Personnes tuées", mode="lines+markers",
                                 line=dict(color=C_RED, width=3),
                                 marker=dict(size=8)), secondary_y=False)
        if "recettes_radars" in df.columns:
            fig.add_trace(go.Scatter(x=df["annee"], y=df["recettes_radars"],
                                     name="Recettes radars (M€)", mode="lines",
                                     line=dict(color=C_PURPLE, width=2, dash="dot")),
                          secondary_y=False)
        for annee, label, c in [(2003,"1ers radars",C_ORANGE),(2013,"Bonnets rouges",C_RED),
                                 (2018,"Gilets jaunes",C_RED),(2020,"COVID",C_RED)]:
            if 2005 <= annee <= 2024:
                fig.add_vline(x=annee, line_dash="dot", line_color=c, line_width=1.2,
                              annotation_text=label, annotation_position="top right",
                              annotation_font_size=8)
        fig.update_layout(height=440, plot_bgcolor="white", barmode="stack",
                          legend=dict(orientation="h", yanchor="bottom", y=1.02),
                          xaxis=dict(tickmode="linear", dtick=1))
        fig.update_yaxes(title_text="Personnes tuées / Recettes M€", secondary_y=False)
        fig.update_yaxes(title_text="Nombre de radars", secondary_y=True, showgrid=False)
        st.plotly_chart(fig, use_container_width=True)

        if "total_radars" in df.columns:
            r = df[["total_radars","tues"]].dropna().corr().iloc[0,1]
            c1, c2 = st.columns(2)
            c1.metric("Corrélation radars / tués (Pearson)", f"r = {r:.3f}",
                      "Plus de radars → moins de tués")
            c2.info("Cette corrélation est significative mais ne prouve pas la causalité directe : "
                    "les radars ont été déployés en même temps que d'autres mesures "
                    "(ESP, 80 km/h, prévention).")

    with sous_onglet[1]:
        st.markdown("### Taux d'équipement en systèmes de sécurité (% des véhicules neufs vendus)")
        st.caption("Sources : CLEPA, ACEA — estimations")

        tech_sel = st.multiselect(
            "Technologies à afficher",
            ["ABS","ESP","Airbag avant","Freinage urgence","ISA"],
            default=["ESP","Freinage urgence","ISA"])

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        colors_t = {"ABS":"#4361EE","ESP":"#4CC9F0","Airbag avant":"#7209B7",
                    "Freinage urgence":"#F72585","ISA":"#3A0CA3"}
        for tech in tech_sel:
            if tech in df.columns:
                fig.add_trace(go.Scatter(
                    x=df["annee"], y=df[tech], name=tech, mode="lines+markers",
                    line=dict(color=colors_t.get(tech,"gray"), width=2),
                    marker=dict(size=5)), secondary_y=True)
        fig.add_trace(go.Scatter(x=df["annee"], y=df["tues"],
                                 name="Personnes tuées", mode="lines+markers",
                                 line=dict(color=C_RED, width=3),
                                 marker=dict(size=8)), secondary_y=False)
        for yr_n, lbl_n in [(2006,"ESP obligatoire"),(2011,"ESP généralisé"),
                             (2022,"GSR2 : ISA obligatoire")]:
            fig.add_vline(x=yr_n, line_dash="dot", line_color=C_GREEN,
                          annotation_text=lbl_n, annotation_font_size=8)
        fig.update_layout(height=420, plot_bgcolor="white",
                          legend=dict(orientation="h", yanchor="bottom", y=1.02),
                          xaxis=dict(tickmode="linear", dtick=1))
        fig.update_yaxes(title_text="Personnes tuées", secondary_y=False)
        fig.update_yaxes(title_text="% équipement", secondary_y=True,
                         range=[0,110], showgrid=False)
        st.plotly_chart(fig, use_container_width=True)

    with sous_onglet[2]:
        st.markdown("### Matrice de corrélation — tous indicateurs")
        cols = ["tues","accidents","total_radars","recettes_radars",
                "ESP","Freinage urgence","ISA","age_parc"]
        df_mat = df[[c for c in cols if c in df.columns]].dropna()
        fig_hm = px.imshow(df_mat.corr().round(2), text_auto=True,
                           color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                           title="Bleu = relation inverse · Rouge = relation directe")
        fig_hm.update_layout(height=400)
        st.plotly_chart(fig_hm, use_container_width=True)

        st.markdown("### Évolution normalisée (base 100 = niveau 2005)")
        df_norm = df[["annee","tues","accidents","total_radars","ESP","Freinage urgence"]].copy()
        base = df_norm[df_norm["annee"]==2005].iloc[0]
        for col in ["tues","accidents","total_radars","ESP","Freinage urgence"]:
            if col in df_norm.columns and base[col] and base[col] != 0:
                df_norm[col] = df_norm[col] / base[col] * 100
        noms = {"tues":"Tués","accidents":"Accidents","total_radars":"Radars",
                "ESP":"Équipement ESP","Freinage urgence":"Freinage urgence"}
        df_melt = df_norm.melt(id_vars="annee", var_name="Indicateur", value_name="Indice")
        df_melt["Indicateur"] = df_melt["Indicateur"].map(noms)
        fig_n = px.line(df_melt, x="annee", y="Indice", color="Indicateur", markers=True,
                        color_discrete_map={"Tués":C_RED,"Accidents":C_BLUE,
                                            "Radars":C_ORANGE,"Équipement ESP":C_GREEN,
                                            "Freinage urgence":C_PURPLE})
        fig_n.add_hline(y=100, line_dash="dot", line_color="gray")
        fig_n.update_layout(height=340, plot_bgcolor="white",
                            legend=dict(orientation="h"),
                            xaxis=dict(tickmode="linear", dtick=1))
        st.plotly_chart(fig_n, use_container_width=True)

    with sous_onglet[3]:
        st.markdown("### Principales réglementations et obligations techniques")
        if len(df_normes) > 0:
            cat_fr = {
                "securite_active": "🟢 Aide à la conduite (ADAS)",
                "securite_passive": "🔵 Sécurité passive (structure, airbags)",
                "reglementation": "🟠 Réglementation (loi, code de la route)",
            }
            cat_sel = st.multiselect("Filtrer par catégorie",
                list(cat_fr.values()), default=list(cat_fr.values()))
            cat_inv = {v: k for k, v in cat_fr.items()}
            cats_actives = [cat_inv[c] for c in cat_sel]
            df_n_f = df_normes[df_normes["categorie"].isin(cats_actives)]
            df_n_f = df_n_f[["annee","norme_nom","scope","impact_estime","source_officielle"]]
            df_n_f.columns = ["Année","Mesure","Périmètre","Impact estimé","Source"]
            st.dataframe(df_n_f.sort_values("Année").reset_index(drop=True),
                         use_container_width=True, hide_index=True)
        else:
            st.warning("Fichier `normes_securite_vehicules.csv` non trouvé.")
