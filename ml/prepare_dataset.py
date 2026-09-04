import csv
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = PROJECT_ROOT / "datasets" / "raw" / "extracted" / "dataset-tickets-german_normalized_50_5_2.csv"
OUTPUT_PATH = PROJECT_ROOT / "datasets" / "processed" / "tickets_ml_v1.csv"

OUTPUT_COLUMNS = [
    "text",
    "category",
    "subcategory",
    "priority",
    "source_queue",
    "source_priority",
    "language",
]

PRIORITY_MAPPING = {
    "very_low": "LOW",
    "low": "LOW",
    "medium": "MEDIUM",
    "high": "HIGH",
    "critical": "HIGH",
}


def split_queue(queue: str) -> tuple[str, str]:
    category, separator, subcategory = queue.partition("/")
    return category, subcategory if separator else queue


def prepare_rows() -> tuple[list[dict[str, str]], int, int]:
    with SOURCE_PATH.open("r", encoding="utf-8-sig", newline="") as source_file:
        reader = csv.DictReader(source_file)
        source_rows = list(reader)

    prepared_rows: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()

    for source_row in source_rows:
        subject = source_row.get("subject", "")
        body = source_row.get("body", "")
        source_queue = source_row.get("queue", "")
        source_priority = source_row.get("priority", "")
        text = f"{subject} {body}"
        category, subcategory = split_queue(source_queue)

        try:
            priority = PRIORITY_MAPPING[source_priority]
        except KeyError as error:
            raise ValueError(f"Unsupported source priority: {source_priority!r}") from error

        if not all(value.strip() for value in (text, category, subcategory, priority)):
            continue

        duplicate_key = (text, category, subcategory, priority)
        if duplicate_key in seen:
            continue
        seen.add(duplicate_key)

        prepared_rows.append(
            {
                "text": text,
                "category": category,
                "subcategory": subcategory,
                "priority": priority,
                "source_queue": source_queue,
                "source_priority": source_priority,
                "language": source_row.get("language", ""),
            }
        )

    return prepared_rows, len(source_rows), len(source_rows) - len(prepared_rows)


def print_distribution(label: str, rows: list[dict[str, str]], column: str) -> None:
    counts = Counter(row[column] for row in rows)
    print(f"{label} distribution:")
    for value in sorted(counts):
        print(f"  {value}: {counts[value]}")


def main() -> None:
    rows, original_count, removed_count = prepare_rows()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Source: {SOURCE_PATH}")
    print(f"Output: {OUTPUT_PATH}")
    print(f"Original row count: {original_count}")
    print(f"Final row count: {len(rows)}")
    print(f"Rows removed: {removed_count}")
    print_distribution("Category", rows, "category")
    print_distribution("Subcategory", rows, "subcategory")
    print_distribution("Priority", rows, "priority")
    print(f"Unique categories: {len({row['category'] for row in rows})}")
    print(f"Unique subcategories: {len({row['subcategory'] for row in rows})}")


if __name__ == "__main__":
    main()
