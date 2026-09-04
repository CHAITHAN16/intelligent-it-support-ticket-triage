import csv
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = PROJECT_ROOT / "datasets" / "raw" / "extracted" / "aa_dataset-tickets-multi-lang-5-2-50-version.csv"
OUTPUT_PATH = PROJECT_ROOT / "datasets" / "processed" / "tickets_priority_ml_v2.csv"

OUTPUT_COLUMNS = [
    "text",
    "priority",
    "source_queue",
    "source_type",
    "language",
]

ALLOWED_QUEUES = {"Technical Support", "IT Support"}
PRIORITY_MAPPING = {
    "low": "LOW",
    "medium": "MEDIUM",
    "high": "HIGH",
}


def prepare_rows() -> tuple[list[dict[str, str]], int, int, int]:
    with SOURCE_PATH.open("r", encoding="utf-8-sig", newline="") as source_file:
        source_rows = list(csv.DictReader(source_file))

    english_rows = [row for row in source_rows if row.get("language") == "en"]
    filtered_rows = [row for row in english_rows if row.get("queue") in ALLOWED_QUEUES]
    prepared_rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for source_row in filtered_rows:
        subject = source_row.get("subject") or ""
        body = source_row.get("body") or ""
        source_priority = source_row.get("priority") or ""
        text = subject + " " + body

        if not source_priority:
            continue
        try:
            priority = PRIORITY_MAPPING[source_priority]
        except KeyError as error:
            raise ValueError(f"Unsupported source priority: {source_priority!r}") from error

        duplicate_key = (text, priority)
        if duplicate_key in seen:
            continue
        seen.add(duplicate_key)

        prepared_rows.append(
            {
                "text": text,
                "priority": priority,
                "source_queue": source_row.get("queue") or "",
                "source_type": source_row.get("type") or "",
                "language": source_row.get("language") or "",
            }
        )

    return prepared_rows, len(english_rows), len(filtered_rows), len(source_rows)


def print_distribution(label: str, rows: list[dict[str, str]], column: str) -> None:
    counts = Counter(row[column] for row in rows)
    print(f"{label} distribution:")
    for value in sorted(counts):
        print(f"  {value}: {counts[value]}")


def main() -> None:
    rows, english_count, filtered_count, _ = prepare_rows()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Source English records: {english_count}")
    print(f"Records after IT queue filtering: {filtered_count}")
    print(f"Records removed: {english_count - len(rows)}")
    print(f"Final row count: {len(rows)}")
    print_distribution("Priority", rows, "priority")
    print_distribution("Queue", rows, "source_queue")
    print_distribution("Type", rows, "source_type")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
