import json
from collections import Counter
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "datasets" / "processed" / "tickets_priority_ml_v2.csv"
MODEL_DIR = PROJECT_ROOT / "ml" / "models"
MODEL_PATH = MODEL_DIR / "priority_model_v2.joblib"
METADATA_PATH = MODEL_DIR / "priority_model_v2_metadata.json"
CONFUSION_MATRIX_PATH = PROJECT_ROOT / "docs" / "ml" / "priority_confusion_matrix_v2.png"
RANDOM_STATE = 42


def load_dataset() -> pd.DataFrame:
    dataset = pd.read_csv(DATASET_PATH)
    required_columns = {"text", "priority"}
    missing_columns = required_columns - set(dataset.columns)
    if missing_columns:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing_columns)}")
    dataset = dataset.dropna(subset=["text", "priority"]).copy()
    dataset["text"] = dataset["text"].astype(str)
    dataset["priority"] = dataset["priority"].astype(str)
    return dataset


def build_pipeline() -> Pipeline:
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    min_df=2,
                    sublinear_tf=True,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1000,
                    random_state=RANDOM_STATE,
                    class_weight="balanced",
                ),
            ),
        ]
    )


def save_confusion_matrix_image(matrix: list[list[int]], class_names: list[str]) -> None:
    figure, axis = plt.subplots(figsize=(8, 6), dpi=200)
    image = axis.imshow(matrix, interpolation="nearest", cmap="Blues")
    axis.figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    axis.set(
        title="Priority Confusion Matrix - ML v2",
        xlabel="Predicted label",
        ylabel="True label",
        xticks=range(len(class_names)),
        yticks=range(len(class_names)),
    )
    axis.set_xticklabels(class_names, rotation=45, ha="right")
    axis.set_yticklabels(class_names)

    threshold = max(max(row) for row in matrix) / 2 if matrix else 0
    for row_index, row in enumerate(matrix):
        for column_index, value in enumerate(row):
            axis.text(
                column_index,
                row_index,
                str(value),
                ha="center",
                va="center",
                color="white" if value > threshold else "black",
            )

    figure.tight_layout()
    CONFUSION_MATRIX_PATH.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(CONFUSION_MATRIX_PATH, bbox_inches="tight")
    plt.close(figure)


def sanitize_number(value: float) -> float:
    return float(value)


def main() -> None:
    dataset = load_dataset()
    texts = dataset["text"].tolist()
    labels = dataset["priority"].tolist()
    class_names = sorted(dataset["priority"].unique().tolist())

    train_texts, test_texts, train_labels, test_labels = train_test_split(
        texts,
        labels,
        test_size=0.2,
        stratify=labels,
        random_state=RANDOM_STATE,
    )

    model = build_pipeline()
    model.fit(train_texts, train_labels)
    predictions = model.predict(test_texts)

    accuracy = accuracy_score(test_labels, predictions)
    macro_precision = precision_score(test_labels, predictions, average="macro", zero_division=0)
    macro_recall = recall_score(test_labels, predictions, average="macro", zero_division=0)
    macro_f1 = f1_score(test_labels, predictions, average="macro", zero_division=0)
    weighted_f1 = f1_score(test_labels, predictions, average="weighted", zero_division=0)
    report = classification_report(
        test_labels,
        predictions,
        labels=class_names,
        target_names=class_names,
        zero_division=0,
    )
    per_class_precision, per_class_recall, per_class_f1, per_class_support = precision_recall_fscore_support(
        test_labels,
        predictions,
        labels=class_names,
        zero_division=0,
    )
    confusion = confusion_matrix(test_labels, predictions, labels=class_names)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    metadata = {
        "model_version": "ml-v2",
        "task": "priority_classification",
        "dataset": "tickets_priority_ml_v2.csv",
        "train_size": len(train_texts),
        "test_size": len(test_texts),
        "random_state": RANDOM_STATE,
        "vectorizer_configuration": {
            "lowercase": True,
            "ngram_range": [1, 2],
            "min_df": 2,
            "sublinear_tf": True,
        },
        "classifier_configuration": {
            "max_iter": 1000,
            "random_state": RANDOM_STATE,
            "class_weight": "balanced",
        },
        "class_distribution": dict(Counter(labels)),
        "accuracy": sanitize_number(accuracy),
        "macro_precision": sanitize_number(macro_precision),
        "macro_recall": sanitize_number(macro_recall),
        "macro_f1": sanitize_number(macro_f1),
        "weighted_f1": sanitize_number(weighted_f1),
        "classes": class_names,
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    save_confusion_matrix_image(confusion.tolist(), class_names)

    sanity_checks = [
        "VPN connection failure",
        "laptop won't start",
        "suspicious login",
        "application crashing",
        "network outage",
        "password reset",
        "malware alert",
        "WiFi disconnected",
        "software installation",
        "critical production server outage",
    ]
    sanity_probabilities = model.predict_proba(sanity_checks)
    sanity_predictions = model.predict(sanity_checks)
    class_index = {class_name: index for index, class_name in enumerate(model.named_steps["classifier"].classes_)}

    print(f"Training samples: {len(train_texts)}")
    print(f"Test samples: {len(test_texts)}")
    print("Training class distribution:")
    for class_name in class_names:
        print(f"  {class_name}: {train_labels.count(class_name)}")
    print(f"Test accuracy: {accuracy:.4f}")
    print(f"Macro precision: {macro_precision:.4f}")
    print(f"Macro recall: {macro_recall:.4f}")
    print(f"Macro F1: {macro_f1:.4f}")
    print(f"Weighted F1: {weighted_f1:.4f}")
    print("Per-class metrics:")
    for index, class_name in enumerate(class_names):
        print(
            f"  {class_name}: precision={per_class_precision[index]:.4f}, "
            f"recall={per_class_recall[index]:.4f}, "
            f"f1={per_class_f1[index]:.4f}, "
            f"support={int(per_class_support[index])}"
        )
    print("Classification report:")
    print(report)
    print("Confusion matrix:")
    print(confusion)
    print(f"Model saved to: {MODEL_PATH}")
    print(f"Metadata saved to: {METADATA_PATH}")
    print(f"Confusion matrix saved to: {CONFUSION_MATRIX_PATH}")
    print("Inference sanity checks:")
    for ticket_text, predicted_label, probabilities in zip(sanity_checks, sanity_predictions, sanity_probabilities):
        predicted_probability = probabilities[class_index[predicted_label]]
        probability_map = {class_name: round(float(probabilities[class_index[class_name]]), 6) for class_name in class_names}
        print(f"  Input: {ticket_text}")
        print(f"    Predicted priority: {predicted_label}")
        print(f"    Probability by class: {probability_map}")
        print(f"    Predicted class probability: {predicted_probability:.6f}")


if __name__ == "__main__":
    main()
