from types import SimpleNamespace

from services.basic_assistance_service import BasicAssistanceService


def message(speaker: str, body: str):
    return SimpleNamespace(speaker=speaker, body=body)


def ticket(*, category="Network", title="VPN connection problem", description="VPN fails to connect"):
    return SimpleNamespace(
        status=SimpleNamespace(value="IN_PROGRESS"),
        ai_predicted_category=category,
        category=category,
        ai_predicted_priority=SimpleNamespace(value="HIGH"),
        title=title,
        description=description,
        solution_status="NO_MATCH",
        solution_confidence=None,
        suggested_solution=None,
    )


def test_vpn_follow_up_uses_answers_and_does_not_repeat_original_questions():
    history = [
        message("AI", "When did the connection issue start, and what error do you see?"),
        message(
            "EMPLOYEE",
            "The VPN issue started this morning. Only my laptop is affected. "
            "I get a connection timed out error whenever I try to connect.",
        ),
    ]

    context = BasicAssistanceService.build_context(ticket(), None, history)
    reply = BasicAssistanceService.reply(ticket(), None, history)

    assert context.start_time == "this morning"
    assert context.affected_devices_users == "One device: laptop"
    assert context.affected_service == "VPN"
    assert context.exact_error == "connection timed out"
    assert context.next_recommended_question == "Can you access the internet when you are not connected to the VPN?"
    assert "started this morning" in reply
    assert "One device: laptop" in reply
    assert "error: connection timed out" in reply
    assert "Can you access the internet when you are not connected to the VPN?" in reply
    assert "When did the connection issue start?" not in reply
    assert "What exact error message appears" not in reply


def test_context_retains_details_across_multiple_employee_messages():
    history = [
        message("EMPLOYEE", "The VPN issue started this morning. Only my laptop is affected. The error is connection timed out."),
        message("AI", "Can you access the internet without the VPN?"),
        message("EMPLOYEE", "I restarted the VPN client but the connection timed out again."),
    ]

    context = BasicAssistanceService.build_context(ticket(), None, history)

    assert context.start_time == "this morning"
    assert context.affected_devices_users == "One device: laptop"
    assert context.affected_service == "VPN"
    assert context.exact_error == "connection timed out"
    assert context.known_troubleshooting_steps == ["the VPN client but the connection timed out again"]
    assert context.next_recommended_question == "Can you access the internet when you are not connected to the VPN?"


def test_new_information_changes_the_next_question_without_reasking_known_details():
    before = [message("EMPLOYEE", "The VPN issue started this morning.")]
    after = before + [message("EMPLOYEE", "Only my laptop is affected.")]

    first = BasicAssistanceService.build_context(ticket(), None, before)
    second = BasicAssistanceService.build_context(ticket(), None, after)

    assert first.next_recommended_question == "Is this affecting only your device, or are other people or devices affected too?"
    assert second.next_recommended_question == "What exact error message appears when you connect?"
    assert "when the issue started" not in second.missing_information


def test_missing_information_lists_unknown_details_but_not_known_details():
    history = [message("EMPLOYEE", "The VPN started yesterday and I see a timeout.")]

    context = BasicAssistanceService.build_context(ticket(), None, history)

    assert context.start_time == "yesterday"
    assert context.affected_service == "VPN"
    assert "when the issue started" not in context.missing_information
    assert "which devices or users are affected" in context.missing_information
    assert "the exact error or behavior" not in context.missing_information
    assert "whether internet works without the VPN" in context.missing_information


def test_categories_receive_relevant_next_questions():
    cases = [
        (ticket(), [], "When did the connection issue start?"),
        (ticket(category="Software", title="Business app crashes", description="Application crash"), [], "Which application is affected?"),
        (ticket(category="Hardware", title="Laptop hardware issue", description="Laptop battery concern"), [], "What device is involved"),
        (ticket(category="Security", title="Suspicious login", description="Security alert"), [], "approved security reporting channel"),
    ]

    for case_ticket, history, expected in cases:
        context = BasicAssistanceService.build_context(case_ticket, None, history)
        assert expected in context.next_recommended_question


def test_basic_assistance_uses_ticket_facts_and_only_curated_article_summary():
    case_ticket = ticket(category="Software", title="Application crash", description="The app closes on sign-in")
    article = SimpleNamespace(
        title="Application crash guide",
        summary="Collect the error text and note when the crash occurs.",
        category="Software",
    )
    case_ticket.solution_status = "MATCHED"
    case_ticket.solution_confidence = 0.8
    case_ticket.suggested_solution = "A procedural solution is not included in basic mode."

    reply = BasicAssistanceService.reply(case_ticket, article, [])

    assert "Current status: IN PROGRESS" in reply
    assert "Predicted category: Software; predicted priority: HIGH" in reply
    assert "cannot confirm the cause" in reply
    assert "Application crash guide" in reply
    assert "procedural solution is not included" not in reply
    assert "passwords, one-time codes, API keys" in reply


def test_basic_assistance_does_not_show_low_relevance_knowledge_article():
    case_ticket = ticket(category="Software", title="Application issue", description="App error")
    case_ticket.solution_status = "MATCHED"
    case_ticket.solution_confidence = 0.1
    case_ticket.suggested_solution = "Do not show this."
    article = SimpleNamespace(title="Low match", summary="Low relevance", category="Software")

    reply = BasicAssistanceService.reply(case_ticket, article, [])

    assert "no sufficiently relevant approved knowledge guidance" in reply
    assert "Low match" not in reply
    assert "Do not show this" not in reply


def test_security_assistance_does_not_repeat_or_expose_secrets_or_procedural_steps():
    case_ticket = ticket(category="Security", title="Suspicious login", description="Security alert")
    case_ticket.solution_status = "MATCHED"
    case_ticket.solution_confidence = 0.9
    case_ticket.suggested_solution = "Disable the firewall."
    article = SimpleNamespace(title="Security alert", summary="An alert needs specialist review.", category="Security")
    history = [message("EMPLOYEE", "I restarted the firewall. My password is hunter2 and OTP: 234123.")]

    context = BasicAssistanceService.build_context(case_ticket, article, history)
    reply = BasicAssistanceService.reply(case_ticket, article, history)

    assert "approved security reporting channel" in context.next_recommended_question
    assert "Disable the firewall" not in reply
    assert "hunter2" not in str(context.as_dict()) + reply
    assert "234123" not in str(context.as_dict()) + reply
    assert "Never share passwords" in reply
