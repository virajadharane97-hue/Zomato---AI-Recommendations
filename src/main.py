"""FastAPI application factory for the restaurant recommendation API.

Usage:
    uvicorn src.main:app --reload

Or run the smoke test directly:
    python -m src.main
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import init_services, router
from src.data.loader import DatasetLoader
from src.data.preprocessor import DataPreprocessor
from src.data.repository import RestaurantRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Shared repository (singleton) ───────────────────────────────────────────

_repository: RestaurantRepository | None = None


def get_repository() -> RestaurantRepository:
    """Return the shared repository instance, creating it if needed."""
    global _repository  # noqa: PLW0603
    if _repository is None:
        _repository = RestaurantRepository(
            loader=DatasetLoader(),
            preprocessor=DataPreprocessor(),
        )
    return _repository


# ── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Preload the dataset on startup and clean up on shutdown."""
    logger.info("Starting up — preloading dataset …")
    repo = get_repository()
    # Trigger lazy load so the first request doesn't wait
    repo.get_all()
    logger.info("Dataset loaded: %d restaurants", repo.count())

    # Wire the repository into the API routes
    init_services(repo)

    yield

    logger.info("Shutting down.")


# ── App factory ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="Zomato Restaurant Recommender API",
    description=(
        "AI-powered restaurant recommendation engine. "
        "Uses Groq LLM to rank and explain restaurant picks "
        "based on user preferences."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(router)


# ── Root endpoint ───────────────────────────────────────────────────────────

@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Zomato Restaurant Recommender API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


# ── CLI smoke test (backward compatible) ────────────────────────────────────

def _smoke_test() -> None:
    """Runs a quick smoke test of the data pipeline (no server)."""
    import time
    from collections import Counter

    repo = get_repository()

    start = time.perf_counter()
    all_rest = repo.get_all()
    elapsed = time.perf_counter() - start

    locations = repo.get_locations()
    cuisines = repo.get_cuisines()

    logger.info(
        "Repository: %d restaurants, %d locations, %d cuisines (loaded in %.2fs)",
        len(all_rest), len(locations), len(cuisines), elapsed,
    )
    logger.info("Sample locations: %s", locations[:10])
    logger.info("Sample cuisines: %s", cuisines[:10])

    tier_counts = Counter(r.budget_tier for r in all_rest)
    logger.info("Budget tier distribution: %s", dict(tier_counts))

    rated = [r.rating for r in all_rest if r.rating > 0]
    if rated:
        logger.info(
            "Rating stats: min=%.1f, max=%.1f, avg=%.2f (%d rated)",
            min(rated), max(rated), sum(rated) / len(rated), len(rated),
        )

    if all_rest:
        logger.info("Sample restaurant: %s", all_rest[0].to_dict())

    logger.info("Smoke test PASSED ✓")


if __name__ == "__main__":
    if "--serve" in sys.argv:
        import uvicorn
        uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
    else:
        _smoke_test()
