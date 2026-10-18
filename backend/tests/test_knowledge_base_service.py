import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from models import Base, KnowledgeBaseArticle
from services.knowledge_base_service import KnowledgeBaseService
from scripts.seed_knowledge_base import seed


@pytest.fixture
def kb_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    next_id = 1

    def assign_sqlite_ids(session, flush_context, instances):
        nonlocal next_id
        for value in session.new:
            if isinstance(value, KnowledgeBaseArticle) and value.id is None:
                value.id = next_id
                next_id += 1

    event.listen(Session, "before_flush", assign_sqlite_ids)
    with Session(engine) as session:
        yield session
    event.remove(Session, "before_flush", assign_sqlite_ids)
    Base.metadata.drop_all(engine)


def test_seed_is_repeatable_and_creates_curated_articles(kb_session):
    seed(kb_session)
    first_count = kb_session.query(KnowledgeBaseArticle).count()
    seed(kb_session)
    assert first_count == 8
    assert kb_session.query(KnowledgeBaseArticle).count() == first_count


@pytest.mark.parametrize(
    ("title", "description", "category", "expected"),
    [
        ("Office Wi-Fi drops", "Cannot connect to wireless office network", "Network", "Office Wi-Fi"),
        ("VPN not connecting", "Remote access VPN tunnel fails", "Network", "VPN connection"),
        ("Suspicious login alert", "Unexpected unauthorized sign in detected", "Security", "Suspicious login"),
    ],
)
def test_retrieves_relevant_article(kb_session, title, description, category, expected):
    seed(kb_session)
    result = KnowledgeBaseService().retrieve(kb_session, title, description, category)
    assert result.status == "MATCHED"
    assert expected in result.article_title
    assert result.confidence is not None
    assert result.suggested_solution


def test_unrelated_ticket_has_no_confident_match(kb_session):
    seed(kb_session)
    result = KnowledgeBaseService().retrieve(kb_session, "Team lunch choices", "Which catering menu should we select?", "Other")
    assert result.status == "NO_MATCH"
    assert result.article_id is None
    assert result.suggested_solution is None


def test_inactive_article_is_not_returned(kb_session):
    kb_session.add(KnowledgeBaseArticle(id=1, title="VPN", summary="VPN trouble", category="Network", resolution_steps="Contact IT", keywords="vpn", active=False))
    kb_session.commit()
    assert KnowledgeBaseService().retrieve(kb_session, "VPN trouble", "VPN not connecting", "Network").status == "NO_MATCH"
