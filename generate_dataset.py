# generate_dataset.py — génère un dataset simulé réaliste pour entraîner le modèle

import numpy as np
import pandas as pd

np.random.seed(42)  # pour avoir les mêmes résultats à chaque fois

N = 1000  # nombre d'employés simulés


def generate_dataset(n=N) -> pd.DataFrame:
    """
    Génère un dataset réaliste avec des features comportementales
    et un label burnout (1 = burnout, 0 = pas burnout).

    Logique : les employés en burnout ont des patterns différents :
    - Plus d'emails tardifs / week-end
    - Plus de réunions refusées
    - Tendances qui s'aggravent dans le temps
    - Plus d'heures de réunion
    """
    records = []

    for i in range(n):
        # 30% des employés sont en burnout
        is_burnout = np.random.random() < 0.30

        if is_burnout:
            # Profil burnout : signaux comportementaux dégradés
            total_emails        = np.random.randint(50, 300)
            late_night_pct      = np.random.uniform(15, 60)    # beaucoup d'emails tardifs
            weekend_pct         = np.random.uniform(10, 40)    # emails le week-end
            avg_send_hour       = np.random.uniform(20, 23)    # envoie tard
            late_night_trend    = np.random.uniform(0.01, 0.15) # tendance qui empire
            total_events        = np.random.randint(20, 80)
            declined_pct        = np.random.uniform(20, 60)    # beaucoup de refus
            decline_trend       = np.random.uniform(0.02, 0.20)
            meeting_hours_week  = np.random.uniform(20, 40)    # surchargé de réunions
            avg_meeting_min     = np.random.uniform(45, 90)
            avg_attendees       = np.random.uniform(4, 12)
        else:
            # Profil sain : patterns normaux
            total_emails        = np.random.randint(10, 150)
            late_night_pct      = np.random.uniform(0, 10)     # peu d'emails tardifs
            weekend_pct         = np.random.uniform(0, 8)
            avg_send_hour       = np.random.uniform(9, 18)     # heures de bureau
            late_night_trend    = np.random.uniform(-0.05, 0.02)
            total_events        = np.random.randint(5, 40)
            declined_pct        = np.random.uniform(0, 15)
            decline_trend       = np.random.uniform(-0.05, 0.01)
            meeting_hours_week  = np.random.uniform(2, 18)
            avg_meeting_min     = np.random.uniform(20, 60)
            avg_attendees       = np.random.uniform(2, 8)

        # Ajouter du bruit réaliste (la vie réelle n'est pas parfaite)
        late_night_pct   += np.random.normal(0, 3)
        weekend_pct      += np.random.normal(0, 2)
        declined_pct     += np.random.normal(0, 4)
        meeting_hours_week += np.random.normal(0, 2)

        # S'assurer que les valeurs restent dans des bornes réalistes
        late_night_pct   = np.clip(late_night_pct, 0, 100)
        weekend_pct      = np.clip(weekend_pct, 0, 100)
        declined_pct     = np.clip(declined_pct, 0, 100)
        meeting_hours_week = np.clip(meeting_hours_week, 0, 60)

        records.append({
            "total_sent_emails":        total_emails,
            "late_night_email_pct":     round(late_night_pct, 1),
            "weekend_email_pct":        round(weekend_pct, 1),
            "avg_send_hour":            round(avg_send_hour, 1),
            "late_night_trend":         round(late_night_trend, 3),
            "total_events":             total_events,
            "declined_event_pct":       round(declined_pct, 1),
            "decline_trend":            round(decline_trend, 3),
            "meeting_hours_per_week":   round(meeting_hours_week, 1),
            "avg_meeting_duration_min": round(avg_meeting_min, 1),
            "avg_attendees_per_meeting":round(avg_attendees, 1),
            "burnout":                  int(is_burnout),   # label : 0 ou 1
        })

    df = pd.DataFrame(records)
    df.to_csv("burnout_dataset.csv", index=False)
    print(f"Dataset généré : {n} employés, {df['burnout'].sum()} en burnout ({df['burnout'].mean()*100:.1f}%)")
    print(f"Fichier sauvegardé : burnout_dataset.csv")
    return df


if __name__ == "__main__":
    generate_dataset()
