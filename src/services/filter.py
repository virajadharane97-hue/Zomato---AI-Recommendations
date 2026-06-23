"""Restaurant filtering and candidate selection.

Applies deterministic hard filters to produce a bounded candidate set
for the LLM ranking step. Includes constraint relaxation when zero
results are found.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.config import settings
from src.models.preferences import UserPreferences
from src.models.restaurant import Restaurant
from src.services.validator import PreferenceNormalizer

if TYPE_CHECKING:
    from src.data.repository import RestaurantRepository

logger = logging.getLogger(__name__)


# ── Data models ─────────────────────────────────────────────────────────────

@dataclass
class FilterResult:
    """Result of the filter pipeline.

    Attributes:
        candidates: Restaurants that survived filtering.
        filters_applied: Dict recording which filters were active.
        relaxed_filters: List of filter names that were relaxed due to
                         zero results (e.g. ["cuisine", "budget"]).
        warnings: Human-readable warnings for the user.
    """

    candidates: list[Restaurant] = field(default_factory=list)
    filters_applied: dict[str, str | float | None] = field(default_factory=dict)
    relaxed_filters: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ── Restaurant Filter ──────────────────────────────────────────────────────

class RestaurantFilter:
    """Sequential filter pipeline for restaurant candidates.

    Applies filters in order:
      1. Location (case-insensitive)
      2. Budget tier
      3. Min rating
      4. Cuisine (any restaurant cuisine contains the requested cuisine)

    Results are sorted by rating descending, then votes descending.

    Usage::

        filter_ = RestaurantFilter(repository)
        result = filter_.filter(preferences)
    """

    def __init__(self, repository: RestaurantRepository) -> None:
        self._repo = repository
        self._normalizer = PreferenceNormalizer()

    def filter(self, preferences: UserPreferences) -> FilterResult:
        """Apply all hard filters and return the filter result.

        If zero candidates remain after all filters, constraint relaxation
        is triggered automatically.

        Args:
            preferences: Validated and optionally normalized user preferences.

        Returns:
            FilterResult with candidates, applied filters, and any warnings.
        """
        all_restaurants = self._repo.get_all()

        norm_location = self._normalizer.normalize_location(preferences.location)
        norm_budget = self._normalizer.normalize_budget(preferences.budget)
        norm_cuisine = self._normalizer.normalize_cuisine(preferences.cuisine)
        norm_min_rating = preferences.min_rating

        result = FilterResult(
            filters_applied={
                "location": norm_location,
                "budget": norm_budget,
                "cuisine": norm_cuisine,
                "min_rating": norm_min_rating,
            },
        )

        # Apply filters sequentially
        candidates = self._apply_location(all_restaurants, norm_location)
        logger.info(
            "After location filter ('%s'): %d candidates",
            norm_location, len(candidates),
        )

        if not candidates:
            result.candidates = []
            result.warnings.append(
                f"No restaurants found in location '{norm_location}'."
            )
            return result

        candidates = self._apply_budget(candidates, norm_budget)
        logger.info(
            "After budget filter ('%s'): %d candidates",
            norm_budget, len(candidates),
        )

        candidates = self._apply_min_rating(candidates, norm_min_rating)
        logger.info(
            "After min_rating filter (>= %.1f): %d candidates",
            norm_min_rating, len(candidates),
        )

        if norm_cuisine:
            candidates = self._apply_cuisine(candidates, norm_cuisine)
            logger.info(
                "After cuisine filter ('%s'): %d candidates",
                norm_cuisine, len(candidates),
            )

        # If zero candidates, try constraint relaxation
        if not candidates:
            candidates, relaxed, warnings = self._relax_constraints(
                all_restaurants, norm_location, norm_budget,
                norm_min_rating, norm_cuisine,
            )
            result.relaxed_filters = relaxed
            result.warnings.extend(warnings)

        # Sort: rating descending, then votes descending
        candidates = self._sort(candidates)

        result.candidates = candidates
        logger.info("Final candidate count: %d", len(candidates))
        return result

    # ── Individual filters ──────────────────────────────────────────────────

    @staticmethod
    def _apply_location(
        restaurants: list[Restaurant], location: str,
    ) -> list[Restaurant]:
        """Filter by location (case-insensitive)."""
        loc_lower = location.lower()
        return [r for r in restaurants if r.location.lower() == loc_lower]

    @staticmethod
    def _apply_budget(
        restaurants: list[Restaurant], budget_tier: str,
    ) -> list[Restaurant]:
        """Filter by budget tier."""
        return [r for r in restaurants if r.budget_tier == budget_tier]

    @staticmethod
    def _apply_min_rating(
        restaurants: list[Restaurant], min_rating: float,
    ) -> list[Restaurant]:
        """Filter by minimum rating."""
        return [r for r in restaurants if r.rating >= min_rating]

    @staticmethod
    def _apply_cuisine(
        restaurants: list[Restaurant], cuisine: str,
    ) -> list[Restaurant]:
        """Filter by cuisine — matches if any restaurant cuisine contains
        the requested cuisine (case-insensitive)."""
        cuisine_lower = cuisine.lower()
        return [
            r for r in restaurants
            if any(cuisine_lower in c.lower() for c in r.cuisines)
        ]

    @staticmethod
    def _sort(restaurants: list[Restaurant]) -> list[Restaurant]:
        """Sort by rating descending, then votes descending."""
        return sorted(
            restaurants,
            key=lambda r: (r.rating, r.votes),
            reverse=True,
        )

    # ── Constraint relaxation ───────────────────────────────────────────────

    def _relax_constraints(
        self,
        all_restaurants: list[Restaurant],
        location: str,
        budget: str,
        min_rating: float,
        cuisine: str | None,
    ) -> tuple[list[Restaurant], list[str], list[str]]:
        """Progressively relax constraints to find candidates.

        Relaxation order (per spec): cuisine → budget → min_rating.
        Location is never relaxed — it's always required.

        Returns:
            Tuple of (candidates, relaxed_filter_names, warning_messages).
        """
        relaxed: list[str] = []
        warnings: list[str] = []

        # Start from location-filtered set
        candidates = self._apply_location(all_restaurants, location)
        if not candidates:
            # If no restaurants in the location at all, nothing to relax
            return [], [], [f"No restaurants found in location '{location}'."]

        # Try relaxing cuisine first
        if cuisine:
            relaxed.append("cuisine")
            warnings.append(
                f"No results for cuisine '{cuisine}'. "
                "Showing results across all cuisines."
            )
            logger.info("Relaxing cuisine filter.")

            # Apply remaining filters: budget + min_rating
            result = self._apply_budget(candidates, budget)
            result = self._apply_min_rating(result, min_rating)
            if result:
                return result, relaxed, warnings

        # Relax budget
        relaxed.append("budget")
        warnings.append(
            f"No results for budget tier '{budget}'. "
            "Showing results across all budget tiers."
        )
        logger.info("Relaxing budget filter.")

        # Apply remaining: min_rating only (cuisine already relaxed or not set)
        result = self._apply_min_rating(candidates, min_rating)
        if result:
            return result, relaxed, warnings

        # Relax min_rating
        relaxed.append("min_rating")
        warnings.append(
            f"No results for minimum rating {min_rating:.1f}. "
            "Showing all rated restaurants."
        )
        logger.info("Relaxing min_rating filter.")

        # Only location filter remains
        return candidates, relaxed, warnings


# ── Candidate Selector ──────────────────────────────────────────────────────

class CandidateSelector:
    """Caps filtered candidates to MAX_CANDIDATES_FOR_LLM.

    Applies tie-breaking (already sorted by filter) and truncates
    to the configured limit.

    Usage::

        selector = CandidateSelector()
        top = selector.select(filter_result.candidates)
    """

    def __init__(self, max_candidates: int | None = None) -> None:
        self._max = max_candidates or settings.MAX_CANDIDATES_FOR_LLM

    def select(self, candidates: list[Restaurant]) -> list[Restaurant]:
        """Return the top N candidates (already assumed sorted).

        Args:
            candidates: Pre-sorted list of restaurant candidates.

        Returns:
            Truncated list of at most ``max_candidates`` restaurants.
        """
        selected = candidates[: self._max]
        if len(candidates) > self._max:
            logger.info(
                "Capped candidates from %d to %d",
                len(candidates), self._max,
            )
        return selected
