"""Quick prediction script — top 5 restaurants for given preferences via Groq.

Usage:  python predict.py
"""

import json
import logging
import os
import re
import sys
from pathlib import Path

# Force UTF-8 output on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Load env file manually (no dotenv library needed for this script) ────
_ENV_PATH = Path(__file__).parent / "env"
if _ENV_PATH.exists():
    for line in _ENV_PATH.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ── User preferences ─────────────────────────────────────────────────────
LOCATION   = "Indiranagar"
MIN_RATING = 4.2
BUDGET     = 1500          # max cost_for_two in INR
TOP_K      = 5
MAX_CANDS  = 20


def main() -> None:
    from src.data.loader import DatasetLoader
    from src.data.preprocessor import DataPreprocessor
    from src.data.repository import RestaurantRepository
    from groq import Groq

    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        sys.exit("GROQ_API_KEY is not set. Add it to the 'env' file.")

    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    # ── Step 1: Load repository (uses local cache) ────────────────────────
    logger.info("Loading restaurant repository …")
    repo = RestaurantRepository()
    all_restaurants = repo.get_all()
    logger.info("Repository loaded: %d total restaurants", len(all_restaurants))

    # ── Step 2: Filter candidates ─────────────────────────────────────────
    candidates = [
        r for r in all_restaurants
        if r.location.lower() == LOCATION.lower()
        and r.rating >= MIN_RATING
        and r.cost_for_two <= BUDGET
        and r.cost_for_two > 0        # exclude missing cost entries
    ]

    # Sort by rating desc, then votes desc
    candidates.sort(key=lambda r: (-r.rating, -r.votes))

    logger.info(
        "Filtered %d candidates (location=%s, rating≥%.1f, cost≤%d)",
        len(candidates), LOCATION, MIN_RATING, BUDGET,
    )

    if not candidates:
        logger.warning("No candidates found. Relaxing min_rating to 3.5 …")
        candidates = [
            r for r in all_restaurants
            if r.location.lower() == LOCATION.lower()
            and r.rating >= 3.5
            and r.cost_for_two <= BUDGET
        ]
        candidates.sort(key=lambda r: (-r.rating, -r.votes))

    # Cap at MAX_CANDS for the prompt
    candidates = candidates[:MAX_CANDS]

    if not candidates:
        sys.exit(f"No restaurants found for {LOCATION}. Try a different location.")

    # ── Step 3: Build Groq prompt ─────────────────────────────────────────
    candidate_list = [
        {
            "id": r.id,
            "name": r.name,
            "cuisines": ", ".join(r.cuisines) if r.cuisines else "N/A",
            "rating": r.rating,
            "cost_for_two": r.cost_for_two,
            "rest_type": r.rest_type,
            "votes": r.votes,
        }
        for r in candidates
    ]

    system_prompt = (
        "You are an expert restaurant recommendation assistant for Indian cities. "
        "You will receive a list of CANDIDATE restaurants and the user's preferences. "
        "Your task is to rank the TOP 5 restaurants from the candidates ONLY — do NOT invent or suggest restaurants not in the list. "
        "Return your answer as valid JSON with exactly this structure:\n"
        "{\n"
        '  "summary": "<one sentence overview of your recommendations>",\n'
        '  "recommendations": [\n'
        '    { "id": "<restaurant id>", "rank": 1, "explanation": "<why this restaurant suits the user>" },\n'
        "    ...\n"
        "  ]\n"
        "}\n"
        "Rank by best overall fit: rating, value-for-money, cuisine variety, and popularity (votes)."
    )

    user_prompt = (
        f"User Preferences:\n"
        f"- Location: {LOCATION}\n"
        f"- Maximum budget (cost for two): ₹{BUDGET}\n"
        f"- Minimum rating: {MIN_RATING}\n\n"
        f"Candidates ({len(candidate_list)} restaurants):\n"
        f"{json.dumps(candidate_list, indent=2)}\n\n"
        f"Return the top {TOP_K} recommendations as JSON."
    )

    # ── Step 4: Call Groq ─────────────────────────────────────────────────
    logger.info("Calling Groq (%s) with %d candidates …", model, len(candidates))
    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    raw_text = response.choices[0].message.content
    logger.info(
        "Groq responded (tokens: prompt=%d, completion=%d)",
        response.usage.prompt_tokens,
        response.usage.completion_tokens,
    )

    # ── Step 5: Parse & enrich ────────────────────────────────────────────
    # Strip markdown fences if present
    clean = re.sub(r"^```[a-z]*\n?", "", raw_text.strip())
    clean = re.sub(r"```$", "", clean.strip())

    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Groq JSON: %s\nRaw:\n%s", e, raw_text)
        sys.exit(1)

    # Build id → restaurant lookup
    id_map = {r.id: r for r in candidates}

    summary = parsed.get("summary", "")
    recs = parsed.get("recommendations", [])

    # ── Step 6: Display ───────────────────────────────────────────────────
    sep = "=" * 70
    print("\n" + sep)
    print(f"  TOP {TOP_K} RESTAURANTS  -  {LOCATION}")
    print(f"  Budget <= Rs.{BUDGET} | Rating >= {MIN_RATING}")
    print(sep)

    if summary:
        print(f"\n  Summary: {summary}\n")

    for rec in recs[:TOP_K]:
        rid  = str(rec.get("id", ""))
        rank = rec.get("rank", "?")
        exp  = rec.get("explanation", "")

        rest = id_map.get(rid)
        if not rest:
            logger.warning("Groq returned unknown id=%s -- skipping", rid)
            continue

        print(f"  #{rank}  {rest.name}")
        print(f"       Cuisine   : {', '.join(rest.cuisines) if rest.cuisines else 'N/A'}")
        print(f"       Rating    : {rest.rating}  ({rest.votes:,} votes)")
        print(f"       Cost/two  : Rs.{rest.cost_for_two}")
        print(f"       Type      : {rest.rest_type}")
        print(f"       Why?      : {exp}")
        print()

    print(sep + "\n")


if __name__ == "__main__":
    main()
"""Predict top 5 restaurants using Groq LLM.

Self-contained script — uses only standard library modules.
Reads parquet via pyarrow or falls back to a pre-filtered approach.
Calls Groq API directly via urllib (no groq package needed).
"""

import json
import os
import ssl
import sys
import urllib.request
import urllib.error

# ── Configuration ───────────────────────────────────────────────────────────

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Load env file manually
env_path = os.path.join(PROJECT_ROOT, "env")
env_vars = {}
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

API_KEY = env_vars.get("GROQ_API_KEY", "")
MODEL = env_vars.get("GROQ_MODEL", "llama-3.3-70b-versatile")
TEMPERATURE = float(env_vars.get("GROQ_TEMPERATURE", "0.3"))
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "train.parquet")

# ── User inputs ─────────────────────────────────────────────────────────────

LOCATION = "Bellandur"
MIN_RATING = 4.2
BUDGET = 1500  # cost_for_two <= 1500

print(f"\n{'='*60}")
print(f"  Restaurant Recommendation — Groq LLM")
print(f"{'='*60}")
print(f"  Location:   {LOCATION}")
print(f"  Min Rating: {MIN_RATING}")
print(f"  Budget:     ≤ ₹{BUDGET} for two")
print(f"{'='*60}\n")

# ── Load and filter data ───────────────────────────────────────────────────

print("Loading dataset...")

try:
    import pandas as pd
    df = pd.read_parquet(DATA_PATH)
    print(f"  Loaded {len(df)} restaurants from parquet")

    # Inspect columns
    print(f"  Columns: {list(df.columns)}")

    # Identify the right column names (may vary by dataset)
    # Common column names in Zomato datasets
    col_map = {}
    for col in df.columns:
        col_lower = col.lower().strip()
        if "name" in col_lower and "restaurant" not in col_lower:
            col_map["name"] = col
        elif col_lower in ("name", "restaurant name", "restaurant_name"):
            col_map["name"] = col
        elif "location" in col_lower or "locality" in col_lower:
            col_map["location"] = col
        elif "cuisine" in col_lower:
            col_map["cuisines"] = col
        elif "cost" in col_lower or "average_cost" in col_lower or "approx_cost" in col_lower:
            col_map["cost"] = col
        elif col_lower in ("rate", "rating", "aggregate_rating"):
            col_map["rating"] = col
        elif "vote" in col_lower:
            col_map["votes"] = col
        elif "type" in col_lower and "rest" in col_lower:
            col_map["rest_type"] = col

    print(f"  Column mapping: {col_map}")

    # Filter
    filtered = df.copy()

    # Location filter
    if "location" in col_map:
        loc_col = col_map["location"]
        filtered = filtered[filtered[loc_col].astype(str).str.lower().str.strip() == LOCATION.lower()]
        print(f"  After location filter: {len(filtered)} restaurants")

    # Rating filter
    if "rating" in col_map:
        rat_col = col_map["rating"]
        filtered[rat_col] = pd.to_numeric(filtered[rat_col].astype(str).str.replace("/5", "").str.strip(), errors="coerce")
        filtered = filtered[filtered[rat_col] >= MIN_RATING]
        print(f"  After rating filter (>= {MIN_RATING}): {len(filtered)} restaurants")

    # Budget filter
    if "cost" in col_map:
        cost_col = col_map["cost"]
        filtered[cost_col] = pd.to_numeric(filtered[cost_col].astype(str).str.replace(",", "").str.strip(), errors="coerce")
        filtered = filtered[filtered[cost_col] <= BUDGET]
        print(f"  After budget filter (<= {BUDGET}): {len(filtered)} restaurants")

    # Sort by rating desc, votes desc
    sort_cols = []
    if "rating" in col_map:
        sort_cols.append(col_map["rating"])
    if "votes" in col_map:
        sort_cols.append(col_map["votes"])
    if sort_cols:
        filtered = filtered.sort_values(sort_cols, ascending=False)

    # Take top 20 candidates for LLM
    candidates = filtered.head(20)
    print(f"  Top candidates for LLM: {len(candidates)}")

    # Build candidate list for LLM
    candidate_list = []
    for idx, (_, row) in enumerate(candidates.iterrows(), start=1):
        entry = {"id": str(idx)}
        if "name" in col_map:
            entry["name"] = str(row[col_map["name"]])
        if "cuisines" in col_map:
            entry["cuisines"] = str(row[col_map["cuisines"]])
        if "rating" in col_map:
            entry["rating"] = float(row[col_map["rating"]]) if pd.notna(row[col_map["rating"]]) else 0.0
        if "cost" in col_map:
            entry["cost_for_two"] = int(row[col_map["cost"]]) if pd.notna(row[col_map["cost"]]) else 0
        if "votes" in col_map:
            entry["votes"] = int(row[col_map["votes"]]) if pd.notna(row[col_map["votes"]]) else 0
        if "rest_type" in col_map:
            entry["type"] = str(row[col_map["rest_type"]])
        candidate_list.append(entry)

except ImportError:
    print("  ERROR: pandas not installed. Cannot load parquet file.")
    print("  Please run: pip install pandas pyarrow")
    sys.exit(1)
except Exception as e:
    print(f"  ERROR loading data: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

if not candidate_list:
    print("\n  No restaurants match your criteria!")
    sys.exit(0)

print(f"\n  Found {len(candidate_list)} candidates. Calling Groq LLM...\n")

# ── Call Groq API ──────────────────────────────────────────────────────────

system_prompt = f"""You are an expert restaurant recommendation assistant. Your task is to rank \
a list of candidate restaurants based on user preferences and provide a short, \
helpful explanation for each pick.

## Rules
1. ONLY recommend restaurants from the provided candidate list — never fabricate names, IDs, or details.
2. Return your response as a valid JSON object with this exact schema:
{{
  "summary": "<A 1-2 sentence overview of your recommendations>",
  "recommendations": [
    {{
      "id": "<restaurant id from the candidate list>",
      "rank": <integer starting from 1>,
      "name": "<restaurant name>",
      "explanation": "<1-2 sentence reason for this pick>"
    }}
  ]
}}
3. Rank the top 5 restaurants. If fewer candidates are available, rank all of them.
4. Consider the user's preferences as primary signals: location, budget, cuisine, and minimum rating.
5. Prefer restaurants with higher ratings and more votes when other factors are equal.
6. Keep explanations concise but specific."""

user_prompt = f"""## User Preferences
- Location: {LOCATION}
- Minimum Rating: {MIN_RATING}
- Maximum Budget: ₹{BUDGET} for two

## Candidate Restaurants ({len(candidate_list)} total)
{json.dumps(candidate_list, indent=2)}

Please rank the top 5 restaurants from the list above and return your response as the specified JSON object."""

payload = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    "temperature": TEMPERATURE,
    "response_format": {"type": "json_object"},
}

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

try:
    # Create SSL context (some environments need this)
    ctx = ssl.create_default_context()

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    # Extract response
    content = result["choices"][0]["message"]["content"]
    usage = result.get("usage", {})
    model_used = result.get("model", MODEL)

    print(f"  Model: {model_used}")
    print(f"  Tokens: {usage.get('prompt_tokens', '?')} prompt, {usage.get('completion_tokens', '?')} completion\n")

    # Parse JSON response
    data = json.loads(content)

    # Display results
    print(f"{'='*60}")
    print(f"  {data.get('summary', 'Top Recommendations')}")
    print(f"{'='*60}\n")

    for rec in data.get("recommendations", []):
        rank = rec.get("rank", "?")
        name = rec.get("name", "Unknown")
        explanation = rec.get("explanation", "")
        rec_id = rec.get("id", "")

        # Find matching candidate for extra details
        match = next((c for c in candidate_list if str(c["id"]) == str(rec_id)), {})
        rating = match.get("rating", "?")
        cost = match.get("cost_for_two", "?")
        cuisines = match.get("cuisines", "?")

        print(f"  #{rank}  {name}")
        print(f"      Rating: {rating}/5  |  Cost: ₹{cost}  |  Cuisines: {cuisines}")
        print(f"      💡 {explanation}")
        print()

except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    print(f"  HTTP Error {e.code}: {body}")
    sys.exit(1)
except Exception as e:
    print(f"  ERROR calling Groq API: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
