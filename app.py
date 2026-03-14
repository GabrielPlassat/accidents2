"""
app.py – Dashboard Accidents Routiers France (2005–2024)  v3.0
=============================================================
Fonctionne en deux modes automatiques :

  MODE LÉGER   → Streamlit Cloud (GitHub)
    Données    : petits CSV (résumés annuels, radars, normes) + stats ONISR
    Onglets    : Vue d'ensemble, Tendances, Véhicules, Corrélations, Données
    Non dispo  : Analyse BAAC 2018-2024 (nécessite les gros fichiers)

  MODE COMPLET → Google Colab + Google Drive
    Données    : tous les fichiers BAAC 2018-2024
    Onglets    : tous les 6 onglets

Déploiement Streamlit Cloud :
  • Pushez ce fichier + data_loader.py + requirements.txt + petits CSV sur GitHub
  • Sur share.streamlit.io : branch=main, file=app.py

Colab complet :
  • Montez Google Drive avec les gros CSV BAAC
  • Renseignez DATA_DIR dans la barre latérale (ex: /content/drive/MyDrive/AccidentsFrance/)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os, sys

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Accidentologie France 2005–2024",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

C_RED    = "#E63946"
C_ORANGE = "#F4A261"
C_BLUE   = "#457B9D"
C_GREEN  = "#2A9D8F"
C_DARK   = "#1D3557"
C_PURPLE = "#7B2D8B"

# Répertoire par défaut :
#   - Sur Colab : /content/drive/MyDrive/AccidentsFrance/ si Drive est monté
#   - Sur Streamlit Cloud : dossier du script (pas de CSV de données, mode léger)
def _default_data_dir():
    colab_drive_path = "/content/drive/MyDrive/AccidentsFrance"
    if os.path.exists(colab_drive_path):
        return colab_drive_path
    return os.path.dirname(os.path.abspath(__file__))

DEFAULT_DATA_DIR = _default_data_dir()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import (
    build_historical_df, load_baac_year, load_full_baac,
    build_correlation_dataset, build_vehicle_trend_2010_2024,
    build_summary_stats_2010_2017, load_radars_csv, load_normes_csv,
    get_monthly_trend, get_dept_stats,
    GRAV_LABELS, LUM_LABELS, ATM_LABELS, COL_LABELS,
    CATV_LABELS, SAFETY_MILESTONES, ADAS_DATA,
)

# ─────────────────────────────────────────────
# DÉTECTION DU MODE (léger / complet)
# ─────────────────────────────────────────────
def detect_baac_available(data_dir):
    """Retourne True si au moins un fichier BAAC 2024 est accessible."""
    test_files = [
        os.path.join(data_dir, "caract2024.csv"),
        os.path.join(data_dir, "caracteristiques2018.csv"),
    ]
    return any(os.path.exists(f) for f in test_files)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚗 Accidentologie France")

    data_dir = st.text_input(
        "📁 Répertoire des données CSV",
        value=DEFAULT_DATA_DIR,
        help=(
            "Sur Streamlit Cloud : laissez tel quel (petits CSV depuis GitHub).\n\n"
            "Sur Colab : chemin Google Drive, ex:\n"
            "/content/drive/MyDrive/AccidentsFrance/"
        ),
    )

    baac_ok = detect_baac_available(data_dir)

    if baac_ok:
        st.success("✅ Mode complet — fichiers BAAC détectés")
    else:
        st.info(
            "ℹ️ Mode léger — fichiers BAAC non détectés\n\n"
            "L'onglet **Analyse BAAC** nécessite les gros fichiers "
            "sur Google Drive (via Colab)."
        )

    st.markdown("---")
    onglet = st.radio("Navigation", [
        "🏠 Vue d'ensemble",
        "📈 Tendances 2005–2024",
        "🚗 Véhicules impliqués",
        "🔍 Analyse BAAC 2018–2024",
        "🚦 Corrélations & Technologies",
        "📋 Données brutes",
    ])
    st.markdown("---")
    st.caption("Sources : BAAC / data.gouv.fr · ONISR · ANTAI · ACEA")
    st.caption("v3.0 — 2025")


# ─────────────────────────────────────────────
# CACHE
# ─────────────────────────────────────────────
@st.cache_data(show_spinner="Chargement historique…")
def get_historical(data_dir):
    return build_historical_df(years=range(2005, 2025), data_dir=data_dir)

@st.cache_data(show_spinner="Chargement BAAC 2018-2024 (peut prendre 1-2 min)…")
def get_baac(data_dir):
    return load_full_baac(years=range(2018, 2025), data_dir=data_dir)

@st.cache_data(show_spinner="Construction dataset corrélations…")
def get_corr_data(data_dir):
    return build_correlation_dataset(data_dir=data_dir)

@st.cache_data(show_spinner="Chargement tendances véhicules…")
def get_vehicle_trend(data_dir):
    return build_vehicle_trend_2010_2024(data_dir=data_dir)

@st.cache_data(show_spinner="Chargement résumés 2010-2017…")
def get_summary_stats(data_dir):
    return build_summary_stats_2010_2017(data_dir=data_dir)

@st.cache_data(show_spinner="Chargement 2024…")
def get_2024(data_dir):
    return load_baac_year(2024, data_dir)

@st.cache_data
def get_radars(data_dir):
    return load_radars_csv(data_dir)

@st.cache_data
def get_normes(data_dir):
    return load_normes_csv(data_dir)


# ─────────────────────────────────────────────
# HELPER : jalons sur graphe
# ─────────────────────────────────────────────
def add_milestones(fig, active_types, year_range=(2005, 2024)):
    colors_map = {"radar": C_ORANGE, "reglementation": C_BLUE,
                  "securite_active": C_GREEN, "evenement": C_RED}
    for m in SAFETY_MILESTONES:
        if m["type"] not in active_types:
            continue
        if not (year_range[0] <= m["annee"] <= year_range[1]):
            continue
        fig.add_vline(
            x=m["annee"], line_dash="dot",
            line_color=colors_map.get(m["type"], "gray"), line_width=1.5,
            annotation_text=m["label"], annotation_position="top right",
            annotation_font_size=8,
        )
    return fig


# ══════════════════════════════════════════════════════════════
# ONGLET 1 — VUE D'ENSEMBLE
# ══════════════════════════════════════════════════════════════
if onglet == "🏠 Vue d'ensemble":
    st.title("🚗 Accidentologie Routière en France")
    st.markdown("### Vue d'ensemble 2024 & tendances 2005–2024")

    try:
        df_hist = get_historical(data_dir)
        last = df_hist[df_hist["annee"] == 2024].iloc[0]
        prev = df_hist[df_hist["annee"] == 2023].iloc[0]
        ref  = df_hist[df_hist["annee"] == 2005].iloc[0]

        # ── KPIs
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("🚨 Accidents 2024", f"{int(last['accidents']):,}",
                  f"{int(last['accidents']-prev['accidents']):+,}")
        c2.metric("💀 Tués (30j)", f"{int(last['tues']):,}",
                  f"{int(last['tues']-prev['tues']):+,}")
        c3.metric("🏥 Hospitalisés", f"{int(last['hospitalises']):,}",
                  f"{int(last['hospitalises']-prev['hospitalises']):+,}")
        c4.metric("🩹 Blessés légers", f"{int(last['blesses_legers']):,}",
                  f"{int(last['blesses_legers']-prev['blesses_legers']):+,}")
        pct = (last["tues"] - ref["tues"]) / ref["tues"] * 100
        c5.metric("📉 Baisse tués vs 2005", f"{pct:.1f}%")

        st.markdown("---")
        col_g, col_d = st.columns([3, 2])

        with col_g:
            st.markdown("#### Évolution 2005–2024")
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_hist["annee"], y=df_hist["accidents"],
                                 name="Accidents", marker_color=C_BLUE,
                                 opacity=0.4, yaxis="y2"))
            fig.add_trace(go.Scatter(x=df_hist["annee"], y=df_hist["tues"],
                                     name="Tués (30j)", mode="lines+markers",
                                     line=dict(color=C_RED, width=3), marker=dict(size=7)))
            fig.add_trace(go.Scatter(x=df_hist["annee"], y=df_hist["hospitalises"],
                                     name="Hospitalisés", mode="lines+markers",
                                     line=dict(color=C_ORANGE, width=2, dash="dash"),
                                     marker=dict(size=5)))
            fig.add_vrect(x0=2019.5, x1=2020.5,
                          fillcolor="rgba(230,57,70,0.1)", line_width=0,
                          annotation_text="COVID", annotation_position="top left")
            fig.add_vline(x=2018, line_dash="dot", line_color=C_GREEN,
                          annotation_text="80 km/h", annotation_font_size=9)
            fig.update_layout(
                height=380, plot_bgcolor="white",
                yaxis=dict(title="Tués / Hospitalisés"),
                yaxis2=dict(title="Accidents", overlaying="y", side="right", showgrid=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                xaxis=dict(tickmode="linear", dtick=1),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_d:
            st.markdown("#### Gravité 2024")
            if baac_ok:
                try:
                    d24 = get_2024(data_dir)
                    df_u24 = d24["usagers"]
                    grav_counts = df_u24["grav"].map(GRAV_LABELS).value_counts()
                    fig_pie = px.pie(values=grav_counts.values, names=grav_counts.index,
                                     color_discrete_sequence=[C_GREEN, C_ORANGE, C_RED, C_BLUE],
                                     hole=0.45)
                    fig_pie.update_traces(textposition="inside", textinfo="percent+label")
                    fig_pie.update_layout(height=380, showlegend=False)
                    st.plotly_chart(fig_pie, use_container_width=True)
                except Exception:
                    st.info("Données de gravité disponibles en mode complet (Colab).")
            else:
                # Gravité estimée depuis ONISR 2024
                grav_est = {"Indemne": 54402 - 3432 - 19126 - 49709,
                            "Tué": 3432, "Hospitalisé": 19126, "Blessé léger": 49709}
                fig_pie = px.pie(values=list(grav_est.values()),
                                 names=list(grav_est.keys()),
                                 color_discrete_sequence=[C_GREEN, C_ORANGE, C_RED, C_BLUE],
                                 hole=0.45)
                fig_pie.update_traces(textposition="inside", textinfo="percent+label")
                fig_pie.update_layout(height=380, showlegend=False)
                st.plotly_chart(fig_pie, use_container_width=True)
                st.caption("Estimation ONISR 2024 — détail exact disponible en mode Colab")

        # Indices normalisés
        st.markdown("#### Indice de progression (base 100 en 2005)")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df_hist["annee"], y=df_hist["idx_acc"],
                                  name="Accidents", mode="lines+markers",
                                  line=dict(color=C_BLUE, width=2)))
        fig2.add_trace(go.Scatter(x=df_hist["annee"], y=df_hist["idx_tues"],
                                  name="Tués", mode="lines+markers",
                                  line=dict(color=C_RED, width=3)))
        fig2.add_hline(y=100, line_dash="dot", line_color="gray")
        fig2.update_layout(height=240, plot_bgcolor="white",
                           legend=dict(orientation="h"),
                           xaxis=dict(tickmode="linear", dtick=1),
                           yaxis=dict(title="Indice (2005=100)"))
        st.plotly_chart(fig2, use_container_width=True)

    except Exception as e:
        st.error(f"Erreur : {e}")


# ══════════════════════════════════════════════════════════════
# ONGLET 2 — TENDANCES HISTORIQUES
# ══════════════════════════════════════════════════════════════
elif onglet == "📈 Tendances 2005–2024":
    st.title("📈 Tendances Historiques 2005–2024")

    try:
        df_hist = get_historical(data_dir)
        df_sum  = get_summary_stats(data_dir)

        col_f1, col_f2 = st.columns([2, 2])
        with col_f1:
            yr = st.slider("Période", 2005, 2024, (2005, 2024))
        with col_f2:
            show_ev = st.multiselect(
                "Jalons à afficher",
                ["radars", "réglementations", "sécurité active", "événements"],
                default=["réglementations", "événements"]
            )
        type_map = {"radars": "radar", "réglementations": "reglementation",
                    "sécurité active": "securite_active", "événements": "evenement"}
        active = [type_map[s] for s in show_ev]
        df_f = df_hist[(df_hist["annee"] >= yr[0]) & (df_hist["annee"] <= yr[1])]

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=df_f["annee"], y=df_f["accidents"],
                             name="Accidents", marker_color=C_BLUE, opacity=0.4),
                      secondary_y=True)
        fig.add_trace(go.Scatter(x=df_f["annee"], y=df_f["tues"],
                                 name="Tués (30j)", mode="lines+markers",
                                 line=dict(color=C_RED, width=3), marker=dict(size=9)),
                      secondary_y=False)
        if df_f["hospitalises"].notna().any():
            fig.add_trace(go.Scatter(x=df_f["annee"], y=df_f["hospitalises"],
                                     name="Hospitalisés", mode="lines",
                                     line=dict(color=C_ORANGE, width=2, dash="dash")),
                          secondary_y=False)
        fig = add_milestones(fig, active, yr)
        fig.update_layout(height=480, plot_bgcolor="white",
                          legend=dict(orientation="h", yanchor="bottom", y=1.02),
                          xaxis=dict(tickmode="linear", dtick=1))
        fig.update_yaxes(title_text="Personnes", secondary_y=False)
        fig.update_yaxes(title_text="Accidents", secondary_y=True, showgrid=False)
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Légende des jalons"):
            cc = st.columns(4)
            cc[0].markdown("🟠 Radars / contrôles")
            cc[1].markdown("🔵 Réglementations")
            cc[2].markdown("🟢 Technologies")
            cc[3].markdown("🔴 Événements")

        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("### Tués pour 100 accidents")
            fig2 = px.line(df_f.dropna(subset=["taux_tue_par_acc"]),
                           x="annee", y="taux_tue_par_acc", markers=True,
                           color_discrete_sequence=[C_RED],
                           labels={"taux_tue_par_acc": "Taux (%)", "annee": "Année"})
            fig2.update_traces(line=dict(width=3), marker=dict(size=9))
            fig2.update_layout(height=280, plot_bgcolor="white",
                               xaxis=dict(tickmode="linear", dtick=1))
            st.plotly_chart(fig2, use_container_width=True)

        with col_b:
            st.markdown("### Gravité des accidents 2010–2017")
            if len(df_sum) > 0:
                df_s = df_sum[["annee", "acc_mortels", "acc_graves", "acc_legers"]].copy()
                df_s.columns = ["Année", "Mortels", "Graves non mortels", "Légers"]
                df_melt = df_s.melt(id_vars="Année", var_name="Gravité", value_name="Nb")
                fig3 = px.bar(df_melt, x="Année", y="Nb", color="Gravité",
                              barmode="stack",
                              color_discrete_map={"Mortels": C_RED,
                                                  "Graves non mortels": C_ORANGE,
                                                  "Légers": C_BLUE})
                fig3.update_layout(height=280, plot_bgcolor="white",
                                   legend=dict(orientation="h"))
                st.plotly_chart(fig3, use_container_width=True)

        st.markdown("### Tableau récapitulatif")
        df_disp = df_f[["annee","accidents","tues","hospitalises",
                         "blesses_legers","taux_tue_par_acc","source"]].copy()
        df_disp.columns = ["Année","Accidents","Tués (30j)","Hospitalisés",
                            "Blessés légers","Taux mortalité (%)","Source"]
        st.dataframe(df_disp.sort_values("Année", ascending=False).reset_index(drop=True),
                     use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Erreur : {e}")


# ══════════════════════════════════════════════════════════════
# ONGLET 3 — VÉHICULES IMPLIQUÉS
# ══════════════════════════════════════════════════════════════
elif onglet == "🚗 Véhicules impliqués":
    st.title("🚗 Véhicules Impliqués dans les Accidents 2010–2024")

    try:
        df_veh = get_vehicle_trend(data_dir)
        all_cats = sorted(df_veh["categorie"].unique())
        sel_cats = st.multiselect("Catégories à afficher", all_cats,
                                  default=[c for c in all_cats if c in [
                                      "Voiture (VP)", "Moto >125cm³",
                                      "Cyclomoteur/Vélo", "Utilitaire (VUL)",
                                      "EDP motorisé", "VAE/Vélo"]])
        if not sel_cats:
            sel_cats = all_cats
        df_f = df_veh[df_veh["categorie"].isin(sel_cats)]

        st.markdown("### Évolution du nombre de véhicules impliqués")
        fig = px.line(df_f, x="annee", y="nb", color="categorie", markers=True,
                      labels={"nb": "Nb véhicules", "annee": "Année", "categorie": ""},
                      color_discrete_sequence=px.colors.qualitative.Safe)
        fig.add_vline(x=2017.5, line_dash="dash", line_color="gray",
                      annotation_text="← Résumés | BAAC →",
                      annotation_position="top center", annotation_font_size=9)
        fig.update_layout(height=400, plot_bgcolor="white",
                          xaxis=dict(tickmode="linear", dtick=1),
                          legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True)

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("### 2018 vs 2024")
            df_comp = df_veh[df_veh["annee"].isin([2018, 2024]) &
                             df_veh["categorie"].isin(sel_cats)]
            fig2 = px.bar(df_comp, x="categorie", y="nb", color="annee",
                          barmode="group",
                          color_discrete_map={2018: C_BLUE, 2024: C_RED},
                          labels={"nb": "Nb véhicules", "categorie": ""})
            fig2.update_xaxes(tickangle=35)
            fig2.update_layout(height=360, plot_bgcolor="white")
            st.plotly_chart(fig2, use_container_width=True)

        with col_b:
            st.markdown("### Parts relatives (%)")
            pivot = df_veh.pivot_table(index="annee", columns="categorie",
                                       values="nb", aggfunc="sum").fillna(0)
            pivot_pct = pivot.div(pivot.sum(axis=1), axis=0) * 100
            cats_plot = [c for c in sel_cats if c in pivot_pct.columns]
            figp = go.Figure()
            colors = px.colors.qualitative.Safe
            for i, cat in enumerate(cats_plot):
                figp.add_trace(go.Scatter(
                    x=pivot_pct.index, y=pivot_pct[cat], name=cat,
                    mode="lines", stackgroup="one",
                    fillcolor=colors[i % len(colors)],
                    line=dict(color=colors[i % len(colors)], width=0.5),
                ))
            figp.add_vline(x=2017.5, line_dash="dash", line_color="gray")
            figp.update_layout(height=360, plot_bgcolor="white",
                               yaxis=dict(title="Part (%)"),
                               xaxis=dict(tickmode="linear", dtick=1),
                               legend=dict(orientation="h"))
            st.plotly_chart(figp, use_container_width=True)

        st.markdown("### Nouvelles mobilités : EDP & VAE (2018–2024)")
        new_mob = ["EDP motorisé", "EDP non motorisé", "VAE/Vélo"]
        df_nm = df_veh[df_veh["categorie"].isin(new_mob) & (df_veh["annee"] >= 2018)]
        if len(df_nm) > 0:
            fig4 = px.bar(df_nm, x="annee", y="nb", color="categorie",
                          barmode="stack",
                          color_discrete_sequence=[C_GREEN, C_ORANGE, C_PURPLE],
                          labels={"nb": "Nb véhicules", "annee": "Année", "categorie": ""})
            fig4.update_layout(height=260, plot_bgcolor="white",
                               xaxis=dict(tickmode="linear", dtick=1))
            st.plotly_chart(fig4, use_container_width=True)

    except Exception as e:
        st.error(f"Erreur : {e}")


# ══════════════════════════════════════════════════════════════
# ONGLET 4 — ANALYSE BAAC (mode complet uniquement)
# ══════════════════════════════════════════════════════════════
elif onglet == "🔍 Analyse BAAC 2018–2024":
    st.title("🔍 Analyse Détaillée BAAC 2018–2024")

    if not baac_ok:
        # ── Écran d'information propre pour Streamlit Cloud ──
        st.markdown("""
        ### Cet onglet nécessite les fichiers BAAC complets

        Les fichiers BAAC (Base des Accidents Corporels de la Circulation) font
        entre 20 et 130 Mo chacun — ils ne peuvent pas être hébergés sur GitHub
        ni sur Streamlit Cloud.

        **Pour accéder à cet onglet, utilisez Google Colab :**
        """)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            #### Étape 1 — Télécharger les données BAAC
            Sur [data.gouv.fr](https://www.data.gouv.fr/fr/datasets/bases-de-donnees-annuelles-des-accidents-corporels-de-la-circulation-routiere-annees-de-2005-a-2023/),
            téléchargez pour chaque année (2018–2024) les 4 fichiers :

            | Fichier | Exemple 2024 |
            |---------|-------------|
            | Caractéristiques | `caract2024.csv` |
            | Lieux | `lieux2024.csv` |
            | Usagers | `usagers2024.csv` |
            | Véhicules | `vehicules2024.csv` |

            Placez-les dans un dossier Google Drive, ex :
            `Mon Drive/AccidentsFrance/`
            """)

        with col2:
            st.markdown("""
            #### Étape 2 — Lancer via Colab
            Ouvrez le notebook `Accidents_France_Dashboard.ipynb`
            (disponible dans le repo GitHub).

            Il monte automatiquement Drive, installe les dépendances
            et ouvre un tunnel public ngrok vers le dashboard.

            Dans la barre latérale, entrez le chemin Drive :
            ```
            /content/drive/MyDrive/AccidentsFrance/
            ```

            Cet onglet se déverrouillera automatiquement.
            """)

        st.markdown("---")
        st.markdown("#### Données disponibles sans BAAC (onglets déjà actifs)")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.success("✅ Vue d'ensemble\n\nKPIs 2024, tendances depuis 2005")
        with col_b:
            st.success("✅ Tendances 2005–2024\n\nCourbes, jalons, taux mortalité")
        with col_c:
            st.success("✅ Corrélations\n\nRadars officiels, ADAS, normes")

        st.info("""
        **Données présentes ici sans BAAC :**
        statistiques annuelles ONISR 2005–2024 · résumés véhicules 2010–2024 ·
        données radars officielles ANTAI 2003–2024 · 30 normes de sécurité 1998–2026
        """)
        st.stop()

    # ── Mode complet : analyse BAAC ──────────────────────────
    try:
        df_caract, df_usagers, df_vehicules, df_lieux = get_baac(data_dir)
        years_avail = sorted(df_caract["annee"].unique())
        sel_years = st.multiselect("Années", years_avail,
                                   default=[max(years_avail)], format_func=str)
        if not sel_years:
            st.warning("Sélectionnez au moins une année.")
            st.stop()

        df_c = df_caract[df_caract["annee"].isin(sel_years)]
        df_u = df_usagers[df_usagers["annee"].isin(sel_years)]
        df_v = df_vehicules[df_vehicules["annee"].isin(sel_years)]
        df_l = df_lieux[df_lieux["annee"].isin(sel_years)]

        tab1, tab2, tab3, tab4 = st.tabs([
            "📅 Temporel", "🚗 Véhicules", "🗺️ Géographie", "🌦️ Conditions"
        ])

        with tab1:
            c1, c2 = st.columns(2)
            with c1:
                monthly = get_monthly_trend(df_c, df_u)
                mois_labels = {1:"Jan",2:"Fév",3:"Mar",4:"Avr",5:"Mai",6:"Jun",
                               7:"Jul",8:"Aoû",9:"Sep",10:"Oct",11:"Nov",12:"Déc"}
                mf = monthly[monthly["annee"].isin(sel_years)].copy()
                fig = px.line(mf, x="mois", y="accidents", color="annee",
                              title="Accidents par mois", markers=True,
                              color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_xaxes(tickvals=list(range(1,13)),
                                 ticktext=list(mois_labels.values()))
                fig.update_layout(height=300, plot_bgcolor="white")
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                try:
                    df_c2 = df_c.copy()
                    df_c2["heure"] = pd.to_numeric(
                        df_c2["hrmn"].astype(str).str.split(":").str[0], errors="coerce")
                    hourly = df_c2.groupby(["annee","heure"]).size().reset_index(name="nb")
                    fig2 = px.line(hourly, x="heure", y="nb", color="annee",
                                   title="Accidents par heure",
                                   color_discrete_sequence=px.colors.qualitative.Set2)
                    fig2.update_layout(height=300, plot_bgcolor="white")
                    st.plotly_chart(fig2, use_container_width=True)
                except Exception:
                    st.warning("Données horaires indisponibles.")
            jours = {1:"Lun",2:"Mar",3:"Mer",4:"Jeu",5:"Ven",6:"Sam",7:"Dim"}
            df_c3 = df_c.copy()
            df_c3["jour"] = pd.to_numeric(df_c3["jour"], errors="coerce")
            daily = df_c3.groupby(["annee","jour"]).size().reset_index(name="nb")
            daily["jour_label"] = daily["jour"].map(jours)
            fig3 = px.bar(daily, x="jour_label", y="nb", color="annee",
                          barmode="group", title="Accidents par jour de la semaine",
                          category_orders={"jour_label": list(jours.values())},
                          color_discrete_sequence=px.colors.qualitative.Set2)
            fig3.update_layout(height=280, plot_bgcolor="white")
            st.plotly_chart(fig3, use_container_width=True)

        with tab2:
            df_v2 = df_v.copy()
            df_v2["catv"] = pd.to_numeric(df_v2["catv"], errors="coerce")
            df_v2["catv_label"] = df_v2["catv"].map(CATV_LABELS).fillna("Autre")
            top_cats = df_v2["catv_label"].value_counts().head(10).index
            c1, c2 = st.columns(2)
            with c1:
                catv_agg = (df_v2[df_v2["catv_label"].isin(top_cats)]
                            .groupby(["annee","catv_label"]).size().reset_index(name="nb"))
                fig = px.bar(catv_agg, x="catv_label", y="nb", color="annee",
                             barmode="group", title="Véhicules impliqués (Top 10)",
                             color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_xaxes(tickangle=40)
                fig.update_layout(height=360, plot_bgcolor="white")
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                merged = df_v2.merge(
                    df_u[["Num_Acc","grav"]].groupby("Num_Acc")
                    .apply(lambda x: (x["grav"]==2).sum())
                    .reset_index(name="tues"), on="Num_Acc", how="left")
                cat_g = (merged[merged["catv_label"].isin(top_cats)]
                         .groupby("catv_label")
                         .agg(tues=("tues","sum"), nb=("Num_Acc","count")).reset_index())
                cat_g["taux"] = cat_g["tues"] / cat_g["nb"] * 100
                fig2 = px.bar(cat_g.sort_values("taux", ascending=True),
                              x="taux", y="catv_label", orientation="h",
                              title="Taux de mortalité (%)",
                              color="taux",
                              color_continuous_scale=["#2A9D8F","#F4A261","#E63946"])
                fig2.update_layout(height=360, plot_bgcolor="white", showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)

        with tab3:
            dept_stats = get_dept_stats(df_c, df_u)
            dept_f = (dept_stats.groupby("dep")
                      .agg(accidents=("accidents","sum"), tues=("tues","sum"))
                      .reset_index())
            c1, c2 = st.columns(2)
            with c1:
                fig = px.bar(dept_f.nlargest(15,"accidents"), x="dep", y="accidents",
                             title="Top 15 dép – Accidents", color="accidents",
                             color_continuous_scale=["#A8DADC","#457B9D","#1D3557"])
                fig.update_layout(height=340, plot_bgcolor="white")
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                fig2 = px.bar(dept_f.nlargest(15,"tues"), x="dep", y="tues",
                              title="Top 15 dép – Tués", color="tues",
                              color_continuous_scale=["#F4A261","#E63946","#9B2226"])
                fig2.update_layout(height=340, plot_bgcolor="white")
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
                    title="Localisation accidents (échantillon 5 000)",
                    opacity=0.4, color_discrete_sequence=px.colors.qualitative.Set2)
                fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
                st.plotly_chart(fig_map, use_container_width=True)

        with tab4:
            c1, c2 = st.columns(2)
            with c1:
                df_c4 = df_c.copy()
                df_c4["lum"] = pd.to_numeric(df_c4["lum"], errors="coerce")
                df_c4["lum_label"] = df_c4["lum"].map(LUM_LABELS).fillna("Inconnu")
                lum_agg = df_c4.groupby(["annee","lum_label"]).size().reset_index(name="nb")
                fig = px.bar(lum_agg, x="lum_label", y="nb", color="annee",
                             barmode="group", title="Luminosité",
                             color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_xaxes(tickangle=30)
                fig.update_layout(height=300, plot_bgcolor="white")
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                df_c4["atm"] = pd.to_numeric(df_c4["atm"], errors="coerce")
                df_c4["atm_label"] = df_c4["atm"].map(ATM_LABELS).fillna("Inconnu")
                atm_agg = df_c4.groupby(["annee","atm_label"]).size().reset_index(name="nb")
                fig2 = px.bar(atm_agg, x="atm_label", y="nb", color="annee",
                              barmode="group", title="Conditions atmosphériques",
                              color_discrete_sequence=px.colors.qualitative.Set2)
                fig2.update_xaxes(tickangle=30)
                fig2.update_layout(height=300, plot_bgcolor="white")
                st.plotly_chart(fig2, use_container_width=True)

    except Exception as e:
        st.error(f"Erreur BAAC : {e}")
        import traceback; st.code(traceback.format_exc())


# ══════════════════════════════════════════════════════════════
# ONGLET 5 — CORRÉLATIONS & TECHNOLOGIES
# ══════════════════════════════════════════════════════════════
elif onglet == "🚦 Corrélations & Technologies":
    st.title("🚦 Corrélations : Radars, Technologies & Accidentologie")

    try:
        df = get_corr_data(data_dir)
        df_normes = get_normes(data_dir)

        subtab1, subtab2, subtab3, subtab4 = st.tabs([
            "📡 Radars & Recettes", "🛡️ Sécurité active (ADAS)",
            "📊 Analyse multivariée", "🗓️ Timeline réglementaire"
        ])

        with subtab1:
            st.markdown("### Déploiement des radars automatiques vs mortalité")
            st.caption("Source : ANTAI / fiches-auto.fr / Cour des Comptes — chiffres officiels")

            col_m, col_r = st.columns([3, 1])
            with col_r:
                show_type = st.multiselect("Afficher",
                    ["Radars fixes", "Total radars", "Recettes (M€)", "PV émis (M)"],
                    default=["Total radars", "Recettes (M€)"])

            fig = make_subplots(specs=[[{"secondary_y": True}]])
            if "Total radars" in show_type and "total_radars" in df.columns:
                fig.add_trace(go.Bar(x=df["annee"], y=df["total_radars"],
                                     name="Total radars", marker_color=C_ORANGE,
                                     opacity=0.55), secondary_y=True)
            if "Radars fixes" in show_type and "radars_fixes" in df.columns:
                fig.add_trace(go.Bar(x=df["annee"], y=df["radars_fixes"],
                                     name="Radars fixes", marker_color="#F4D35E",
                                     opacity=0.55), secondary_y=True)
            fig.add_trace(go.Scatter(x=df["annee"], y=df["tues"],
                                     name="Tués (30j)", mode="lines+markers",
                                     line=dict(color=C_RED, width=3),
                                     marker=dict(size=8)), secondary_y=False)
            if "Recettes (M€)" in show_type and "recettes_radars" in df.columns:
                fig.add_trace(go.Scatter(x=df["annee"], y=df["recettes_radars"],
                                         name="Recettes radars (M€)", mode="lines",
                                         line=dict(color=C_PURPLE, width=2, dash="dot")),
                              secondary_y=False)
            if "PV émis (M)" in show_type and "pv_emis_millions" in df.columns:
                fig.add_trace(go.Scatter(x=df["annee"], y=df["pv_emis_millions"] * 80,
                                         name="PV émis ×80 (échelle)", mode="lines",
                                         line=dict(color=C_GREEN, width=1.5, dash="dash")),
                              secondary_y=False)

            # Annotations événements clés
            for annee, label, color in [
                (2003, "1ers radars", C_ORANGE),
                (2013, "Bonnets rouges\n−130 radars", C_RED),
                (2018, "Gilets jaunes\n−400 radars", C_RED),
                (2020, "COVID", C_RED),
            ]:
                if 2005 <= annee <= 2024:
                    fig.add_vline(x=annee, line_dash="dot", line_color=color,
                                  line_width=1.2, annotation_text=label,
                                  annotation_position="top right",
                                  annotation_font_size=8)

            fig.update_layout(height=460, plot_bgcolor="white", barmode="stack",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02),
                              xaxis=dict(tickmode="linear", dtick=1))
            fig.update_yaxes(title_text="Tués / Recettes M€", secondary_y=False)
            fig.update_yaxes(title_text="Nombre de radars", secondary_y=True, showgrid=False)
            st.plotly_chart(fig, use_container_width=True)

            # Corrélation
            col_a, col_b = st.columns(2)
            with col_a:
                if "total_radars" in df.columns:
                    r_tot = df[["total_radars","tues"]].dropna().corr().iloc[0,1]
                    r_fix = df[["radars_fixes","tues"]].dropna().corr().iloc[0,1]
                    r_rec = df[["recettes_radars","tues"]].dropna().corr().iloc[0,1]
                    df_corr_r = pd.DataFrame({
                        "Indicateur": ["Total radars", "Radars fixes", "Recettes (M€)"],
                        "Corrélation (Pearson)": [round(r_tot,3), round(r_fix,3), round(r_rec,3)],
                        "Interprétation": [
                            "↓ Plus de radars = moins de tués",
                            "↓ Plus de radars = moins de tués",
                            "↓ Plus de recettes = moins de tués",
                        ]
                    })
                    st.markdown("**Corrélations radars ↔ tués**")
                    st.dataframe(df_corr_r, use_container_width=True, hide_index=True)
                    st.caption("Note : corrélation ≠ causalité. D'autres facteurs coévoluent (ADAS, comportements, réglementation).")

            with col_b:
                if "total_radars" in df.columns:
                    df_sc = df.dropna(subset=["total_radars","tues"])
                    fig3 = px.scatter(df_sc, x="total_radars", y="tues",
                                      text="annee", trendline="ols",
                                      labels={"total_radars":"Nb radars total",
                                              "tues":"Tués (30j)"},
                                      color_discrete_sequence=[C_BLUE])
                    fig3.update_traces(textposition="top center", textfont_size=8)
                    fig3.update_layout(height=300, plot_bgcolor="white")
                    st.plotly_chart(fig3, use_container_width=True)

        with subtab2:
            st.markdown("### Taux d'équipement ADAS vs mortalité")
            st.caption("Sources : CLEPA, ACEA — % des véhicules neufs vendus équipés (estimations)")

            adas_choices = st.multiselect(
                "Technologies ADAS",
                ["ABS", "ESP", "Airbag avant", "Freinage urgence", "ISA"],
                default=["ESP", "Freinage urgence", "ISA"])

            fig = make_subplots(specs=[[{"secondary_y": True}]])
            colors_adas = {"ABS":"#4361EE","ESP":"#4CC9F0","Airbag avant":"#7209B7",
                           "Freinage urgence":"#F72585","ISA":"#3A0CA3"}
            for tech in adas_choices:
                if tech in df.columns:
                    fig.add_trace(go.Scatter(
                        x=df["annee"], y=df[tech], name=tech,
                        mode="lines+markers",
                        line=dict(color=colors_adas.get(tech,"gray"), width=2),
                        marker=dict(size=5)), secondary_y=True)
            fig.add_trace(go.Scatter(x=df["annee"], y=df["tues"],
                                     name="Tués (30j)", mode="lines+markers",
                                     line=dict(color=C_RED, width=3),
                                     marker=dict(size=8)), secondary_y=False)

            for yr_n, lbl_n in [(2006,"ESP obligatoire VN"),(2011,"ESP généralisé"),
                                  (2014,"eCall VN"),(2022,"GSR2 : ISA")]:
                if 2005 <= yr_n <= 2024:
                    fig.add_vline(x=yr_n, line_dash="dot", line_color=C_GREEN,
                                  annotation_text=lbl_n, annotation_font_size=8)

            fig.update_layout(height=440, plot_bgcolor="white",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02),
                              xaxis=dict(tickmode="linear", dtick=1))
            fig.update_yaxes(title_text="Tués", secondary_y=False)
            fig.update_yaxes(title_text="% équipement", secondary_y=True,
                             range=[0,110], showgrid=False)
            st.plotly_chart(fig, use_container_width=True)

            corr_rows = []
            for tech in ["ABS","ESP","Airbag avant","Freinage urgence","ISA"]:
                if tech in df.columns:
                    sub = df[["tues",tech]].dropna()
                    if len(sub) > 3:
                        r = sub.corr().iloc[0,1]
                        corr_rows.append({
                            "Technologie": tech,
                            "Corrélation Pearson": round(r, 3),
                            "Signal": "↓ Fort" if r < -0.7 else ("↓ Modéré" if r < -0.4 else "→ Faible"),
                        })
            if corr_rows:
                st.markdown("**Corrélations individuelles ADAS → tués**")
                st.dataframe(pd.DataFrame(corr_rows), use_container_width=True, hide_index=True)
            st.info("Corrélation ≠ causalité. L'ESP, le freinage d'urgence et l'ISA coïncident avec d'autres mesures (radars, 80 km/h). L'attribution précise de chaque technologie reste un sujet de recherche actif (ETSC, CEREMA).")

        with subtab3:
            st.markdown("### Matrice de corrélation — tous indicateurs")
            cols_corr = ["tues","accidents","total_radars","recettes_radars",
                         "ESP","Freinage urgence","ISA","age_parc"]
            df_mat = df[[c for c in cols_corr if c in df.columns]].dropna()
            corr_matrix = df_mat.corr()
            fig_hm = px.imshow(corr_matrix.round(2), text_auto=True,
                               color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                               title="Pearson — bleu=négatif (relation inverse), rouge=positif")
            fig_hm.update_layout(height=420)
            st.plotly_chart(fig_hm, use_container_width=True)

            st.markdown("### Évolution normalisée (base 100 en 2005)")
            df_norm = df[["annee","tues","accidents","total_radars","ESP","Freinage urgence"]].copy()
            base = df_norm[df_norm["annee"]==2005].iloc[0]
            for col in ["tues","accidents","total_radars","ESP","Freinage urgence"]:
                if col in df_norm.columns and base[col] and base[col] != 0:
                    df_norm[col] = df_norm[col] / base[col] * 100
            df_melt = df_norm.melt(id_vars="annee",
                                   var_name="Indicateur", value_name="Indice")
            rename_map = {"tues":"Tués","accidents":"Accidents",
                          "total_radars":"Total radars",
                          "ESP":"Équipement ESP",
                          "Freinage urgence":"Freinage urgence"}
            df_melt["Indicateur"] = df_melt["Indicateur"].map(rename_map)
            fig_n = px.line(df_melt, x="annee", y="Indice", color="Indicateur",
                            markers=True,
                            labels={"Indice":"Indice (2005=100)","annee":"Année"},
                            color_discrete_map={"Tués":C_RED,"Accidents":C_BLUE,
                                                "Total radars":C_ORANGE,
                                                "Équipement ESP":C_GREEN,
                                                "Freinage urgence":C_PURPLE})
            fig_n.add_hline(y=100, line_dash="dot", line_color="gray")
            fig_n.update_layout(height=360, plot_bgcolor="white",
                                legend=dict(orientation="h"),
                                xaxis=dict(tickmode="linear", dtick=1))
            st.plotly_chart(fig_n, use_container_width=True)

        with subtab4:
            st.markdown("### Timeline des mesures de sécurité routière")
            if len(df_normes) > 0:
                cat_filter = st.multiselect(
                    "Filtrer par catégorie",
                    ["securite_active", "securite_passive", "reglementation"],
                    default=["securite_active", "reglementation"],
                    format_func=lambda x: {
                        "securite_active": "🟢 Sécurité active (ADAS)",
                        "securite_passive": "🔵 Sécurité passive",
                        "reglementation": "🟠 Réglementation",
                    }.get(x, x)
                )
                df_n_f = df_normes[df_normes["categorie"].isin(cat_filter)]
                st.dataframe(
                    df_n_f[["annee","norme_nom","categorie","scope","impact_estime","source_officielle"]]
                    .sort_values("annee").rename(columns={
                        "annee":"Année","norme_nom":"Norme/Mesure",
                        "categorie":"Catégorie","scope":"Périmètre",
                        "impact_estime":"Impact estimé",
                        "source_officielle":"Source officielle"
                    }).reset_index(drop=True),
                    use_container_width=True, hide_index=True
                )
            else:
                st.warning("Fichier `normes_securite_vehicules.csv` non trouvé dans le répertoire des données.")

            # Timeline visuelle
            colors_map = {"securite_active": C_GREEN, "securite_passive": C_BLUE,
                          "reglementation": C_ORANGE}
            fig_tl = go.Figure()
            fig_tl.add_trace(go.Scatter(x=[2003, 2026], y=[0, 0],
                                        mode="lines", line=dict(color="gray", width=1.5),
                                        showlegend=False))
            for mtype, label_fr in [
                ("securite_active","🟢 Sécurité active"),
                ("reglementation","🟠 Réglementation"),
                ("securite_passive","🔵 Sécurité passive")
            ]:
                sub = df_normes[df_normes["categorie"] == mtype] if len(df_normes) else pd.DataFrame()
                if len(sub) == 0:
                    sub_ms = [m for m in SAFETY_MILESTONES if m["type"] == mtype]
                    if not sub_ms: continue
                    years_m = [m["annee"] for m in sub_ms]
                    labels_m = [m["label"] for m in sub_ms]
                else:
                    years_m = sub["annee"].tolist()
                    labels_m = sub["norme_nom"].tolist()
                fig_tl.add_trace(go.Scatter(
                    x=years_m, y=[0]*len(years_m), mode="markers+text",
                    marker=dict(size=14, color=colors_map[mtype], symbol="circle"),
                    text=labels_m, textposition="top center",
                    textfont=dict(size=8, color=colors_map[mtype]),
                    name=label_fr,
                    hovertemplate="%{text}<br>Année : %{x}<extra></extra>"
                ))
            fig_tl.update_layout(
                height=360, plot_bgcolor="white",
                yaxis=dict(showticklabels=False, showgrid=False, zeroline=False,
                           range=[-0.5, 2.5]),
                xaxis=dict(tickmode="linear", dtick=1, range=[2002, 2027]),
                legend=dict(orientation="h", yanchor="top", y=-0.05),
            )
            st.plotly_chart(fig_tl, use_container_width=True)

    except Exception as e:
        st.error(f"Erreur : {e}")


# ══════════════════════════════════════════════════════════════
# ONGLET 6 — DONNÉES BRUTES
# ══════════════════════════════════════════════════════════════
elif onglet == "📋 Données brutes":
    st.title("📋 Données brutes & Sources")

    tab_a, tab_b = st.tabs(["📥 Accès BAAC (mode Colab)", "📊 Petits CSV (disponibles ici)"])

    with tab_a:
        if not baac_ok:
            st.info("Fichiers BAAC non détectés — montez Google Drive dans Colab et renseignez le chemin.")
        else:
            year_sel = st.selectbox("Année BAAC", list(range(2024, 2017, -1)))
            table_sel = st.selectbox("Table", ["caract","usagers","vehicules","lieux"])
            if st.button("📥 Charger"):
                try:
                    d = load_baac_year(year_sel, data_dir)
                    df_show = d[table_sel]
                    st.success(f"✓ {len(df_show):,} lignes — {len(df_show.columns)} colonnes")
                    st.dataframe(df_show.head(500), use_container_width=True)
                    csv = df_show.to_csv(index=False, sep=";").encode("utf-8")
                    st.download_button(f"💾 Télécharger", csv,
                                       f"{table_sel}{year_sel}_export.csv", "text/csv")
                except Exception as e:
                    st.error(f"Erreur : {e}")

    with tab_b:
        st.markdown("#### Résumés annuels véhicules (2010–2024)")
        year_s = st.selectbox("Année", list(range(2024, 2009, -1)), key="yr_s")
        try:
            df_s = pd.read_csv(os.path.join(data_dir, f"{year_s}.csv"),
                               sep=";", encoding="utf-8", low_memory=False)
            st.success(f"✓ {len(df_s):,} lignes")
            st.dataframe(df_s.head(200), use_container_width=True)
        except Exception as e:
            st.warning(f"Fichier {year_s}.csv non trouvé : {e}")

        st.markdown("---")
        st.markdown("#### Radars officiels 2003–2024")
        df_r = get_radars(data_dir)
        if len(df_r):
            st.dataframe(df_r, use_container_width=True, hide_index=True)
        else:
            st.warning("radars_france.csv non trouvé")

        st.markdown("---")
        st.markdown("#### Normes de sécurité 1998–2026")
        df_n = get_normes(data_dir)
        if len(df_n):
            st.dataframe(df_n[["annee","norme_nom","categorie","scope","impact_estime"]],
                         use_container_width=True, hide_index=True)
        else:
            st.warning("normes_securite_vehicules.csv non trouvé")

    st.markdown("---")
    st.markdown("### 🔗 Sources de téléchargement")
    st.markdown("""
    | Source | URL | Données |
    |--------|-----|---------|
    | **BAAC** | [data.gouv.fr](https://www.data.gouv.fr/fr/datasets/bases-de-donnees-annuelles-des-accidents-corporels-de-la-circulation-routiere-annees-de-2005-a-2023/) | Fichiers BAAC 2018-2024 |
    | **ONISR** | [securite-routiere.gouv.fr](https://www.securite-routiere.gouv.fr/les-medias/la-mediatheque/bilan-de-laccidentalite) | Bilans annuels |
    | **ANTAI** | [antai.gouv.fr](https://www.antai.gouv.fr/le-controle-automatise/) | Statistiques radars |
    | **Euro NCAP** | [euroncap.com](https://www.euroncap.com/fr/) | Scores sécurité |
    """)
