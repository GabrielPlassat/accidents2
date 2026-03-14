# 🚗 Dashboard Accidentologie Routière France (2005–2024)

Tableau de bord interactif de l'accidentologie routière française, avec perspective historique de 2005 à 2024.

## 📊 Fonctionnalités

| Onglet | Contenu |
|--------|---------|
| **Vue d'ensemble** | KPIs 2024, évolution depuis 2005, gravité |
| **Tendances historiques** | Courbes 2005-2024, annotations événements, taux de mortalité |
| **Analyse détaillée** | Temporel, véhicules, géographie, conditions (BAAC 2018-2024) |
| **Technologies & Réglementations** | Radars, normes sécurité, corrélations |
| **Données brutes** | Accès et export des tables BAAC |

## 📁 Structure des données

```
data/
├── caract2024.csv          # Caractéristiques accidents 2024
├── lieux2024.csv           # Lieux accidents 2024
├── usagers2024.csv         # Usagers impliqués 2024
├── vehicules2024.csv       # Véhicules impliqués 2024
├── ...                     # Même structure pour 2018-2023
├── 2009.csv → 2024.csv     # Résumés annuels véhicules impliqués
```

### Disponibilité des données
- **2018–2024** : Tables BAAC complètes (4 fichiers par an)
- **2005–2017** : Statistiques ONISR consolidées + résumés annuels

### Ajouter les données 2010–2017
Téléchargez les archives sur [data.gouv.fr](https://www.data.gouv.fr/fr/datasets/bases-de-donnees-annuelles-des-accidents-corporels-de-la-circulation-routiere-annees-de-2005-a-2023/)
et déposez-les dans le même dossier avec la convention de nommage :
```
caracteristiques{année}.csv
lieux{année}.csv
usagers{année}.csv
vehicules{année}.csv
```

---

## 🚀 Lancement

### Option 1 – Streamlit Cloud (recommandé)
1. Pushez ce repo sur GitHub
2. Connectez-vous sur [share.streamlit.io](https://share.streamlit.io)
3. Déployez `app.py`
4. Configurez le chemin des données via la barre latérale

### Option 2 – Google Colab

```python
# Installer les dépendances
!pip install streamlit plotly pandas numpy scipy statsmodels pyngrok -q

# Cloner le repo
!git clone https://github.com/VOTRE_USER/Accidents2024.git
%cd Accidents2024

# Lancer avec ngrok (tunnel public)
from pyngrok import ngrok
import subprocess, threading

def run_streamlit():
    subprocess.run(["streamlit", "run", "app.py", "--server.port=8501",
                    "--server.headless=true"])

thread = threading.Thread(target=run_streamlit)
thread.start()

tunnel = ngrok.connect(8501)
print(f"Dashboard accessible ici : {tunnel.public_url}")
```

### Option 3 – Local (si Python installé)

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 📡 Données complémentaires à intégrer

| Source | Données | URL |
|--------|---------|-----|
| **ANTAI** | Infractions et radars par département | antai.gouv.fr |
| **ONISR** | Bilans annuels complets | securite-routiere.gouv.fr |
| **Euro NCAP** | Scores sécurité par modèle | euroncap.com |
| **ADEME** | Parc automobile, âge moyen | ademe.fr |

---

## 🔮 Roadmap

- [ ] Intégration normes Euro NCAP par constructeur/modèle
- [ ] Carte choroplèthe départements (GeoJSON)
- [ ] Données radars ANTAI officielles par département
- [ ] Modèle de régression : impact des technologies sur la mortalité
- [ ] Comparatif européen (ETSC)
- [ ] Prédiction 2025 par modèle ML

---

## 📖 Sources

- [BAAC – data.gouv.fr](https://www.data.gouv.fr/fr/datasets/bases-de-donnees-annuelles-des-accidents-corporels-de-la-circulation-routiere-annees-de-2005-a-2023/)
- [ONISR – Bilan de l'accidentalité](https://www.securite-routiere.gouv.fr)
- [Euro NCAP](https://www.euroncap.com)
- [ANTAI](https://www.antai.gouv.fr)
