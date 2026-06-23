"""Pydantic request / response schemas for the REST API.

These models serve as the API contract and are decoupled from the internal
dataclass models used in the pipeline.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Request schemas ─────────────────────────────────────────────────────────


class RecommendRequest(BaseModel):
    """POST /api/v1/recommend request body."""

    location: str = Field(
        ...,
        min_length=1,
        description="City or locality name (required).",
        json_schema_extra={"examples": ["Bangalore"]},
    )
    budget: str = Field(
        ...,
        pattern=r"^(low|medium|high)$",
        description="Budget tier — one of 'low', 'medium', 'high'.",
        json_schema_extra={"examples": ["medium"]},
    )
    cuisine: str | None = Field(
        default=None,
        description="Optional cuisine preference (e.g. 'Italian').",
        json_schema_extra={"examples": ["Italian"]},
    )
    min_rating: float = Field(
        default=0.0,
        ge=0.0,
        le=5.0,
        description="Minimum acceptable rating (0.0–5.0).",
    )
    additional: str | None = Field(
        default=None,
        description="Optional free-text preferences (e.g. 'family-friendly').",
    )


# ── Response schemas ────────────────────────────────────────────────────────


class RecommendationItem(BaseModel):
    """A single ranked restaurant recommendation."""

    rank: int
    name: str
    cuisine: str
    rating: float
    estimated_cost: int
    explanation: str


class RecommendationMetadataOut(BaseModel):
    """Metadata about the recommendation pipeline run."""

    candidates_considered: int = 0
    filters_applied: dict = Field(default_factory=dict)
    model: str = ""


class RecommendResponse(BaseModel):
    """POST /api/v1/recommend response body."""

    summary: str | None = None
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    metadata: RecommendationMetadataOut = Field(
        default_factory=RecommendationMetadataOut,
    )


class HealthResponse(BaseModel):
    """GET /api/v1/health response body."""

    status: str = "ok"
    dataset_loaded: bool = False


class LocationsResponse(BaseModel):
    """GET /api/v1/locations response body."""

    locations: list[str] = Field(default_factory=list)
    count: int = 0


class CuisinesResponse(BaseModel):
    """GET /api/v1/cuisines response body."""

    cuisines: list[str] = Field(default_factory=list)
    count: int = 0


class ErrorResponse(BaseModel):
    """Standard error response body."""

    detail: str
    suggestions: dict[str, list[str]] = Field(default_factory=dict)
