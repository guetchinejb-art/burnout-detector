# dashboard.py — interface visuelle du détecteur de burnout

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import json
import pickle
import os
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# ── Configuration de la page ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Burnout Detector",
    page_icon="🧠",
    layout="wide"
)

# ── Styles CSS personnalisés ──────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        border: 1px solid #e0e0e0;
    }
    .score-low    { color: #2e7d32; font-size: 48px; font-weight: bold; }
    .score-medium { color: #f57c00; font-size: 48px; font-weight: bold; }
    .score-high   { color: #c62828; font-size: 48px; font-weight: bold; }
    .signal-ok    { color: #2e7d32; }
    .signal-warn  { color: #f57c00; }
    .signal-alert { color: #c62828; }
</style>
""", unsafe_allow_html=True)


# ── Fonctions utilitaires ─────────────────────────────────────────────────────
@st.cache_data
def load_snapshots():
    """Charge l'historique des analyses depuis SQLite."""
    if not os.path.exists("burnout_data.db"):
        return pd.DataFrame()
    conn = sqlite3.connect("burnout_data.db")
    df = pd.read_sql("SELECT * FROM behavior_snapshots ORDER BY collected_at DESC", conn)
    conn.close()
    if df.empty:
        return df
    df["features"] = df["features_json"].apply(json.loads)
    df["collected_at"] = pd.to_datetime(df["collected_at"])
    return df


def load_model():
    """Charge le modèle ML sauvegardé."""
    if not os.path.exists("burnout_model.pkl"):
        return None, None, None
    with open("burnout_model.pkl", "rb") as f:
        saved = pickle.load(f)
    return saved["model"], saved["scaler"], saved["features"]


def predict_risk(features_dict, model, scaler, feature_names):
    """Calcule le score de risque ML."""
    if model is None:
        return None
    X = pd.DataFrame([{f: features_dict.get(f, 0) for f in feature_names}])
    X_scaled = scaler.transform(X)
    proba = model.predict_proba(X_scaled)[0][1]
    return round(proba * 100, 1)


def score_color(score):
    if score < 25:
        return "score-low", "🟢 Faible"
    elif score < 50:
        return "score-medium", "🟡 Modéré"
    elif score < 75:
        return "score-high", "🔴 Élevé"
    else:
        return "score-high", "🚨 Critique"


def signal_status(value, warn_threshold, alert_threshold, higher_is_bad=True):
    if higher_is_bad:
        if value >= alert_threshold:
            return "signal-alert", "🔴"
        elif value >= warn_threshold:
            return "signal-warn", "🟡"
        else:
            return "signal-ok", "🟢"
    else:
        if value <= alert_threshold:
            return "signal-alert", "🔴"
        elif value <= warn_threshold:
            return "signal-warn", "🟡"
        else:
            return "signal-ok", "🟢"


# ── Chargement des données ────────────────────────────────────────────────────
df_snapshots = load_snapshots()
model, scaler, feature_names = load_model()

# ── En-tête ───────────────────────────────────────────────────────────────────
st.title("🧠 Burnout Detector")
st.markdown("Détection précoce du burnout par analyse comportementale — **données anonymisées**")
st.divider()

# ── Cas : aucune donnée ───────────────────────────────────────────────────────
if df_snapshots.empty:
    st.warning("Aucune analyse trouvée. Lance d'abord `python main.py` pour collecter tes données.")
    st.stop()

# ── Dernière analyse ──────────────────────────────────────────────────────────
latest = df_snapshots.iloc[0]
features = latest["features"]
collected_at = latest["collected_at"].strftime("%d %b %Y à %H:%M")

# Score ML ou heuristique
ml_score = predict_risk(features, model, scaler, feature_names)
display_score = ml_score if ml_score is not None else features.get("risk_score", 0)
css_class, level_label = score_color(display_score)

st.subheader(f"📊 Dernière analyse — {collected_at}")

# ── Score principal ───────────────────────────────────────────────────────────
col_score, col_interp = st.columns([1, 2])

with col_score:
    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size:14px; color:#666;">Score de risque burnout</div>
        <div class="{css_class}">{display_score}</div>
        <div style="font-size:13px; color:#666;">/ 100</div>
        <div style="font-size:18px; margin-top:10px;">{level_label}</div>
    </div>
    """, unsafe_allow_html=True)

with col_interp:
    st.markdown("### Interprétation")
    if display_score < 25:
        st.success("✅ Aucun signal préoccupant détecté. Les patterns de travail sont normaux.")
    elif display_score < 50:
        st.warning("⚠️ Quelques signaux à surveiller. Une conversation de check-in est recommandée.")
    elif display_score < 75:
        st.error("🔴 Signaux préoccupants détectés. Une intervention est recommandée.")
    else:
        st.error("🚨 Signaux critiques. Une intervention urgente est fortement conseillée.")

    if ml_score is not None:
        st.caption(f"Score calculé par le modèle Random Forest (ML) — probabilité : {ml_score}%")
    else:
        st.caption("Score calculé par règles heuristiques — installe le modèle ML pour plus de précision")

st.divider()

# ── Détail des signaux ────────────────────────────────────────────────────────
st.subheader("📬 Signaux détectés")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 📧 Emails")

    late_pct = features.get("late_night_email_pct", 0)
    css, icon = signal_status(late_pct, 10, 25)
    st.markdown(f'<span class="{css}">{icon} Emails tardifs/nuit : **{late_pct}%**</span>', unsafe_allow_html=True)

    wk_pct = features.get("weekend_email_pct", 0)
    css, icon = signal_status(wk_pct, 8, 20)
    st.markdown(f'<span class="{css}">{icon} Emails week-end : **{wk_pct}%**</span>', unsafe_allow_html=True)

    trend = features.get("late_night_trend", 0)
    css, icon = signal_status(trend, 0.02, 0.08)
    direction = "↗ aggravation" if trend > 0 else "↘ amélioration"
    st.markdown(f'<span class="{css}">{icon} Tendance emails tardifs : **{trend} ({direction})**</span>', unsafe_allow_html=True)

    hour = features.get("avg_send_hour", 0)
    css, icon = signal_status(hour, 20, 22)
    st.markdown(f'<span class="{css}">{icon} Heure moyenne d\'envoi : **{hour}h**</span>', unsafe_allow_html=True)

    st.metric("Total emails envoyés (30j)", features.get("total_sent_emails", 0))

with col2:
    st.markdown("#### 📅 Calendrier")

    dec_pct = features.get("declined_event_pct", 0)
    css, icon = signal_status(dec_pct, 15, 30)
    st.markdown(f'<span class="{css}">{icon} Réunions refusées : **{dec_pct}%**</span>', unsafe_allow_html=True)

    dec_trend = features.get("decline_trend", 0)
    css, icon = signal_status(dec_trend, 0.02, 0.10)
    direction = "↗ aggravation" if dec_trend > 0 else "↘ amélioration"
    st.markdown(f'<span class="{css}">{icon} Tendance refus : **{dec_trend} ({direction})**</span>', unsafe_allow_html=True)

    mtg_hrs = features.get("meeting_hours_per_week", 0)
    css, icon = signal_status(mtg_hrs, 20, 30)
    st.markdown(f'<span class="{css}">{icon} Heures réunion/semaine : **{mtg_hrs}h**</span>', unsafe_allow_html=True)

    st.metric("Total réunions analysées", features.get("total_events", 0))
    st.metric("Durée moyenne réunion", f"{features.get('avg_meeting_duration_min', 0)} min")

st.divider()

# ── Historique ────────────────────────────────────────────────────────────────
if len(df_snapshots) > 1:
    st.subheader("📈 Historique des scores")

    scores = []
    dates  = []
    for _, row in df_snapshots.iterrows():
        f = row["features"]
        s = predict_risk(f, model, scaler, feature_names)
        if s is None:
            s = f.get("risk_score", 0)
        scores.append(s)
        dates.append(row["collected_at"])

    hist_df = pd.DataFrame({"Date": dates, "Score": scores}).sort_values("Date")

    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(hist_df["Date"], hist_df["Score"], marker="o", color="steelblue", linewidth=2)
    ax.axhline(25, color="green",  linestyle="--", alpha=0.5, label="Seuil faible (25)")
    ax.axhline(50, color="orange", linestyle="--", alpha=0.5, label="Seuil modéré (50)")
    ax.axhline(75, color="red",    linestyle="--", alpha=0.5, label="Seuil élevé (75)")
    ax.set_ylim(0, 100)
    ax.set_ylabel("Score de risque")
    ax.set_title("Évolution du score de risque dans le temps")
    ax.legend(loc="upper right", fontsize=8)
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig)
else:
    st.info("Lance `python main.py` plusieurs fois pour voir l'évolution dans le temps.")

st.divider()

# ── Pied de page ──────────────────────────────────────────────────────────────
st.caption("🔒 Seules les métadonnées comportementales sont analysées. Aucun contenu de message n'est collecté ou stocké.")
