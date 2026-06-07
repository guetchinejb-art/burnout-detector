# auth.py — authentification Google OAuth2

import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from config import CREDENTIALS_FILE, TOKEN_FILE, SCOPES


def get_credentials() -> Credentials:
    """
    Gère le flux OAuth2 complet :
    - Si token.json existe et est valide → l'utilise directement
    - Si le token est expiré → le rafraîchit automatiquement
    - Si aucun token → ouvre le navigateur pour autorisation
    Retourne des credentials prêts à l'emploi.
    """
    creds = None

    # Charger le token existant s'il existe
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Si pas de credentials valides, en obtenir de nouveaux
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Rafraîchir automatiquement le token expiré
            creds.refresh(Request())
        else:
            # Premier lancement : ouvre le navigateur pour l'autorisation
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Sauvegarder le token pour les prochaines exécutions
        with open(TOKEN_FILE, "w") as token_file:
            token_file.write(creds.to_json())

    return creds
