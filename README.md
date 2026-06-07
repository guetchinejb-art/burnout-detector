# Guide d'installation — Burnout Collector

## Structure du projet

```
burnout_collector/
├── config.py              # Paramètres globaux
├── auth.py                # Authentification OAuth2
├── gmail_collector.py     # Collecte métadonnées Gmail
├── calendar_collector.py  # Collecte données Calendar
├── main.py                # Pipeline principal
├── requirements.txt       # Dépendances Python
└── README.md              # Ce fichier
```

---

## Étape 1 — Créer le projet Google Cloud

1. Aller sur https://console.cloud.google.com
2. Créer un nouveau projet : "BurnoutDetector"
3. Dans le menu → "APIs et services" → "Bibliothèque"
4. Activer ces 2 APIs :
   - **Gmail API**
   - **Google Calendar API**

---

## Étape 2 — Créer les credentials OAuth2

1. "APIs et services" → "Identifiants" → "Créer des identifiants"
2. Choisir "ID client OAuth"
3. Type d'application : **Application de bureau**
4. Nom : "BurnoutCollector"
5. Télécharger le fichier JSON → renommer en `credentials.json`
6. Placer `credentials.json` dans le dossier du projet

---

## Étape 3 — Configurer l'écran de consentement OAuth

1. "APIs et services" → "Écran de consentement OAuth"
2. Type : **Externe** (pour tester avec ton compte)
3. Remplir le nom de l'app et l'email de contact
4. Scopes → ajouter :
   - `gmail.metadata`
   - `calendar.readonly`
5. Utilisateurs test → ajouter ton email Google

---

## Étape 4 — Installer les dépendances Python

```bash
# Créer un environnement virtuel (recommandé)
python -m venv venv

# Activer l'environnement
# Sur Windows :
venv\Scripts\activate
# Sur Mac/Linux :
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

---

## Étape 5 — Lancer le pipeline

```bash
python main.py
```

Au premier lancement :
- Un navigateur s'ouvre automatiquement
- Connecte-toi avec ton compte Google
- Autorise les permissions demandées
- Le token est sauvegardé → les lancements suivants sont automatiques

---

## Exemple de sortie attendue

```
Démarrage du pipeline de collecte...
(Seules les métadonnées sont collectées — pas le contenu des messages)

1. Authentification Google...
   OK

2. Collecte Gmail...
Collecte des emails envoyés depuis 2026/05/08...
  → 247 emails collectés

3. Collecte Calendar...
Collecte des événements calendrier sur 30 jours...
  → 89 événements collectés

4. Calcul du score de risque...
5. Sauvegarde en base de données...
  → Données sauvegardées dans burnout_data.db

=======================================================
  RAPPORT D'ANALYSE COMPORTEMENTALE
=======================================================

  Score de risque burnout : 38.5/100
  Interprétation         : Modéré — quelques signaux à surveiller

  --- Signaux email ---
  Emails envoyés (30j)   : 247
  Emails tardifs/nuit    : 12.3%
  Emails week-end        : 8.5%
  Tendance emails tardifs: +0.023 (+ = aggravation)

  --- Signaux calendrier ---
  Réunions analysées     : 89
  Réunions refusées      : 15.7%
  Tendance refus         : +0.041
  Heures réunion/semaine : 18.5h
  Durée moy. réunion     : 47 min

=======================================================
```

---

## Ce que le code collecte (et ce qu'il ne collecte PAS)

| Collecté | Non collecté |
|----------|-------------|
| Heure d'envoi des emails | Contenu des emails |
| Jour de la semaine | Destinataires des emails |
| Durée des réunions | Titre des réunions |
| Nombre de participants | Identité des participants |
| Réponse aux invitations | Notes de réunion |

---

## Prochaine étape : modèle ML

Les features sauvegardées dans `burnout_data.db` seront utilisées
pour entraîner un modèle de classification (Random Forest / XGBoost)
dans l'étape suivante du projet.

```python
import sqlite3, pandas as pd

conn = sqlite3.connect("burnout_data.db")
df = pd.read_sql("SELECT * FROM behavior_snapshots", conn)
print(df.head())
```
