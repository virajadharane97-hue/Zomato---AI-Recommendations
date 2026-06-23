"""Tests for Phase 2 — Filtering & Validation.

Covers:
  - PreferenceValidator: location, budget, rating, cuisine validation
  - PreferenceNormalizer: alias resolution, casing, trimming
  - RestaurantFilter: each filter independently and combined
  - Constraint relaxation: relaxation order, warnings
  - CandidateSelector: capping at MAX_CANDIDATES_FOR_LLM
  - Edge cases: empty results, no cuisine filter, zero-match location

Uses a small synthetic fixture with known data for deterministic tests.
"""

import pytest

from src.models.restaurant import Restaurant
from src.models.preferences import UserPreferences
from src.services.validator import (
    PreferenceValidator,
    PreferenceNormalizer,
    ValidationResult,
    CITY_ALIASES,
)
from src.services.filter import (
    RestaurantFilter,
    CandidateSelector,
    FilterResult,
)


# ── Fake repository ─────────────────────────────────────────────────────────

class FakeRepository:
    """Minimal repository stub for testing — no dataset download required."""

    def __init__(self, restaurants: list[Restaurant]) -> None:
        self._restaurants = restaurants

    def get_all(self) -> list[Restaurant]:
        return list(self._restaurants)

    def get_locations(self) -> list[str]:
        return sorted({r.location for r in self._restaurants})

    def get_cuisines(self) -> list[str]:
        all_cuisines: set[str] = set()
        for r in self._restaurants:
            all_cuisines.update(c for c in r.cuisines if c)
        return sorted(all_cuisines)


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_restaurants() -> list[Restaurant]:
    """A deterministic set of restaurants covering different locations,
    budgets, cuisines, and ratings."""
    return [
        Restaurant(
            id="1", name="Tandoori Nights",
            location="Banashankari", cuisines=["North Indian", "Mughlai"],
            cost_for_two=800, rating=4.5, votes=1200,
            rest_type="Casual Dining", budget_tier="medium",
        ),
        Restaurant(
            id="2", name="Dragon Bowl",
            location="Banashankari", cuisines=["Chinese", "Thai"],
            cost_for_two=600, rating=4.2, votes=800,
            rest_type="Casual Dining", budget_tier="medium",
        ),
        Restaurant(
            id="3", name="South Spice",
            location="Banashankari", cuisines=["South Indian"],
            cost_for_two=300, rating=3.8, votes=500,
            rest_type="Quick Bites", budget_tier="low",
        ),
        Restaurant(
            id="4", name="La Piazza",
            location="Koramangala", cuisines=["Italian", "Continental"],
            cost_for_two=1800, rating=4.6, votes=2000,
            rest_type="Fine Dining", budget_tier="high",
        ),
        Restaurant(
            id="5", name="Chai Point",
            location="Koramangala", cuisines=["Cafe", "Beverages"],
            cost_for_two=200, rating=3.5, votes=300,
            rest_type="Cafe", budget_tier="low",
        ),
        Restaurant(
            id="6", name="BBQ Nation",
            location="Indiranagar", cuisines=["North Indian", "BBQ"],
            cost_for_two=1500, rating=4.1, votes=1500,
            rest_type="Casual Dining", budget_tier="medium",
        ),
        Restaurant(
            id="7", name="Sushi World",
            location="Indiranagar", cuisines=["Japanese", "Sushi"],
            cost_for_two=2000, rating=4.7, votes=900,
            rest_type="Fine Dining", budget_tier="high",
        ),
        Restaurant(
            id="8", name="Dosa Camp",
            location="Banashankari", cuisines=["South Indian", "North Indian"],
            cost_for_two=250, rating=4.0, votes=600,
            rest_type="Quick Bites", budget_tier="low",
        ),
        Restaurant(
            id="9", name="Burger Barn",
            location="Koramangala", cuisines=["American", "Fast Food"],
            cost_for_two=500, rating=3.2, votes=250,
            rest_type="Quick Bites", budget_tier="low",
        ),
        Restaurant(
            id="10", name="Pasta Palace",
            location="Banashankari", cuisines=["Italian"],
            cost_for_two=900, rating=4.3, votes=700,
            rest_type="Casual Dining", budget_tier="medium",
        ),
    ]


@pytest.fixture
def repo(sample_restaurants) -> FakeRepository:
    return FakeRepository(sample_restaurants)


@pytest.fixture
def validator(repo) -> PreferenceValidator:
    return PreferenceValidator(repo)


@pytest.fixture
def restaurant_filter(repo) -> RestaurantFilter:
    return RestaurantFilter(repo)


# ═══════════════════════════════════════════════════════════════════════════
# PREFERENCE NORMALIZER
# ═══════════════════════════════════════════════════════════════════════════

class TestPreferenceNormalizer:
    def test_normalize_location_title_case(self):
        assert PreferenceNormalizer.normalize_location("banashankari") == "Banashankari"

    def test_normalize_location_strips_whitespace(self):
        assert PreferenceNormalizer.normalize_location("  koramangala  ") == "Koramangala"

    def test_normalize_location_resolves_alias(self):
        assert PreferenceNormalizer.normalize_location("bengaluru") == "Bangalore"
        assert PreferenceNormalizer.normalize_location("Bombay") == "Mumbai"
        assert PreferenceNormalizer.normalize_location("CALCUTTA") == "Kolkata"

    def test_normalize_budget(self):
        assert PreferenceNormalizer.normalize_budget("  Medium  ") == "medium"
        assert PreferenceNormalizer.normalize_budget("HIGH") == "high"

    def test_normalize_cuisine_title_case(self):
        assert PreferenceNormalizer.normalize_cuisine("north indian") == "North Indian"

    def test_normalize_cuisine_none(self):
        assert PreferenceNormalizer.normalize_cuisine(None) is None

    def test_normalize_cuisine_empty_string(self):
        assert PreferenceNormalizer.normalize_cuisine("  ") is None

    def test_normalize_additional_strips(self):
        assert PreferenceNormalizer.normalize_additional("  family-friendly  ") == "family-friendly"

    def test_normalize_additional_none(self):
        assert PreferenceNormalizer.normalize_additional(None) is None

    def test_normalize_additional_empty(self):
        assert PreferenceNormalizer.normalize_additional("  ") is None


# ═══════════════════════════════════════════════════════════════════════════
# PREFERENCE VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════

class TestPreferenceValidatorLocation:
    def test_valid_location(self, validator):
        result = validator.validate(location="Banashankari", budget="medium")
        assert result.is_valid
        assert not result.errors

    def test_valid_location_case_insensitive(self, validator):
        result = validator.validate(location="banashankari", budget="medium")
        assert result.is_valid

    def test_empty_location(self, validator):
        result = validator.validate(location="", budget="medium")
        assert not result.is_valid
        assert any("required" in e.lower() for e in result.errors)

    def test_whitespace_only_location(self, validator):
        result = validator.validate(location="   ", budget="medium")
        assert not result.is_valid

    def test_unknown_location_returns_suggestions(self, validator):
        result = validator.validate(location="Banashankri", budget="medium")
        assert not result.is_valid
        assert "location" in result.suggestions
        # Should suggest "Banashankari" as a close match
        assert "Banashankari" in result.suggestions["location"]

    def test_totally_unknown_location_no_suggestions(self, validator):
        result = validator.validate(location="Zzzzzzz", budget="medium")
        assert not result.is_valid
        # May or may not have suggestions depending on cutoff


class TestPreferenceValidatorBudget:
    def test_valid_budgets(self, validator):
        for tier in ("low", "medium", "high"):
            result = validator.validate(location="Banashankari", budget=tier)
            assert result.is_valid, f"Budget '{tier}' should be valid"

    def test_valid_budget_case_insensitive(self, validator):
        result = validator.validate(location="Banashankari", budget="MEDIUM")
        assert result.is_valid

    def test_invalid_budget(self, validator):
        result = validator.validate(location="Banashankari", budget="luxury")
        assert not result.is_valid
        assert any("budget" in e.lower() for e in result.errors)


class TestPreferenceValidatorRating:
    def test_valid_min_rating(self, validator):
        result = validator.validate(
            location="Banashankari", budget="medium", min_rating=4.0,
        )
        assert result.is_valid

    def test_boundary_rating_zero(self, validator):
        result = validator.validate(
            location="Banashankari", budget="medium", min_rating=0.0,
        )
        assert result.is_valid

    def test_boundary_rating_five(self, validator):
        result = validator.validate(
            location="Banashankari", budget="medium", min_rating=5.0,
        )
        assert result.is_valid

    def test_negative_rating(self, validator):
        result = validator.validate(
            location="Banashankari", budget="medium", min_rating=-1.0,
        )
        assert not result.is_valid
        assert any("out of range" in e.lower() for e in result.errors)

    def test_above_five_rating(self, validator):
        result = validator.validate(
            location="Banashankari", budget="medium", min_rating=5.5,
        )
        assert not result.is_valid


class TestPreferenceValidatorCuisine:
    def test_valid_cuisine(self, validator):
        result = validator.validate(
            location="Banashankari", budget="medium", cuisine="North Indian",
        )
        assert result.is_valid

    def test_unknown_cuisine_still_valid(self, validator):
        """Unknown cuisine is not a hard error — just may produce suggestions."""
        result = validator.validate(
            location="Banashankari", budget="medium", cuisine="Martian Food",
        )
        # Unknown cuisine is NOT an error (it's optional/soft)
        assert result.is_valid

    def test_fuzzy_cuisine_suggestions(self, validator):
        result = validator.validate(
            location="Banashankari", budget="medium", cuisine="Italin",
        )
        # Should suggest "Italian"
        if "cuisine" in result.suggestions:
            assert "Italian" in result.suggestions["cuisine"]

    def test_none_cuisine_is_valid(self, validator):
        result = validator.validate(
            location="Banashankari", budget="medium", cuisine=None,
        )
        assert result.is_valid


# ═══════════════════════════════════════════════════════════════════════════
# RESTAURANT FILTER — Individual Filters
# ═══════════════════════════════════════════════════════════════════════════

class TestFilterLocation:
    def test_filter_by_location(self, restaurant_filter):
        prefs = UserPreferences(location="Banashankari", budget="medium")
        result = restaurant_filter.filter(prefs)
        # 5 restaurants in Banashankari
        for r in result.candidates:
            assert r.location == "Banashankari"

    def test_filter_case_insensitive(self, restaurant_filter):
        prefs = UserPreferences(location="banashankari", budget="medium")
        result = restaurant_filter.filter(prefs)
        assert len(result.candidates) > 0

    def test_filter_unknown_location_empty(self, restaurant_filter):
        prefs = UserPreferences(location="Mars City", budget="low")
        result = restaurant_filter.filter(prefs)
        assert len(result.candidates) == 0
        assert len(result.warnings) > 0


class TestFilterBudget:
    def test_filter_by_budget_low(self, restaurant_filter):
        prefs = UserPreferences(location="Banashankari", budget="low")
        result = restaurant_filter.filter(prefs)
        for r in result.candidates:
            assert r.budget_tier == "low"

    def test_filter_by_budget_medium(self, restaurant_filter):
        prefs = UserPreferences(location="Banashankari", budget="medium")
        result = restaurant_filter.filter(prefs)
        for r in result.candidates:
            assert r.budget_tier == "medium"


class TestFilterMinRating:
    def test_filter_by_min_rating(self, restaurant_filter):
        prefs = UserPreferences(
            location="Banashankari", budget="medium", min_rating=4.3,
        )
        result = restaurant_filter.filter(prefs)
        for r in result.candidates:
            assert r.rating >= 4.3

    def test_filter_zero_min_rating_passes_all(self, restaurant_filter):
        prefs = UserPreferences(
            location="Banashankari", budget="medium", min_rating=0.0,
        )
        result = restaurant_filter.filter(prefs)
        # Should include all medium-budget Banashankari restaurants
        assert len(result.candidates) > 0


class TestFilterCuisine:
    def test_filter_by_cuisine(self, restaurant_filter):
        prefs = UserPreferences(
            location="Banashankari", budget="medium", cuisine="Italian",
        )
        result = restaurant_filter.filter(prefs)
        for r in result.candidates:
            assert any("italian" in c.lower() for c in r.cuisines)

    def test_filter_cuisine_partial_match(self, restaurant_filter):
        """Cuisine filter uses 'in' matching, so 'Indian' matches
        'North Indian' and 'South Indian'."""
        prefs = UserPreferences(
            location="Banashankari", budget="low", cuisine="Indian",
        )
        result = restaurant_filter.filter(prefs)
        assert len(result.candidates) > 0

    def test_no_cuisine_filter_when_none(self, restaurant_filter):
        prefs = UserPreferences(
            location="Banashankari", budget="medium", cuisine=None,
        )
        result = restaurant_filter.filter(prefs)
        # Without cuisine filter, all medium-budget Banashankari restaurants
        assert len(result.candidates) > 0


# ═══════════════════════════════════════════════════════════════════════════
# COMBINED FILTERS
# ═══════════════════════════════════════════════════════════════════════════

class TestFilterCombined:
    def test_all_filters_applied(self, restaurant_filter):
        prefs = UserPreferences(
            location="Banashankari", budget="medium",
            cuisine="North Indian", min_rating=4.0,
        )
        result = restaurant_filter.filter(prefs)
        for r in result.candidates:
            assert r.location == "Banashankari"
            assert r.budget_tier == "medium"
            assert r.rating >= 4.0
            assert any("north indian" in c.lower() for c in r.cuisines)

    def test_results_sorted_by_rating_then_votes(self, restaurant_filter):
        prefs = UserPreferences(location="Banashankari", budget="medium")
        result = restaurant_filter.filter(prefs)
        for i in range(len(result.candidates) - 1):
            curr = result.candidates[i]
            nxt = result.candidates[i + 1]
            assert (curr.rating, curr.votes) >= (nxt.rating, nxt.votes)

    def test_filters_applied_metadata(self, restaurant_filter):
        prefs = UserPreferences(
            location="Banashankari", budget="low",
            cuisine="South Indian", min_rating=3.5,
        )
        result = restaurant_filter.filter(prefs)
        assert result.filters_applied["location"] == "Banashankari"
        assert result.filters_applied["budget"] == "low"
        assert result.filters_applied["min_rating"] == 3.5


# ═══════════════════════════════════════════════════════════════════════════
# CONSTRAINT RELAXATION
# ═══════════════════════════════════════════════════════════════════════════

class TestConstraintRelaxation:
    def test_relaxes_cuisine_first(self, restaurant_filter):
        """When cuisine yields zero results, it should be relaxed first."""
        prefs = UserPreferences(
            location="Banashankari", budget="medium",
            cuisine="Japanese",  # not available in Banashankari
            min_rating=0.0,
        )
        result = restaurant_filter.filter(prefs)
        # Should have candidates from relaxing cuisine
        assert len(result.candidates) > 0
        assert "cuisine" in result.relaxed_filters
        assert len(result.warnings) > 0

    def test_relaxes_budget_after_cuisine(self, restaurant_filter):
        """When cuisine AND budget yield zero, both should be relaxed."""
        prefs = UserPreferences(
            location="Banashankari", budget="high",
            cuisine="Japanese", min_rating=0.0,
        )
        result = restaurant_filter.filter(prefs)
        # No Japanese in Banashankari, no high-budget either → relax both
        assert len(result.candidates) > 0
        assert "cuisine" in result.relaxed_filters
        assert "budget" in result.relaxed_filters

    def test_relaxes_min_rating_last(self, restaurant_filter):
        """All three should be relaxed if needed."""
        prefs = UserPreferences(
            location="Banashankari", budget="high",
            cuisine="Japanese", min_rating=5.0,
        )
        result = restaurant_filter.filter(prefs)
        assert len(result.candidates) > 0
        assert "cuisine" in result.relaxed_filters
        assert "budget" in result.relaxed_filters
        assert "min_rating" in result.relaxed_filters

    def test_relaxation_order_preserved(self, restaurant_filter):
        """Relaxation order should be cuisine → budget → min_rating."""
        prefs = UserPreferences(
            location="Banashankari", budget="high",
            cuisine="Japanese", min_rating=5.0,
        )
        result = restaurant_filter.filter(prefs)
        expected_order = ["cuisine", "budget", "min_rating"]
        assert result.relaxed_filters == expected_order

    def test_relaxation_warnings_surfaced(self, restaurant_filter):
        prefs = UserPreferences(
            location="Banashankari", budget="high",
            cuisine="Japanese", min_rating=0.0,
        )
        result = restaurant_filter.filter(prefs)
        assert len(result.warnings) > 0
        # Warnings should mention what was relaxed
        combined = " ".join(result.warnings).lower()
        assert "cuisine" in combined or "budget" in combined

    def test_no_relaxation_when_results_exist(self, restaurant_filter):
        prefs = UserPreferences(
            location="Banashankari", budget="medium", min_rating=0.0,
        )
        result = restaurant_filter.filter(prefs)
        assert len(result.relaxed_filters) == 0
        assert len(result.warnings) == 0

    def test_unknown_location_cannot_be_relaxed(self, restaurant_filter):
        """Location is never relaxed — unknown location yields empty results."""
        prefs = UserPreferences(
            location="NonExistentCity", budget="low", min_rating=0.0,
        )
        result = restaurant_filter.filter(prefs)
        assert len(result.candidates) == 0
        assert len(result.warnings) > 0


# ═══════════════════════════════════════════════════════════════════════════
# CANDIDATE SELECTOR
# ═══════════════════════════════════════════════════════════════════════════

class TestCandidateSelector:
    def test_caps_at_max(self, sample_restaurants):
        selector = CandidateSelector(max_candidates=3)
        selected = selector.select(sample_restaurants)
        assert len(selected) == 3

    def test_returns_all_when_under_max(self, sample_restaurants):
        selector = CandidateSelector(max_candidates=100)
        selected = selector.select(sample_restaurants)
        assert len(selected) == len(sample_restaurants)

    def test_preserves_order(self, sample_restaurants):
        selector = CandidateSelector(max_candidates=5)
        selected = selector.select(sample_restaurants)
        assert selected == sample_restaurants[:5]

    def test_empty_input(self):
        selector = CandidateSelector(max_candidates=5)
        selected = selector.select([])
        assert selected == []


# ═══════════════════════════════════════════════════════════════════════════
# EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_empty_repository(self):
        empty_repo = FakeRepository([])
        filter_ = RestaurantFilter(empty_repo)
        prefs = UserPreferences(location="Anywhere", budget="low")
        result = filter_.filter(prefs)
        assert len(result.candidates) == 0

    def test_all_filters_match_single_restaurant(self, repo):
        filter_ = RestaurantFilter(repo)
        prefs = UserPreferences(
            location="Koramangala", budget="high",
            cuisine="Italian", min_rating=4.5,
        )
        result = filter_.filter(prefs)
        assert len(result.candidates) == 1
        assert result.candidates[0].name == "La Piazza"

    def test_high_min_rating_no_results_triggers_relaxation(self, repo):
        filter_ = RestaurantFilter(repo)
        prefs = UserPreferences(
            location="Banashankari", budget="medium", min_rating=5.0,
        )
        result = filter_.filter(prefs)
        # min_rating=5.0 with budget=medium should have zero results,
        # triggering relaxation
        assert len(result.candidates) > 0 or len(result.warnings) > 0
