"""Prepare the first clean English category dataset."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "datasets" / "raw" / "extracted" / (
    "aa_dataset-tickets-multi-lang-5-2-50-version.csv"
)
OUTPUT_PATH = ROOT / "datasets" / "processed" / "tickets_category_ml_v1.csv"
TAG_COLUMNS = [f"tag_{index}" for index in range(1, 9)]
TARGET_CATEGORIES = ["Network", "Security", "Software", "Other"]


def normalize(value: object) -> str:
    """Normalize text for deterministic matching without changing output text."""
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def has_term(text: str, terms: set[str]) -> bool:
    return any(
        re.search(r"(?<![a-z])" + re.escape(term) + r"(?![a-z])", text)
        for term in terms
    )


def has_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def has_issue_language(text: str) -> bool:
    return has_phrase(
        text,
        (
            "problem",
            "issue",
            "failure",
            "failed",
            "malfunction",
            "not working",
            "does not work",
            "doesn t work",
            "unable",
            "cannot",
            "can t",
            "wont",
            "won t",
            "error",
            "crash",
            "crashing",
            "outage",
            "disruption",
            "disconnect",
            "disconnected",
            "blocked",
            "denied",
            "breach",
            "attack",
            "virus",
            "malware",
            "phishing",
            "vulnerability",
            "intrusion",
            "threat",
            "access",
        ),
    )


def category_evidence(row: pd.Series) -> dict[str, bool]:
    subject = normalize(row["subject"])
    body = normalize(row["body"])
    text = f"{subject} {body}".strip()
    tag_values = {
        normalize(value)
        for value in row[TAG_COLUMNS]
        if pd.notna(value) and str(value).strip()
    }
    issue = has_issue_language(text)
    evidence: dict[str, bool] = {}

    hardware_objects = {
        "laptop",
        "desktop",
        "printer",
        "monitor",
        "keyboard",
        "mouse",
        "headset",
        "webcam",
        "screen",
        "display",
        "battery",
        "charger",
        "hard drive",
        "hdd",
        "usb",
        "peripheral",
        "firmware",
        "device",
        "equipment",
        "pc",
        "computer",
    }
    evidence["Hardware"] = (
        has_term(text, hardware_objects)
        and (
            bool({"hardware", "hardware conflict"} & tag_values)
            or has_phrase(
                text,
                (
                    "hardware failure",
                    "hardware problem",
                    "hardware issue",
                    "hardware is",
                    "hardware no longer",
                ),
            )
        )
        and issue
    )

    network_terms = {
        "network",
        "vpn",
        "router",
        "switch",
        "wifi",
        "wi fi",
        "wireless",
        "dhcp",
        "dns",
        "firewall",
        "connectivity",
    }
    evidence["Network"] = (
        has_term(text, network_terms)
        and issue
        and (
            bool({"network", "vpn", "router", "switch"} & tag_values)
            or has_phrase(
                text,
                (
                    "network connectivity",
                    "network connection",
                    "wifi",
                    "wi fi",
                    "wireless",
                    "dhcp",
                    "dns",
                    "router",
                    "switch",
                    "vpn connection",
                    "network outage",
                ),
            )
        )
    )

    security_terms = {
        "security",
        "breach",
        "malware",
        "virus",
        "phishing",
        "vulnerability",
        "intrusion",
        "threat",
        "attack",
        "unauthorized",
        "cybersecurity",
        "cyber threat",
        "endpoint security",
        "information security",
        "data security",
        "security incident",
        "security breach",
        "encryption",
        "privacy",
        "safeguard",
        "safeguarding",
        "protect",
        "securely",
        "securing",
    }
    security_tags = {
        "cybersecurity",
        "data security",
        "information security",
        "endpoint security",
        "system security",
        "data breach",
        "malware",
        "virus",
        "phishing",
        "vulnerability",
        "intrusion",
        "cyber threat",
        "unauthorized access",
        "security best practices",
        "security improvement",
        "security measures",
        "security update",
    }
    evidence["Security"] = (
        (has_term(text, security_terms) or bool(security_tags & tag_values))
        and (
            has_phrase(
                text,
                (
                    "breach",
                    "attack",
                    "malware",
                    "virus",
                    "phishing",
                    "vulnerability",
                    "intrusion",
                    "threat",
                    "unauthorized",
                    "encryption",
                    "privacy",
                    "safeguard",
                    "safeguarding",
                    "protect",
                    "secure",
                    "security",
                ),
            )
            and (
                issue
                or has_phrase(
                    text,
                    (
                        "safeguard",
                        "safeguarding",
                        "protect",
                        "security measures",
                        "security best practices",
                        "secure medical",
                        "securely connect",
                        "securing",
                    ),
                )
            )
        )
    )

    access_tags = {
        "access control",
        "access management",
        "access restriction",
        "unauthorized access",
        "authentication",
        "password",
        "password reset",
        "credential",
        "credentials",
    }
    access_text = has_phrase(
        text,
        (
            "login problem",
            "login issue",
            "log in",
            "password",
            "account management",
            "account access",
            "permission",
            "permissions",
            "authentication",
            "authenticate",
            "access denied",
            "access issue",
            "sign in",
            "signin",
            "credential",
        ),
    )
    evidence["Access & Identity"] = (
        (access_text or bool(access_tags & tag_values))
        and (
            issue
            or has_phrase(
                text,
                (
                    "permission",
                    "access denied",
                    "account management",
                    "account access",
                    "password reset",
                    "login problem",
                    "login issue",
                    "authentication process",
                ),
            )
        )
    )

    software_terms = {
        "software",
        "application",
        "app",
        "outlook",
        "api",
        "database",
        "docker",
        "python",
        "windows",
        "macos",
        "ubuntu",
        "microservice",
        "microservices",
        "bug",
        "crash",
    }
    software_tags = {
        "software bug",
        "software problem",
        "software malfunction",
        "software conflict",
        "software incompatibility",
        "software compatibility",
        "software update",
        "application issue",
        "app issue",
        "software enhancement",
        "software integration",
    }
    evidence["Software"] = (
        has_term(text, software_terms)
        and issue
        and (
            bool(software_tags & tag_values)
            or has_phrase(
                text,
                (
                    "software error",
                    "software problem",
                    "software issue",
                    "software failure",
                    "software malfunction",
                    "application error",
                    "application issue",
                    "application crash",
                    "application problem",
                    "app crash",
                    "app error",
                    "bug in",
                    "bug affecting",
                    "crashing",
                ),
            )
        )
    )

    other_tags = {
        "marketing",
        "digital marketing",
        "sales",
        "brand",
        "branding",
        "seo",
        "campaign",
        "social media",
        "audience",
        "customer service",
        "billing",
        "payment",
        "human resources",
        "hr",
    }
    evidence["Other"] = bool(other_tags & tag_values) and not any(evidence.values())
    return evidence


def main() -> None:
    source = pd.read_csv(INPUT_PATH)
    original_row_count = len(source)

    filtered = source[
        source["language"].eq("en")
        & source["queue"].isin({"Technical Support", "IT Support"})
    ].copy()
    filtered["text"] = (
        filtered["subject"].fillna("").astype(str).str.strip()
        + " "
        + filtered["body"].fillna("").astype(str).str.strip()
    ).str.strip()
    filtered = filtered[filtered["text"].ne("")].copy()

    evidence = filtered.apply(category_evidence, axis=1, result_type="expand")
    evidence["match_count"] = evidence.sum(axis=1)
    evidence["target_match_count"] = evidence[TARGET_CATEGORIES].sum(axis=1)
    evidence["assigned_category"] = evidence[TARGET_CATEGORIES].idxmax(axis=1)
    excluded_evidence = evidence[["Hardware", "Access & Identity"]].any(axis=1)
    valid_target = (evidence["target_match_count"] == 1) & ~excluded_evidence
    evidence.loc[~valid_target, "assigned_category"] = pd.NA

    hardware_count = int((evidence["Hardware"] & (evidence["match_count"] == 1)).sum())
    access_count = int(
        (evidence["Access & Identity"] & (evidence["match_count"] == 1)).sum()
    )
    ambiguous_count = int((evidence["match_count"] > 1).sum())
    unlabeled_count = int((evidence["match_count"] == 0).sum())

    usable = filtered.loc[evidence["assigned_category"].notna()].copy()
    usable["category"] = evidence.loc[evidence["assigned_category"].notna(), "assigned_category"].to_numpy()
    usable = usable[usable["category"].isin(TARGET_CATEGORIES)].copy()

    output = usable[
        ["text", "category", "queue", "type", "priority", "language"]
    ].rename(
        columns={
            "queue": "source_queue",
            "type": "source_type",
            "priority": "source_priority",
        }
    )
    output = output.drop_duplicates(subset=["text", "category"], keep="first")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(OUTPUT_PATH, index=False)

    counts = output["category"].value_counts().reindex(TARGET_CATEGORIES, fill_value=0)
    percentages = (counts / len(output) * 100).round(2)

    print(f"original row count: {original_row_count}")
    print(f"filtered English IT count: {len(filtered)}")
    print(f"final usable row count: {len(output)}")
    print(f"excluded ambiguous count: {ambiguous_count}")
    print(f"excluded unlabeled count: {unlabeled_count}")
    print(f"excluded Hardware count: {hardware_count}")
    print(f"excluded Access & Identity count: {access_count}")
    print("count per final category:")
    print(counts.to_string())
    print("percentage per class:")
    print(percentages.to_string())
    print(f"output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
