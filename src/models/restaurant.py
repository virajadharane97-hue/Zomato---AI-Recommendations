"""Canonical restaurant data model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Restaurant:
    """Represents a single restaurant record after preprocessing.

    Attributes:
        id: Stable identifier (dataset index or original id).
        name: Restaurant name.
        location: City or locality.
        cuisines: List of cuisine tags (e.g. ["Italian", "Continental"]).
        cost_for_two: Approximate cost for two people (INR).
        rating: Aggregate rating (e.g. 4.2).
        votes: Number of user votes (popularity signal).
        rest_type: Restaurant type (e.g. "Casual Dining", "Cafe").
        budget_tier: Derived from cost_for_two — "low", "medium", or "high".
    """

    id: str
    name: str
    location: str
    cuisines: list[str] = field(default_factory=list)
    cost_for_two: int = 0
    rating: float = 0.0
    votes: int = 0
    rest_type: str = ""
    budget_tier: str = ""

    def to_dict(self) -> dict:
        """Return a compact dict suitable for JSON serialization / prompts."""
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "cuisines": ", ".join(self.cuisines),
            "cost_for_two": self.cost_for_two,
            "rating": self.rating,
            "votes": self.votes,
            "rest_type": self.rest_type,
            "budget_tier": self.budget_tier,
        }
