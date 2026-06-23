"""Recommendation service — orchestrates the full recommendation pipeline.

Pipeline stages:
  1. Validate user preferences
  2. Filter restaurant candidates
  3. Select top candidates for LLM
  4. Build prompt
  5. Call Groq LLM
  6. Parse response
  7. Enrich with full restaurant data
  8. Return RecommendationResponse
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.config import settings
from src.models.preferences import UserPreferences
from src.models.recommendation import (
    Recommendation,
    RecommendationMetadata,
    RecommendationResponse,
)
from src.models.restaurant import Restaurant
from src.services.filter import CandidateSelector, FilterResult, RestaurantFilter
from src.services.llm_client import LLMClient, LLMRanking, LLMResponse
from src.services.prompt_builder import PromptBuilder
from src.services.validator import PreferenceValidator, ValidationResult

if TYPE_CHECKING:
    from src.data.repository import RestaurantRepository

logger = logging.getLogger(__name__)


# ── Enricher ────────────────────────────────────────────────────────────────

class RecommendationEnricher:
    """Joins LLM rankings with full Restaurant records.

    Merges the rank and explanation from the LLM with the restaurant's
    name, cuisine, rating, and cost to produce display-ready
    ``Recommendation`` objects.
    """

    @staticmethod
    def enrich(
        rankings: list[LLMRanking],
        candidates: list[Restaurant],
    ) -> list[Recommendation]:
        """Merge LLM rankings with restaurant data.

        Args:
            rankings: Parsed LLM rankings with id, rank, explanation.
            candidates: Full Restaurant objects used as candidates.

        Returns:
            List of Recommendation objects, ordered by rank.
        """
        # Build lookup by ID for O(1) access
        candidate_map: dict[str, Restaurant] = {c.id: c for c in candidates}

        recommendations: list[Recommendation] = []
        for ranking in rankings:
            restaurant = candidate_map.get(ranking.id)
            if restaurant is None:
                logger.warning(
                    "LLM returned unknown restaurant ID '%s' — skipping.",
                    ranking.id,
                )
                continue

            recommendations.append(Recommendation(
                rank=ranking.rank,
                name=restaurant.name,
                cuisine=", ".join(restaurant.cuisines),
                rating=restaurant.rating,
                estimated_cost=restaurant.cost_for_two,
                explanation=ranking.explanation,
            ))

        # Sort by rank for consistency
        recommendations.sort(key=lambda r: r.rank)
        return recommendations

    @staticmethod
    def heuristic_enrich(
        candidates: list[Restaurant],
        top_k: int,
    ) -> list[Recommendation]:
        """Create recommendations from candidates without LLM explanations.

        Used as a fallback when Groq is unavailable.

        Args:
            candidates: Pre-sorted restaurant candidates.
            top_k: Number of recommendations to return.

        Returns:
            List of Recommendation objects with generic explanations.
        """
        recommendations: list[Recommendation] = []
        for i, restaurant in enumerate(candidates[:top_k], start=1):
            recommendations.append(Recommendation(
                rank=i,
                name=restaurant.name,
                cuisine=", ".join(restaurant.cuisines),
                rating=restaurant.rating,
                estimated_cost=restaurant.cost_for_two,
                explanation=(
                    f"Highly rated ({restaurant.rating}/5) with "
                    f"{restaurant.votes} votes. "
                    f"Ranked by rating — AI explanation unavailable."
                ),
            ))
        return recommendations


# ── Recommendation Service (Orchestrator) ───────────────────────────────────

class RecommendationService:
    """Orchestrates the full recommendation pipeline.

    Wires together: validator → filter → candidate selector → prompt
    builder → LLM client → enricher → response.

    Usage::

        service = RecommendationService(repository)
        response = service.recommend(preferences)
    """

    def __init__(
        self,
        repository: RestaurantRepository,
        *,
        validator: PreferenceValidator | None = None,
        filter_: RestaurantFilter | None = None,
        selector: CandidateSelector | None = None,
        prompt_builder: PromptBuilder | None = None,
        llm_client: LLMClient | None = None,
        enricher: RecommendationEnricher | None = None,
        top_k: int | None = None,
    ) -> None:
        self._repo = repository
        self._validator = validator or PreferenceValidator(repository)
        self._filter = filter_ or RestaurantFilter(repository)
        self._selector = selector or CandidateSelector()
        self._prompt_builder = prompt_builder or PromptBuilder(top_k=top_k)
        self._llm_client = llm_client or LLMClient()
        self._enricher = enricher or RecommendationEnricher()
        self._top_k = top_k or settings.TOP_K_RECOMMENDATIONS

    def recommend(self, preferences: UserPreferences) -> RecommendationResponse:
        """Run the full recommendation pipeline.

        Args:
            preferences: User's restaurant search preferences.

        Returns:
            RecommendationResponse with ranked recommendations and metadata.

        Raises:
            ValueError: If preferences fail validation with errors.
        """
        # 1. Validate
        validation = self._validate(preferences)
        if not validation.is_valid:
            raise ValueError(
                "Invalid preferences: " + "; ".join(validation.errors)
            )

        # 2. Filter
        filter_result = self._filter.filter(preferences)
        logger.info(
            "Filter result: %d candidates, %d warnings",
            len(filter_result.candidates), len(filter_result.warnings),
        )

        # 3. Select top candidates
        candidates = self._selector.select(filter_result.candidates)
        logger.info("Selected %d candidates for LLM", len(candidates))

        # Build metadata
        metadata = RecommendationMetadata(
            candidates_considered=len(candidates),
            filters_applied=filter_result.filters_applied,
        )

        # 4. Handle empty candidates
        if not candidates:
            return RecommendationResponse(
                summary="No restaurants matched your criteria.",
                recommendations=[],
                metadata=metadata,
            )

        # 5. Build prompt → call LLM → parse
        messages = self._prompt_builder.build(preferences, candidates)
        llm_response = self._llm_client.complete(messages)
        metadata.model = llm_response.model

        # 6. Enrich
        if llm_response.is_fallback or not llm_response.rankings:
            # Heuristic fallback
            recommendations = self._enricher.heuristic_enrich(
                candidates, self._top_k,
            )
            summary = llm_response.summary or (
                "Ranked by rating — AI explanation unavailable."
            )
        else:
            # LLM-based enrichment
            recommendations = self._enricher.enrich(
                llm_response.rankings, candidates,
            )
            summary = llm_response.summary

        # 7. Build response
        response = RecommendationResponse(
            summary=summary,
            recommendations=recommendations,
            metadata=metadata,
        )

        logger.info(
            "Recommendation complete: %d results, model=%s, fallback=%s",
            len(recommendations), llm_response.model, llm_response.is_fallback,
        )

        return response

    # ── Private helpers ─────────────────────────────────────────────────────

    def _validate(self, preferences: UserPreferences) -> ValidationResult:
        """Validate user preferences."""
        return self._validator.validate(
            location=preferences.location,
            budget=preferences.budget,
            cuisine=preferences.cuisine,
            min_rating=preferences.min_rating,
        )
