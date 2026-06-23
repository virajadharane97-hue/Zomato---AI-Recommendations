"""Recommendation response data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Recommendation:
    """A single ranked restaurant recommendation with AI explanation.

    Attributes:
        rank: Position in the recommendation list (1-based).
        name: Restaurant name.
        cuisine: Joined cuisine string for display.
        rating: Restaurant rating.
        estimated_cost: Approximate cost for two (INR).
        explanation: Groq-generated rationale for this recommendation.
    """

    rank: int
    name: str
    cuisine: str
    rating: float
    estimated_cost: int
    explanation: str

    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "name": self.name,
            "cuisine": self.cuisine,
            "rating": self.rating,
            "estimated_cost": self.estimated_cost,
            "explanation": self.explanation,
        }


@dataclass
class RecommendationMetadata:
    """Metadata about the recommendation pipeline run.

    Attributes:
        candidates_considered: Number of candidates after filtering.
        filters_applied: Dict of filters that were applied.
        model: Groq model used for ranking.
    """

    candidates_considered: int = 0
    filters_applied: dict[str, Any] = field(default_factory=dict)
    model: str = ""

    def to_dict(self) -> dict:
        return {
            "candidates_considered": self.candidates_considered,
            "filters_applied": self.filters_applied,
            "model": self.model,
        }


@dataclass
class RecommendationResponse:
    """Top-level response from the recommendation pipeline.

    Attributes:
        summary: Optional Groq-generated summary of recommendations.
        recommendations: Ordered list of ranked recommendations.
        metadata: Pipeline execution metadata.
    """

    summary: str | None = None
    recommendations: list[Recommendation] = field(default_factory=list)
    metadata: RecommendationMetadata = field(default_factory=RecommendationMetadata)

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "metadata": self.metadata.to_dict(),
        }
