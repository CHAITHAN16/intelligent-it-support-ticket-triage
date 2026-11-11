from __future__ import annotations

import re
from dataclasses import dataclass

from models import KnowledgeBaseArticle, Ticket
from services.knowledge_base_service import LOW_CONFIDENCE_THRESHOLD


_TIME_RE = re.compile(
    r"\b(?:this morning|this afternoon|tonight|today|yesterday|last night|"
    r"this week|last week|since\s+(?:[\w-]+\s+)?(?:morning|afternoon|evening|yesterday|today))\b",
    re.IGNORECASE,
)
_SERVICE_NAMES = (
    ("vpn", "VPN"),
    ("wi-fi", "Wi-Fi"),
    ("wifi", "Wi-Fi"),
    ("wireless", "Wi-Fi"),
    ("email", "Email"),
    ("outlook", "Outlook"),
    ("printer", "Printer"),
    ("printing", "Printing"),
    ("teams", "Microsoft Teams"),
    ("sharepoint", "SharePoint"),
    ("network", "Network"),
    ("laptop", "Laptop"),
    ("computer", "Computer"),
    ("application", "Application"),
    ("app", "Application"),
)
_ERROR_PHRASES = (
    "connection timed out",
    "connection timeout",
    "timed out",
    "timeout",
    "connection refused",
    "authentication failed",
    "access denied",
    "server unavailable",
    "service unavailable",
    "cannot connect",
    "can't connect",
    "failed to connect",
    "error",
)
_STEP_RE = re.compile(
    r"\bI\s+(?:have\s+)?(?:tried|restarted|rebooted|checked|tested|reconnected|"
    r"updated|reinstalled|cleared|followed)\s+([^.!?\n]{2,140})",
    re.IGNORECASE,
)
_SECRET_RE = re.compile(
    r"\b(?:password|passcode|one[ -]?time(?: password)?(?: code)?|otp|"
    r"api[ _-]?key|access[ _-]?token|token)\b",
    re.IGNORECASE,
)
_SECRET_VALUE_RE = re.compile(
    r"\b(password|passcode|one[ -]?time(?: password)?(?: code)?|otp|"
    r"api[ _-]?key|access[ _-]?token|token)\b\s*(?:(?:is|was)\s+|[:=]\s*|\s+)"
    r"[^\s,;]+",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class BasicAssistanceContext:
    issue_summary: str
    start_time: str | None
    affected_devices_users: str | None
    affected_service: str | None
    exact_error: str | None
    known_troubleshooting_steps: list[str]
    missing_information: list[str]
    next_recommended_question: str

    def as_dict(self) -> dict[str, object]:
        return {
            "issue_summary": self.issue_summary,
            "start_time": self.start_time,
            "affected_devices_users": self.affected_devices_users,
            "affected_service": self.affected_service,
            "exact_error": self.exact_error,
            "known_troubleshooting_steps": self.known_troubleshooting_steps,
            "missing_information": self.missing_information,
            "next_recommended_question": self.next_recommended_question,
        }


class BasicAssistanceService:
    """Provide deterministic, provider-free assistance grounded in ticket history."""

    @staticmethod
    def build_context(
        ticket: Ticket,
        article: KnowledgeBaseArticle | None,
        history: list[object],
    ) -> BasicAssistanceContext:
        employee_text = "\n".join(
            str(getattr(message, "body", ""))
            for message in history
            if getattr(message, "speaker", None) == "EMPLOYEE"
        )
        source_text = " ".join(part for part in (ticket.title, ticket.description, employee_text) if part)
        safe_text = _SECRET_RE.sub(" ", _SECRET_VALUE_RE.sub("[REDACTED]", source_text))
        lowered = safe_text.lower()
        category = (ticket.ai_predicted_category or ticket.category or "").strip().lower()
        issue_summary = ticket.title.strip()
        if ticket.description.strip() and ticket.description.strip().lower() not in issue_summary.lower():
            issue_summary = f"{issue_summary}: {ticket.description.strip()}"

        time_match = _TIME_RE.search(safe_text)
        start_time = time_match.group(0) if time_match else None

        affected = None
        if re.search(r"\b(?:only|just)\s+(?:my|the)\s+(?:laptop|computer|desktop|phone|device)\b", lowered):
            device_match = re.search(r"\b(laptop|computer|desktop|phone|device)\b", lowered)
            affected = f"One device: {device_match.group(1) if device_match else 'employee device'}"
        elif re.search(r"\b(?:only me|just me|only myself|no one else)\b", lowered):
            affected = "One user (employee)"
        else:
            count_match = re.search(r"\b(\d+)\s+(users?|devices?|computers?|laptops?)\b", lowered)
            if count_match:
                affected = f"{count_match.group(1)} {count_match.group(2)}"
            elif re.search(r"\b(?:everyone|all users|multiple users|several users|many users)\b", lowered):
                affected = "Multiple users"

        affected_service = None
        for needle, label in _SERVICE_NAMES:
            if re.search(rf"\b{re.escape(needle)}\b", lowered):
                affected_service = label
                break
        if affected_service is None and article is not None:
            affected_service = article.title

        exact_error = None
        for phrase in _ERROR_PHRASES:
            match = re.search(rf"\b{re.escape(phrase)}\b", safe_text, re.IGNORECASE)
            if match:
                exact_error = match.group(0)
                break

        steps: list[str] = []
        for message in history:
            if getattr(message, "speaker", None) != "EMPLOYEE":
                continue
            body = _SECRET_VALUE_RE.sub("[REDACTED]", str(getattr(message, "body", "")))
            for match in _STEP_RE.finditer(body):
                step = match.group(1).strip(" ,;:")
                if step and step not in steps:
                    steps.append(step)

        missing: list[str] = []
        if start_time is None:
            missing.append("when the issue started")
        if affected is None:
            missing.append("which devices or users are affected")
        if affected_service is None:
            missing.append("which service or application is affected")
        if exact_error is None:
            missing.append("the exact error or behavior")
        if not steps:
            missing.append("what troubleshooting has already been tried")

        question = BasicAssistanceService._next_question(
            category=category,
            service=affected_service,
            start_time=start_time,
            affected=affected,
            exact_error=exact_error,
            steps=steps,
        )
        if affected_service == "VPN":
            missing.append("whether internet works without the VPN")
        return BasicAssistanceContext(
            issue_summary=issue_summary,
            start_time=start_time,
            affected_devices_users=affected,
            affected_service=affected_service,
            exact_error=exact_error,
            known_troubleshooting_steps=steps,
            missing_information=missing,
            next_recommended_question=question,
        )

    @staticmethod
    def _next_question(
        *,
        category: str,
        service: str | None,
        start_time: str | None,
        affected: str | None,
        exact_error: str | None,
        steps: list[str],
    ) -> str:
        if category == "security":
            return "Please use your organization's approved security reporting channel immediately. Do not investigate further or share sensitive details here."
        if category == "hardware":
            return "What device is involved, and is there any heat, swelling, liquid exposure, or visible damage? Stop using it and contact IT if so."
        if category == "network" or service in {"VPN", "Wi-Fi", "Network"}:
            if start_time is None:
                return "When did the connection issue start?"
            if affected is None:
                return "Is this affecting only your device, or are other people or devices affected too?"
            if exact_error is None:
                return "What exact error message appears when you connect?"
            if service == "VPN":
                return "Can you access the internet when you are not connected to the VPN?"
            if service == "Wi-Fi":
                return "Can another device connect to the same Wi-Fi network?"
            if not steps:
                return "What have you already tried, if anything? Please avoid changing network settings."
            return "Does the connection work from another location or network, if your organization permits that test?"
        if category == "software" or service in {"Application", "Outlook", "Microsoft Teams", "SharePoint"}:
            if service is None or service == "Application":
                return "Which application is affected?"
            if start_time is None:
                return "When did the application issue start?"
            if exact_error is None:
                return "What exact error or behavior do you see in the application?"
            if affected is None:
                return "Is anyone else seeing this application issue, or is it limited to your device?"
            if not steps:
                return "What have you tried so far, if anything?"
            return "Does the issue happen every time, or only after a particular action?"
        if start_time is None:
            return "When did this issue start?"
        if affected is None:
            return "Which device or users are affected?"
        if service is None:
            return "Which service or application is involved?"
        if exact_error is None:
            return "What exact error or behavior do you see?"
        if not steps:
            return "What have you already tried, if anything?"
        return "Is there another detail about the impact that would help the assigned IT team?"

    @staticmethod
    def reply(
        ticket: Ticket,
        article: KnowledgeBaseArticle | None,
        history: list[object],
    ) -> str:
        context = BasicAssistanceService.build_context(ticket, article, history)
        category = ticket.ai_predicted_category or ticket.category
        priority = ticket.ai_predicted_priority
        lines = [
            "I can help explain the ticket and collect details for IT.",
            f"Current status: {ticket.status.value.replace('_', ' ')}.",
            f"Predicted category: {category or 'not available yet'}; predicted priority: {priority.value if priority else 'not available yet'}.",
            "I cannot confirm the cause from the report alone.",
        ]
        known = []
        if context.start_time:
            known.append(f"started {context.start_time}")
        if context.affected_devices_users:
            known.append(context.affected_devices_users)
        if context.affected_service:
            known.append(f"service: {context.affected_service}")
        if context.exact_error:
            known.append(f"error: {context.exact_error}")
        if context.known_troubleshooting_steps:
            known.append("steps tried: " + "; ".join(context.known_troubleshooting_steps))
        if known:
            lines.append("What I have so far: " + "; ".join(known) + ".")

        article_is_relevant = (
            article is not None
            and ticket.solution_status == "MATCHED"
            and ticket.solution_confidence is not None
            and float(ticket.solution_confidence) >= LOW_CONFIDENCE_THRESHOLD
        )
        if article_is_relevant:
            lines.append(f"Approved knowledge guidance: {article.title}. {article.summary}")
        elif ticket.solution_status in {"NO_MATCH", "MATCHED"}:
            lines.append("There is no sufficiently relevant approved knowledge guidance to share for this ticket. Your assigned IT team can investigate.")
        else:
            lines.append("Approved knowledge guidance is not available yet. Your assigned IT team can help if the issue is urgent.")

        if (category or "").lower() not in {"security", "hardware"}:
            lines.append("Safe next step: record the error, when it happened, and who or what was affected. Avoid changing system or network settings or installing unapproved tools.")
        lines.append(f"Next question: {context.next_recommended_question}")
        lines.append("Never share passwords, one-time codes, API keys, access tokens, or other secrets here.")
        return "\n\n".join(lines)
