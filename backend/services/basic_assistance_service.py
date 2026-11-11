from __future__ import annotations

from models import KnowledgeBaseArticle, Ticket


_CLARIFICATION_QUESTIONS = (
    "When did this start, and what were you doing just before it happened?",
    "What exact error or behavior do you see, and does it affect anyone else?",
)


class BasicAssistanceService:
    """Provide deterministic, provider-free guidance for any employee ticket."""

    @staticmethod
    def reply(
        ticket: Ticket,
        article: KnowledgeBaseArticle | None,
        *,
        first_message: bool,
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
            if not sensitive_category and ticket.suggested_solution:
                lines.append(f"Curated troubleshooting steps:\n{ticket.suggested_solution}")
            elif sensitive_category:
                lines.append("Because this may involve security or hardware, please contact your assigned IT team before attempting changes or repairs.")
        elif ticket.solution_status == "NO_MATCH":
            lines.append("I could not find sufficiently relevant approved knowledge guidance. Your assigned IT team can investigate.")
        else:
            lines.append("Approved knowledge guidance is not available yet. Your assigned IT team can help if the issue is urgent.")

        if first_message:
            question = _CLARIFICATION_QUESTIONS[0]
        else:
            question = _CLARIFICATION_QUESTIONS[1]
        lines.append(f"To help narrow down what to check next: {question}")
        lines.append("Do not share passwords, one-time codes, API keys, access tokens, or other secrets here.")
        return "\n\n".join(lines)
