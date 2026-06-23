"""User preferences data model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UserPreferences:
    """Represents the user's restaurant search preferences.

    Attributes:
        location: Required — city or locality name.
        budget: Required — one of "low", "medium", "high".
        cuisine: Optional — primary cuisine preference.
        min_rating: Minimum acceptable rating (0.0–5.0).
        additional: Optional free-text preferences (e.g. "family-friendly").
    """

    location: str
    budget: str
    cuisine: str | None = None
    min_rating: float = 0.0
    additional: str | None = None

    def to_dict(self) -> dict:
        """Return a dict suitable for prompt building / logging."""
        return {
            "location": self.location,
            "budget": self.budget,
            "cuisine": self.cuisine,
            "min_rating": self.min_rating,
            "additional": self.additional,
        }
