"""Standalone test runner — verifies Phase 3 components without pytest or pydantic.

Mocks out ``src.config`` so we don't need pydantic installed.
"""
import json
import sys
import os
import traceback
import types

# Ensure project root is on sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# ── Mock out src.config before any project imports ──────────────────────────
# Create a fake Settings object and inject it as src.config.settings
config_module = types.ModuleType("src.config")

class _FakeSettings:
    GROQ_API_KEY = ""
    GROQ_MODEL = "llama-3.3-70b-versatile"
    GROQ_FALLBACK_MODEL = "llama-3.1-8b-instant"
    GROQ_TEMPERATURE = 0.3
    HF_DATASET_NAME = "ManikaSaini/zomato-restaurant-recommendation"
    MAX_CANDIDATES_FOR_LLM = 20
    TOP_K_RECOMMENDATIONS = 5
    DATA_CACHE_PATH = "./data"
    BUDGET_THRESHOLDS = {
        "low": (0, 500),
        "medium": (501, 1500),
        "high": (1501, float("inf")),
    }

config_module.settings = _FakeSettings()
config_module.Settings = _FakeSettings
sys.modules["src.config"] = config_module

# Also mock pydantic_settings / pydantic so transitive imports don't fail
for mod_name in ["pydantic", "pydantic_settings", "pydantic.fields"]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = types.ModuleType(mod_name)

# Now safe to import project modules
from src.models.preferences import UserPreferences
from src.models.restaurant import Restaurant
from src.services.prompt_builder import PromptBuilder
from src.services.llm_client import LLMClient, LLMRanking, LLMResponse, ResponseParser
from src.services.recommendation import RecommendationEnricher, RecommendationService

# ── Fakes ───────────────────────────────────────────────────────────────────

class FakeRepository:
    def __init__(self, restaurants):
        self._restaurants = restaurants
    def get_all(self):
        return list(self._restaurants)
    def get_locations(self):
        return sorted({r.location for r in self._restaurants})
    def get_cuisines(self):
        c = set()
        for r in self._restaurants:
            c.update(x for x in r.cuisines if x)
        return sorted(c)

class FakeLLMClient:
    def __init__(self, response):
        self._response = response
        self.last_messages = None
    def complete(self, messages):
        self.last_messages = messages
        return self._response

RESTAURANTS = [
    Restaurant(id="1", name="Tandoori Nights", location="Banashankari",
               cuisines=["North Indian", "Mughlai"], cost_for_two=800,
               rating=4.5, votes=1200, rest_type="Casual Dining", budget_tier="medium"),
    Restaurant(id="2", name="Dragon Bowl", location="Banashankari",
               cuisines=["Chinese", "Thai"], cost_for_two=600,
               rating=4.2, votes=800, rest_type="Casual Dining", budget_tier="medium"),
    Restaurant(id="3", name="South Spice", location="Banashankari",
               cuisines=["South Indian"], cost_for_two=300,
               rating=3.8, votes=500, rest_type="Quick Bites", budget_tier="low"),
    Restaurant(id="6", name="Pasta Palace", location="Banashankari",
               cuisines=["Italian"], cost_for_two=900,
               rating=4.3, votes=700, rest_type="Casual Dining", budget_tier="medium"),
]

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  PASS: {name}")
        passed += 1
    else:
        print(f"  FAIL: {name} {detail}")
        failed += 1

# ── Tests ───────────────────────────────────────────────────────────────────

print("\n=== PromptBuilder ===")
try:
    builder = PromptBuilder(top_k=3)
    prefs = UserPreferences(location="Banashankari", budget="medium", cuisine="North Indian", min_rating=4.0, additional="family-friendly")
    candidates = [r for r in RESTAURANTS if r.budget_tier == "medium"]
    msgs = builder.build(prefs, candidates)
    test("Returns 2 messages", len(msgs) == 2)
    test("System role", msgs[0]["role"] == "system")
    test("User role", msgs[1]["role"] == "user")
    test("Contains location", "Banashankari" in msgs[1]["content"])
    test("Contains cuisine", "North Indian" in msgs[1]["content"])
    test("Contains additional", "family-friendly" in msgs[1]["content"])
    test("Contains candidate IDs", all(c.id in msgs[1]["content"] for c in candidates))
    test("Contains no-fabrication rule", "fabricat" in msgs[0]["content"].lower() or "only recommend" in msgs[0]["content"].lower())
    # Verify JSON array in user prompt
    user_content = msgs[1]["content"]
    start = user_content.find("[{")
    end = user_content.rfind("}]") + 2
    parsed = json.loads(user_content[start:end])
    test("Candidates JSON parseable", len(parsed) == len(candidates))
except Exception as e:
    print(f"  ERROR: {e}")
    traceback.print_exc()
    failed += 1

print("\n=== ResponseParser ===")
try:
    # Valid JSON
    raw = json.dumps({"summary": "Great!", "recommendations": [
        {"id": "1", "rank": 1, "explanation": "Best"},
        {"id": "2", "rank": 2, "explanation": "Good"},
    ]})
    summary, rankings = ResponseParser.parse(raw)
    test("Valid JSON summary", summary == "Great!")
    test("Valid JSON rankings count", len(rankings) == 2)
    test("Rankings sorted", rankings[0].rank == 1 and rankings[1].rank == 2)

    # Code block wrapping
    raw2 = '```json\n{"summary":"Test","recommendations":[{"id":"1","rank":1,"explanation":"OK"}]}\n```'
    s2, r2 = ResponseParser.parse(raw2)
    test("Code block parsing", s2 == "Test" and len(r2) == 1)

    # Invalid JSON
    try:
        ResponseParser.parse("not json")
        test("Invalid JSON raises", False)
    except ValueError:
        test("Invalid JSON raises", True)

    # Missing recommendations
    try:
        ResponseParser.parse(json.dumps({"summary": "no recs"}))
        test("Missing recs raises", False)
    except ValueError:
        test("Missing recs raises", True)

    # Extra fields ignored
    raw3 = json.dumps({"summary": "X", "recommendations": [{"id": "1", "rank": 1, "explanation": "OK", "extra": True}], "extra_top": 1})
    s3, r3 = ResponseParser.parse(raw3)
    test("Extra fields ignored", len(r3) == 1)

    # Missing ID skipped
    raw4 = json.dumps({"summary": "X", "recommendations": [{"rank": 1, "explanation": "no id"}, {"id": "2", "rank": 2, "explanation": "ok"}]})
    _, r4 = ResponseParser.parse(raw4)
    test("Missing ID skipped", len(r4) == 1 and r4[0].id == "2")

    # Non-dict top-level
    try:
        ResponseParser.parse("[1, 2, 3]")
        test("Non-dict raises", False)
    except ValueError:
        test("Non-dict raises", True)
except Exception as e:
    print(f"  ERROR: {e}")
    traceback.print_exc()
    failed += 1

print("\n=== RecommendationEnricher ===")
try:
    enricher = RecommendationEnricher()
    rankings = [LLMRanking(id="1", rank=1, explanation="Best"), LLMRanking(id="2", rank=2, explanation="Good")]
    recs = enricher.enrich(rankings, RESTAURANTS)
    test("Enrich count", len(recs) == 2)
    test("Enrich name", recs[0].name == "Tandoori Nights")
    test("Enrich rank", recs[0].rank == 1)
    test("Enrich cuisine", recs[0].cuisine == "North Indian, Mughlai")
    test("Enrich cost", recs[0].estimated_cost == 800)

    # Unknown ID skipped
    rankings2 = [LLMRanking(id="999", rank=1, explanation="?"), LLMRanking(id="1", rank=2, explanation="ok")]
    recs2 = enricher.enrich(rankings2, RESTAURANTS)
    test("Unknown ID skipped", len(recs2) == 1)

    # Heuristic fallback
    recs3 = enricher.heuristic_enrich(RESTAURANTS, top_k=2)
    test("Heuristic count", len(recs3) == 2)
    test("Heuristic explanation", "AI explanation unavailable" in recs3[0].explanation)
except Exception as e:
    print(f"  ERROR: {e}")
    traceback.print_exc()
    failed += 1

print("\n=== LLMClient (no API key fallback) ===")
try:
    client = LLMClient(api_key="", model="test")
    resp = client.complete([{"role": "user", "content": "test"}])
    test("Fallback is_fallback", resp.is_fallback)
    test("Fallback model", resp.model == "heuristic-fallback")
    test("Fallback empty rankings", len(resp.rankings) == 0)
except Exception as e:
    print(f"  ERROR: {e}")
    traceback.print_exc()
    failed += 1

print("\n=== RecommendationService (mocked LLM) ===")
try:
    repo = FakeRepository(RESTAURANTS)

    # Full pipeline with LLM response
    llm_resp = LLMResponse(
        summary="Top picks!", rankings=[
            LLMRanking(id="1", rank=1, explanation="Perfect match"),
            LLMRanking(id="6", rank=2, explanation="Great Italian"),
            LLMRanking(id="2", rank=3, explanation="Solid choice"),
        ], model="test-model", latency_ms=100,
    )
    fake_llm = FakeLLMClient(llm_resp)
    service = RecommendationService(repository=repo, llm_client=fake_llm, top_k=3)
    prefs = UserPreferences(location="Banashankari", budget="medium", min_rating=0.0)
    result = service.recommend(prefs)
    test("Pipeline summary", result.summary == "Top picks!")
    test("Pipeline recs count", len(result.recommendations) == 3)
    test("Pipeline first rec", result.recommendations[0].name == "Tandoori Nights")
    test("Pipeline metadata model", result.metadata.model == "test-model")
    test("Pipeline candidates > 0", result.metadata.candidates_considered > 0)
    test("LLM received 2 msgs", fake_llm.last_messages is not None and len(fake_llm.last_messages) == 2)

    # Fallback path
    fallback_resp = LLMResponse(summary="Fallback", rankings=[], model="heuristic-fallback", is_fallback=True)
    fake_llm2 = FakeLLMClient(fallback_resp)
    service2 = RecommendationService(repository=repo, llm_client=fake_llm2, top_k=2)
    result2 = service2.recommend(prefs)
    test("Fallback has recs", len(result2.recommendations) > 0)
    test("Fallback explanation", "AI explanation unavailable" in result2.recommendations[0].explanation)

    # No candidates (unknown location — rejected by validator)
    try:
        prefs_bad_loc = UserPreferences(location="NonExistentCity", budget="low", min_rating=0.0)
        service.recommend(prefs_bad_loc)
        test("Unknown location raises ValueError", False)
    except ValueError:
        test("Unknown location raises ValueError", True)

    # Invalid prefs raises
    try:
        service.recommend(UserPreferences(location="", budget="luxury"))
        test("Invalid prefs raises", False)
    except ValueError:
        test("Invalid prefs raises", True)

    # Metadata includes filters
    result4 = service.recommend(UserPreferences(location="Banashankari", budget="medium", cuisine="North Indian", min_rating=4.0))
    test("Metadata has filters", "location" in result4.metadata.filters_applied)

    # Unknown IDs handled gracefully
    llm_resp2 = LLMResponse(summary="Test", rankings=[
        LLMRanking(id="999", rank=1, explanation="Unknown"),
        LLMRanking(id="1", rank=2, explanation="Known"),
    ], model="test-model")
    fake_llm3 = FakeLLMClient(llm_resp2)
    service3 = RecommendationService(repository=repo, llm_client=fake_llm3, top_k=3)
    result5 = service3.recommend(prefs)
    names = [r.name for r in result5.recommendations]
    test("Unknown ID skipped in pipeline", "Tandoori Nights" in names)

    # Empty rankings triggers heuristic
    empty_resp = LLMResponse(summary="I couldn't decide", rankings=[], model="test-model", is_fallback=False)
    fake_llm4 = FakeLLMClient(empty_resp)
    service4 = RecommendationService(repository=repo, llm_client=fake_llm4, top_k=2)
    result6 = service4.recommend(prefs)
    test("Empty rankings -> heuristic", len(result6.recommendations) > 0 and "AI explanation unavailable" in result6.recommendations[0].explanation)

except Exception as e:
    print(f"  ERROR: {e}")
    traceback.print_exc()
    failed += 1

# ── Summary ─────────────────────────────────────────────────────────────────

print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed")
print(f"{'='*50}")
sys.exit(1 if failed else 0)
