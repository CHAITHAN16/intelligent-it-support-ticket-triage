from __future__ import annotations

from models import KnowledgeBaseArticle, Ticket


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

        if article is not None and ticket.solution_status == "MATCHED":
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

        question = _QUESTIONS_BY_CATEGORY.get(
            risk_category,
            "When did this start, what were you doing just before it happened, and what exact error or behavior do you see?",
        )
        lines.append(f"To help narrow down what to check next: {question}")
        lines.append("Do not share passwords, one-time codes, API keys, access tokens, or other secrets here.")
        return "\n\n".join(lines)
