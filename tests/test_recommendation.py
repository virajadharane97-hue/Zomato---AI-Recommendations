"""Tests for Phase 3 — Groq Integration (LLM Layer).

Covers:
  - PromptBuilder: message structure, candidate serialization, preference formatting
  - ResponseParser: valid JSON, invalid JSON, missing fields, extra fields
  - RecommendationEnricher: join rankings with restaurant data, heuristic fallback
  - RecommendationService: end-to-end with mocked LLM client

Uses synthetic fixtures — no real Groq API calls.
"""

import json

import pytest

from src.models.preferences import UserPreferences
from src.models.restaurant import Restaurant
from src.services.prompt_builder import PromptBuilder
from src.services.llm_client import (
    LLMClient,
    LLMRanking,
    LLMResponse,
    ResponseParser,
)
from src.services.recommendation import (
    RecommendationEnricher,
    RecommendationService,
)
from src.services.filter import RestaurantFilter, CandidateSelector
from src.services.validator import PreferenceValidator


# ── Fake repository ─────────────────────────────────────────────────────────

class FakeRepository:
    """Minimal repository stub for testing."""

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


# ── Fake LLM client ────────────────────────────────────────────────────────

class FakeLLMClient:
    """Stub LLM client that returns a fixed JSON response."""

    def __init__(self, response: LLMResponse) -> None:
        self._response = response
        self.last_messages: list[dict] | None = None

    def complete(self, messages: list[dict[str, str]]) -> LLMResponse:
        self.last_messages = messages
        return self._response


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_restaurants() -> list[Restaurant]:
    """Deterministic set of restaurants for testing."""
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
            id="6", name="Pasta Palace",
            location="Banashankari", cuisines=["Italian"],
            cost_for_two=900, rating=4.3, votes=700,
            rest_type="Casual Dining", budget_tier="medium",
        ),
    ]


@pytest.fixture
def repo(sample_restaurants) -> FakeRepository:
    return FakeRepository(sample_restaurants)


@pytest.fixture
def sample_preferences() -> UserPreferences:
    return UserPreferences(
        location="Banashankari",
        budget="medium",
        cuisine="North Indian",
        min_rating=4.0,
        additional="family-friendly",
    )


@pytest.fixture
def sample_candidates(sample_restaurants) -> list[Restaurant]:
    """Subset of restaurants that would survive filtering."""
    return [r for r in sample_restaurants if r.location == "Banashankari" and r.budget_tier == "medium"]


# ═══════════════════════════════════════════════════════════════════════════
# PROMPT BUILDER
# ═══════════════════════════════════════════════════════════════════════════

class TestPromptBuilder:
    def test_build_returns_two_messages(self, sample_preferences, sample_candidates):
        builder = PromptBuilder(top_k=3)
        messages = builder.build(sample_preferences, sample_candidates)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_system_prompt_contains_top_k(self, sample_preferences, sample_candidates):
        builder = PromptBuilder(top_k=5)
        messages = builder.build(sample_preferences, sample_candidates)
        assert "5" in messages[0]["content"]

    def test_system_prompt_forbids_fabrication(self, sample_preferences, sample_candidates):
        builder = PromptBuilder()
        messages = builder.build(sample_preferences, sample_candidates)
        system = messages[0]["content"].lower()
        assert "fabricat" in system or "only recommend" in system

    def test_user_prompt_contains_preferences(self, sample_preferences, sample_candidates):
        builder = PromptBuilder()
        messages = builder.build(sample_preferences, sample_candidates)
        user = messages[1]["content"]
        assert "Banashankari" in user
        assert "medium" in user
        assert "North Indian" in user
        assert "family-friendly" in user

    def test_user_prompt_contains_all_candidate_ids(self, sample_preferences, sample_candidates):
        builder = PromptBuilder()
        messages = builder.build(sample_preferences, sample_candidates)
        user = messages[1]["content"]
        for c in sample_candidates:
            assert c.id in user

    def test_user_prompt_contains_candidate_names(self, sample_preferences, sample_candidates):
        builder = PromptBuilder()
        messages = builder.build(sample_preferences, sample_candidates)
        user = messages[1]["content"]
        for c in sample_candidates:
            assert c.name in user

    def test_candidates_serialized_as_json(self, sample_preferences, sample_candidates):
        builder = PromptBuilder()
        messages = builder.build(sample_preferences, sample_candidates)
        user = messages[1]["content"]
        # The candidates section should contain parseable JSON
        # Find the JSON array in the user prompt
        start = user.find("[{")
        end = user.rfind("}]") + 2
        assert start >= 0 and end > start
        parsed = json.loads(user[start:end])
        assert len(parsed) == len(sample_candidates)

    def test_optional_fields_omitted_when_none(self, sample_candidates):
        prefs = UserPreferences(location="Banashankari", budget="medium")
        builder = PromptBuilder()
        messages = builder.build(prefs, sample_candidates)
        user = messages[1]["content"]
        assert "Preferred Cuisine" not in user
        assert "Additional Preferences" not in user

    def test_min_rating_shown_when_nonzero(self, sample_candidates):
        prefs = UserPreferences(
            location="Banashankari", budget="medium", min_rating=4.0,
        )
        builder = PromptBuilder()
        messages = builder.build(prefs, sample_candidates)
        user = messages[1]["content"]
        assert "Minimum Rating" in user


# ═══════════════════════════════════════════════════════════════════════════
# RESPONSE PARSER
# ═══════════════════════════════════════════════════════════════════════════

class TestResponseParser:
    def test_parse_valid_json(self):
        raw = json.dumps({
            "summary": "Great options!",
            "recommendations": [
                {"id": "1", "rank": 1, "explanation": "Best match"},
                {"id": "2", "rank": 2, "explanation": "Good alternative"},
            ]
        })
        summary, rankings = ResponseParser.parse(raw)
        assert summary == "Great options!"
        assert len(rankings) == 2
        assert rankings[0].id == "1"
        assert rankings[0].rank == 1
        assert rankings[1].id == "2"

    def test_parse_json_in_code_block(self):
        raw = '```json\n{"summary":"Test","recommendations":[{"id":"1","rank":1,"explanation":"OK"}]}\n```'
        summary, rankings = ResponseParser.parse(raw)
        assert summary == "Test"
        assert len(rankings) == 1

    def test_parse_invalid_json_raises(self):
        with pytest.raises(ValueError, match="Failed to parse JSON"):
            ResponseParser.parse("This is not JSON at all")

    def test_parse_missing_recommendations_raises(self):
        raw = json.dumps({"summary": "No recs"})
        with pytest.raises(ValueError, match="recommendations"):
            ResponseParser.parse(raw)

    def test_parse_extra_fields_ignored(self):
        raw = json.dumps({
            "summary": "Extra fields",
            "recommendations": [
                {"id": "1", "rank": 1, "explanation": "OK", "extra_field": "ignored"}
            ],
            "extra_top_level": True,
        })
        summary, rankings = ResponseParser.parse(raw)
        assert len(rankings) == 1
        assert rankings[0].id == "1"

    def test_parse_missing_id_skipped(self):
        raw = json.dumps({
            "summary": "Test",
            "recommendations": [
                {"rank": 1, "explanation": "No ID"},
                {"id": "2", "rank": 2, "explanation": "Has ID"},
            ]
        })
        summary, rankings = ResponseParser.parse(raw)
        assert len(rankings) == 1
        assert rankings[0].id == "2"

    def test_parse_rankings_sorted_by_rank(self):
        raw = json.dumps({
            "summary": "Test",
            "recommendations": [
                {"id": "3", "rank": 3, "explanation": "Third"},
                {"id": "1", "rank": 1, "explanation": "First"},
                {"id": "2", "rank": 2, "explanation": "Second"},
            ]
        })
        _, rankings = ResponseParser.parse(raw)
        assert [r.rank for r in rankings] == [1, 2, 3]

    def test_parse_non_dict_top_level_raises(self):
        with pytest.raises(ValueError, match="Expected JSON object"):
            ResponseParser.parse("[1, 2, 3]")


# ═══════════════════════════════════════════════════════════════════════════
# RECOMMENDATION ENRICHER
# ═══════════════════════════════════════════════════════════════════════════

class TestRecommendationEnricher:
    def test_enrich_joins_rankings_with_candidates(self, sample_candidates):
        rankings = [
            LLMRanking(id="1", rank=1, explanation="Best pick"),
            LLMRanking(id="2", rank=2, explanation="Runner up"),
        ]
        enricher = RecommendationEnricher()
        recs = enricher.enrich(rankings, sample_candidates)
        assert len(recs) == 2
        assert recs[0].name == "Tandoori Nights"
        assert recs[0].rank == 1
        assert recs[0].explanation == "Best pick"
        assert recs[1].name == "Dragon Bowl"

    def test_enrich_skips_unknown_ids(self, sample_candidates):
        rankings = [
            LLMRanking(id="999", rank=1, explanation="Unknown"),
            LLMRanking(id="1", rank=2, explanation="Known"),
        ]
        enricher = RecommendationEnricher()
        recs = enricher.enrich(rankings, sample_candidates)
        assert len(recs) == 1
        assert recs[0].name == "Tandoori Nights"

    def test_enrich_includes_cuisine_and_cost(self, sample_candidates):
        rankings = [LLMRanking(id="1", rank=1, explanation="Test")]
        enricher = RecommendationEnricher()
        recs = enricher.enrich(rankings, sample_candidates)
        assert recs[0].cuisine == "North Indian, Mughlai"
        assert recs[0].estimated_cost == 800
        assert recs[0].rating == 4.5

    def test_heuristic_enrich(self, sample_candidates):
        enricher = RecommendationEnricher()
        recs = enricher.heuristic_enrich(sample_candidates, top_k=2)
        assert len(recs) == 2
        assert recs[0].rank == 1
        assert recs[1].rank == 2
        assert "AI explanation unavailable" in recs[0].explanation

    def test_heuristic_enrich_caps_at_top_k(self, sample_candidates):
        enricher = RecommendationEnricher()
        recs = enricher.heuristic_enrich(sample_candidates, top_k=1)
        assert len(recs) == 1


# ═══════════════════════════════════════════════════════════════════════════
# LLM CLIENT
# ═══════════════════════════════════════════════════════════════════════════

class TestLLMClientFallback:
    def test_no_api_key_returns_heuristic_fallback(self):
        client = LLMClient(api_key="", model="test")
        response = client.complete([{"role": "user", "content": "test"}])
        assert response.is_fallback
        assert response.model == "heuristic-fallback"
        assert len(response.rankings) == 0


# ═══════════════════════════════════════════════════════════════════════════
# RECOMMENDATION SERVICE (Integration)
# ═══════════════════════════════════════════════════════════════════════════

class TestRecommendationServiceWithMockedLLM:
    """Integration tests using a fake LLM client to verify the full pipeline."""

    def _make_service(
        self, repo, llm_response: LLMResponse, top_k: int = 3,
    ) -> tuple[RecommendationService, FakeLLMClient]:
        fake_llm = FakeLLMClient(llm_response)
        service = RecommendationService(
            repository=repo,
            llm_client=fake_llm,
            top_k=top_k,
        )
        return service, fake_llm

    def test_full_pipeline_with_llm_response(self, repo):
        """End-to-end: mock LLM returns ranked JSON → enriched output."""
        llm_response = LLMResponse(
            summary="Top picks for you!",
            rankings=[
                LLMRanking(id="1", rank=1, explanation="Perfect match for North Indian"),
                LLMRanking(id="6", rank=2, explanation="Great Italian option"),
                LLMRanking(id="2", rank=3, explanation="Solid Chinese choice"),
            ],
            model="llama-3.3-70b-versatile",
            latency_ms=500,
            prompt_tokens=100,
            completion_tokens=50,
        )

        service, fake_llm = self._make_service(repo, llm_response, top_k=3)
        prefs = UserPreferences(
            location="Banashankari", budget="medium", min_rating=0.0,
        )

        result = service.recommend(prefs)

        assert result.summary == "Top picks for you!"
        assert len(result.recommendations) == 3
        assert result.recommendations[0].name == "Tandoori Nights"
        assert result.recommendations[0].rank == 1
        assert result.recommendations[1].name == "Pasta Palace"
        assert result.metadata.model == "llama-3.3-70b-versatile"
        assert result.metadata.candidates_considered > 0

    def test_pipeline_with_fallback_llm(self, repo):
        """When LLM returns fallback, heuristic enrichment is used."""
        llm_response = LLMResponse(
            summary="Ranked by rating — AI explanation unavailable.",
            rankings=[],
            model="heuristic-fallback",
            is_fallback=True,
        )

        service, _ = self._make_service(repo, llm_response, top_k=2)
        prefs = UserPreferences(
            location="Banashankari", budget="medium", min_rating=0.0,
        )

        result = service.recommend(prefs)

        assert len(result.recommendations) > 0
        assert "unavailable" in result.summary.lower()
        # Heuristic enrichment uses generic explanations
        assert "AI explanation unavailable" in result.recommendations[0].explanation

    def test_pipeline_with_unknown_location_raises(self, repo):
        """When location is unknown, validation fails with ValueError."""
        llm_response = LLMResponse()  # shouldn't be called

        service, _ = self._make_service(repo, llm_response)
        prefs = UserPreferences(
            location="NonExistentCity", budget="low", min_rating=0.0,
        )

        with pytest.raises(ValueError, match="Invalid preferences"):
            service.recommend(prefs)

    def test_pipeline_invalid_preferences_raises(self, repo):
        """Invalid preferences should raise ValueError."""
        llm_response = LLMResponse()

        service, _ = self._make_service(repo, llm_response)
        prefs = UserPreferences(
            location="",  # invalid: empty
            budget="luxury",  # invalid: not low/medium/high
        )

        with pytest.raises(ValueError, match="Invalid preferences"):
            service.recommend(prefs)

    def test_pipeline_sends_messages_to_llm(self, repo):
        """Verify that the LLM receives properly formatted messages."""
        llm_response = LLMResponse(
            summary="Test",
            rankings=[LLMRanking(id="1", rank=1, explanation="Test")],
            model="test-model",
        )

        service, fake_llm = self._make_service(repo, llm_response)
        prefs = UserPreferences(
            location="Banashankari", budget="medium", min_rating=0.0,
        )

        service.recommend(prefs)

        # Verify messages were sent to LLM
        assert fake_llm.last_messages is not None
        assert len(fake_llm.last_messages) == 2
        assert fake_llm.last_messages[0]["role"] == "system"
        assert fake_llm.last_messages[1]["role"] == "user"

    def test_pipeline_metadata_includes_filters(self, repo):
        """Metadata should record which filters were applied."""
        llm_response = LLMResponse(
            summary="Test",
            rankings=[LLMRanking(id="1", rank=1, explanation="Test")],
            model="test-model",
        )

        service, _ = self._make_service(repo, llm_response)
        prefs = UserPreferences(
            location="Banashankari", budget="medium",
            cuisine="North Indian", min_rating=4.0,
        )

        result = service.recommend(prefs)

        assert "location" in result.metadata.filters_applied
        assert "budget" in result.metadata.filters_applied
        assert result.metadata.model == "test-model"

    def test_llm_returns_unknown_ids_gracefully(self, repo):
        """If LLM returns IDs not in candidates, they're skipped."""
        llm_response = LLMResponse(
            summary="Test",
            rankings=[
                LLMRanking(id="999", rank=1, explanation="Unknown"),
                LLMRanking(id="1", rank=2, explanation="Known"),
            ],
            model="test-model",
        )

        service, _ = self._make_service(repo, llm_response)
        prefs = UserPreferences(
            location="Banashankari", budget="medium", min_rating=0.0,
        )

        result = service.recommend(prefs)

        # Only the known ID should be in recommendations
        names = [r.name for r in result.recommendations]
        assert "Tandoori Nights" in names

    def test_empty_llm_rankings_triggers_heuristic(self, repo):
        """If LLM returns no rankings, heuristic fallback is used."""
        llm_response = LLMResponse(
            summary="I couldn't decide",
            rankings=[],
            model="test-model",
            is_fallback=False,  # not explicitly fallback, just empty
        )

        service, _ = self._make_service(repo, llm_response, top_k=2)
        prefs = UserPreferences(
            location="Banashankari", budget="medium", min_rating=0.0,
        )

        result = service.recommend(prefs)

        # Should still produce recommendations via heuristic
        assert len(result.recommendations) > 0
        assert "AI explanation unavailable" in result.recommendations[0].explanation
