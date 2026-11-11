from __future__ import annotations

from models import KnowledgeBaseArticle, Ticket
from services.knowledge_base_service import LOW_CONFIDENCE_THRESHOLD


_QUESTIONS_BY_CATEGORY = {
    "network": "When did the connection issue start, which service or location is affected, and what error do you see?",
    "software": "Which application and action are involved, when did this start, and what exact error appears?",
    "security": "Use your organization's approved security reporting channel now. Do not investigate further or include sensitive details here.",
    "hardware": "What device and symptom are involved? Stop using it and contact IT if it is hot, swollen, wet, or damaged.",
}


class BasicAssistanceService:
    """Provide deterministic, provider-free guidance for any employee ticket."""

    @staticmethod
    def reply(
        ticket: Ticket,
        article: KnowledgeBaseArticle | None,
        employee_message: str | None = None,
    ) -> str:
        category = ticket.ai_predicted_category or ticket.category
        priority = ticket.ai_predicted_priority
        lines = [
            "I can help you understand the ticket and gather useful details for IT.",
            f"Current status: {ticket.status.value.replace('_', ' ')}.",
            f"Predicted category: {category or 'not available yet'}; predicted priority: {priority.value if priority else 'not available yet'}.",
        ]
        if category:
            lines.append(
                f"The report is currently grouped under {category}. That describes the support area, not a confirmed cause."
            )
        else:
            lines.append("The issue description alone is not enough to confirm its cause.")

        article_match_is_sufficient = (
            ticket.solution_confidence is not None
            and float(ticket.solution_confidence) >= LOW_CONFIDENCE_THRESHOLD
        )
        if article is not None and ticket.solution_status == "MATCHED" and article_match_is_sufficient:
            lines.append(f"Relevant knowledge guidance: {article.title}. {article.summary}")
            sensitive_category = article.category.strip().lower() in {"security", "hardware"}
            if sensitive_category:
                lines.append("Because this may involve security or hardware, please contact your assigned IT team before attempting changes or repairs.")
        risk_category = (category or "").strip().lower()
        if risk_category in {"security", "hardware"}:
            lines.append("Avoid changing security or network settings, installing tools, opening equipment, or sharing sensitive information. Contact your assigned IT team for next steps.")
        elif ticket.solution_status == "NO_MATCH":
            lines.append("I could not find sufficiently relevant approved knowledge guidance. Your assigned IT team can investigate.")
        elif article is None:
            lines.append("Approved knowledge guidance is not available yet. Your assigned IT team can help if the issue is urgent.")

        if risk_category not in {"security", "hardware"}:
            lines.append("Safe next step: note the exact error, when it began, and whether other people or devices are affected. Avoid changing system or network settings or installing unapproved tools.")

        question = _QUESTIONS_BY_CATEGORY.get(
            risk_category,
            "When did this start, what were you doing just before it happened, and what exact error or behavior do you see?",
        )
        if employee_message:
            normalized_message = employee_message.lower()
            if "status" in normalized_message:
                question = f"The latest ticket status is {ticket.status.value.replace('_', ' ')}. {question}"
            elif any(term in normalized_message for term in ("why", "cause", "meaning", "what happened")):
                question = f"I cannot confirm the cause from a ticket description. The current predicted category is {category or 'not available yet'}; that prediction identifies a support area, not a diagnosis. {question}"
            else:
                question = f"Thanks for the update. I have recorded it in this ticket conversation. {question}"
        lines.append(f"To help narrow down what to check next: {question}")
        lines.append("Do not share passwords, one-time codes, API keys, access tokens, or other secrets here.")
        return "\n\n".join(lines)
