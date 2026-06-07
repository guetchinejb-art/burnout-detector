# model.py — modèle ML de détection de burnout

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve
)
import pickle
import os

# Features utilisées par le modèle
FEATURES = [
    "total_sent_emails",
    "late_night_email_pct",
    "weekend_email_pct",
    "avg_send_hour",
    "late_night_trend",
    "total_events",
    "declined_event_pct",
    "decline_trend",
    "meeting_hours_per_week",
    "avg_meeting_duration_min",
    "avg_attendees_per_meeting",
]

TARGET = "burnout"


def load_data(filepath="burnout_dataset.csv") -> tuple:
    """Charge et prépare les données."""
    df = pd.read_csv(filepath)
    print(f"Dataset chargé : {len(df)} lignes, {df['burnout'].mean()*100:.1f}% burnout")

    X = df[FEATURES]
    y = df[TARGET]
    return X, y


def train_model(X, y) -> tuple:
    """
    Entraîne un Random Forest et évalue ses performances.
    Retourne le modèle entraîné et le scaler.
    """
    # Séparation train/test (80% / 20%)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\nEntraînement : {len(X_train)} exemples")
    print(f"Test         : {len(X_test)} exemples")

    # Normalisation des features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled  = scaler.transform(X_test)

    # Modèle Random Forest
    print("\nEntraînement du modèle Random Forest...")
    model = RandomForestClassifier(
        n_estimators=100,       # 100 arbres de décision
        max_depth=8,            # profondeur maximale
        min_samples_split=10,   # évite le surapprentissage
        random_state=42,
        class_weight="balanced" # compense le déséquilibre burnout/non-burnout
    )
    model.fit(X_train_scaled, y_train)

    # Validation croisée (5 folds) — mesure plus fiable
    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring="roc_auc")
    print(f"Score AUC (validation croisée) : {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    # Évaluation sur le jeu de test
    y_pred  = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)[:, 1]

    print("\n--- Rapport de classification ---")
    print(classification_report(y_test, y_pred, target_names=["Pas burnout", "Burnout"]))

    auc = roc_auc_score(y_test, y_proba)
    print(f"AUC-ROC sur le test : {auc:.3f}")

    return model, scaler, X_test, y_test, y_pred, y_proba


def plot_results(model, X_test, y_test, y_pred, y_proba):
    """Génère et sauvegarde les graphiques d'évaluation."""
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle("Évaluation du modèle de détection de burnout", fontsize=14, fontweight="bold")

    # 1. Matrice de confusion
    cm = confusion_matrix(y_test, y_pred)
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Blues", ax=axes[0],
        xticklabels=["Pas burnout", "Burnout"],
        yticklabels=["Pas burnout", "Burnout"]
    )
    axes[0].set_title("Matrice de confusion")
    axes[0].set_ylabel("Réel")
    axes[0].set_xlabel("Prédit")

    # 2. Courbe ROC
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    auc = roc_auc_score(y_test, y_proba)
    axes[1].plot(fpr, tpr, color="steelblue", lw=2, label=f"AUC = {auc:.3f}")
    axes[1].plot([0, 1], [0, 1], "k--", lw=1)
    axes[1].set_xlabel("Taux faux positifs")
    axes[1].set_ylabel("Taux vrais positifs")
    axes[1].set_title("Courbe ROC")
    axes[1].legend()

    # 3. Importance des features
    importances = pd.Series(model.feature_importances_, index=FEATURES).sort_values()
    colors = ["#E24B4A" if imp > importances.median() else "#7BAFD4" for imp in importances]
    importances.plot(kind="barh", ax=axes[2], color=colors)
    axes[2].set_title("Importance des features")
    axes[2].set_xlabel("Importance")

    plt.tight_layout()
    plt.savefig("model_evaluation.png", dpi=150, bbox_inches="tight")
    print("\nGraphiques sauvegardés : model_evaluation.png")
    plt.show()


def save_model(model, scaler):
    """Sauvegarde le modèle et le scaler pour utilisation future."""
    with open("burnout_model.pkl", "wb") as f:
        pickle.dump({"model": model, "scaler": scaler, "features": FEATURES}, f)
    print("Modèle sauvegardé : burnout_model.pkl")


def predict_from_features(features_dict: dict) -> dict:
    """
    Prédit le risque de burnout à partir d'un dictionnaire de features.
    Utilisé pour connecter le modèle au pipeline de collecte.
    """
    if not os.path.exists("burnout_model.pkl"):
        print("Modèle non trouvé — lance d'abord train_model()")
        return {}

    with open("burnout_model.pkl", "rb") as f:
        saved = pickle.load(f)

    model   = saved["model"]
    scaler  = saved["scaler"]
    feat    = saved["features"]

    # Construire le vecteur de features dans le bon ordre
    X = pd.DataFrame([{f: features_dict.get(f, 0) for f in feat}])
    X_scaled = scaler.transform(X)

    proba     = model.predict_proba(X_scaled)[0][1]
    risk_score = round(proba * 100, 1)

    if risk_score < 25:
        level = "Faible"
    elif risk_score < 50:
        level = "Modéré"
    elif risk_score < 75:
        level = "Élevé"
    else:
        level = "Critique"

    return {
        "risk_score_ml":    risk_score,
        "risk_level":       level,
        "burnout_probability": f"{risk_score}%"
    }


def run():
    # 1. Générer le dataset si nécessaire
    if not os.path.exists("burnout_dataset.csv"):
        print("Dataset non trouvé — génération automatique...")
        from generate_dataset import generate_dataset
        generate_dataset()

    # 2. Charger les données
    X, y = load_data()

    # 3. Entraîner le modèle
    model, scaler, X_test, y_test, y_pred, y_proba = train_model(X, y)

    # 4. Visualiser les résultats
    plot_results(model, X_test, y_test, y_pred, y_proba)

    # 5. Sauvegarder le modèle
    save_model(model, scaler)

    # 6. Tester avec les données réelles collectées
    print("\n--- Test avec tes données réelles ---")
    mes_features = {
        "total_sent_emails":         11,
        "late_night_email_pct":      9.1,
        "weekend_email_pct":         9.1,
        "avg_send_hour":             14.0,
        "late_night_trend":         -0.2,
        "total_events":              2,
        "declined_event_pct":        0.0,
        "decline_trend":             0.0,
        "meeting_hours_per_week":    1.2,
        "avg_meeting_duration_min":  150.0,
        "avg_attendees_per_meeting": 3.0,
    }
    result = predict_from_features(mes_features)
    print(f"Score ML      : {result['risk_score_ml']}/100")
    print(f"Niveau        : {result['risk_level']}")
    print(f"Probabilité   : {result['burnout_probability']}")


if __name__ == "__main__":
    run()
