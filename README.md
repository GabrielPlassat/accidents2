# Accidentologie Routière en France (2005–2024)

Tableau de bord interactif de l'accidentologie routière française, de 2005 à 2024.
Déployé sur **Streamlit Cloud** — aucune installation requise.

---

## Ce que montre le dashboard

| Onglet | Contenu |
|--------|---------|
| **Vue d'ensemble** | KPIs 2024, évolution depuis 2005, indice de progression |
| **Tendances 2005–2024** | Courbes accidents / tués / hospitalisés, jalons réglementaires |
| **Véhicules impliqués** | Évolution par catégorie 2010–2024, nouvelles mobilités (EDP, VAE) |
| **Analyse BAAC 2018–2024** | Analyse détaillée par heure, département, conditions météo |
| **Corrélations & Technologies** | Radars officiels, équipement ADAS, matrice de corrélation, timeline réglementaire |
| **Données brutes** | Accès aux fichiers chargés, radars, normes de sécurité |

**Chiffres clés :** 5 318 tués en 2005 → 3 432 en 2024, soit **−35 %** en 20 ans.

---

## Données intégrées en permanence

Ces fichiers sont dans le repo et chargés automatiquement :

```
2009.csv … 2024.csv            résumés annuels véhicules impliqués
radars_france.csv              nb radars, PV émis, recettes 2003–2024 (ANTAI / Cour des Comptes)
normes_securite_vehicules.csv  30 normes de sécurité 1998–2026 (UE / France)
```

Les statistiques ONISR 2005–2017 (accidents, tués, hospitalisés) sont intégrées directement dans `data_loader.py`.

---

## Onglet Analyse BAAC — charger ses propres données

L'onglet **Analyse BAAC 2018–2024** nécessite les fichiers détaillés de la base nationale des accidents. Ces fichiers font entre 5 et 130 Mo chacun et ne peuvent pas être hébergés sur GitHub.

### Comment faire

**1. Téléchargez les fichiers sur data.gouv.fr**

[Bases de données annuelles des accidents corporels 2005–2024](https://www.data.gouv.fr/datasets/bases-de-donnees-annuelles-des-accidents-corporels-de-la-circulation-routiere-annees-de-2005-a-2024)

Pour chaque année souhaitée (2018 à 2024), téléchargez les 4 fichiers :

| Table | Contenu | Nom fichier (ex. 2024) |
|-------|---------|----------------------|
| Caractéristiques | Date, heure, commune, météo | `caract2024.csv` |
| Lieux | Type de route, profil, infrastructure | `lieux2024.csv` |
| Usagers | Gravité, âge, sexe, équipement | `usagers2024.csv` |
| Véhicules | Catégorie, manœuvre, choc | `vehicules2024.csv` |

**2. Glissez-déposez dans le dashboard**

Dans l'onglet **Analyse BAAC**, une zone de dépôt vous permet de charger plusieurs fichiers d'un coup (Ctrl+clic pour en sélectionner plusieurs). Le dashboard détecte automatiquement chaque type de fichier et l'année correspondante.

Vous pouvez charger une seule année ou plusieurs à la fois.

---

## Structure du repo

```
app.py                         code principal du dashboard
data_loader.py                 chargement et normalisation des données
requirements.txt               dépendances Python
README.md                      ce fichier
2009.csv … 2024.csv            résumés annuels (data.gouv.fr)
radars_france.csv              données radars officielles
normes_securite_vehicules.csv  normes de sécurité européennes et françaises
```

---

## Sources

| Source | Données |
|--------|---------|
| [BAAC — data.gouv.fr](https://www.data.gouv.fr/datasets/bases-de-donnees-annuelles-des-accidents-corporels-de-la-circulation-routiere-annees-de-2005-a-2024) | Fichiers détaillés accidents 2018–2024 |
| [ONISR](https://www.securite-routiere.gouv.fr/les-medias/la-mediatheque/bilan-de-laccidentalite) | Bilans annuels 2005–2017 |
| [ANTAI](https://www.antai.gouv.fr/le-controle-automatise/) | Statistiques radars automatiques |
| [Cour des Comptes](https://www.ccomptes.fr) | Recettes radars (budgets annuels) |
| [Règlement UE 2019/2144 — GSR2](https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32019R2144) | Normes ADAS obligatoires 2022–2026 |
| [ACEA / CLEPA](https://www.acea.auto) | Taux d'équipement ADAS par année |
