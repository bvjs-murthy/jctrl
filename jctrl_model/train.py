"""Train the JCTRL prototype model from synthetic traffic states."""
from pathlib import Path
import argparse
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_absolute_error, classification_report

from .model import JCTRLModel, FEATURE_NAMES


def train(csv_path, out_path=None):
    df = pd.read_csv(csv_path)
    X = df[FEATURE_NAMES]
    y_phase = df["target_phase"]
    y_duration = df["target_green_duration"]

    X_train, X_test, yp_train, yp_test, yd_train, yd_test = train_test_split(
        X, y_phase, y_duration, test_size=0.2, random_state=42, stratify=y_phase
    )

    classifier = RandomForestClassifier(n_estimators=150, max_depth=12, random_state=42, n_jobs=-1)
    duration_model = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)
    classifier.fit(X_train, yp_train)
    duration_model.fit(X_train, yd_train)

    pred_phase = classifier.predict(X_test)
    pred_duration = duration_model.predict(X_test)
    print(f"Phase accuracy: {accuracy_score(yp_test, pred_phase):.3f}")
    print(f"Duration MAE: {mean_absolute_error(yd_test, pred_duration):.2f}s")
    print(classification_report(yp_test, pred_phase))

    model = JCTRLModel(classifier, duration_model)
    out_path = Path(out_path or Path(__file__).parent / "artifacts" / "jctrl_model.joblib")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out_path)
    print(f"Saved model -> {out_path}")
    return model


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data", default=str(Path(__file__).parent / "data" / "training_data.csv"))
    p.add_argument("--out", default=None)
    a = p.parse_args()
    train(a.data, a.out)
