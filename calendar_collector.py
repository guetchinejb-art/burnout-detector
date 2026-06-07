# calendar_collector.py — collecte des événements Google Calendar

from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from config import ANALYSIS_WINDOW_DAYS, LATE_HOUR_START, EARLY_HOUR_END, WEEKEND_DAYS


def build_calendar_service(creds: Credentials):
    """Crée le client Calendar API."""
    return build("calendar", "v3", credentials=creds)


def get_calendar_events(service, days: int = ANALYSIS_WINDOW_DAYS) -> list[dict]:
    """
    Récupère les événements du calendrier principal.
    On collecte : durée, heure, jour, nombre de participants.
    Pas les titres détaillés ni les contenus de description.
    """
    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(days=days)).isoformat()
    time_max = now.isoformat()

    events_data = []
    page_token = None

    print(f"Collecte des événements calendrier sur {days} jours...")

    while True:
        result = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,          # développer les événements récurrents
            orderBy="startTime",
            pageToken=page_token,
            maxResults=500
        ).execute()

        events = result.get("items", [])

        for event in events:
            start = event.get("start", {})
            end = event.get("end", {})

            # Ignorer les événements toute la journée (pas d'heure précise)
            start_str = start.get("dateTime")
            end_str = end.get("dateTime")
            if not start_str or not end_str:
                continue

            start_dt = datetime.fromisoformat(start_str).replace(tzinfo=None)
            end_dt = datetime.fromisoformat(end_str).replace(tzinfo=None)
            duration_min = (end_dt - start_dt).total_seconds() / 60

            # Nombre de participants (sans leurs identités)
            attendees = event.get("attendees", [])
            num_attendees = len(attendees)

            # L'utilisateur a-t-il accepté, refusé ou ignoré ?
            user_response = "unknown"
            for attendee in attendees:
                if attendee.get("self"):
                    user_response = attendee.get("responseStatus", "unknown")
                    break

            events_data.append({
                "start_at": start_dt,
                "hour": start_dt.hour,
                "weekday": start_dt.weekday(),
                "duration_min": round(duration_min),
                "num_attendees": num_attendees,
                "is_late_night": start_dt.hour >= LATE_HOUR_START or start_dt.hour < EARLY_HOUR_END,
                "is_weekend": start_dt.weekday() in WEEKEND_DAYS,
                "is_declined": user_response == "declined",
                "is_accepted": user_response == "accepted",
            })

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    print(f"  → {len(events_data)} événements collectés")
    return events_data


def compute_calendar_features(events: list[dict]) -> dict:
    """
    Calcule les features calendrier pour le modèle ML.
    """
    if not events:
        return {}

    total = len(events)
    late_events = sum(1 for e in events if e["is_late_night"])
    weekend_events = sum(1 for e in events if e["is_weekend"])
    declined = sum(1 for e in events if e["is_declined"])
    durations = [e["duration_min"] for e in events]
    attendee_counts = [e["num_attendees"] for e in events]

    # Charge réunion : heures totales en réunion par semaine
    total_meeting_hours = sum(durations) / 60
    meeting_hours_per_week = round(total_meeting_hours / (ANALYSIS_WINDOW_DAYS / 7), 1)

    # Tendance des refus (signal fort de désengagement)
    sorted_events = sorted(events, key=lambda x: x["start_at"])
    mid = len(sorted_events) // 2
    first_decline_rate = sum(1 for e in sorted_events[:mid] if e["is_declined"]) / max(mid, 1)
    second_decline_rate = sum(1 for e in sorted_events[mid:] if e["is_declined"]) / max(len(sorted_events) - mid, 1)
    decline_trend = round(second_decline_rate - first_decline_rate, 3)

    return {
        "total_events": total,
        "late_night_event_count": late_events,
        "late_night_event_pct": round(late_events / total * 100, 1),
        "weekend_event_count": weekend_events,
        "declined_event_count": declined,
        "declined_event_pct": round(declined / total * 100, 1),
        "decline_trend": decline_trend,                 # positif = de plus en plus de refus
        "avg_meeting_duration_min": round(sum(durations) / total, 1),
        "meeting_hours_per_week": meeting_hours_per_week,
        "avg_attendees_per_meeting": round(sum(attendee_counts) / total, 1),
    }


# Import manquant ajouté ici pour éviter les erreurs
from config import ANALYSIS_WINDOW_DAYS
