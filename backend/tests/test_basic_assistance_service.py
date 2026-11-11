from types import SimpleNamespace

from services.basic_assistance_service import BasicAssistanceService


def test_basic_assistance_uses_ticket_facts_and_only_curated_article_summary():
    ticket = SimpleNamespace(
        status=SimpleNamespace(value="IN_PROGRESS"),
        ai_predicted_category="Software",
        category="Software",
        ai_predicted_priority=SimpleNamespace(value="HIGH"),
        solution_status="MATCHED",
        solution_confidence=0.8,
        suggested_solution="A procedural solution is not included in basic mode.",
    )
    article = SimpleNamespace(
        title="Application crash guide",
        summary="Collect the error text and note when the crash occurs.",
        category="Software",
    )

    reply = BasicAssistanceService.reply(ticket, article)

    assert "Current status: IN PROGRESS" in reply
    assert "Predicted category: Software; predicted priority: HIGH" in reply
    assert "not a confirmed cause" in reply
    assert "Application crash guide" in reply
    assert "procedural solution is not included" not in reply
    assert "passwords, one-time codes, API keys" in reply


def test_basic_assistance_does_not_show_low_relevance_knowledge_article():
    ticket = SimpleNamespace(
        status=SimpleNamespace(value="NEW"),
        ai_predicted_category="Software",
        category="Software",
        ai_predicted_priority=None,
        solution_status="MATCHED",
        solution_confidence=0.1,
        suggested_solution="Do not show this.",
    )
    article = SimpleNamespace(title="Low match", summary="Low relevance", category="Software")

    reply = BasicAssistanceService.reply(ticket, article)

    assert "below the approved relevance level" in reply
    assert "Low match" not in reply
    assert "Do not show this" not in reply


def test_security_basic_assistance_escalates_without_troubleshooting_steps():
    ticket = SimpleNamespace(
        status=SimpleNamespace(value="NEW"),
        ai_predicted_category="Security",
        category="Security",
        ai_predicted_priority=None,
        solution_status="MATCHED",
        solution_confidence=0.9,
        suggested_solution="Disable the firewall.",
    )
    article = SimpleNamespace(title="Security alert", summary="An alert needs specialist review.", category="Security")

    reply = BasicAssistanceService.reply(ticket, article)

    assert "Security alert" in reply
    assert "approved security reporting channel" in reply
    assert "Disable the firewall" not in reply
