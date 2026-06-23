"""FastAPI route definitions for the recommendation API.

Endpoints:
  POST /api/v1/recommend  — Get AI-powered restaurant recommendations
  GET  /api/v1/health     — Service health check
  GET  /api/v1/locations   — List available locations
  GET  /api/v1/cuisines    — List available cuisines
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from src.api.schemas import (
    CuisinesResponse,
    ErrorResponse,
    HealthResponse,
    LocationsResponse,
    RecommendationItem,
    RecommendationMetadataOut,
    RecommendRequest,
    RecommendResponse,
)
from src.data.repository import RestaurantRepository
from src.models.preferences import UserPreferences
from src.services.recommendation import RecommendationService

logger = logging.getLogger(__name__)

# ── Router ──────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/v1", tags=["recommendations"])

# Module-level reference set by the app factory (lifespan)
_repository: RestaurantRepository | None = None
_service: RecommendationService | None = None


def init_services(repository: RestaurantRepository) -> None:
    """Initialize the shared repository and recommendation service.

    Called once during app startup (lifespan event).
    """
    global _repository, _service  # noqa: PLW0603
    _repository = repository
    _service = RecommendationService(repository)
    logger.info("API services initialized.")


def _get_repo() -> RestaurantRepository:
    if _repository is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready — dataset not loaded yet.",
        )
    return _repository


def _get_service() -> RecommendationService:
    if _service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready — dataset not loaded yet.",
        )
    return _service


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
)
async def health() -> HealthResponse:
    """Returns service status and whether the dataset has been loaded."""
    loaded = _repository is not None and _repository.is_loaded
    return HealthResponse(status="ok", dataset_loaded=loaded)


@router.get(
    "/locations",
    response_model=LocationsResponse,
    summary="List available locations",
)
async def list_locations() -> LocationsResponse:
    """Returns distinct locations from the dataset, sorted alphabetically."""
    repo = _get_repo()
    locations = repo.get_locations()
    return LocationsResponse(locations=locations, count=len(locations))


@router.get(
    "/cuisines",
    response_model=CuisinesResponse,
    summary="List available cuisines",
)
async def list_cuisines() -> CuisinesResponse:
    """Returns distinct cuisines from the dataset, sorted alphabetically."""
    repo = _get_repo()
    cuisines = repo.get_cuisines()
    return CuisinesResponse(cuisines=cuisines, count=len(cuisines))


@router.post(
    "/recommend",
    response_model=RecommendResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid preferences"},
        502: {"model": RecommendResponse, "description": "Groq failure — fallback results"},
        503: {"description": "Service not ready"},
    },
    summary="Get AI-powered restaurant recommendations",
)
async def recommend(request: RecommendRequest) -> RecommendResponse:
    """Accept user preferences, run the recommendation pipeline, and return ranked results.

    On validation errors returns 400 with suggestions.
    On Groq failure returns 200 with heuristic fallback results.
    """
    service = _get_service()

    # Build internal UserPreferences from API request
    preferences = UserPreferences(
        location=request.location,
        budget=request.budget,
        cuisine=request.cuisine,
        min_rating=request.min_rating,
        additional=request.additional,
    )

    try:
        response = service.recommend(preferences)
    except ValueError as exc:
        # Validation errors from the service layer
        logger.warning("Validation error: %s", exc)

        # Try to extract suggestions from the validator
        suggestions: dict[str, list[str]] = {}
        try:
            from src.services.validator import PreferenceValidator
            validator = PreferenceValidator(_get_repo())
            result = validator.validate(
                location=request.location,
                budget=request.budget,
                cuisine=request.cuisine,
                min_rating=request.min_rating,
            )
            suggestions = result.suggestions
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
            headers={"X-Suggestions": str(suggestions)} if suggestions else None,
        )
    except Exception as exc:
        logger.exception("Unexpected error during recommendation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Recommendation pipeline failed: {exc}",
        )

    # Map internal dataclass response → Pydantic response model
    return RecommendResponse(
        summary=response.summary,
        recommendations=[
            RecommendationItem(
                rank=r.rank,
                name=r.name,
                cuisine=r.cuisine,
                rating=r.rating,
                estimated_cost=r.estimated_cost,
                explanation=r.explanation,
            )
            for r in response.recommendations
        ],
        metadata=RecommendationMetadataOut(
            candidates_considered=response.metadata.candidates_considered,
            filters_applied=response.metadata.filters_applied,
            model=response.metadata.model,
        ),
    )
