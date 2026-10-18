import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split

from src.data import load_dataset
from src.model import build_model


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = PROJECT_ROOT / "models"
MODEL_PATH = MODEL_DIR / "spam_model.joblib"
METRICS_PATH = MODEL_DIR / "metrics.json"


def main():
    data = load_dataset()

    X_train, X_test, y_train, y_test = train_test_split(
        data["text"],
        data["label"],
        test_size=0.2,
        random_state=42,
        stratify=data["label"],
    )

    model = build_model()
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    metrics = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_messages": int(len(data)),
        "training_messages": int(len(X_train)),
        "test_messages": int(len(X_test)),
        "accuracy": float(accuracy_score(y_test, predictions)),
        "spam_precision": float(
            precision_score(y_test, predictions, pos_label="spam", zero_division=0)
        ),
        "spam_recall": float(
            recall_score(y_test, predictions, pos_label="spam", zero_division=0)
        ),
        "spam_f1": float(
            f1_score(y_test, predictions, pos_label="spam", zero_division=0)
        ),
        "confusion_matrix": confusion_matrix(
            y_test,
            predictions,
            labels=["ham", "spam"],
        ).tolist(),
        "confusion_matrix_labels": ["ham", "spam"],
        "classification_report": classification_report(
            y_test,
            predictions,
            labels=["ham", "spam"],
            target_names=["ham", "spam"],
            output_dict=True,
            zero_division=0,
        ),
    }

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    METRICS_PATH.write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    print(f"Dataset messages: {len(data)}")
    print(f"Training messages: {len(X_train)}")
    print(f"Test messages: {len(X_test)}")
    print("\nClassification report:")
    print(
        classification_report(
            y_test,
            predictions,
            labels=["ham", "spam"],
            target_names=["ham", "spam"],
            zero_division=0,
        )
    )
    print("Confusion matrix (rows=actual, columns=predicted; ham, spam):")
    print(metrics["confusion_matrix"])
    print(f"\nSaved model: {MODEL_PATH}")
    print(f"Saved metrics: {METRICS_PATH}")


if __name__ == "__main__":
    main()