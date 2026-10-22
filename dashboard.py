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
    page_title="Burnout Detector.ai",
    page_icon="🧠",
    layout="wide"
)

# ── Traductions EN/FR ─────────────────────────────────────────────────────────
TRANSLATIONS = {
    "FR": {
        "title": "🧠 Burnout Detector.ai",
        "subtitle": "Détection précoce du burnout par analyse comportementale — **données anonymisées**",
        "no_data": "Aucune analyse trouvée. Lance d'abord `python main.py` pour collecter tes données.",
        "last_analysis": "📊 Dernière analyse — {date}",
        "risk_score_label": "Score de risque burnout",
        "score_out_of": "/ 100",
        "interpretation": "### Interprétation",
        "interp_low": "✅ Aucun signal préoccupant détecté. Les patterns de travail sont normaux.",
        "interp_medium": "⚠️ Quelques signaux à surveiller. Une conversation de check-in est recommandée.",
        "interp_high": "🔴 Signaux préoccupants détectés. Une intervention est recommandée.",
        "interp_critical": "🚨 Signaux critiques. Une intervention urgente est fortement conseillée.",
        "ml_caption": "Score calculé par le modèle Random Forest (ML) — probabilité : {score}%",
        "heuristic_caption": "Score calculé par règles heuristiques — installe le modèle ML pour plus de précision",
        "signals_header": "📬 Signaux détectés",
        "emails_header": "#### 📧 Emails",
        "late_emails": "Emails tardifs/nuit : **{val}%**",
        "weekend_emails": "Emails week-end : **{val}%**",
        "late_trend": "Tendance emails tardifs : **{val} ({dir})**",
        "avg_hour": "Heure moyenne d'envoi : **{val}h**",
        "total_emails": "Total emails envoyés (30j)",
        "calendar_header": "#### 📅 Calendrier",
        "declined_pct": "Réunions refusées : **{val}%**",
        "decline_trend": "Tendance refus : **{val} ({dir})**",
        "meeting_hrs": "Heures réunion/semaine : **{val}h**",
        "total_meetings": "Total réunions analysées",
        "avg_duration": "Durée moyenne réunion",
        "min_unit": "min",
        "history_header": "📈 Historique des scores",
        "history_empty": "Lance `python main.py` plusieurs fois pour voir l'évolution dans le temps.",
        "score_axis": "Score de risque",
        "chart_title": "Évolution du score de risque dans le temps",
        "legend_low": "Seuil faible (25)",
        "legend_medium": "Seuil modéré (50)",
        "legend_high": "Seuil élevé (75)",
        "footer": "🔒 Seules les métadonnées comportementales sont analysées. Aucun contenu de message n'est collecté ou stocké.",
        "aggravation": "↗ aggravation",
        "amelioration": "↘ amélioration",
        "lang_label": "Langue / Language",
        "score_labels": {
            "low": "🟢 Faible",
            "medium": "🟡 Modéré",
            "high": "🔴 Élevé",
            "critical": "🚨 Critique",
        }
    },
    "EN": {
        "title": "🧠 Burnout Detector.ai",
        "subtitle": "Early burnout detection through behavioral analysis — **anonymized data**",
        "no_data": "No analysis found. Run `python main.py` first to collect your data.",
        "last_analysis": "📊 Latest analysis — {date}",
        "risk_score_label": "Burnout risk score",
        "score_out_of": "/ 100",
        "interpretation": "### Interpretation",
        "interp_low": "✅ No concerning signals detected. Work patterns look healthy.",
        "interp_medium": "⚠️ A few signals to monitor. A check-in conversation is recommended.",
        "interp_high": "🔴 Concerning signals detected. Intervention is recommended.",
        "interp_critical": "🚨 Critical signals. Urgent intervention is strongly advised.",
        "ml_caption": "Score computed by Random Forest model (ML) — probability: {score}%",
        "heuristic_caption": "Score computed by heuristic rules — install the ML model for more precision",
        "signals_header": "📬 Detected signals",
        "emails_header": "#### 📧 Emails",
        "late_emails": "Late-night emails: **{val}%**",
        "weekend_emails": "Weekend emails: **{val}%**",
        "late_trend": "Late-night email trend: **{val} ({dir})**",
        "avg_hour": "Average send time: **{val}h**",
        "total_emails": "Total emails sent (30d)",
        "calendar_header": "#### 📅 Calendar",
        "declined_pct": "Declined meetings: **{val}%**",
        "decline_trend": "Decline trend: **{val} ({dir})**",
        "meeting_hrs": "Meeting hours/week: **{val}h**",
        "total_meetings": "Total meetings analyzed",
        "avg_duration": "Average meeting duration",
        "min_unit": "min",
        "history_header": "📈 Score history",
        "history_empty": "Run `python main.py` several times to see the trend over time.",
        "score_axis": "Risk score",
        "chart_title": "Risk score over time",
        "legend_low": "Low threshold (25)",
        "legend_medium": "Moderate threshold (50)",
        "legend_high": "High threshold (75)",
        "footer": "🔒 Only behavioral metadata is analyzed. No message content is collected or stored.",
        "aggravation": "↗ worsening",
        "amelioration": "↘ improving",
        "lang_label": "Langue / Language",
        "score_labels": {
            "low": "🟢 Low",
            "medium": "🟡 Moderate",
            "high": "🔴 High",
            "critical": "🚨 Critical",
        }
    }
}

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

# ── Sélecteur de langue (sidebar) ─────────────────────────────────────────────
if "lang" not in st.session_state:
    st.session_state.lang = "FR"

with st.sidebar:
    st.session_state.lang = st.selectbox(
        "🌐 Langue / Language",
        options=["FR", "EN"],
        index=0 if st.session_state.lang == "FR" else 1,
        key="lang_selector"
    )

T = TRANSLATIONS[st.session_state.lang]


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
    labels = T["score_labels"]
    if score < 25:
        return "score-low", labels["low"]
    elif score < 50:
        return "score-medium", labels["medium"]
    elif score < 75:
        return "score-high", labels["high"]
    else:
        return "score-high", labels["critical"]


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
st.title(T["title"])
st.markdown(T["subtitle"])
st.divider()

# ── Cas : aucune donnée ───────────────────────────────────────────────────────
if df_snapshots.empty:
    st.warning(T["no_data"])
    st.stop()

# ── Dernière analyse ──────────────────────────────────────────────────────────
latest = df_snapshots.iloc[0]
features = latest["features"]
collected_at = latest["collected_at"].strftime("%d %b %Y à %H:%M")

# Score ML ou heuristique
ml_score = predict_risk(features, model, scaler, feature_names)
display_score = ml_score if ml_score is not None else features.get("risk_score", 0)
css_class, level_label = score_color(display_score)

st.subheader(T["last_analysis"].format(date=collected_at))

# ── Score principal ───────────────────────────────────────────────────────────
col_score, col_interp = st.columns([1, 2])

with col_score:
    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size:14px; color:#666;">{T["risk_score_label"]}</div>
        <div class="{css_class}">{display_score}</div>
        <div style="font-size:13px; color:#666;">{T["score_out_of"]}</div>
        <div style="font-size:18px; margin-top:10px;">{level_label}</div>
    </div>
    """, unsafe_allow_html=True)

with col_interp:
    st.markdown(T["interpretation"])
    if display_score < 25:
        st.success(T["interp_low"])
    elif display_score < 50:
        st.warning(T["interp_medium"])
    elif display_score < 75:
        st.error(T["interp_high"])
    else:
        st.error(T["interp_critical"])

    if ml_score is not None:
        st.caption(T["ml_caption"].format(score=ml_score))
    else:
        st.caption(T["heuristic_caption"])

st.divider()

# ── Détail des signaux ────────────────────────────────────────────────────────
st.subheader(T["signals_header"])

col1, col2 = st.columns(2)

with col1:
    st.markdown(T["emails_header"])

    late_pct = features.get("late_night_email_pct", 0)
    css, icon = signal_status(late_pct, 10, 25)
    st.markdown(f'<span class="{css}">{icon} {T["late_emails"].format(val=late_pct)}</span>', unsafe_allow_html=True)

    wk_pct = features.get("weekend_email_pct", 0)
    css, icon = signal_status(wk_pct, 8, 20)
    st.markdown(f'<span class="{css}">{icon} {T["weekend_emails"].format(val=wk_pct)}</span>', unsafe_allow_html=True)

    trend = features.get("late_night_trend", 0)
    css, icon = signal_status(trend, 0.02, 0.08)
    direction = T["aggravation"] if trend > 0 else T["amelioration"]
    st.markdown(f'<span class="{css}">{icon} {T["late_trend"].format(val=trend, dir=direction)}</span>', unsafe_allow_html=True)

    hour = features.get("avg_send_hour", 0)
    css, icon = signal_status(hour, 20, 22)
    st.markdown(f'<span class="{css}">{icon} {T["avg_hour"].format(val=hour)}</span>', unsafe_allow_html=True)

    st.metric(T["total_emails"], features.get("total_sent_emails", 0))

with col2:
    st.markdown(T["calendar_header"])

    dec_pct = features.get("declined_event_pct", 0)
    css, icon = signal_status(dec_pct, 15, 30)
    st.markdown(f'<span class="{css}">{icon} {T["declined_pct"].format(val=dec_pct)}</span>', unsafe_allow_html=True)

    dec_trend = features.get("decline_trend", 0)
    css, icon = signal_status(dec_trend, 0.02, 0.10)
    direction = T["aggravation"] if dec_trend > 0 else T["amelioration"]
    st.markdown(f'<span class="{css}">{icon} {T["decline_trend"].format(val=dec_trend, dir=direction)}</span>', unsafe_allow_html=True)

    mtg_hrs = features.get("meeting_hours_per_week", 0)
    css, icon = signal_status(mtg_hrs, 20, 30)
    st.markdown(f'<span class="{css}">{icon} {T["meeting_hrs"].format(val=mtg_hrs)}</span>', unsafe_allow_html=True)

    st.metric(T["total_meetings"], features.get("total_events", 0))
    st.metric(T["avg_duration"], f"{features.get('avg_meeting_duration_min', 0)} {T['min_unit']}")

st.divider()

# ── Historique ────────────────────────────────────────────────────────────────
if len(df_snapshots) > 1:
    st.subheader(T["history_header"])

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
    ax.axhline(25, color="green",  linestyle="--", alpha=0.5, label=T["legend_low"])
    ax.axhline(50, color="orange", linestyle="--", alpha=0.5, label=T["legend_medium"])
    ax.axhline(75, color="red",    linestyle="--", alpha=0.5, label=T["legend_high"])
    ax.set_ylim(0, 100)
    ax.set_ylabel(T["score_axis"])
    ax.set_title(T["chart_title"])
    ax.legend(loc="upper right", fontsize=8)
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig)
else:
    st.info(T["history_empty"])

st.divider()

# ── Pied de page ──────────────────────────────────────────────────────────────
st.caption(T["footer"])
