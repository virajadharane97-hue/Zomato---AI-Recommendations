"""Prompt builder for Groq LLM ranking requests.

Constructs system and user prompts that instruct the LLM to rank
restaurant candidates based on user preferences, returning structured
JSON output.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from src.config import settings

if TYPE_CHECKING:
    from src.models.preferences import UserPreferences
    from src.models.restaurant import Restaurant

logger = logging.getLogger(__name__)

# ── System prompt ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are an expert restaurant recommendation assistant. Your task is to rank \
a list of candidate restaurants based on user preferences and provide a short, \
helpful explanation for each pick.

## Rules
1. ONLY recommend restaurants from the provided candidate list — never fabricate \
names, IDs, or details.
2. Return your response as a **valid JSON object** with this exact schema:
{{
  "summary": "<A 1-2 sentence overview of your recommendations>",
  "recommendations": [
    {{
      "id": "<restaurant id from the candidate list>",
      "rank": <integer starting from 1>,
      "explanation": "<1-2 sentence reason for this pick>"
    }}
  ]
}}
3. Rank the top {top_k} restaurants. If fewer candidates are available, rank all of them.
4. Consider the user's preferences as primary signals: location, budget, cuisine, \
and minimum rating. Treat any "additional" preferences as soft, secondary signals.
5. Prefer restaurants with higher ratings and more votes when other factors are equal.
6. Keep explanations concise but specific — mention what makes each pick a good \
match for the user.
"""


class PromptBuilder:
    """Builds system and user prompts for the Groq ranking call.

    Usage::

        builder = PromptBuilder()
        messages = builder.build(preferences, candidates)
        # messages is a list of {"role": ..., "content": ...} dicts
    """

    def __init__(self, top_k: int | None = None) -> None:
        self._top_k = top_k or settings.TOP_K_RECOMMENDATIONS

    def build(
        self,
        preferences: UserPreferences,
        candidates: list[Restaurant],
    ) -> list[dict[str, str]]:
        """Build the full message list for a Groq chat completion.

        Args:
            preferences: Validated user preferences.
            candidates: Pre-filtered and sorted restaurant candidates.

        Returns:
            List of message dicts with 'role' and 'content' keys.
        """
        system = self._build_system_prompt()
        user = self._build_user_prompt(preferences, candidates)

        logger.debug(
            "Prompt built: %d candidates, top_k=%d, user prompt length=%d chars",
            len(candidates), self._top_k, len(user),
        )

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    # ── Private helpers ─────────────────────────────────────────────────────

    def _build_system_prompt(self) -> str:
        """Build the system prompt with top_k substituted."""
        return SYSTEM_PROMPT.format(top_k=self._top_k)

    def _build_user_prompt(
        self,
        preferences: UserPreferences,
        candidates: list[Restaurant],
    ) -> str:
        """Build the user prompt with preferences and candidate data."""
        # Serialize preferences
        prefs_section = self._format_preferences(preferences)

        # Serialize candidates as compact JSON
        candidates_section = self._format_candidates(candidates)

        return (
            f"## User Preferences\n{prefs_section}\n\n"
            f"## Candidate Restaurants ({len(candidates)} total)\n"
            f"{candidates_section}\n\n"
            f"Please rank the top {self._top_k} restaurants from the list above "
            f"and return your response as the specified JSON object."
        )

    @staticmethod
    def _format_preferences(preferences: UserPreferences) -> str:
        """Format user preferences as a readable block."""
        lines = [
            f"- Location: {preferences.location}",
            f"- Budget: {preferences.budget}",
        ]
        if preferences.cuisine:
            lines.append(f"- Preferred Cuisine: {preferences.cuisine}")
        if preferences.min_rating > 0.0:
            lines.append(f"- Minimum Rating: {preferences.min_rating}")
        if preferences.additional:
            lines.append(f"- Additional Preferences: {preferences.additional}")
        return "\n".join(lines)

    @staticmethod
    def _format_candidates(candidates: list[Restaurant]) -> str:
        """Format candidates as a compact JSON array for token efficiency."""
        compact = [
            {
                "id": c.id,
                "name": c.name,
                "cuisines": ", ".join(c.cuisines),
                "rating": c.rating,
                "votes": c.votes,
                "cost_for_two": c.cost_for_two,
                "rest_type": c.rest_type,
            }
            for c in candidates
        ]
        return json.dumps(compact, separators=(",", ":"))
