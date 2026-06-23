"""Data preprocessor — transforms raw Zomato dataset into canonical Restaurant schema.

Handles:
  - Column selection and renaming to canonical schema.
  - Parsing `rate` from "4.1/5" format to float.
  - Coercing `approx_cost(for two people)` from string to int.
  - Parsing cuisine strings into lists.
  - Normalizing location strings.
  - Deriving `budget_tier` from `cost_for_two` using configurable thresholds.
  - Deduplication by (name, location).
  - Dropping rows with invalid critical fields.
"""

from __future__ import annotations

import logging
import re

import pandas as pd

from src.config import settings
from src.models.restaurant import Restaurant

logger = logging.getLogger(__name__)

# ── Column mapping: raw dataset → canonical schema ──────────────────────
_COLUMN_MAP: dict[str, str] = {
    "name": "name",
    "location": "location",
    "rest_type": "rest_type",
    "cuisines": "cuisines",
    "approx_cost(for two people)": "cost_for_two",
    "rate": "rating",
    "votes": "votes",
    "listed_in(city)": "city",
}


class DataPreprocessor:
    """Cleans and normalizes the raw Zomato dataset into a list of Restaurant objects.

    Usage::

        preprocessor = DataPreprocessor()
        restaurants = preprocessor.process(raw_df)
    """

    def __init__(self, budget_thresholds: dict | None = None) -> None:
        self._budget_thresholds = budget_thresholds or settings.BUDGET_THRESHOLDS

    # ── Public API ─────────────────────────────────────────────────────────

    def process(self, df: pd.DataFrame) -> list[Restaurant]:
        """Transform raw DataFrame into a list of Restaurant objects.

        Args:
            df: Raw dataset as returned by DatasetLoader.

        Returns:
            List of cleaned, validated Restaurant instances.
        """
        rows_before = len(df)
        logger.info("Preprocessing %d raw rows …", rows_before)

        # 1. Select & rename columns
        df = self._select_columns(df)

        # 2. Parse rating from "4.1/5" → 4.1
        df = self._parse_rating(df)

        # 3. Parse cost from string "1,200" → 1200
        df = self._parse_cost(df)

        # 4. Parse cuisines from comma-separated string → list[str]
        df = self._parse_cuisines(df)

        # 5. Normalize location strings
        df = self._normalize_location(df)

        # 6. Use `city` as location fallback (if `location` is null)
        df = self._fill_location_from_city(df)

        # 7. Drop rows with invalid critical fields (also fills nulls in rating/cost/votes)
        df = self._drop_invalid(df)

        # 8. Derive budget_tier (must run after _drop_invalid which fills null costs)
        df = self._derive_budget_tier(df)

        # 9. Deduplicate
        df = self._deduplicate(df)

        rows_after = len(df)
        logger.info(
            "Preprocessing complete: %d → %d rows (dropped %d)",
            rows_before,
            rows_after,
            rows_before - rows_after,
        )

        # 10. Convert to Restaurant objects
        return self._to_restaurants(df)

    # ── Step implementations ───────────────────────────────────────────────

    def _select_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Select relevant columns and rename to canonical names."""
        # Find columns that exist in the dataset
        available = {col: new for col, new in _COLUMN_MAP.items() if col in df.columns}
        missing = set(_COLUMN_MAP.keys()) - set(available.keys())

        if missing:
            logger.warning("Expected columns missing from dataset: %s", missing)

        # Keep original columns we need plus the index for id generation
        cols_to_keep = list(available.keys())
        result = df[cols_to_keep].copy()
        result.rename(columns=available, inplace=True)

        # Preserve original index as 'id' before any reset
        result["id"] = df.index.astype(str)

        return result

    def _parse_rating(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse '4.1/5' → 4.1. Handle 'NEW', '-', nan, etc."""
        def _extract_rating(val) -> float | None:
            if pd.isna(val):
                return None
            val_str = str(val).strip()
            # Try pattern like "4.1/5" or "4.1 /5"
            match = re.match(r"^(\d+\.?\d*)\s*/\s*5$", val_str)
            if match:
                rating = float(match.group(1))
                return rating if 0.0 <= rating <= 5.0 else None
            # Try plain float
            try:
                rating = float(val_str)
                return rating if 0.0 <= rating <= 5.0 else None
            except ValueError:
                return None

        df["rating"] = df["rating"].apply(_extract_rating)
        return df

    def _parse_cost(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse '1,200' → 1200. Handle nan, non-numeric, etc."""
        def _extract_cost(val) -> int | None:
            if pd.isna(val):
                return None
            val_str = str(val).strip().replace(",", "")
            try:
                cost = int(float(val_str))
                return cost if cost > 0 else None
            except (ValueError, TypeError):
                return None

        df["cost_for_two"] = df["cost_for_two"].apply(_extract_cost)
        return df

    def _parse_cuisines(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse 'North Indian, Chinese' → ['North Indian', 'Chinese'].

        Splits on commas, semicolons, pipes, and ampersands.
        Strips whitespace and filters empty strings.
        """
        def _split_cuisines(val) -> list[str]:
            if pd.isna(val) or str(val).strip().lower() in ("", "null", "none"):
                return []
            # Split on comma, semicolon, pipe, ampersand
            parts = re.split(r"[,;|&]", str(val))
            return [p.strip() for p in parts if p.strip()]

        df["cuisines"] = df["cuisines"].apply(_split_cuisines)
        return df

    def _normalize_location(self, df: pd.DataFrame) -> pd.DataFrame:
        """Trim and title-case location strings."""
        df["location"] = df["location"].apply(
            lambda x: str(x).strip().title() if pd.notna(x) and str(x).strip() else None
        )
        return df

    def _fill_location_from_city(self, df: pd.DataFrame) -> pd.DataFrame:
        """If `location` is null, fall back to `city` column."""
        if "city" in df.columns:
            mask = df["location"].isna() | (df["location"] == "None") | (df["location"] == "")
            df.loc[mask, "location"] = df.loc[mask, "city"].apply(
                lambda x: str(x).strip().title() if pd.notna(x) else None
            )
        # Drop the city column — we use location only
        df.drop(columns=["city"], inplace=True, errors="ignore")
        return df

    def _derive_budget_tier(self, df: pd.DataFrame) -> pd.DataFrame:
        """Derive budget_tier from cost_for_two using configurable thresholds."""

        def _tier(cost: int | None) -> str:
            if cost is None:
                return ""
            for tier_name, (low, high) in self._budget_thresholds.items():
                if low <= cost <= high:
                    return tier_name
            return "high"  # fallback for anything above defined thresholds

        df["budget_tier"] = df["cost_for_two"].apply(_tier)
        return df

    def _drop_invalid(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop rows missing critical fields: name, location, rating."""
        before = len(df)
        # Name and location are essential
        df = df.dropna(subset=["name", "location"])
        # Rating can be null — we keep them but with rating=0 for filtering purposes
        df["rating"] = df["rating"].fillna(0.0)
        # Cost can be null — we keep them with 0 for filtering
        df["cost_for_two"] = df["cost_for_two"].fillna(0)
        # Votes default to 0
        df["votes"] = df["votes"].fillna(0).astype(int)
        # rest_type default to empty string
        df["rest_type"] = df["rest_type"].fillna("").astype(str)

        after = len(df)
        if before != after:
            logger.info("Dropped %d rows with missing name/location", before - after)
        return df

    def _deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate restaurants by (name, location), keeping the one with more votes."""
        before = len(df)
        df = df.sort_values("votes", ascending=False)
        df = df.drop_duplicates(subset=["name", "location"], keep="first")
        after = len(df)
        if before != after:
            logger.info("Deduplicated: removed %d duplicate entries", before - after)
        return df

    # ── Conversion ────────────────────────────────────────────────────────

    def _to_restaurants(self, df: pd.DataFrame) -> list[Restaurant]:
        """Convert DataFrame rows to Restaurant dataclass instances."""
        restaurants: list[Restaurant] = []
        for _, row in df.iterrows():
            restaurants.append(
                Restaurant(
                    id=str(row.get("id", "")),
                    name=str(row.get("name", "")),
                    location=str(row.get("location", "")),
                    cuisines=row.get("cuisines", []) if isinstance(row.get("cuisines"), list) else [],
                    cost_for_two=int(row.get("cost_for_two", 0)),
                    rating=float(row.get("rating", 0.0)),
                    votes=int(row.get("votes", 0)),
                    rest_type=str(row.get("rest_type", "")),
                    budget_tier=str(row.get("budget_tier", "")),
                )
            )
        return restaurants
