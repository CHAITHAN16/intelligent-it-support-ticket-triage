"""Train and evaluate the first category classifier."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "datasets" / "processed" / "tickets_category_ml_v1.csv"
MODEL_PATH = ROOT / "ml" / "models" / "category_model_v1.joblib"
METADATA_PATH = ROOT / "ml" / "models" / "category_model_v1_metadata.json"
CONFUSION_MATRIX_PATH = ROOT / "docs" / "ml" / "category_confusion_matrix_v1.png"
RANDOM_STATE = 42


def main() -> None:
    df = pd.read_csv(DATASET_PATH)
    X = df["text"]
    y = df["category"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        stratify=y,
        random_state=RANDOM_STATE,
    )

    vectorizer_settings = {
        "lowercase": True,
        "ngram_range": [1, 2],
        "min_df": 2,
        "sublinear_tf": True,
    }
    model_settings = {
        "max_iter": 1000,
        "random_state": RANDOM_STATE,
        "class_weight": "balanced",
    }

    pipeline = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(**vectorizer_settings),
            ),
            (
                "classifier",
                LogisticRegression(**model_settings),
            ),
        ]
    )
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    classes = list(pipeline.named_steps["classifier"].classes_)
    y_probability = pipeline.predict_proba(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    macro_precision = precision_score(
        y_test, y_pred, labels=classes, average="macro", zero_division=0
    )
    macro_recall = recall_score(
        y_test, y_pred, labels=classes, average="macro", zero_division=0
    )
    macro_f1 = f1_score(
        y_test, y_pred, labels=classes, average="macro", zero_division=0
    )
    weighted_f1 = f1_score(
        y_test, y_pred, labels=classes, average="weighted", zero_division=0
    )
    report = classification_report(
        y_test,
        y_pred,
        labels=classes,
        target_names=classes,
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(y_test, y_pred, labels=classes)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFUSION_MATRIX_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)

    plt.figure(figsize=(7, 6))
    sns.heatmap(
        matrix,
        annot=True,
        fmt="d",
        cmap="Blues",
        cbar=False,
        xticklabels=classes,
        yticklabels=classes,
    )
    plt.xlabel("Predicted category")
    plt.ylabel("True category")
    plt.title("Category Classification Confusion Matrix v1")
    plt.tight_layout()
    plt.savefig(CONFUSION_MATRIX_PATH, dpi=160)
    plt.close()

    metadata = {
        "model_name": "category_classifier",
        "model_version": "v1",
        "dataset_name": "tickets_category_ml_v1.csv",
        "dataset_row_count": int(len(df)),
        "classes": classes,
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "random_state": RANDOM_STATE,
        "vectorizer_settings": vectorizer_settings,
        "model_settings": model_settings,
        "evaluation": {
            "accuracy": float(accuracy),
            "macro_precision": float(macro_precision),
            "macro_recall": float(macro_recall),
            "macro_f1": float(macro_f1),
            "weighted_f1": float(weighted_f1),
            "per_class": {
                label: {
                    "precision": float(report[label]["precision"]),
                    "recall": float(report[label]["recall"]),
                    "f1": float(report[label]["f1-score"]),
                    "support": int(report[label]["support"]),
                }
                for label in classes
            },
            "confusion_matrix": matrix.tolist(),
        },
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"dataset rows: {len(df)}")
    print(f"train size: {len(X_train)}")
    print(f"test size: {len(X_test)}")
    print("evaluation metrics:")
    print(f"test accuracy: {accuracy:.6f}")
    print(f"macro precision: {macro_precision:.6f}")
    print(f"macro recall: {macro_recall:.6f}")
    print(f"macro F1: {macro_f1:.6f}")
    print(f"weighted F1: {weighted_f1:.6f}")
    print("per-class metrics:")
    for label in classes:
        print(
            f"{label}: precision={report[label]['precision']:.6f}, "
            f"recall={report[label]['recall']:.6f}, "
            f"F1={report[label]['f1-score']:.6f}, "
            f"support={int(report[label]['support'])}"
        )
    print("confusion matrix:")
    print(matrix)

    sanity_texts = [
        "Network connection keeps dropping on my laptop",
        "Critical security breach detected on company system",
        "Application keeps crashing after the latest update",
        "Need help with marketing campaign",
    ]
    sanity_probabilities = pipeline.predict_proba(sanity_texts)
    sanity_predictions = pipeline.predict(sanity_texts)
    print("sanity predictions:")
    for text, prediction, probabilities in zip(
        sanity_texts, sanity_predictions, sanity_probabilities
    ):
        probability_map = {
            label: round(float(probability), 6)
            for label, probability in zip(classes, probabilities)
        }
        print(f"{text}")
        print(f"predicted category: {prediction}")
        print(f"probability by class: {probability_map}")

    print(f"model: {MODEL_PATH}")
    print(f"metadata: {METADATA_PATH}")
    print(f"confusion matrix image: {CONFUSION_MATRIX_PATH}")


if __name__ == "__main__":
    main()
