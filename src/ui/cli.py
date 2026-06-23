"""Interactive CLI for the restaurant recommendation system.

Prompts the user for preferences and displays formatted recommendation
results in the terminal.

Usage:
    python -m src.ui.cli
"""

from __future__ import annotations

import logging
import sys
import time

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Formatting helpers ──────────────────────────────────────────────────────

SEPARATOR = "─" * 72
HEADER_SEP = "═" * 72


def _print_banner() -> None:
    """Print the application banner."""
    print()
    print(HEADER_SEP)
    print("  🍽️  Zomato Restaurant Recommender — AI-Powered Picks")
    print(HEADER_SEP)
    print()


def _print_recommendation_card(rec) -> None:
    """Print a single recommendation as a formatted card."""
    rank_badge = f"#{rec.rank}"
    stars = "★" * int(rec.rating) + "☆" * (5 - int(rec.rating))

    print(f"  ┌{'─' * 68}┐")
    print(f"  │  {rank_badge:<4}  {rec.name:<58} │")
    print(f"  │{'─' * 68}│")
    print(f"  │  Cuisine  : {rec.cuisine:<53} │")
    print(f"  │  Rating   : {stars} ({rec.rating:.1f}/5){' ' * (43 - len(stars))} │")
    print(f"  │  Cost/2   : ₹{rec.estimated_cost:<53} │")
    print(f"  │{'─' * 68}│")

    # Word-wrap explanation into lines of ~60 chars
    explanation = rec.explanation
    words = explanation.split()
    lines: list[str] = []
    current_line = ""
    for word in words:
        if len(current_line) + len(word) + 1 > 60:
            lines.append(current_line)
            current_line = word
        else:
            current_line = f"{current_line} {word}".strip()
    if current_line:
        lines.append(current_line)

    print(f"  │  {'AI Insight:':<65} │")
    for line in lines:
        print(f"  │    {line:<63} │")

    print(f"  └{'─' * 68}┘")
    print()


def _print_results(response) -> None:
    """Print the full recommendation response."""
    print()
    print(HEADER_SEP)
    print("  📋  RECOMMENDATIONS")
    print(HEADER_SEP)

    if response.summary:
        print()
        print(f"  Summary: {response.summary}")

    print()

    if not response.recommendations:
        print("  ⚠️  No restaurants matched your criteria.")
        print("     Try broadening your filters (different location, budget, or cuisine).")
        print()
        return

    for rec in response.recommendations:
        _print_recommendation_card(rec)

    # Metadata footer
    meta = response.metadata
    print(SEPARATOR)
    print(f"  📊  Candidates considered: {meta.candidates_considered}")
    print(f"  🤖  Model: {meta.model or 'N/A'}")
    if meta.filters_applied:
        filters_str = ", ".join(
            f"{k}={v}" for k, v in meta.filters_applied.items() if v is not None
        )
        print(f"  🔍  Filters: {filters_str}")
    print(SEPARATOR)
    print()


# ── Input collection ────────────────────────────────────────────────────────

def _collect_preferences(repo) -> dict:
    """Interactively collect user preferences from stdin."""
    locations = repo.get_locations()
    cuisines = repo.get_cuisines()

    print("  Enter your preferences below (press Enter to skip optional fields):\n")

    # Location (required)
    print(f"  Available locations ({len(locations)} total):")
    # Show a sample of locations
    sample = locations[:15]
    print(f"    {', '.join(sample)}")
    if len(locations) > 15:
        print(f"    ... and {len(locations) - 15} more")
    print()

    while True:
        location = input("  📍 Location (required): ").strip()
        if location:
            break
        print("     ⚠️  Location is required. Please enter a location.\n")

    # Budget (required)
    print()
    while True:
        budget = input("  💰 Budget [low / medium / high] (required): ").strip().lower()
        if budget in ("low", "medium", "high"):
            break
        print("     ⚠️  Please enter one of: low, medium, high\n")

    # Cuisine (optional)
    print()
    print(f"  Available cuisines ({len(cuisines)} total):")
    sample_cuisines = cuisines[:15]
    print(f"    {', '.join(sample_cuisines)}")
    if len(cuisines) > 15:
        print(f"    ... and {len(cuisines) - 15} more")
    print()
    cuisine = input("  🍳 Cuisine (optional, press Enter to skip): ").strip() or None

    # Min rating (optional)
    print()
    while True:
        rating_input = input("  ⭐ Minimum rating [0.0 – 5.0] (default: 0.0): ").strip()
        if not rating_input:
            min_rating = 0.0
            break
        try:
            min_rating = float(rating_input)
            if 0.0 <= min_rating <= 5.0:
                break
            print("     ⚠️  Rating must be between 0.0 and 5.0\n")
        except ValueError:
            print("     ⚠️  Please enter a valid number\n")

    # Additional preferences (optional)
    print()
    additional = input("  📝 Additional preferences (optional, e.g. 'rooftop', 'family-friendly'): ").strip() or None

    return {
        "location": location,
        "budget": budget,
        "cuisine": cuisine,
        "min_rating": min_rating,
        "additional": additional,
    }


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    """Run the interactive CLI recommendation flow."""
    from src.data.loader import DatasetLoader
    from src.data.preprocessor import DataPreprocessor
    from src.data.repository import RestaurantRepository
    from src.models.preferences import UserPreferences
    from src.services.recommendation import RecommendationService

    _print_banner()

    print("  Loading dataset… ", end="", flush=True)
    start = time.perf_counter()
    repo = RestaurantRepository(
        loader=DatasetLoader(),
        preprocessor=DataPreprocessor(),
    )
    repo.get_all()  # trigger lazy load
    elapsed = time.perf_counter() - start
    print(f"✓ ({repo.count()} restaurants in {elapsed:.1f}s)\n")

    print(SEPARATOR)

    service = RecommendationService(repo)

    while True:
        prefs_dict = _collect_preferences(repo)
        preferences = UserPreferences(**prefs_dict)

        print()
        print("  🔄 Generating recommendations… ", end="", flush=True)
        start = time.perf_counter()

        try:
            response = service.recommend(preferences)
            elapsed = time.perf_counter() - start
            print(f"✓ ({elapsed:.1f}s)")
            _print_results(response)
        except ValueError as exc:
            elapsed = time.perf_counter() - start
            print(f"✗ ({elapsed:.1f}s)")
            print(f"\n  ❌ Error: {exc}\n")

        # Ask to continue
        again = input("  🔁 Search again? [Y/n]: ").strip().lower()
        if again in ("n", "no", "q", "quit", "exit"):
            print("\n  Thanks for using the Zomato Recommender! 👋\n")
            break
        print()
        print(SEPARATOR)


if __name__ == "__main__":
    main()
