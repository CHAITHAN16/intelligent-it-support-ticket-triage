from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import KnowledgeBaseArticle


MIN_CONFIDENCE = 0.18
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {"a", "an", "and", "are", "for", "from", "i", "in", "is", "it", "my", "of", "on", "or", "the", "to", "with", "this", "that", "when", "after", "please", "help", "problem"}


@dataclass(frozen=True)
class SolutionRecommendation:
    status: str
    suggested_solution: str | None
    article_id: int | None
    article_title: str | None
    confidence: float | None
    source: str | None


def _tokens(text: str) -> set[str]:
    return {token for token in _TOKEN_RE.findall(text.lower()) if token not in _STOP_WORDS and len(token) > 1}


class KnowledgeBaseService:
    def __init__(self, minimum_confidence: float = MIN_CONFIDENCE):
        self.minimum_confidence = minimum_confidence

    def retrieve(self, db: Session, title: str, description: str, category: str | None) -> SolutionRecommendation:
        ticket_tokens = _tokens(f"{title} {description}")
        ticket_category = (category or "").strip().lower()
        scored: list[tuple[float, KnowledgeBaseArticle]] = []
        articles = db.scalars(select(KnowledgeBaseArticle).where(KnowledgeBaseArticle.active.is_(True))).all()
        for article in articles:
            fields = (article.title, article.summary, article.category, article.keywords, article.resolution_steps)
            article_tokens = _tokens(" ".join(fields))
            if not ticket_tokens or not article_tokens:
                continue
            overlap = len(ticket_tokens & article_tokens) / len(ticket_tokens | article_tokens)
            category_bonus = 0.12 if ticket_category and article.category.lower() == ticket_category else 0.0
            title_overlap = len(ticket_tokens & _tokens(article.title))
            title_bonus = min(title_overlap * 0.025, 0.075)
            score = min(overlap + category_bonus + title_bonus, 1.0)
            scored.append((score, article))

        if not scored:
            return self._no_match()
        score, article = max(scored, key=lambda item: (item[0], item[1].id))
        if score < self.minimum_confidence:
            return self._no_match()
        return SolutionRecommendation(
            status="MATCHED",
            suggested_solution=article.resolution_steps,
            article_id=article.id,
            article_title=article.title,
            confidence=round(score, 4),
            source=f"Prototype curated knowledge base: {article.title}",
        )

    @staticmethod
    def _no_match() -> SolutionRecommendation:
        return SolutionRecommendation(
            status="NO_MATCH",
            suggested_solution=None,
            article_id=None,
            article_title=None,
            confidence=None,
            source=None,
        )
