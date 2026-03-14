"""
app.py – Dashboard Accidents Routiers France (2005–2024)  v2.0
=============================================================
Tableau de bord Streamlit avec perspective historique complète,
analyse par véhicule 2010-2024, et onglet corrélations
Technologies / Réglementations / Sécurité active.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os, sys

# ─────────────────────────────────────────────
# CONFIG PAGE
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
C_LIGHT  = "#A8DADC"
C_PURPLE = "#7B2D8B"

DEFAULT_DATA_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import (
    build_historical_df, load_baac_year, load_full_baac,
    build_correlation_dataset, build_vehicle_trend_2010_2024,
    build_summary_stats_2010_2017,
    get_monthly_trend, get_dept_stats,
    GRAV_LABELS, LUM_LABELS, ATM_LABELS, COL_LABELS, CATR_LABELS,
    CATV_LABELS, RADAR_DATA, SAFETY_MILESTONES, ADAS_DATA, AGE_PARC,
)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚗 Accidentologie France")
    data_dir = st.text_input(
        "📁 Répertoire des données CSV",
        value=DEFAULT_DATA_DIR,
        help="Chemin absolu vers le dossier contenant tous les fichiers CSV BAAC"
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
    st.caption("Sources : BAAC / data.gouv.fr · ONISR · ANTAI · ACEA · CCFA")
    st.caption("v2.0 — 2025")


# ─────────────────────────────────────────────
# CACHE
# ─────────────────────────────────────────────
@st.cache_data(show_spinner="Chargement historique complet…")
def get_historical(data_dir):
    return build_historical_df(years=range(2005, 2025), data_dir=data_dir)

@st.cache_data(show_spinner="Chargement BAAC 2018-2024…")
def get_baac(data_dir):
    return load_full_baac(years=range(2018, 2025), data_dir=data_dir)

@st.cache_data(show_spinner="Construction dataset corrélations…")
def get_corr_data(data_dir):
    return build_correlation_dataset(data_dir=data_dir)

@st.cache_data(show_spinner="Chargement tendances véhicules 2010-2024…")
def get_vehicle_trend(data_dir):
    return build_vehicle_trend_2010_2024(data_dir=data_dir)

@st.cache_data(show_spinner="Chargement résumés 2010-2017…")
def get_summary_stats(data_dir):
    return build_summary_stats_2010_2017(data_dir=data_dir)

@st.cache_data(show_spinner="Chargement 2024…")
def get_2024(data_dir):
    return load_baac_year(2024, data_dir)


# ─────────────────────────────────────────────
# HELPER: ajouter jalons sur un fig plotly
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
            annotation_text=m["label"],
            annotation_position="top right",
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
        d24 = get_2024(data_dir)
        df_u24 = d24["usagers"]

        last = df_hist[df_hist["annee"] == 2024].iloc[0]
        prev = df_hist[df_hist["annee"] == 2023].iloc[0]
        ref  = df_hist[df_hist["annee"] == 2005].iloc[0]

        # ── KPIs ─────────────────────────────────────────────
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
        c5.metric("📉 Baisse tués vs 2005", f"{pct:.1f}%", "–67% en 20 ans")

        st.markdown("---")
        col_g, col_d = st.columns([3, 2])

        with col_g:
            st.markdown("#### Évolution 2005–2024")
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_hist["annee"], y=df_hist["accidents"],
                                 name="Accidents", marker_color=C_BLUE,
                                 opacity=0.45, yaxis="y2"))
            fig.add_trace(go.Scatter(x=df_hist["annee"], y=df_hist["tues"],
                                     name="Tués (30j)", mode="lines+markers",
                                     line=dict(color=C_RED, width=3),
                                     marker=dict(size=7)))
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
                yaxis2=dict(title="Nb accidents", overlaying="y", side="right",
                            showgrid=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                xaxis=dict(tickmode="linear", dtick=1),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_d:
            st.markdown("#### Gravité 2024")
            grav_counts = df_u24["grav"].map(GRAV_LABELS).value_counts()
            fig_pie = px.pie(values=grav_counts.values, names=grav_counts.index,
                             color_discrete_sequence=[C_GREEN, C_ORANGE, C_RED, C_BLUE],
                             hole=0.45)
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            fig_pie.update_layout(height=380, showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True)

        # ── Indices normalisés ────────────────────────────────
        st.markdown("#### Indice de progression (base 100 en 2005)")
        df_n = df_hist.copy()
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df_n["annee"], y=df_n["idx_acc"],
                                  name="Accidents", mode="lines+markers",
                                  line=dict(color=C_BLUE, width=2)))
        fig2.add_trace(go.Scatter(x=df_n["annee"], y=df_n["idx_tues"],
                                  name="Tués", mode="lines+markers",
                                  line=dict(color=C_RED, width=3)))
        fig2.add_hline(y=100, line_dash="dot", line_color="gray")
        fig2.add_hrect(y0=0, y1=50, fillcolor="rgba(42,157,143,0.07)", line_width=0)
        fig2.update_layout(height=240, plot_bgcolor="white",
                           legend=dict(orientation="h"),
                           xaxis=dict(tickmode="linear", dtick=1),
                           yaxis=dict(title="Indice (2005=100)"))
        st.plotly_chart(fig2, use_container_width=True)

    except Exception as e:
        st.error(f"Erreur : {e}")
        st.info("Vérifiez le répertoire des données dans la barre latérale.")


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
            show_ev = st.multiselect("Jalons à afficher",
                ["radars", "réglementations", "sécurité active", "événements"],
                default=["réglementations", "événements"])
        type_map = {"radars": "radar", "réglementations": "reglementation",
                    "sécurité active": "securite_active", "événements": "evenement"}
        active = [type_map[s] for s in show_ev]
        df_f = df_hist[(df_hist["annee"] >= yr[0]) & (df_hist["annee"] <= yr[1])]

        # ── Graphique principal ────────────────────────────────
        st.markdown("### Accidents corporels et mortalité")
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=df_f["annee"], y=df_f["accidents"],
                             name="Accidents", marker_color=C_BLUE,
                             opacity=0.45), secondary_y=True)
        fig.add_trace(go.Scatter(x=df_f["annee"], y=df_f["tues"],
                                 name="Tués (30j)", mode="lines+markers",
                                 line=dict(color=C_RED, width=3),
                                 marker=dict(size=9)), secondary_y=False)
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

        # Légende couleurs
        with st.expander("Légende des jalons"):
            cc = st.columns(4)
            cc[0].markdown(f"🟠 **Radars / contrôles**")
            cc[1].markdown(f"🔵 **Réglementations**")
            cc[2].markdown(f"🟢 **Technologies de sécurité**")
            cc[3].markdown(f"🔴 **Événements exceptionnels**")

        st.markdown("---")

        col_a, col_b = st.columns(2)
        with col_a:
            # Taux de mortalité
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
            # Accidents par gravité 2010-2017 (depuis résumés)
            st.markdown("### Répartition par gravité 2010–2017")
            if len(df_sum) > 0:
                df_s = df_sum[["annee", "acc_mortels", "acc_graves", "acc_legers"]].copy()
                df_s.columns = ["Année", "Mortels", "Graves non mortels", "Légers"]
                df_melt = df_s.melt(id_vars="Année", var_name="Gravité", value_name="Nb")
                fig3 = px.bar(df_melt, x="Année", y="Nb", color="Gravité",
                              barmode="stack",
                              color_discrete_map={"Mortels": C_RED,
                                                  "Graves non mortels": C_ORANGE,
                                                  "Légers": C_BLUE},
                              labels={"Nb": "Nb accidents", "Année": "Année"})
                fig3.update_layout(height=280, plot_bgcolor="white",
                                   legend=dict(orientation="h"))
                st.plotly_chart(fig3, use_container_width=True)

        # Tableau récap
        st.markdown("### Tableau récapitulatif")
        df_disp = df_f[["annee","accidents","tues","hospitalises",
                         "blesses_legers","taux_tue_par_acc","source"]].copy()
        df_disp.columns = ["Année","Accidents","Tués (30j)","Hospitalisés",
                            "Blessés légers","Taux mortalité (%)","Source"]
        df_disp["Taux mortalité (%)"] = df_disp["Taux mortalité (%)"].round(2)
        st.dataframe(df_disp.sort_values("Année", ascending=False).reset_index(drop=True),
                     use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Erreur : {e}")


# ══════════════════════════════════════════════════════════════
# ONGLET 3 — VÉHICULES IMPLIQUÉS 2010-2024
# ══════════════════════════════════════════════════════════════
elif onglet == "🚗 Véhicules impliqués":
    st.title("🚗 Véhicules Impliqués dans les Accidents 2010–2024")
    st.caption("Données harmonisées : résumés annuels 2010-2017 + BAAC 2018-2024")

    try:
        df_veh = get_vehicle_trend(data_dir)

        # Filtres
        all_cats = sorted(df_veh["categorie"].unique())
        sel_cats = st.multiselect("Catégories à afficher", all_cats,
                                  default=[c for c in all_cats
                                           if c in ["Voiture (VP)", "Moto >125cm³",
                                                    "Cyclomoteur/Vélo", "Utilitaire (VUL)",
                                                    "EDP motorisé", "VAE/Vélo"]])
        if not sel_cats:
            sel_cats = all_cats

        df_f = df_veh[df_veh["categorie"].isin(sel_cats)]

        # ── Graphe principal : évolution ──────────────────────
        st.markdown("### Évolution du nombre de véhicules impliqués")
        fig = px.line(df_f, x="annee", y="nb", color="categorie",
                      markers=True,
                      labels={"nb": "Nb véhicules impliqués", "annee": "Année",
                              "categorie": "Catégorie"},
                      color_discrete_sequence=px.colors.qualitative.Safe)
        fig.add_vline(x=2017.5, line_dash="dash", line_color="gray",
                      annotation_text="← Résumés | BAAC →",
                      annotation_position="top center",
                      annotation_font_size=9)
        fig.update_layout(height=420, plot_bgcolor="white",
                          xaxis=dict(tickmode="linear", dtick=1),
                          legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True)

        col_a, col_b = st.columns(2)
        with col_a:
            # Barres 2024 vs 2018
            st.markdown("### Comparaison 2018 vs 2024 (BAAC)")
            df_comp = df_veh[df_veh["annee"].isin([2018, 2024]) &
                             df_veh["categorie"].isin(sel_cats)]
            fig2 = px.bar(df_comp, x="categorie", y="nb", color="annee",
                          barmode="group",
                          color_discrete_map={2018: C_BLUE, 2024: C_RED},
                          labels={"nb": "Nb véhicules", "categorie": "", "annee": "Année"})
            fig2.update_xaxes(tickangle=35)
            fig2.update_layout(height=380, plot_bgcolor="white")
            st.plotly_chart(fig2, use_container_width=True)

        with col_b:
            # Parts relatives par année
            st.markdown("### Parts relatives par catégorie (%)")
            pivot = df_veh.pivot_table(index="annee", columns="categorie",
                                       values="nb", aggfunc="sum").fillna(0)
            pivot_pct = pivot.div(pivot.sum(axis=1), axis=0) * 100

            cats_plot = [c for c in sel_cats if c in pivot_pct.columns]
            fig3 = go.Figure()
            colors = px.colors.qualitative.Safe
            for i, cat in enumerate(cats_plot):
                fig3.add_trace(go.Scatter(
                    x=pivot_pct.index, y=pivot_pct[cat],
                    name=cat, mode="lines", stackgroup="one",
                    fillcolor=colors[i % len(colors)],
                    line=dict(color=colors[i % len(colors)], width=0.5),
                ))
            fig3.add_vline(x=2017.5, line_dash="dash", line_color="gray")
            fig3.update_layout(height=380, plot_bgcolor="white",
                               yaxis=dict(title="Part (%)"),
                               xaxis=dict(tickmode="linear", dtick=1),
                               legend=dict(orientation="h"))
            st.plotly_chart(fig3, use_container_width=True)

        # ── Tendances nouvelles mobilités ─────────────────────
        st.markdown("### Nouvelles mobilités : EDP & VAE (2018-2024)")
        new_mob = ["EDP motorisé", "EDP non motorisé", "VAE/Vélo"]
        df_nm = df_veh[df_veh["categorie"].isin(new_mob) & (df_veh["annee"] >= 2018)]
        if len(df_nm) > 0:
            fig4 = px.bar(df_nm, x="annee", y="nb", color="categorie",
                          barmode="stack",
                          color_discrete_sequence=[C_GREEN, C_ORANGE, C_PURPLE],
                          labels={"nb": "Nb véhicules impliqués",
                                  "annee": "Année", "categorie": "Type"})
            fig4.update_layout(height=280, plot_bgcolor="white",
                               xaxis=dict(tickmode="linear", dtick=1))
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Données EDP/VAE disponibles uniquement depuis 2018 (BAAC)")

    except Exception as e:
        st.error(f"Erreur : {e}")


# ══════════════════════════════════════════════════════════════
# ONGLET 4 — ANALYSE BAAC 2018-2024
# ══════════════════════════════════════════════════════════════
elif onglet == "🔍 Analyse BAAC 2018–2024":
    st.title("🔍 Analyse Détaillée BAAC 2018–2024")

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
                monthly_f = monthly[monthly["annee"].isin(sel_years)].copy()
                monthly_f["mois_label"] = monthly_f["mois"].map(mois_labels)
                fig = px.line(monthly_f, x="mois", y="accidents", color="annee",
                              title="Accidents par mois", markers=True,
                              labels={"accidents":"Nb accidents","mois":"Mois"},
                              color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_xaxes(tickvals=list(range(1,13)),
                                 ticktext=list(mois_labels.values()))
                fig.update_layout(height=320, plot_bgcolor="white")
                st.plotly_chart(fig, use_container_width=True)

            with c2:
                try:
                    df_c2 = df_c.copy()
                    df_c2["heure"] = pd.to_numeric(
                        df_c2["hrmn"].astype(str).str.split(":").str[0], errors="coerce")
                    hourly = (df_c2.groupby(["annee","heure"]).size()
                              .reset_index(name="accidents"))
                    fig2 = px.line(hourly[hourly["annee"].isin(sel_years)],
                                   x="heure", y="accidents", color="annee",
                                   title="Accidents par heure",
                                   labels={"accidents":"Nb","heure":"Heure"},
                                   color_discrete_sequence=px.colors.qualitative.Set2)
                    fig2.update_layout(height=320, plot_bgcolor="white")
                    st.plotly_chart(fig2, use_container_width=True)
                except Exception as e:
                    st.warning(f"Heure indisponible : {e}")

            jours = {1:"Lun",2:"Mar",3:"Mer",4:"Jeu",5:"Ven",6:"Sam",7:"Dim"}
            df_c3 = df_c.copy()
            df_c3["jour"] = pd.to_numeric(df_c3["jour"], errors="coerce")
            daily = (df_c3.groupby(["annee","jour"]).size()
                     .reset_index(name="accidents"))
            daily["jour_label"] = daily["jour"].map(jours)
            fig3 = px.bar(daily[daily["annee"].isin(sel_years)],
                          x="jour_label", y="accidents", color="annee",
                          barmode="group", title="Accidents par jour de la semaine",
                          category_orders={"jour_label": list(jours.values())},
                          color_discrete_sequence=px.colors.qualitative.Set2)
            fig3.update_layout(height=300, plot_bgcolor="white")
            st.plotly_chart(fig3, use_container_width=True)

        with tab2:
            df_v2 = df_v.copy()
            df_v2["catv"] = pd.to_numeric(df_v2["catv"], errors="coerce")
            df_v2["catv_label"] = df_v2["catv"].map(CATV_LABELS).fillna("Autre")
            top_cats = df_v2["catv_label"].value_counts().head(10).index

            c1, c2 = st.columns(2)
            with c1:
                catv_agg = (df_v2[df_v2["catv_label"].isin(top_cats)]
                            .groupby(["annee","catv_label"]).size()
                            .reset_index(name="nb"))
                fig = px.bar(catv_agg, x="catv_label", y="nb", color="annee",
                             barmode="group", title="Véhicules impliqués (Top 10)",
                             color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_xaxes(tickangle=40)
                fig.update_layout(height=380, plot_bgcolor="white")
                st.plotly_chart(fig, use_container_width=True)

            with c2:
                merged = df_v2.merge(
                    df_u[["Num_Acc","grav"]].groupby("Num_Acc")
                    .apply(lambda x: (x["grav"]==2).sum())
                    .reset_index(name="tues"),
                    on="Num_Acc", how="left"
                )
                cat_g = (merged[merged["catv_label"].isin(top_cats)]
                         .groupby("catv_label")
                         .agg(tues=("tues","sum"), nb=("Num_Acc","count"))
                         .reset_index())
                cat_g["taux"] = cat_g["tues"] / cat_g["nb"] * 100
                fig2 = px.bar(cat_g.sort_values("taux", ascending=True),
                              x="taux", y="catv_label", orientation="h",
                              title="Taux de mortalité par véhicule (%)",
                              color="taux",
                              color_continuous_scale=["#2A9D8F","#F4A261","#E63946"])
                fig2.update_layout(height=380, plot_bgcolor="white", showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)

        with tab3:
            dept_stats = get_dept_stats(df_c, df_u)
            dept_f = (dept_stats[dept_stats["annee"].isin(sel_years)]
                      .groupby("dep")
                      .agg(accidents=("accidents","sum"), tues=("tues","sum"))
                      .reset_index())
            c1, c2 = st.columns(2)
            with c1:
                fig = px.bar(dept_f.nlargest(15,"accidents"), x="dep", y="accidents",
                             title="Top 15 dép – Accidents",
                             color="accidents",
                             color_continuous_scale=["#A8DADC","#457B9D","#1D3557"])
                fig.update_layout(height=360, plot_bgcolor="white")
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                fig2 = px.bar(dept_f.nlargest(15,"tues"), x="dep", y="tues",
                              title="Top 15 dép – Tués",
                              color="tues",
                              color_continuous_scale=["#F4A261","#E63946","#9B2226"])
                fig2.update_layout(height=360, plot_bgcolor="white")
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
                    zoom=5, height=460, mapbox_style="carto-positron",
                    title="Localisation accidents (échantillon 5 000)",
                    opacity=0.4,
                    color_discrete_sequence=px.colors.qualitative.Set2)
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
                fig.update_layout(height=320, plot_bgcolor="white")
                st.plotly_chart(fig, use_container_width=True)

            with c2:
                df_c4["atm"] = pd.to_numeric(df_c4["atm"], errors="coerce")
                df_c4["atm_label"] = df_c4["atm"].map(ATM_LABELS).fillna("Inconnu")
                atm_agg = df_c4.groupby(["annee","atm_label"]).size().reset_index(name="nb")
                fig2 = px.bar(atm_agg, x="atm_label", y="nb", color="annee",
                              barmode="group", title="Conditions atmosphériques",
                              color_discrete_sequence=px.colors.qualitative.Set2)
                fig2.update_xaxes(tickangle=30)
                fig2.update_layout(height=320, plot_bgcolor="white")
                st.plotly_chart(fig2, use_container_width=True)

            df_c4["col"] = pd.to_numeric(df_c4["col"], errors="coerce")
            df_c4["col_label"] = df_c4["col"].map(COL_LABELS).fillna("Inconnu")
            col_agg = df_c4.groupby("col_label").size().reset_index(name="nb")
            fig3 = px.pie(col_agg, values="nb", names="col_label",
                          title="Types de collision",
                          color_discrete_sequence=px.colors.qualitative.Set3,
                          hole=0.3)
            fig3.update_layout(height=340)
            st.plotly_chart(fig3, use_container_width=True)

    except Exception as e:
        st.error(f"Erreur BAAC : {e}")
        import traceback; st.code(traceback.format_exc())


# ══════════════════════════════════════════════════════════════
# ONGLET 5 — CORRÉLATIONS & TECHNOLOGIES
# ══════════════════════════════════════════════════════════════
elif onglet == "🚦 Corrélations & Technologies":
    st.title("🚦 Corrélations : Technologies, Contrôles & Accidentologie")
    st.markdown("""
    > Analyse des relations entre le déploiement des radars, les normes de sécurité active
    > (ADAS) et l'évolution de la mortalité routière en France de 2005 à 2024.
    """)

    try:
        df = get_corr_data(data_dir)

        subtab1, subtab2, subtab3, subtab4 = st.tabs([
            "📡 Radars & Vitesse", "🛡️ Sécurité active (ADAS)",
            "📊 Analyse multivariée", "🗓️ Timeline réglementaire"
        ])

        # ── SUB-TAB 1 : RADARS ─────────────────────────────────
        with subtab1:
            st.markdown("### Déploiement des radars automatiques vs mortalité")
            st.caption("Sources : ANTAI, ONISR — Radars fixes et mobiles embarqués")

            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=df["annee"], y=df["radars_fixes"],
                                 name="Radars fixes", marker_color=C_ORANGE,
                                 opacity=0.6), secondary_y=True)
            fig.add_trace(go.Bar(x=df["annee"], y=df["radars_mobiles"],
                                 name="Radars mobiles emb.", marker_color="#FFD166",
                                 opacity=0.6), secondary_y=True)
            fig.add_trace(go.Scatter(x=df["annee"], y=df["tues"],
                                     name="Tués (30j)", mode="lines+markers",
                                     line=dict(color=C_RED, width=3),
                                     marker=dict(size=8)), secondary_y=False)
            fig.add_trace(go.Scatter(x=df["annee"], y=df["accidents"],
                                     name="Accidents", mode="lines",
                                     line=dict(color=C_BLUE, width=1.5, dash="dot"),
                                     visible="legendonly"), secondary_y=False)

            # COVID
            fig.add_vrect(x0=2019.7, x1=2020.3,
                          fillcolor="rgba(230,57,70,0.12)", line_width=0,
                          annotation_text="COVID", annotation_position="top left")
            # 80km/h
            fig.add_vline(x=2018, line_dash="dot", line_color=C_GREEN,
                          annotation_text="80 km/h", annotation_font_size=9)
            # 1er radar
            fig.add_vline(x=2003.5, line_dash="dot", line_color=C_ORANGE,
                          annotation_text="1ers radars", annotation_font_size=9)

            fig.update_layout(height=460, plot_bgcolor="white",
                              barmode="stack",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02),
                              xaxis=dict(tickmode="linear", dtick=1))
            fig.update_yaxes(title_text="Personnes tuées / Accidents",
                             secondary_y=False)
            fig.update_yaxes(title_text="Nombre de radars",
                             secondary_y=True, showgrid=False)
            st.plotly_chart(fig, use_container_width=True)

            # Recettes radars
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("#### Recettes radars vs tués")
                fig2 = make_subplots(specs=[[{"secondary_y": True}]])
                fig2.add_trace(go.Bar(x=df["annee"], y=df["recettes_radars"],
                                      name="Recettes (M€)", marker_color="#F4D35E",
                                      opacity=0.7), secondary_y=True)
                fig2.add_trace(go.Scatter(x=df["annee"], y=df["tues"],
                                          name="Tués", mode="lines+markers",
                                          line=dict(color=C_RED, width=2.5),
                                          marker=dict(size=7)), secondary_y=False)
                fig2.update_layout(height=300, plot_bgcolor="white",
                                   legend=dict(orientation="h"),
                                   xaxis=dict(tickmode="linear", dtick=2))
                fig2.update_yaxes(title_text="Tués", secondary_y=False)
                fig2.update_yaxes(title_text="Recettes M€", secondary_y=True,
                                  showgrid=False)
                st.plotly_chart(fig2, use_container_width=True)

            with col_b:
                st.markdown("#### Corrélation radars fixes → tués")
                df_c2 = df.dropna(subset=["radars_fixes","tues"])
                fig3 = px.scatter(df_c2, x="radars_fixes", y="tues",
                                  text="annee", trendline="ols",
                                  labels={"radars_fixes":"Nb radars fixes",
                                          "tues":"Personnes tuées"},
                                  color_discrete_sequence=[C_BLUE])
                fig3.update_traces(textposition="top center", textfont_size=8)
                fig3.update_layout(height=300, plot_bgcolor="white")
                st.plotly_chart(fig3, use_container_width=True)

                # Coefficient de corrélation
                r = df_c2[["radars_fixes","tues"]].corr().iloc[0,1]
                st.metric("Corrélation de Pearson (radars / tués)",
                          f"r = {r:.3f}",
                          help="Valeur négative = plus de radars → moins de tués")

        # ── SUB-TAB 2 : ADAS ──────────────────────────────────
        with subtab2:
            st.markdown("### Taux d'équipement ADAS vs mortalité")
            st.caption("Sources : CLEPA, ACEA — % des véhicules neufs vendus équipés")

            adas_choices = st.multiselect(
                "Technologies ADAS à afficher",
                ["ABS", "ESP", "Airbag avant", "Freinage urgence", "ISA"],
                default=["ESP", "Freinage urgence", "ISA"]
            )

            fig = make_subplots(specs=[[{"secondary_y": True}]])
            colors_adas = {
                "ABS": "#4361EE", "ESP": "#4CC9F0",
                "Airbag avant": "#7209B7", "Freinage urgence": "#F72585",
                "ISA": "#3A0CA3"
            }
            for tech in adas_choices:
                if tech in df.columns:
                    fig.add_trace(go.Scatter(
                        x=df["annee"], y=df[tech],
                        name=tech, mode="lines+markers",
                        line=dict(color=colors_adas.get(tech, "gray"), width=2),
                        marker=dict(size=5)
                    ), secondary_y=True)
            fig.add_trace(go.Scatter(
                x=df["annee"], y=df["tues"],
                name="Tués (30j)", mode="lines+markers",
                line=dict(color=C_RED, width=3),
                marker=dict(size=8)
            ), secondary_y=False)

            # Jalons normatifs
            normes = [
                (2006, "ESP obligatoire VN", C_GREEN),
                (2011, "ESP généralisé", C_GREEN),
                (2014, "eCall VN", C_BLUE),
                (2022, "GSR2 : ISA", C_PURPLE),
            ]
            for yr_n, lbl_n, col_n in normes:
                if 2005 <= yr_n <= 2024:
                    fig.add_vline(x=yr_n, line_dash="dot", line_color=col_n,
                                  annotation_text=lbl_n, annotation_font_size=8)

            fig.update_layout(height=460, plot_bgcolor="white",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02),
                              xaxis=dict(tickmode="linear", dtick=1))
            fig.update_yaxes(title_text="Personnes tuées", secondary_y=False)
            fig.update_yaxes(title_text="% équipement ADAS", secondary_y=True,
                             range=[0, 110], showgrid=False)
            st.plotly_chart(fig, use_container_width=True)

            # Corrélations ADAS / tués
            st.markdown("#### Corrélations individuelles ADAS → tués")
            corr_rows = []
            for tech in ["ABS", "ESP", "Airbag avant", "Freinage urgence", "ISA"]:
                if tech in df.columns:
                    sub = df[["tues", tech]].dropna()
                    if len(sub) > 3:
                        r = sub.corr().iloc[0, 1]
                        corr_rows.append({
                            "Technologie": tech,
                            "Corrélation Pearson": round(r, 3),
                            "Interprétation": "⬇️ Négatif (↑ équipement → ↓ tués)" if r < -0.5
                            else ("↗️ Positif (paradoxe ou autre facteur)" if r > 0.3
                                  else "➡️ Faible corrélation")
                        })
            if corr_rows:
                df_corr = pd.DataFrame(corr_rows)
                st.dataframe(df_corr, use_container_width=True, hide_index=True)

            st.info("""
            **Lecture des corrélations :**
            Une corrélation négative forte (r proche de -1) suggère que l'augmentation
            du taux d'équipement est associée à la baisse de la mortalité.
            ⚠️ La corrélation ne prouve pas la causalité — d'autres facteurs coévoluent
            (radars, vitesse limite, comportements).
            """)

        # ── SUB-TAB 3 : ANALYSE MULTIVARIÉE ───────────────────
        with subtab3:
            st.markdown("### Analyse multivariée 2005–2024")

            # Heatmap corrélations
            st.markdown("#### Matrice de corrélation")
            cols_corr = ["tues", "accidents", "radars_fixes", "recettes_radars",
                         "ESP", "Freinage urgence", "ISA", "age_parc"]
            df_mat = df[[c for c in cols_corr if c in df.columns]].dropna()
            corr_matrix = df_mat.corr()

            fig_hm = px.imshow(
                corr_matrix.round(2),
                text_auto=True,
                color_continuous_scale="RdBu_r",
                zmin=-1, zmax=1,
                title="Matrice de corrélation (Pearson)",
                aspect="auto"
            )
            fig_hm.update_layout(height=400)
            st.plotly_chart(fig_hm, use_container_width=True)

            st.markdown("""
            > **Lecture :**
            > - Cases **bleues** (valeur proche de -1) : relation inverse forte
            >   (ex. ESP ↑ → tués ↓)
            > - Cases **rouges** (proche de +1) : relation directe
            >   (ex. âge parc ↑ → tués ↑ car parc vieillissant = moins d'ADAS)
            """)

            # Graphe normalisé multi-indicateurs
            st.markdown("#### Évolution normalisée (base 100 en 2005)")
            df_norm = df[["annee","tues","accidents","radars_fixes",
                          "ESP","Freinage urgence","ISA"]].copy()
            base = df_norm[df_norm["annee"]==2005].iloc[0]
            for col in ["tues","accidents","radars_fixes","ESP","Freinage urgence","ISA"]:
                if base[col] and base[col] != 0:
                    df_norm[col] = df_norm[col] / base[col] * 100
                else:
                    df_norm[col] = np.nan

            df_melt = df_norm.melt(id_vars="annee",
                                   value_vars=["tues","accidents","radars_fixes",
                                               "ESP","Freinage urgence"],
                                   var_name="Indicateur", value_name="Indice")
            rename_map = {"tues":"Tués","accidents":"Accidents",
                          "radars_fixes":"Radars fixes",
                          "ESP":"Équipement ESP","Freinage urgence":"Freinage urgence"}
            df_melt["Indicateur"] = df_melt["Indicateur"].map(rename_map)

            fig_norm = px.line(df_melt, x="annee", y="Indice",
                               color="Indicateur", markers=True,
                               labels={"Indice":"Indice (2005=100)","annee":"Année"},
                               color_discrete_map={
                                   "Tués": C_RED,
                                   "Accidents": C_BLUE,
                                   "Radars fixes": C_ORANGE,
                                   "Équipement ESP": C_GREEN,
                                   "Freinage urgence": C_PURPLE,
                               })
            fig_norm.add_hline(y=100, line_dash="dot", line_color="gray",
                               annotation_text="Base 2005")
            fig_norm.update_layout(height=380, plot_bgcolor="white",
                                   legend=dict(orientation="h"),
                                   xaxis=dict(tickmode="linear", dtick=1))
            st.plotly_chart(fig_norm, use_container_width=True)

            # Variation annuelle
            st.markdown("#### Variations annuelles (Δ%)")
            df_var = df[["annee","var_tues","var_accidents","var_radars_fixes"]].copy()
            df_var.columns = ["Année","Δ% Tués","Δ% Accidents","Δ% Radars"]
            df_var = df_var.dropna()
            df_var_melt = df_var.melt(id_vars="Année",
                                      var_name="Indicateur", value_name="Variation")
            fig_var = px.bar(df_var_melt, x="Année", y="Variation",
                             color="Indicateur", barmode="group",
                             labels={"Variation":"Δ%"},
                             color_discrete_map={"Δ% Tués": C_RED,
                                                 "Δ% Accidents": C_BLUE,
                                                 "Δ% Radars": C_ORANGE})
            fig_var.add_hline(y=0, line_color="gray")
            fig_var.update_layout(height=320, plot_bgcolor="white",
                                  xaxis=dict(tickmode="linear", dtick=1))
            st.plotly_chart(fig_var, use_container_width=True)

        # ── SUB-TAB 4 : TIMELINE ──────────────────────────────
        with subtab4:
            st.markdown("### Timeline des mesures de sécurité routière")

            categories = st.multiselect(
                "Filtrer par type",
                ["Radars / contrôles", "Réglementations",
                 "Technologies de sécurité", "Événements exceptionnels"],
                default=["Radars / contrôles", "Réglementations",
                         "Technologies de sécurité"]
            )
            type_map2 = {
                "Radars / contrôles": "radar",
                "Réglementations": "reglementation",
                "Technologies de sécurité": "securite_active",
                "Événements exceptionnels": "evenement",
            }
            active_types = [type_map2[c] for c in categories]
            ms_f = [m for m in SAFETY_MILESTONES if m["type"] in active_types]

            colors_map = {"radar": C_ORANGE, "reglementation": C_BLUE,
                          "securite_active": C_GREEN, "evenement": C_RED}
            symbols_map = {"radar": "diamond", "reglementation": "square",
                           "securite_active": "circle", "evenement": "star"}

            fig_tl = go.Figure()
            fig_tl.add_trace(go.Scatter(
                x=[2003, 2025], y=[0, 0],
                mode="lines", line=dict(color="#CBD5E0", width=2),
                showlegend=False
            ))

            # Grouper par type pour la légende
            for mtype, label in [("radar","🟠 Radars"),("reglementation","🔵 Réglementations"),
                                  ("securite_active","🟢 Technologies"),("evenement","🔴 Événements")]:
                if mtype not in active_types:
                    continue
                sub = [m for m in ms_f if m["type"] == mtype]
                if not sub:
                    continue
                years_m = [m["annee"] for m in sub]
                labels_m = [m["label"] for m in sub]
                fig_tl.add_trace(go.Scatter(
                    x=years_m, y=[0] * len(sub),
                    mode="markers+text",
                    marker=dict(size=16, color=colors_map[mtype],
                                symbol=symbols_map[mtype]),
                    text=labels_m, textposition="top center",
                    textfont=dict(size=9, color=colors_map[mtype]),
                    name=label,
                    hovertemplate="%{text}<br>Année : %{x}<extra></extra>"
                ))

            fig_tl.update_layout(
                height=380, plot_bgcolor="white",
                yaxis=dict(showticklabels=False, showgrid=False,
                           zeroline=False, range=[-0.5, 2.5]),
                xaxis=dict(tickmode="linear", dtick=1, range=[2002, 2026]),
                legend=dict(orientation="h", yanchor="top", y=-0.05),
            )
            st.plotly_chart(fig_tl, use_container_width=True)

            # Tableau détaillé
            st.markdown("#### Détail des mesures")
            df_ms = pd.DataFrame(ms_f)
            df_ms["Type"] = df_ms["type"].map({
                "radar": "🟠 Radars",
                "reglementation": "🔵 Réglementation",
                "securite_active": "🟢 Sécurité active",
                "evenement": "🔴 Événement",
            })
            df_ms = df_ms[["annee","Type","label"]].sort_values("annee")
            df_ms.columns = ["Année", "Catégorie", "Mesure / Événement"]
            st.dataframe(df_ms.reset_index(drop=True),
                         use_container_width=True, hide_index=True)

            # Tableau normes véhicules
            st.markdown("---")
            st.markdown("#### 🚗 Normes Euro NCAP & obligations techniques")
            ncap = pd.DataFrame([
                {"Année": 2003, "Norme": "ABS obligatoire VN Europe",
                 "Impact estimé": "-6% accidents graves"},
                {"Année": 2006, "Norme": "ESP obligatoire VN (Dir. 2007/46/CE)",
                 "Impact estimé": "–25% sorties de route sur chaussée mouillée"},
                {"Année": 2011, "Norme": "ESP généralisé à tout le parc vendu",
                 "Impact estimé": "–4 000 décès/an en Europe (estimé ETSC)"},
                {"Année": 2014, "Norme": "eCall homologation VN (prévol. 2018)",
                 "Impact estimé": "–4% décès (alerte secours accélérée)"},
                {"Année": 2018, "Norme": "Euro NCAP 2025 : 5★ = AEB piétons obligatoire",
                 "Impact estimé": "–20% collisions piétons (projection)"},
                {"Année": 2022, "Norme": "GSR2 : ISA, détect. somnolence, boîte noire",
                 "Impact estimé": "–30% décès vitesse excessive (ETSC, horizon 2030)"},
                {"Année": 2024, "Norme": "eCall universel tous VN homologués",
                 "Impact estimé": "Couverture totale parc neuf"},
            ])
            st.dataframe(ncap, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Erreur corrélations : {e}")
        import traceback; st.code(traceback.format_exc())


# ══════════════════════════════════════════════════════════════
# ONGLET 6 — DONNÉES BRUTES
# ══════════════════════════════════════════════════════════════
elif onglet == "📋 Données brutes":
    st.title("📋 Accès aux données brutes")

    st.markdown("""
    ### Structure des fichiers

    | Fichier | Période | Contenu |
    |---------|---------|---------|
    | `caract{année}.csv` | 2018-2024 | Date, heure, conditions, localisation |
    | `lieux{année}.csv` | 2018-2024 | Type route, profil, infrastructure |
    | `usagers{année}.csv` | 2018-2024 | Gravité, âge, sexe, équipement |
    | `vehicules{année}.csv` | 2018-2024 | Catégorie, manœuvre, choc |
    | `{année}.csv` | 2009-2024 | Résumé véhicules impliqués |
    """)

    year_sel = st.selectbox("Année BAAC (2018-2024)", list(range(2024, 2017, -1)))
    table_sel = st.selectbox("Table", ["caract", "usagers", "vehicules", "lieux"])

    if st.button("📥 Charger"):
        try:
            d = load_baac_year(year_sel, data_dir)
            df_show = d[table_sel]
            st.success(f"✓ {len(df_show):,} lignes — {len(df_show.columns)} colonnes")
            st.dataframe(df_show.head(500), use_container_width=True)
            csv = df_show.to_csv(index=False, sep=";").encode("utf-8")
            st.download_button(f"💾 Télécharger {table_sel}{year_sel}.csv",
                               csv, f"{table_sel}{year_sel}_export.csv", "text/csv")
        except Exception as e:
            st.error(f"Erreur : {e}")

    st.markdown("---")
    st.markdown("### 📥 Données à intégrer pour enrichir les corrélations")
    st.info("""
    **Données déjà intégrées (estimations) :**
    - Nombre de radars fixes et mobiles 2003-2024
    - Taux d'équipement ADAS (ABS, ESP, airbag, freinage urgence, ISA)
    - Âge moyen du parc automobile (CCFA)

    **Prochaines intégrations (à télécharger et déposer dans le dossier data) :**

    | Fichier attendu | Source | Contenu |
    |-----------------|--------|---------|
    | `radars_detail.csv` | ANTAI | Radars par département, type, recettes |
    | `normes_securite.csv` | Euro NCAP | Scores par modèle et millésime |
    | `parc_auto.csv` | CCFA/ADEME | Parc en circulation par type, âge, motorisation |
    | `infractions.csv` | ANTAI | Nombre de PV par type d'infraction et année |

    → Une fois ces fichiers présents, le dashboard les intégrera automatiquement.
    """)

    st.markdown("### 🔗 Sources de téléchargement")
    st.markdown("""
    - 📂 [BAAC – data.gouv.fr](https://www.data.gouv.fr/fr/datasets/bases-de-donnees-annuelles-des-accidents-corporels-de-la-circulation-routiere-annees-de-2005-a-2023/)
    - 📊 [ONISR – Bilan de l'accidentalité](https://www.securite-routiere.gouv.fr/les-medias/la-mediatheque/bilan-de-laccidentalite)
    - 📡 [ANTAI – Données ouvertes](https://www.antai.gouv.fr/ressources)
    - 🚗 [Euro NCAP – Résultats](https://www.euroncap.com/fr/resultats-des-tests/)
    - 🔧 [ADEME – Données parc auto](https://data.ademe.fr/)
    """)
