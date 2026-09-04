import csv
import json
from pathlib import Path

import joblib
from PIL import Image, ImageDraw
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


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "datasets" / "processed" / "tickets_ml_v1.csv"
MODEL_DIR = PROJECT_ROOT / "ml" / "models"
MODEL_PATH = MODEL_DIR / "subcategory_model.joblib"
METADATA_PATH = MODEL_DIR / "subcategory_model_metadata.json"
CONFUSION_MATRIX_PATH = PROJECT_ROOT / "docs" / "ml" / "subcategory_confusion_matrix.png"
RANDOM_STATE = 42


def load_it_tickets() -> tuple[list[str], list[str]]:
    with DATASET_PATH.open("r", encoding="utf-8-sig", newline="") as dataset_file:
        rows = csv.DictReader(dataset_file)
        it_rows = [row for row in rows if row["category"] == "IT & Technology"]

    texts = [row["text"] for row in it_rows]
    labels = [row["subcategory"] for row in it_rows]
    return texts, labels


def save_confusion_matrix(matrix: list[list[int]], class_names: list[str]) -> None:
    cell_size = 150
    left_margin = 210
    top_margin = 100
    image = Image.new(
        "RGB",
        (left_margin + cell_size * len(class_names) + 30, top_margin + cell_size * len(class_names) + 50),
        "white",
    )
    draw = ImageDraw.Draw(image)
    maximum = max(max(row) for row in matrix) or 1

    draw.text((10, 10), "IT subcategory confusion matrix", fill="black")
    for index, class_name in enumerate(class_names):
        x = left_margin + index * cell_size
        y = top_margin + index * cell_size
        draw.text((x + 5, top_margin - 35), class_name, fill="black")
        draw.text((10, y + cell_size // 2 - 8), class_name, fill="black")

    for row_index, row in enumerate(matrix):
        for column_index, value in enumerate(row):
            intensity = int(255 - (value / maximum) * 180)
            x0 = left_margin + column_index * cell_size
            y0 = top_margin + row_index * cell_size
            draw.rectangle((x0, y0, x0 + cell_size, y0 + cell_size), fill=(intensity, intensity, 255), outline="black")
            label = str(value)
            draw.text((x0 + cell_size // 2 - 5 * len(label), y0 + cell_size // 2 - 8), label, fill="black")

    image.save(CONFUSION_MATRIX_PATH)


def main() -> None:
    texts, labels = load_it_tickets()
    class_names = sorted(set(labels))
    train_texts, test_texts, train_labels, test_labels = train_test_split(
        texts,
        labels,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=labels,
    )

    model = Pipeline(
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
                LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
            ),
        ]
    )
    model.fit(train_texts, train_labels)
    predictions = model.predict(test_texts)

    accuracy = accuracy_score(test_labels, predictions)
    macro_precision = precision_score(test_labels, predictions, average="macro", zero_division=0)
    macro_recall = recall_score(test_labels, predictions, average="macro", zero_division=0)
    macro_f1 = f1_score(test_labels, predictions, average="macro", zero_division=0)
    report = classification_report(
        test_labels,
        predictions,
        labels=class_names,
        target_names=class_names,
        zero_division=0,
    )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    CONFUSION_MATRIX_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    METADATA_PATH.write_text(
        json.dumps(
            {
                "model_name": "IT support subcategory classifier",
                "model_version": "ml-v1",
                "target": "subcategory",
                "dataset_path": "datasets/processed/tickets_ml_v1.csv",
                "training_sample_count": len(train_texts),
                "test_sample_count": len(test_texts),
                "random_state": RANDOM_STATE,
                "class_names": class_names,
                "accuracy": accuracy,
                "macro_precision": macro_precision,
                "macro_recall": macro_recall,
                "macro_f1": macro_f1,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    save_confusion_matrix(confusion_matrix(test_labels, predictions, labels=class_names).tolist(), class_names)

    print(f"Training samples: {len(train_texts)}")
    print(f"Test samples: {len(test_texts)}")
    print("Training class distribution:")
    for class_name in class_names:
        print(f"  {class_name}: {train_labels.count(class_name)}")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Macro precision: {macro_precision:.4f}")
    print(f"Macro recall: {macro_recall:.4f}")
    print(f"Macro F1: {macro_f1:.4f}")
    print("Classification report:")
    print(report)
    print(f"Model saved to: {MODEL_PATH}")
    print(f"Metadata saved to: {METADATA_PATH}")
    print(f"Confusion matrix saved to: {CONFUSION_MATRIX_PATH}")


if __name__ == "__main__":
    main()
