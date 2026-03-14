"""
data_loader.py  –  v2.0
=======================
Chargement et normalisation des données d'accidents routiers français.
Couvre :
  • BAAC complet 2018–2024 (4 tables par année)
  • Résumés annuels 2010–2017 (fichiers {année}.csv)
  • Statistiques ONISR publiées 2005–2017
"""

import pandas as pd
import numpy as np
import os

# ════════════════════════════════════════════════════════════════
# STATISTIQUES ONISR OFFICIELLES
# Sources : bilans annuels ONISR / securite-routiere.gouv.fr
# ════════════════════════════════════════════════════════════════
ONISR_STATS = {
    2005: (85371, 5318, 41070, None),
    2006: (80330, 4709, 38746, None),
    2007: (80172, 4620, 37794, None),
    2008: (74487, 4275, 36199, None),
    2009: (74512, 4273, 37309, None),
    2010: (69444, 3992, 34882, None),
    2011: (67031, 3963, 33571, None),
    2012: (62345, 3645, 31207, None),
    2013: (58494, 3268, 28668, None),
    2014: (59737, 3384, 27965, None),
    2015: (58465, 3461, 27187, None),
    2016: (59186, 3477, 26958, None),
    2017: (60429, 3448, 26814, None),
}

# ════════════════════════════════════════════════════════════════
# DONNÉES RADARS
# Sources : ANTAI, ONISR, presse spécialisée
# ════════════════════════════════════════════════════════════════
RADAR_DATA = {
    # annee: (radars_fixes, radars_mobiles, recettes_M€)
    2003: (0,    0,    0),
    2004: (1000, 0,    30),
    2005: (1500, 0,    68),
    2006: (1780, 0,    96),
    2007: (2050, 0,    120),
    2008: (2445, 0,    160),
    2009: (2795, 100,  200),
    2010: (3182, 250,  270),
    2011: (3547, 430,  350),
    2012: (3800, 550,  500),
    2013: (4080, 650,  590),
    2014: (4200, 700,  600),
    2015: (4450, 780,  640),
    2016: (4600, 850,  700),
    2017: (4700, 900,  720),
    2018: (4820, 950,  736),
    2019: (4900, 980,  760),
    2020: (4950, 1000, 620),
    2021: (5100, 1050, 680),
    2022: (5200, 1100, 740),
    2023: (5250, 1150, 760),
    2024: (5300, 1200, 780),
}

# ════════════════════════════════════════════════════════════════
# ÂGE MOYEN DU PARC AUTOMOBILE (Source : CCFA)
# ════════════════════════════════════════════════════════════════
AGE_PARC = {
    2005: 7.1, 2006: 7.2, 2007: 7.3, 2008: 7.3,
    2009: 7.4, 2010: 7.5, 2011: 7.7, 2012: 8.0,
    2013: 8.2, 2014: 8.3, 2015: 8.4, 2016: 8.5,
    2017: 8.7, 2018: 8.9, 2019: 9.1, 2020: 9.4,
    2021: 9.7, 2022: 9.9, 2023: 10.1, 2024: 10.3,
}

# ════════════════════════════════════════════════════════════════
# TAUX D'ÉQUIPEMENT ADAS (% véhicules neufs vendus)
# Sources : CLEPA, ACEA, estimations
# ════════════════════════════════════════════════════════════════
ADAS_DATA = {
    2005: {"ABS": 70,  "ESP": 25,  "Airbag avant": 85,  "Freinage urgence": 2,  "ISA": 0},
    2006: {"ABS": 75,  "ESP": 35,  "Airbag avant": 88,  "Freinage urgence": 3,  "ISA": 0},
    2007: {"ABS": 80,  "ESP": 45,  "Airbag avant": 90,  "Freinage urgence": 5,  "ISA": 0},
    2008: {"ABS": 85,  "ESP": 55,  "Airbag avant": 92,  "Freinage urgence": 8,  "ISA": 0},
    2009: {"ABS": 88,  "ESP": 62,  "Airbag avant": 93,  "Freinage urgence": 10, "ISA": 0},
    2010: {"ABS": 90,  "ESP": 68,  "Airbag avant": 94,  "Freinage urgence": 12, "ISA": 0},
    2011: {"ABS": 93,  "ESP": 75,  "Airbag avant": 95,  "Freinage urgence": 16, "ISA": 0},
    2012: {"ABS": 95,  "ESP": 83,  "Airbag avant": 96,  "Freinage urgence": 20, "ISA": 0},
    2013: {"ABS": 97,  "ESP": 90,  "Airbag avant": 97,  "Freinage urgence": 25, "ISA": 0},
    2014: {"ABS": 98,  "ESP": 95,  "Airbag avant": 97,  "Freinage urgence": 30, "ISA": 0},
    2015: {"ABS": 99,  "ESP": 97,  "Airbag avant": 98,  "Freinage urgence": 35, "ISA": 0},
    2016: {"ABS": 100, "ESP": 99,  "Airbag avant": 98,  "Freinage urgence": 40, "ISA": 1},
    2017: {"ABS": 100, "ESP": 100, "Airbag avant": 99,  "Freinage urgence": 47, "ISA": 2},
    2018: {"ABS": 100, "ESP": 100, "Airbag avant": 99,  "Freinage urgence": 55, "ISA": 4},
    2019: {"ABS": 100, "ESP": 100, "Airbag avant": 99,  "Freinage urgence": 62, "ISA": 6},
    2020: {"ABS": 100, "ESP": 100, "Airbag avant": 99,  "Freinage urgence": 68, "ISA": 9},
    2021: {"ABS": 100, "ESP": 100, "Airbag avant": 100, "Freinage urgence": 74, "ISA": 13},
    2022: {"ABS": 100, "ESP": 100, "Airbag avant": 100, "Freinage urgence": 80, "ISA": 20},
    2023: {"ABS": 100, "ESP": 100, "Airbag avant": 100, "Freinage urgence": 85, "ISA": 32},
    2024: {"ABS": 100, "ESP": 100, "Airbag avant": 100, "Freinage urgence": 90, "ISA": 45},
}

# ════════════════════════════════════════════════════════════════
# JALONS RÉGLEMENTAIRES & TECHNOLOGIQUES
# ════════════════════════════════════════════════════════════════
SAFETY_MILESTONES = [
    {"annee": 2003, "label": "1ers radars fixes (1 000)", "type": "radar"},
    {"annee": 2004, "label": "Ceinture ARR obligatoire", "type": "reglementation"},
    {"annee": 2006, "label": "ESP obligatoire VN Europe", "type": "securite_active"},
    {"annee": 2008, "label": "ABS obligatoire motos >125cc", "type": "securite_active"},
    {"annee": 2010, "label": "3 000 radars fixes dépassés", "type": "radar"},
    {"annee": 2011, "label": "ESP généralisé → 4 000 vies/an EU", "type": "securite_active"},
    {"annee": 2012, "label": "Alcootest obligatoire auto", "type": "reglementation"},
    {"annee": 2014, "label": "eCall homologation VN", "type": "securite_active"},
    {"annee": 2018, "label": "80 km/h routes bidirectionnelles", "type": "reglementation"},
    {"annee": 2019, "label": "EDP réglementés", "type": "reglementation"},
    {"annee": 2020, "label": "COVID-19 – Confinements", "type": "evenement"},
    {"annee": 2022, "label": "GSR2 : ISA + détect. somnolence VN", "type": "securite_active"},
    {"annee": 2024, "label": "eCall universel tous VN", "type": "securite_active"},
]

# ════════════════════════════════════════════════════════════════
# CORRESPONDANCES LIBELLÉS
# ════════════════════════════════════════════════════════════════
CATV_LABELS = {
    1: "Bicyclette", 2: "Cyclomoteur <50cm³", 7: "Voiture (VP)",
    10: "Utilitaire (VUL)", 13: "PL >3.5T", 14: "PL articulé",
    15: "Bus/Car", 17: "Tramway", 30: "Scooter <50cm³",
    31: "Moto 50-125cm³", 32: "Moto >125cm³", 33: "Moto lourde (side)",
    34: "Quad lourd", 35: "Quad léger", 40: "EDP motorisé",
    41: "EDP non motorisé", 42: "VAE", 50: "EDP", 80: "VAE (assisté)",
    99: "Autre",
}
GRAV_LABELS = {1: "Indemne", 2: "Tué", 3: "Hospitalisé", 4: "Blessé léger"}
LUM_LABELS  = {1: "Plein jour", 2: "Crépuscule/Aube", 3: "Nuit sans éclairage",
               4: "Nuit sans éclairage allumé", 5: "Nuit éclairage allumé"}
ATM_LABELS  = {-1: "Non renseigné", 1: "Normale", 2: "Pluie légère",
               3: "Pluie forte", 4: "Neige/Grêle", 5: "Brouillard",
               6: "Vent/Tempête", 7: "Éblouissement", 8: "Couvert", 9: "Autre"}
COL_LABELS  = {-1: "Non renseigné", 1: "Frontale", 2: "Arrière", 3: "Côté",
               4: "3 véhicules+", 5: "Autre", 6: "Sans collision", 7: "Piéton"}
CATR_LABELS = {1: "Autoroute", 2: "Route nationale", 3: "Route dép.",
               4: "Voie communale", 5: "Hors réseau public",
               6: "Parking", 7: "Métropole urbaine", 9: "Autre"}


# ════════════════════════════════════════════════════════════════
# CHARGEMENT BAAC 2018-2024
# ════════════════════════════════════════════════════════════════
def _get_caract_file(year, data_dir="."):
    mapping = {
        2018: ("caracteristiques2018.csv", "iso-8859-1", ","),
        2019: ("caracteristiques2019.csv", "utf-8", ";"),
        2020: ("caracteristiques2020.csv", "utf-8", ";"),
        2021: ("carcteristiques2021.csv",  "utf-8", ";"),
        2022: ("carcteristiques2022.csv",  "utf-8", ";"),
        2023: ("caract2023.csv",           "utf-8", ";"),
        2024: ("caract2024.csv",           "utf-8", ";"),
    }
    fname, enc, sep = mapping[year]
    return os.path.join(data_dir, fname), enc, sep


def load_baac_year(year, data_dir="."):
    """Charge les 4 tables BAAC pour une année (2018-2024)."""
    fpath, enc, sep = _get_caract_file(year, data_dir)
    df_c = pd.read_csv(fpath, encoding=enc, sep=sep, low_memory=False)
    df_c = df_c.rename(columns={"Accident_Id": "Num_Acc"})
    df_c["annee"] = year

    u_sep = "," if year == 2018 else ";"
    df_u = pd.read_csv(os.path.join(data_dir, f"usagers{year}.csv"),
                       sep=u_sep, encoding="utf-8", low_memory=False)

    v_sep = "," if year == 2018 else ";"
    df_v = pd.read_csv(os.path.join(data_dir, f"vehicules{year}.csv"),
                       sep=v_sep, encoding="utf-8", low_memory=False)

    l_sep = "," if year == 2018 else ";"
    df_l = pd.read_csv(os.path.join(data_dir, f"lieux{year}.csv"),
                       sep=l_sep, encoding="utf-8", low_memory=False)

    return {"caract": df_c, "usagers": df_u, "vehicules": df_v, "lieux": df_l}


def load_full_baac(years=range(2018, 2025), data_dir="."):
    """Concatène les BAAC pour plusieurs années."""
    caracts, usagers, vehicules, lieux_list = [], [], [], []
    for y in years:
        try:
            d = load_baac_year(y, data_dir)
            for key, df in d.items():
                df["annee"] = y
            caracts.append(d["caract"])
            usagers.append(d["usagers"])
            vehicules.append(d["vehicules"])
            lieux_list.append(d["lieux"])
        except Exception as e:
            print(f"  ✗ BAAC {y}: {e}")
    return (
        pd.concat(caracts, ignore_index=True) if caracts else pd.DataFrame(),
        pd.concat(usagers, ignore_index=True) if usagers else pd.DataFrame(),
        pd.concat(vehicules, ignore_index=True) if vehicules else pd.DataFrame(),
        pd.concat(lieux_list, ignore_index=True) if lieux_list else pd.DataFrame(),
    )


# ════════════════════════════════════════════════════════════════
# EXTRACTION RÉSUMÉS 2010-2017
# ════════════════════════════════════════════════════════════════
def load_summary_year(year, data_dir="."):
    """Charge et analyse un fichier résumé annuel (2010-2017)."""
    f = os.path.join(data_dir, f"{year}.csv")
    df = pd.read_csv(f, sep=";", encoding="utf-8", low_memory=False)
    type_col = next((c for c in df.columns if "Type Accident" in c), None)
    if type_col is None:
        return None
    acc = df.groupby("Id_accident").agg(
        type_acc=(type_col, "first"),
        territoire=("Lieu Admin Actuel - Territoire Nom", "first"),
        age_veh_moy=("Age véhicule", "mean"),
    ).reset_index()
    n_mort  = (acc["type_acc"].str.contains("mortel", case=False, na=False) &
               ~acc["type_acc"].str.contains("non mortel", case=False, na=False)).sum()
    n_grave = acc["type_acc"].str.contains("grave non mortel", case=False, na=False).sum()
    n_leger = acc["type_acc"].str.contains("léger|leger", case=False, na=False).sum()
    cat_counts = df.groupby("Catégorie véhicule")["Id_accident"].nunique().to_dict()
    return {
        "annee": year, "accidents": len(acc),
        "acc_mortels": int(n_mort), "acc_graves": int(n_grave),
        "acc_legers": int(n_leger),
        "age_veh_moy": round(acc["age_veh_moy"].mean(), 1),
        "cat_veh": cat_counts, "source": "Résumé annuel",
    }


def build_summary_stats_2010_2017(data_dir="."):
    """DataFrame des stats détaillées 2010-2017 depuis les résumés."""
    rows = []
    for year in range(2010, 2018):
        d = load_summary_year(year, data_dir)
        if d:
            rows.append(d)
    return pd.DataFrame(rows)


# ════════════════════════════════════════════════════════════════
# KPIs ANNUELS UNIFIÉS
# ════════════════════════════════════════════════════════════════
def build_yearly_kpis(year, data_dir="."):
    """KPIs annuels, quelle que soit la source disponible."""
    if year >= 2018:
        try:
            d = load_baac_year(year, data_dir)
            df_u, df_c = d["usagers"], d["caract"]
            return {
                "annee": year,
                "accidents":     df_c["Num_Acc"].nunique(),
                "tues":          int((df_u["grav"] == 2).sum()),
                "hospitalises":  int((df_u["grav"] == 3).sum()),
                "blesses_legers":int((df_u["grav"] == 4).sum()),
                "age_parc":      AGE_PARC.get(year),
                "source":        "BAAC",
            }
        except Exception as e:
            print(f"[WARN] BAAC {year}: {e}")

    if year in ONISR_STATS:
        acc, tue, hosp, leg = ONISR_STATS[year]
        return {
            "annee": year, "accidents": acc,
            "tues": tue, "hospitalises": hosp,
            "blesses_legers": leg,
            "age_parc": AGE_PARC.get(year),
            "source": "ONISR",
        }
    return None


def build_historical_df(years=range(2005, 2025), data_dir="."):
    """DataFrame historique complet 2005-2024."""
    rows = [build_yearly_kpis(y, data_dir) for y in years]
    df = pd.DataFrame([r for r in rows if r]).sort_values("annee").reset_index(drop=True)
    df["taux_tue_par_acc"] = (df["tues"] / df["accidents"] * 100).round(2)
    base5 = df.loc[df["annee"] == 2005, "tues"].values
    base5a = df.loc[df["annee"] == 2005, "accidents"].values
    if len(base5):
        df["idx_tues"] = (df["tues"] / base5[0] * 100).round(1)
        df["idx_acc"]  = (df["accidents"] / base5a[0] * 100).round(1)
    return df


# ════════════════════════════════════════════════════════════════
# DATASET ENRICHI POUR CORRÉLATIONS
# ════════════════════════════════════════════════════════════════
def build_correlation_dataset(data_dir="."):
    """
    DataFrame 2005-2024 intégrant accidents, tués, radars, ADAS, âge parc.
    Prêt pour analyses de corrélation.
    """
    df = build_historical_df(data_dir=data_dir)

    df_rad = pd.DataFrame([
        {"annee": y, "radars_fixes": v[0], "radars_mobiles": v[1], "recettes_radars": v[2]}
        for y, v in RADAR_DATA.items()
    ])
    df_adas = pd.DataFrame([
        {"annee": y, **vals} for y, vals in ADAS_DATA.items()
    ])
    df = df.merge(df_rad, on="annee", how="left")
    df = df.merge(df_adas, on="annee", how="left")

    for col in ["tues", "accidents", "radars_fixes"]:
        if col in df.columns:
            df[f"var_{col}"] = df[col].pct_change() * 100

    return df


# ════════════════════════════════════════════════════════════════
# TENDANCE VÉHICULES IMPLIQUÉS 2010-2024
# ════════════════════════════════════════════════════════════════
def build_vehicle_trend_2010_2024(data_dir="."):
    """
    Série temporelle véhicules impliqués par catégorie harmonisée,
    couvrant 2010-2017 (résumés) et 2018-2024 (BAAC).
    """
    rows = []
    catv_mapping_old = {
        "VT": "Voiture (VP)", "Cyclo": "Cyclomoteur/Vélo",
        "Moto lourde": "Moto >125cm³", "Moto légère": "Moto 50-125cm³",
        "VU": "Utilitaire (VUL)", "PL": "PL >3.5T",
        "TC": "Bus/Car", "Autres": "Autre",
    }
    for year in range(2010, 2018):
        try:
            f = os.path.join(data_dir, f"{year}.csv")
            df = pd.read_csv(f, sep=";", encoding="utf-8", low_memory=False)
            cat_counts = df.groupby("Catégorie véhicule")["Id_accident"].nunique()
            for cat, n in cat_counts.items():
                rows.append({"annee": year,
                             "categorie": catv_mapping_old.get(cat, cat),
                             "nb": int(n)})
        except Exception as e:
            print(f"[WARN] résumé véhicules {year}: {e}")

    catv_mapping_new = {
        7: "Voiture (VP)", 1: "Cyclomoteur/Vélo", 2: "Cyclomoteur/Vélo",
        32: "Moto >125cm³", 33: "Moto >125cm³",
        31: "Moto 50-125cm³", 30: "Cyclomoteur/Vélo",
        10: "Utilitaire (VUL)", 13: "PL >3.5T", 14: "PL >3.5T",
        15: "Bus/Car", 37: "Bus/Car",
        40: "EDP motorisé", 41: "EDP non motorisé",
        80: "VAE/Vélo", 42: "VAE/Vélo",
    }
    for year in range(2018, 2025):
        try:
            v_sep = "," if year == 2018 else ";"
            df_v = pd.read_csv(os.path.join(data_dir, f"vehicules{year}.csv"),
                               sep=v_sep, encoding="utf-8", low_memory=False)
            df_v["catv"] = pd.to_numeric(df_v["catv"], errors="coerce")
            df_v["cat_label"] = df_v["catv"].map(catv_mapping_new).fillna("Autre")
            cat_counts = df_v.groupby("cat_label")["Num_Acc"].count()
            for cat, n in cat_counts.items():
                rows.append({"annee": year, "categorie": cat, "nb": int(n)})
        except Exception as e:
            print(f"[WARN] véhicules BAAC {year}: {e}")

    df = pd.DataFrame(rows)
    return df.groupby(["annee", "categorie"])["nb"].sum().reset_index()


def get_monthly_trend(df_caract, df_usagers):
    """Tendances mensuelles (BAAC 2018-2024)."""
    df_u_agg = (df_usagers[df_usagers["grav"] == 2]
                .groupby("Num_Acc").size().reset_index(name="tues"))
    df = df_caract[["Num_Acc", "mois", "annee"]].merge(df_u_agg, on="Num_Acc", how="left")
    df["tues"] = df["tues"].fillna(0)
    return (df.groupby(["annee", "mois"])
            .agg(accidents=("Num_Acc", "count"), tues=("tues", "sum"))
            .reset_index()
            .assign(mois=lambda x: x["mois"].astype(int),
                    annee=lambda x: x["annee"].astype(int)))


def get_dept_stats(df_caract, df_usagers):
    """Statistiques par département (BAAC)."""
    df_u_agg = (df_usagers.groupby("Num_Acc")
                .agg(tues=("grav", lambda x: (x == 2).sum()),
                     blesses=("grav", lambda x: (x >= 3).sum()))
                .reset_index())
    df = df_caract[["Num_Acc", "dep", "annee"]].merge(df_u_agg, on="Num_Acc", how="left")
    df["dep"] = df["dep"].astype(str).str.zfill(3)
    return (df.groupby(["annee", "dep"])
            .agg(accidents=("Num_Acc", "count"),
                 tues=("tues", "sum"),
                 blesses=("blesses", "sum"))
            .reset_index())
