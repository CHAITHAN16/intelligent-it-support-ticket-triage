"""Safely backfill confidence for triaged tickets using their configured model version."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import SessionLocal
from services.confidence_backfill import backfill_missing_classification_confidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist confidence-only updates; without this flag, run a dry run.",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        summary = backfill_missing_classification_confidence(db, apply=args.apply)

    mode = "applied" if args.apply else "dry run"
    print(
        f"Confidence backfill {mode}: scanned={summary.scanned}, "
        f"eligible={summary.ready}, updated={summary.updated}, "
        f"skipped={summary.skipped}"
    )
    if not args.apply and summary.ready:
        print("Review the counts, then rerun with --apply to persist confidence only.")


if __name__ == "__main__":
    main()
