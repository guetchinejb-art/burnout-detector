# main.py — point d'entrée principal du pipeline de collecte

import json
import sqlite3
from datetime import datetime
from auth import get_credentials
from gmail_collector import build_gmail_service, get_email_metadata, compute_email_features
from calendar_collector import build_calendar_service, get_calendar_events, compute_calendar_features
from config import DB_PATH, ANALYSIS_WINDOW_DAYS


def save_to_db(features: dict, user_id: str = "user_001"):
    """
    Sauvegarde les features calculées en base SQLite.
    Chaque ligne = un snapshot d'analyse à un moment donné.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Créer la table si elle n'existe pas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS behavior_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            collected_at TEXT NOT NULL,
            features_json TEXT NOT NULL,
            risk_score REAL
        )
    """)

    cursor.execute("""
        INSERT INTO behavior_snapshots (user_id, collected_at, features_json)
        VALUES (?, ?, ?)
    """, (user_id, datetime.now().isoformat(), json.dumps(features)))

    conn.commit()
    conn.close()
    print(f"  → Données sauvegardées dans {DB_PATH}")


def compute_simple_risk_score(features: dict) -> float:
    """
    Score de risque simplifié (0 à 100) basé sur les règles heuristiques.
    Ce score sera remplacé par le modèle ML dans la prochaine étape.

    Logique :
    - Emails tardifs / week-end → signal fort
    - Réunions refusées en hausse → signal fort
    - Beaucoup d'heures de réunion → signal modéré
    - Tendance haussière sur les signaux → amplificateur
    """
    score = 0.0

    # Emails tardifs ou week-end (max 30 pts)
    late_email_pct = features.get("late_night_email_pct", 0)
    weekend_email_pct = features.get("weekend_email_pct", 0)
    score += min(late_email_pct * 1.5, 20)
    score += min(weekend_email_pct * 1.0, 10)

    # Tendance d'aggravation des emails tardifs (max 15 pts)
    late_trend = features.get("late_night_trend", 0)
    if late_trend > 0:
        score += min(late_trend * 50, 15)

    # Réunions refusées (max 25 pts)
    decline_pct = features.get("declined_event_pct", 0)
    score += min(decline_pct * 1.5, 20)

    # Tendance de refus croissante (max 15 pts)
    decline_trend = features.get("decline_trend", 0)
    if decline_trend > 0:
        score += min(decline_trend * 100, 15)

    # Surcharge de réunions (max 15 pts)
    meeting_hours = features.get("meeting_hours_per_week", 0)
    if meeting_hours > 20:
        score += min((meeting_hours - 20) * 1.5, 15)

    return round(min(score, 100), 1)


def interpret_risk(score: float) -> str:
    """Interprétation lisible du score de risque."""
    if score < 25:
        return "Faible — aucun signal préoccupant détecté"
    elif score < 50:
        return "Modéré — quelques signaux à surveiller"
    elif score < 75:
        return "Élevé — intervention recommandée"
    else:
        return "Critique — intervention urgente conseillée"


def print_report(features: dict, score: float):
    """Affiche un rapport lisible dans le terminal."""
    print("\n" + "=" * 55)
    print("  RAPPORT D'ANALYSE COMPORTEMENTALE")
    print("=" * 55)

    print(f"\n  Score de risque burnout : {score}/100")
    print(f"  Interprétation         : {interpret_risk(score)}")

    print("\n  --- Signaux email ---")
    print(f"  Emails envoyés (30j)   : {features.get('total_sent_emails', 'N/A')}")
    print(f"  Emails tardifs/nuit    : {features.get('late_night_email_pct', 0)}%")
    print(f"  Emails week-end        : {features.get('weekend_email_pct', 0)}%")
    print(f"  Tendance emails tardifs: {'+' if features.get('late_night_trend', 0) > 0 else ''}{features.get('late_night_trend', 0)} (+ = aggravation)")

    print("\n  --- Signaux calendrier ---")
    print(f"  Réunions analysées     : {features.get('total_events', 'N/A')}")
    print(f"  Réunions refusées      : {features.get('declined_event_pct', 0)}%")
    print(f"  Tendance refus         : {'+' if features.get('decline_trend', 0) > 0 else ''}{features.get('decline_trend', 0)}")
    print(f"  Heures réunion/semaine : {features.get('meeting_hours_per_week', 0)}h")
    print(f"  Durée moy. réunion     : {features.get('avg_meeting_duration_min', 0)} min")

    print("\n" + "=" * 55)


def run():
    """Pipeline principal de collecte et d'analyse."""
    print("Démarrage du pipeline de collecte...")
    print("(Seules les métadonnées sont collectées — pas le contenu des messages)\n")

    # 1. Authentification
    print("1. Authentification Google...")
    creds = get_credentials()
    print("   OK\n")

    # 2. Collecte Gmail
    print("2. Collecte Gmail...")
    gmail_service = build_gmail_service(creds)
    emails = get_email_metadata(gmail_service, days=ANALYSIS_WINDOW_DAYS)
    email_features = compute_email_features(emails)

    # 3. Collecte Calendar
    print("\n3. Collecte Calendar...")
    calendar_service = build_calendar_service(creds)
    events = get_calendar_events(calendar_service, days=ANALYSIS_WINDOW_DAYS)
    calendar_features = compute_calendar_features(events)

    # 4. Fusion des features
    all_features = {**email_features, **calendar_features}

    # 5. Calcul du score
    print("\n4. Calcul du score de risque...")
    score = compute_simple_risk_score(all_features)

    # 6. Sauvegarde
    print("5. Sauvegarde en base de données...")
    save_to_db({**all_features, "risk_score": score})

    # 7. Rapport
    print_report(all_features, score)

    return all_features, score


if __name__ == "__main__":
    run()
