"""Application configuration loaded from environment variables / .env file.

Uses pydantic-settings for typed, validated configuration with dotenv support.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the restaurant recommendation system.

    All values can be overridden via environment variables or a `.env` file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Groq API ──────────────────────────────────────────────────────────
    GROQ_API_KEY: str = Field(
        default="",
        description="Groq API key (required for LLM features).",
    )
    GROQ_MODEL: str = Field(
        default="llama-3.3-70b-versatile",
        description="Primary Groq model for ranking & explanations.",
    )
    GROQ_FALLBACK_MODEL: str = Field(
        default="llama-3.1-8b-instant",
        description="Fallback Groq model used when primary is unavailable.",
    )
    GROQ_TEMPERATURE: float = Field(
        default=0.3,
        description="Sampling temperature for Groq completions.",
    )

    # ── Dataset ────────────────────────────────────────────────────────────
    HF_DATASET_NAME: str = Field(
        default="ManikaSaini/zomato-restaurant-recommendation",
        description="Hugging Face dataset identifier.",
    )

    # ── Recommendation Pipeline ───────────────────────────────────────────
    MAX_CANDIDATES_FOR_LLM: int = Field(
        default=20,
        description="Maximum number of candidate restaurants sent to Groq.",
    )
    TOP_K_RECOMMENDATIONS: int = Field(
        default=5,
        description="Number of top recommendations to return.",
    )

    # ── Cache ──────────────────────────────────────────────────────────────
    DATA_CACHE_PATH: Path = Field(
        default=Path("./data"),
        description="Directory for locally cached dataset files.",
    )

    # ── Budget Thresholds (INR) ───────────────────────────────────────────
    BUDGET_THRESHOLDS: Dict[str, Tuple[int, float]] = Field(
        default={
            "low": (0, 500),
            "medium": (501, 1500),
            "high": (1501, float("inf")),
        },
        description="Budget tier boundaries derived from cost_for_two.",
    )

    # ── Validators ────────────────────────────────────────────────────────

    @field_validator("GROQ_TEMPERATURE")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if not 0.0 <= v <= 2.0:
            raise ValueError("GROQ_TEMPERATURE must be between 0.0 and 2.0")
        return v

    @field_validator("MAX_CANDIDATES_FOR_LLM")
    @classmethod
    def validate_max_candidates(cls, v: int) -> int:
        if v < 1:
            raise ValueError("MAX_CANDIDATES_FOR_LLM must be at least 1")
        return v

    @field_validator("TOP_K_RECOMMENDATIONS")
    @classmethod
    def validate_top_k(cls, v: int) -> int:
        if v < 1:
            raise ValueError("TOP_K_RECOMMENDATIONS must be at least 1")
        return v


# Singleton instance — imported by other modules as `from src.config import settings`
settings = Settings()
