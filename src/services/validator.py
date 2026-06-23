"""Preference validation and normalization.

Validates user preferences against the dataset vocabulary and returns
structured errors / suggestions when inputs don't match.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from difflib import get_close_matches
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.data.repository import RestaurantRepository

logger = logging.getLogger(__name__)

# ── City aliases ────────────────────────────────────────────────────────────
# Maps common alternate names → canonical name present in the dataset.
CITY_ALIASES: dict[str, str] = {
    "bengaluru": "Bangalore",
    "bombay": "Mumbai",
    "calcutta": "Kolkata",
    "madras": "Chennai",
    "poona": "Pune",
    "trivandrum": "Thiruvananthapuram",
    "pondicherry": "Puducherry",
    "gurgaon": "Gurugram",
}

VALID_BUDGET_TIERS = {"low", "medium", "high"}


# ── Data models ─────────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    """Result of preference validation.

    Attributes:
        is_valid: True if all required fields pass validation.
        errors: List of human-readable error messages.
        suggestions: Dict mapping field names to suggested corrections
                     (e.g. {"location": ["Banashankari", "Basavanagudi"]}).
    """

    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    suggestions: dict[str, list[str]] = field(default_factory=dict)


# ── Normalizer ──────────────────────────────────────────────────────────────

class PreferenceNormalizer:
    """Normalizes raw user preference values before validation.

    Performs:
    - Location alias resolution (e.g. "Bengaluru" → "Bangalore")
    - Cuisine lowercasing for matching
    - Free-text trimming
    """

    @staticmethod
    def normalize_location(location: str) -> str:
        """Normalize a location string: trim, title-case, resolve aliases."""
        cleaned = location.strip()
        alias_key = cleaned.lower()
        if alias_key in CITY_ALIASES:
            return CITY_ALIASES[alias_key]
        return cleaned.title()

    @staticmethod
    def normalize_budget(budget: str) -> str:
        """Normalize budget tier to lowercase."""
        return budget.strip().lower()

    @staticmethod
    def normalize_cuisine(cuisine: str | None) -> str | None:
        """Normalize cuisine string: trim and title-case."""
        if cuisine is None:
            return None
        cleaned = cuisine.strip()
        return cleaned.title() if cleaned else None

    @staticmethod
    def normalize_additional(additional: str | None) -> str | None:
        """Trim free-text additional field."""
        if additional is None:
            return None
        cleaned = additional.strip()
        return cleaned if cleaned else None


# ── Validator ───────────────────────────────────────────────────────────────

class PreferenceValidator:
    """Validates user preferences against the dataset vocabulary.

    Usage::

        validator = PreferenceValidator(repository)
        result = validator.validate(preferences)
        if not result.is_valid:
            print(result.errors, result.suggestions)
    """

    def __init__(self, repository: RestaurantRepository) -> None:
        self._repo = repository
        self._normalizer = PreferenceNormalizer()

    def validate(
        self,
        location: str,
        budget: str,
        cuisine: str | None = None,
        min_rating: float = 0.0,
    ) -> ValidationResult:
        """Validate all preference fields and return a structured result.

        Args:
            location: City or locality name (required, non-empty).
            budget: Budget tier — must be one of "low", "medium", "high".
            cuisine: Optional cuisine preference.
            min_rating: Minimum rating, must be in [0.0, 5.0].

        Returns:
            ValidationResult with is_valid, errors, and suggestions.
        """
        result = ValidationResult()

        # 1. Location validation
        self._validate_location(location, result)

        # 2. Budget validation
        self._validate_budget(budget, result)

        # 3. Min-rating validation
        self._validate_min_rating(min_rating, result)

        # 4. Cuisine validation (optional)
        if cuisine is not None:
            self._validate_cuisine(cuisine, result)

        result.is_valid = len(result.errors) == 0
        return result

    # ── Private helpers ─────────────────────────────────────────────────────

    def _validate_location(self, location: str, result: ValidationResult) -> None:
        """Location must be non-empty and match at least one value in the dataset."""
        if not location or not location.strip():
            result.errors.append("Location is required and cannot be empty.")
            return

        normalized = self._normalizer.normalize_location(location)
        known_locations = self._repo.get_locations()
        known_lower = [loc.lower() for loc in known_locations]

        if normalized.lower() not in known_lower:
            # Find closest matches using fuzzy matching
            close = get_close_matches(
                normalized.lower(), known_lower, n=5, cutoff=0.5
            )
            suggestions = [
                known_locations[known_lower.index(m)] for m in close
            ]
            result.errors.append(
                f"Location '{location.strip()}' not found in the dataset."
            )
            if suggestions:
                result.suggestions["location"] = suggestions
                logger.debug(
                    "Location '%s' not found. Suggestions: %s",
                    location, suggestions,
                )

    def _validate_budget(self, budget: str, result: ValidationResult) -> None:
        """Budget must be one of the valid tier names."""
        normalized = self._normalizer.normalize_budget(budget)
        if normalized not in VALID_BUDGET_TIERS:
            result.errors.append(
                f"Invalid budget '{budget}'. Must be one of: "
                f"{', '.join(sorted(VALID_BUDGET_TIERS))}."
            )

    def _validate_min_rating(self, min_rating: float, result: ValidationResult) -> None:
        """Min-rating must be a float in [0.0, 5.0]."""
        try:
            val = float(min_rating)
        except (TypeError, ValueError):
            result.errors.append(
                f"Invalid min_rating '{min_rating}'. Must be a number between 0.0 and 5.0."
            )
            return

        if not (0.0 <= val <= 5.0):
            result.errors.append(
                f"min_rating {val} is out of range. Must be between 0.0 and 5.0."
            )

    def _validate_cuisine(self, cuisine: str, result: ValidationResult) -> None:
        """Cuisine should fuzzy-match against the dataset vocabulary."""
        if not cuisine.strip():
            return  # empty cuisine treated as "no preference"

        normalized = self._normalizer.normalize_cuisine(cuisine)
        known_cuisines = self._repo.get_cuisines()
        known_lower = [c.lower() for c in known_cuisines]

        if normalized and normalized.lower() not in known_lower:
            close = get_close_matches(
                normalized.lower(), known_lower, n=5, cutoff=0.5
            )
            suggestions = [
                known_cuisines[known_lower.index(m)] for m in close
            ]
            # Cuisine mismatch is a warning, not a hard error — it's optional
            if suggestions:
                result.suggestions["cuisine"] = suggestions
                logger.debug(
                    "Cuisine '%s' not found. Suggestions: %s",
                    cuisine, suggestions,
                )
            # NOTE: We do NOT add an error for unknown cuisine.
            # The filter will simply return no cuisine-match results,
            # and constraint relaxation will handle it.
