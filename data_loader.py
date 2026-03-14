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
    # annee: (accidents, tues_30j, blesses_hospitalises, blesses_legers)
    # 2005-2017 : bilans ONISR publies
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
    # 2018-2024 : calcules depuis BAAC — fallback quand fichiers non disponibles
    2018: (57783, 3392, 22169, 50360),
    2019: (58840, 3498, 20858, 53307),
    2020: (47744, 2780, 16775, 42473),
    2021: (56518, 3219, 19093, 51733),
    2022: (55302, 3550, 19260, 49981),
    2023: (54822, 3398, 19271, 49603),
    2024: (54402, 3432, 19126, 49709),
}

# ════════════════════════════════════════════════════════════════
# DONNÉES RADARS — chargées depuis radars_france.csv
# Sources officielles : ANTAI, Cour des Comptes, fiches-auto.fr
# ════════════════════════════════════════════════════════════════
# Fallback si le fichier n'est pas trouvé
RADAR_DATA = {
    2003: (48,   0,    4.8),
    2004: (228,  165,  30),
    2005: (689,  313,  68),
    2006: (822,  457,  96),
    2007: (1137, 721,  147),
    2008: (1473, 827,  247),
    2009: (1661, 932,  400),
    2010: (1823, 933,  477),
    2011: (2100, 933,  641),
    2012: (2345, 929,  730),
    2013: (2473, 867,  579),
    2014: (2511, 841,  740),
    2015: (2541, 787,  789),
    2016: (2525, 884,  920),
    2017: (2509, 884,  1014),
    2018: (2499, 904,  864),
    2019: (2137, 950,  760),
    2020: (2326, 905,  743),
    2021: (2393, 973,  859),
    2022: (2482, 999,  928),
    2023: (2541, 999,  965),
    2024: (2600, 999,  889),
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
    # codes officiels BAAC -> libellé complet
    0:  "Non renseigné",
    1:  "Vélo",
    2:  "Cyclomoteur ≤50cm³",
    3:  "Voiturette / tricycle motorisé",
    7:  "Voiture (VP)",
    10: "Utilitaire (VUL)",
    13: "PL >3.5T",
    14: "PL articulé >3.5T",
    15: "Tracteur routier seul",
    16: "Tracteur routier + semi-rem.",
    17: "Tramway",
    20: "Engin spécial",
    21: "Tracteur agricole",
    30: "Scooter ≤50cm³",
    31: "Moto 50-125cm³",
    32: "Moto >125cm³",
    33: "Moto >125cm³ (side-car)",
    34: "Quad lourd >50cm³",
    35: "Quad léger ≤50cm³",
    36: "Autobus",
    37: "Autocar",
    38: "Train / TER",
    39: "Tramway (autre)",
    40: "Trottinette électrique",
    41: "EDP non motorisé",
    42: "Vélo à assistance électrique (VAE)",
    43: "EDPM (autres engins motorisés personnels)",
    50: "EDP (toutes catégories)",
    60: "Piéton",
    80: "VAE (autre)",
    99: "Autre véhicule",
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
# DONNÉES ANNUELLES EMBARQUÉES (ex-fichiers 2009–2024.csv)
# Extraites une fois des fichiers source, intégrées ici pour éviter
# tout fichier CSV volumineux dans le repo GitHub.
# Source : data.gouv.fr — résumés annuels accidents corporels
# ════════════════════════════════════════════════════════════════
SUMMARY_ANNUELS = {
    2009: {"accidents":74512,"acc_mortels":4169,"acc_graves":28469,"acc_legers":41874,"vt":59007,"cyclo":13859,"moto_lourde":11089,"moto_legere":6321,"vu":6060,"pl":3324,"tc":1262,"autres":1630},
    2010: {"accidents":69444,"acc_mortels":3940,"acc_graves":25988,"acc_legers":39516,"vt":55188,"cyclo":12022,"moto_lourde":10293,"moto_legere":5841,"vu":5850,"pl":3361,"tc":1096,"autres":1584},
    2011: {"accidents":67031,"acc_mortels":3837,"acc_graves":25588,"acc_legers":37606,"vt":53064,"cyclo":10911,"moto_lourde":10708,"moto_legere":5743,"vu":5764,"pl":3218,"tc":1139,"autres":1471},
    2012: {"accidents":62345,"acc_mortels":3612,"acc_graves":23297,"acc_legers":35436,"vt":49274,"cyclo":9652,"moto_lourde":9729,"moto_legere":5322,"vu":5520,"pl":3007,"tc":1086,"autres":1426},
    2013: {"accidents":58494,"acc_mortels":3209,"acc_graves":22528,"acc_legers":32757,"vt":46255,"cyclo":8245,"moto_lourde":9344,"moto_legere":4790,"vu":5398,"pl":2843,"tc":1013,"autres":1427},
    2014: {"accidents":59737,"acc_mortels":3358,"acc_graves":22678,"acc_legers":33701,"vt":47265,"cyclo":8351,"moto_lourde":9800,"moto_legere":4786,"vu":5372,"pl":2813,"tc":943,"autres":1563},
    2015: {"accidents":58465,"acc_mortels":3344,"acc_graves":22937,"acc_legers":32184,"vt":46625,"cyclo":7804,"moto_lourde":9699,"moto_legere":4420,"vu":5260,"pl":2785,"tc":976,"autres":1324},
    2016: {"accidents":59186,"acc_mortels":3437,"acc_graves":23214,"acc_legers":32535,"vt":47791,"cyclo":7299,"moto_lourde":9668,"moto_legere":4442,"vu":5304,"pl":2861,"tc":963,"autres":1235},
    2017: {"accidents":60429,"acc_mortels":3379,"acc_graves":24089,"acc_legers":32961,"vt":49029,"cyclo":6422,"moto_lourde":10807,"moto_legere":4455,"vu":4856,"pl":2892,"tc":948,"autres":1363},
    2018: {"accidents":57531,"acc_mortels":3225,"acc_graves":19203,"acc_legers":35103,"vt":45086,"cyclo":6692,"moto_lourde":9855,"moto_legere":4463,"vu":5847,"pl":2882,"tc":853,"autres":1653},
    2019: {"accidents":57787,"acc_mortels":3226,"acc_graves":17647,"acc_legers":36914,"vt":44863,"cyclo":6597,"moto_lourde":9720,"moto_legere":4270,"vu":5942,"pl":2811,"tc":880,"autres":1865},
    2020: {"accidents":46403,"acc_mortels":2542,"acc_graves":14307,"acc_legers":29554,"vt":35632,"cyclo":5777,"moto_lourde":7406,"moto_legere":3445,"vu":4949,"pl":2161,"tc":612,"autres":1474},
    2021: {"accidents":54917,"acc_mortels":2941,"acc_graves":16167,"acc_legers":35809,"vt":42679,"cyclo":7049,"moto_lourde":8768,"moto_legere":3862,"vu":6348,"pl":2592,"tc":735,"autres":1630},
    2022: {"accidents":53607,"acc_mortels":3550,"acc_graves":19260,"acc_legers":30797,"vt":41720,"cyclo":5937,"moto_lourde":8654,"moto_legere":3709,"vu":6342,"pl":2513,"tc":808,"autres":1524},
    2023: {"accidents":54822,"acc_mortels":3398,"acc_graves":19271,"acc_legers":32153,"vt":41375,"cyclo":5427,"moto_lourde":8948,"moto_legere":3568,"vu":6431,"pl":2484,"tc":827,"autres":1492},
    2024: {"accidents":54402,"acc_mortels":3432,"acc_graves":19126,"acc_legers":31951,"vt":40718,"cyclo":5047,"moto_lourde":8875,"moto_legere":3301,"vu":6620,"pl":2361,"tc":931,"autres":1391},
}


def build_summary_stats_2010_2017(data_dir="."):
    """DataFrame des stats de gravité 2010–2017 depuis les données embarquées."""
    rows = []
    for year in range(2010, 2018):
        d = SUMMARY_ANNUELS.get(year, {})
        if d:
            rows.append({
                "annee": year,
                "accidents": d["accidents"],
                "acc_mortels": d["acc_mortels"],
                "acc_graves": d["acc_graves"],
                "acc_legers": d["acc_legers"],
            })
    return pd.DataFrame(rows)


# ════════════════════════════════════════════════════════════════
# TENDANCE VÉHICULES IMPLIQUÉS 2009-2024
# ════════════════════════════════════════════════════════════════
def build_vehicle_trend_2010_2024(data_dir="."):
    """
    Série temporelle véhicules impliqués par catégorie harmonisée.
    2009-2017 : données embarquées (SUMMARY_ANNUELS).
    2018-2024 : depuis les fichiers BAAC si disponibles,
                sinon depuis les données embarquées.
    """
    rows = []

    # Correspondance catv -> groupe harmonisé (pour BAAC 2018-2024)
    CATV_GROUPES = {
        7:  "Voiture (VP)",
        10: "Utilitaire (VUL)",
        13: "PL / Camion", 14: "PL / Camion", 15: "PL / Camion", 16: "PL / Camion",
        1:  "Vélo",
        42: "VAE (vélo assisté)", 80: "VAE (vélo assisté)",
        2:  "Cyclomoteur ≤50cm³", 30: "Cyclomoteur ≤50cm³",
        31: "Moto 50-125cm³",
        32: "Moto >125cm³", 33: "Moto >125cm³",
        34: "Quad", 35: "Quad",
        36: "Bus / Car", 37: "Bus / Car",
        40: "Trottinette / EDP motorisé", 43: "Trottinette / EDP motorisé",
        50: "Trottinette / EDP motorisé",
        41: "EDP non motorisé",
        17: "Tramway / Train", 38: "Tramway / Train", 39: "Tramway / Train",
        3:  "Voiturette",
        20: "Engin spécial", 21: "Engin spécial",
        60: "Piéton",
    }

    # ── 2009-2017 : données embarquées ─────────────────────────
    # Note : les résumés annuels 2009-2017 ne distinguent pas vélo / cyclomoteur.
    # "cyclo" = cyclomoteur uniquement, vélos inclus dans "autres".
    cat_map_old = {
        "vt":          "Voiture (VP)",
        "cyclo":        "Cyclomoteur ≤50cm³",
        "moto_lourde":  "Moto >125cm³",
        "moto_legere":  "Moto 50-125cm³",
        "vu":           "Utilitaire (VUL)",
        "pl":           "PL / Camion",
        "tc":           "Bus / Car",
        "autres":       "Autre",
    }
    for year in range(2009, 2018):
        d = SUMMARY_ANNUELS.get(year, {})
        for key, label in cat_map_old.items():
            if key in d and d[key] > 0:
                rows.append({"annee": year, "categorie": label, "nb": d[key]})

    # ── 2018-2024 : BAAC si dispo (données complètes + piétons) ──
    for year in range(2018, 2025):
        v_path = os.path.join(data_dir, f"vehicules{year}.csv")
        u_sep = "," if year == 2018 else ";"
        u_path = os.path.join(data_dir, f"usagers{year}.csv")
        if os.path.exists(v_path):
            try:
                df_v = pd.read_csv(v_path, sep=u_sep, encoding="utf-8", low_memory=False)
                df_v["catv"] = pd.to_numeric(df_v["catv"], errors="coerce")
                df_v["cat_label"] = df_v["catv"].map(CATV_GROUPES).fillna("Autre")
                for cat, n in df_v.groupby("cat_label")["Num_Acc"].count().items():
                    rows.append({"annee": year, "categorie": cat, "nb": int(n)})
                # Piétons depuis fichier usagers (catu=3)
                if os.path.exists(u_path):
                    df_u = pd.read_csv(u_path, sep=u_sep, encoding="utf-8", low_memory=False)
                    n_pietons = int((df_u["catu"] == 3).sum())
                    if n_pietons > 0:
                        rows.append({"annee": year, "categorie": "Piéton", "nb": n_pietons})
                continue
            except Exception as e:
                print(f"[WARN] véhicules BAAC {year}: {e}")
        # Fallback données embarquées
        d = SUMMARY_ANNUELS.get(year, {})
        for key, label in cat_map_old.items():
            if key in d and d[key] > 0:
                rows.append({"annee": year, "categorie": label, "nb": d[key]})

    df = pd.DataFrame(rows)
    return df.groupby(["annee", "categorie"])["nb"].sum().reset_index()

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
def load_radars_csv(data_dir="."):
    """
    Charge radars_france.csv si disponible, sinon fallback sur RADAR_DATA.
    Retourne un DataFrame avec les colonnes radars.
    """
    fpath = os.path.join(data_dir, "radars_france.csv")
    if os.path.exists(fpath):
        df = pd.read_csv(fpath, sep=";", encoding="utf-8")
        df = df.rename(columns={
            "radars_mobiles_hibou": "radars_mobiles",
            "recettes_amendes_ME": "recettes_radars",
        })
        return df
    # Fallback
    return pd.DataFrame([
        {"annee": y, "radars_fixes": v[0], "radars_mobiles": v[1],
         "recettes_radars": v[2], "total_radars": v[0] + v[1]}
        for y, v in RADAR_DATA.items()
    ])


def load_normes_csv(data_dir="."):
    """
    Charge normes_securite_vehicules.csv si disponible.
    Retourne un DataFrame des normes.
    """
    fpath = os.path.join(data_dir, "normes_securite_vehicules.csv")
    if os.path.exists(fpath):
        return pd.read_csv(fpath, sep=";", encoding="utf-8")
    return pd.DataFrame()


def build_correlation_dataset(data_dir="."):
    """
    DataFrame 2005-2024 intégrant accidents, tués, radars officiels,
    ADAS estimés, âge parc. Prêt pour analyses de corrélation.
    """
    df = build_historical_df(data_dir=data_dir)

    # Radars : depuis CSV officiel en priorité
    df_rad = load_radars_csv(data_dir)
    # Garder uniquement colonnes utiles
    rad_cols = ["annee", "radars_fixes", "total_radars",
                "recettes_radars", "pv_emis_millions"]
    rad_cols = [c for c in rad_cols if c in df_rad.columns]
    df = df.merge(df_rad[rad_cols], on="annee", how="left")

    # ADAS : estimations (pas encore de CSV officiel)
    df_adas = pd.DataFrame([
        {"annee": y, **vals} for y, vals in ADAS_DATA.items()
    ])
    df = df.merge(df_adas, on="annee", how="left")

    # Variations annuelles
    for col in ["tues", "accidents", "radars_fixes", "total_radars"]:
        if col in df.columns:
            df[f"var_{col}"] = df[col].pct_change() * 100

    return df


# ════════════════════════════════════════════════════════════════
# TENDANCE VÉHICULES IMPLIQUÉS 2010-2024
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
