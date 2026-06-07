# config.py — paramètres du projet

# Fichier credentials OAuth2 téléchargé depuis Google Cloud Console
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

# Permissions demandées (lecture seule, métadonnées uniquement)
SCOPES = [
    "https://www.googleapis.com/auth/gmail.metadata",       # emails : expéditeur, heure, objet (pas le contenu)
    "https://www.googleapis.com/auth/calendar.readonly",    # calendrier : événements, durées, participants
]

# Fenêtre d'analyse (en jours)
ANALYSIS_WINDOW_DAYS = 30

# Seuils de signaux (ajustables selon le contexte)
LATE_HOUR_START = 22       # emails après 22h considérés comme "tard"
EARLY_HOUR_END = 6         # emails avant 6h considérés comme "très tôt"
WEEKEND_DAYS = [5, 6]      # samedi=5, dimanche=6

# Base de données locale
DB_PATH = "burnout_data.db"
