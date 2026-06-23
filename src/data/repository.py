"""Restaurant repository — in-memory query interface over preprocessed restaurant data.

Supports:
  - Lazy initialization on first access.
  - Efficient lookups by location, cuisine, budget tier.
  - Distinct location and cuisine lists for UI dropdowns.
"""

from __future__ import annotations

import logging
from typing import Callable

import pandas as pd

from src.data.loader import DatasetLoader
from src.data.preprocessor import DataPreprocessor
from src.models.restaurant import Restaurant

logger = logging.getLogger(__name__)


class RestaurantRepository:
    """In-memory query interface over the preprocessed restaurant dataset.

    Lazily loads and preprocesses the dataset on first access.

    Usage::

        repo = RestaurantRepository()
        all_restaurants = repo.get_all()
        locations = repo.get_locations()
    """

    def __init__(
        self,
        loader: DatasetLoader | None = None,
        preprocessor: DataPreprocessor | None = None,
    ) -> None:
        self._loader = loader or DatasetLoader()
        self._preprocessor = preprocessor or DataPreprocessor()
        self._restaurants: list[Restaurant] | None = None
        self._df: pd.DataFrame | None = None
        self._loaded = False

    # ── Lazy loading ───────────────────────────────────────────────────────

    def _ensure_loaded(self) -> None:
        """Load dataset on first access (lazy initialization)."""
        if self._loaded:
            return

        logger.info("Loading and preprocessing dataset (first access) …")
        raw_df = self._loader.load()
        self._restaurants = self._preprocessor.process(raw_df)

        # Also build a DataFrame for efficient queries
        records = [r.to_dict() for r in self._restaurants]
        self._df = pd.DataFrame(records)

        self._loaded = True
        logger.info("Repository initialized with %d restaurants", len(self._restaurants))

    @property
    def is_loaded(self) -> bool:
        """Check whether the dataset has been loaded."""
        return self._loaded

    # ── Public query API ───────────────────────────────────────────────────

    def get_all(self) -> list[Restaurant]:
        """Return all restaurants in the repository."""
        self._ensure_loaded()
        return list(self._restaurants)

    def get_locations(self) -> list[str]:
        """Return distinct location names, sorted alphabetically."""
        self._ensure_loaded()
        return sorted(self._df["location"].unique().tolist())

    def get_cuisines(self) -> list[str]:
        """Return distinct cuisine names extracted from all restaurants, sorted alphabetically."""
        self._ensure_loaded()
        all_cuisines: set[str] = set()
        for r in self._restaurants:
            all_cuisines.update(c for c in r.cuisines if c)
        return sorted(all_cuisines)

    def get_by_location(self, location: str) -> list[Restaurant]:
        """Return restaurants matching a location (case-insensitive)."""
        self._ensure_loaded()
        loc_lower = location.lower().strip()
        return [r for r in self._restaurants if r.location.lower() == loc_lower]

    def get_by_cuisine(self, cuisine: str) -> list[Restaurant]:
        """Return restaurants that serve a given cuisine (case-insensitive)."""
        self._ensure_loaded()
        cuisine_lower = cuisine.lower().strip()
        return [
            r for r in self._restaurants
            if any(c.lower() == cuisine_lower for c in r.cuisines)
        ]

    def get_by_budget(self, budget_tier: str) -> list[Restaurant]:
        """Return restaurants matching a budget tier."""
        self._ensure_loaded()
        tier_lower = budget_tier.lower().strip()
        return [r for r in self._restaurants if r.budget_tier == tier_lower]

    def count(self) -> int:
        """Return total number of restaurants."""
        self._ensure_loaded()
        return len(self._restaurants)

    # ── Reload ─────────────────────────────────────────────────────────────

    def reload(self, *, force: bool = False) -> None:
        """Force a reload of the dataset (useful for refreshing cached data)."""
        self._loaded = False
        self._restaurants = None
        self._df = None
        raw_df = self._loader.load(force=force)
        self._restaurants = self._preprocessor.process(raw_df)
        records = [r.to_dict() for r in self._restaurants]
        self._df = pd.DataFrame(records)
        self._loaded = True
        logger.info("Repository reloaded with %d restaurants", len(self._restaurants))
