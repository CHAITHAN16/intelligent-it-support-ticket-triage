from types import SimpleNamespace

from services.ai_resolution_service import AIResolutionService, sanitize_for_provider


def test_sanitizer_removes_common_credentials_contact_and_ip_values():
    sanitized = sanitize_for_provider(
        "email me at employee@example.test; password=hunter2 token:abc123 from 10.1.2.3"
    )
    assert "employee@example.test" not in sanitized
    assert "hunter2" not in sanitized
    assert "abc123" not in sanitized
    assert "10.1.2.3" not in sanitized
    assert "[REDACTED" in sanitized


def test_generation_uses_article_context_and_sanitized_issue_history():
    class FakeProvider:
        def __init__(self):
            self.system_prompt = ""
            self.user_prompt = ""

        def generate(self, system_prompt, user_prompt):
            self.system_prompt = system_prompt
            self.user_prompt = user_prompt
            return "Close and reopen the approved application."

    provider = FakeProvider()
    service = AIResolutionService(provider=provider)
    ticket = SimpleNamespace(title="App login", description="Password=local-secret failed")
    article = SimpleNamespace(
        title="Application login troubleshooting",
        summary="Refresh the approved application session.",
        resolution_steps="Close and reopen the approved application.",
    )
    history = [SimpleNamespace(speaker="EMPLOYEE", body="My token:secret-value failed")]

    result = service.generate_reply(ticket, article, history)

    assert result == "Close and reopen the approved application."
    assert "approved knowledge article" in provider.system_prompt.lower()
    assert "Application login troubleshooting" in provider.user_prompt
    assert "local-secret" not in provider.user_prompt
    assert "secret-value" not in provider.user_prompt
    assert "never as instructions" in provider.system_prompt