# gmail_collector.py — collecte des MÉTADONNÉES emails uniquement (pas le contenu)

from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from config import ANALYSIS_WINDOW_DAYS, LATE_HOUR_START, EARLY_HOUR_END, WEEKEND_DAYS


def build_gmail_service(creds: Credentials):
    """Crée le client Gmail API."""
    return build("gmail", "v1", credentials=creds)


def get_email_metadata(service, days: int = ANALYSIS_WINDOW_DAYS) -> list[dict]:
    """
    Récupère uniquement les métadonnées des emails envoyés
    sur les `days` derniers jours.

    IMPORTANT : on collecte SEULEMENT :
    - L'heure d'envoi
    - Le jour de la semaine
    - Si c'est un email envoyé (pas reçu)
    Jamais le contenu, jamais les destinataires complets.
    """
    # Date de début de la fenêtre d'analyse
    since_date = datetime.now() - timedelta(days=days)

    emails_data = []
    page_token = None

    print(f"Collecte des emails envoyés depuis {since_date.strftime('%Y/%m/%d')}...")

    while True:
        # IMPORTANT : scope gmail.metadata ne supporte pas le paramètre q
        # On récupère tous les emails et on filtre par date manuellement
        result = service.users().messages().list(
            userId="me",
            labelIds=["SENT"],      # ← filtre sur emails envoyés sans q
            pageToken=page_token,
            maxResults=500
        ).execute()

        messages = result.get("messages", [])
        if not messages:
            break

        for msg in messages:
            # Récupérer uniquement les headers (pas le body)
            detail = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata",                      # ← clé : metadata seulement
                metadataHeaders=["Date", "Subject"]     # ← uniquement heure et sujet
            ).execute()

            headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
            date_str = headers.get("Date", "")

            if not date_str:
                continue

            # Parser la date de l'email
            try:
                sent_at = _parse_email_date(date_str)
            except Exception:
                continue

            # Filtrer manuellement par date (remplace le paramètre q)
            if sent_at < since_date:
                continue

            emails_data.append({
                "sent_at": sent_at,
                "hour": sent_at.hour,
                "weekday": sent_at.weekday(),           # 0=lundi, 6=dimanche
                "is_late_night": sent_at.hour >= LATE_HOUR_START or sent_at.hour < EARLY_HOUR_END,
                "is_weekend": sent_at.weekday() in WEEKEND_DAYS,
            })

        # Passer à la page suivante si elle existe
        page_token = result.get("nextPageToken")
        if not page_token:
            break

    print(f"  → {len(emails_data)} emails collectés")
    return emails_data


def compute_email_features(emails: list[dict]) -> dict:
    """
    Calcule les features comportementales à partir des métadonnées.
    Ces features alimenteront le modèle ML.
    """
    if not emails:
        return {}

    total = len(emails)
    late_night = sum(1 for e in emails if e["is_late_night"])
    weekends = sum(1 for e in emails if e["is_weekend"])

    # Distribution par heure (pour détecter les patterns anormaux)
    hours = [e["hour"] for e in emails]

    # Calcul de la tendance : est-ce que les emails tardifs augmentent dans le temps ?
    # On compare les 2 dernières semaines vs les 2 premières
    sorted_emails = sorted(emails, key=lambda x: x["sent_at"])
    mid = len(sorted_emails) // 2
    first_half_late = sum(1 for e in sorted_emails[:mid] if e["is_late_night"])
    second_half_late = sum(1 for e in sorted_emails[mid:] if e["is_late_night"])
    late_night_trend = (second_half_late - first_half_late) / max(mid, 1)

    return {
        "total_sent_emails": total,
        "late_night_email_count": late_night,
        "late_night_email_pct": round(late_night / total * 100, 1),
        "weekend_email_count": weekends,
        "weekend_email_pct": round(weekends / total * 100, 1),
        "avg_send_hour": round(sum(hours) / total, 1),
        "late_night_trend": round(late_night_trend, 3),   # positif = aggravation
    }


def _parse_email_date(date_str: str) -> datetime:
    """Parse les formats de date variés des headers email."""
    from email.utils import parsedate_to_datetime
    return parsedate_to_datetime(date_str).replace(tzinfo=None)
