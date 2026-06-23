"""Groq LLM client with retry logic, response parsing, and heuristic fallback.

Wraps the ``groq`` SDK chat completions API. Handles:
  - Invalid JSON retries (lower temperature)
  - 429 rate-limit retries (exponential backoff)
  - Heuristic fallback when Groq is unavailable
  - Per-request metadata logging (model, latency, tokens)
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from src.config import settings

logger = logging.getLogger(__name__)

# ── Response data models ────────────────────────────────────────────────────

@dataclass
class LLMRanking:
    """Parsed ranking from the LLM response.

    Attributes:
        id: Restaurant ID from the candidate list.
        rank: Assigned rank (1-based).
        explanation: LLM-generated reason for this pick.
    """

    id: str
    rank: int
    explanation: str


@dataclass
class LLMResponse:
    """Structured response from the LLM call.

    Attributes:
        summary: Overview text from the LLM.
        rankings: Ordered list of ranked restaurant picks.
        model: Model ID that produced the response.
        latency_ms: Round-trip latency in milliseconds.
        prompt_tokens: Tokens used by the prompt.
        completion_tokens: Tokens used by the completion.
        is_fallback: True if heuristic fallback was used instead of LLM.
    """

    summary: str | None = None
    rankings: list[LLMRanking] = field(default_factory=list)
    model: str = ""
    latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    is_fallback: bool = False


# ── Response Parser ─────────────────────────────────────────────────────────

class ResponseParser:
    """Parses and validates Groq JSON output into structured rankings.

    Expected schema::

        {
          "summary": str,
          "recommendations": [
            {"id": str, "rank": int, "explanation": str}
          ]
        }
    """

    @staticmethod
    def parse(raw_text: str) -> tuple[str | None, list[LLMRanking]]:
        """Parse Groq output text into summary + rankings.

        Args:
            raw_text: Raw text from Groq completion.

        Returns:
            Tuple of (summary, rankings).

        Raises:
            ValueError: If JSON is malformed or schema is invalid.
        """
        # Try to extract JSON from the response
        text = raw_text.strip()

        # Handle cases where the model wraps JSON in markdown code blocks
        if text.startswith("```"):
            # Remove ```json ... ``` wrapping
            lines = text.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.strip().startswith("```") and not in_block:
                    in_block = True
                    continue
                elif line.strip() == "```" and in_block:
                    break
                elif in_block:
                    json_lines.append(line)
            text = "\n".join(json_lines)

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse JSON from LLM response: {exc}") from exc

        # Validate schema
        if not isinstance(data, dict):
            raise ValueError(f"Expected JSON object, got {type(data).__name__}")

        summary = data.get("summary")
        recs = data.get("recommendations")

        if not isinstance(recs, list):
            raise ValueError(
                "Missing or invalid 'recommendations' field — expected a list."
            )

        rankings: list[LLMRanking] = []
        for item in recs:
            if not isinstance(item, dict):
                continue
            rec_id = str(item.get("id", ""))
            rank = item.get("rank", 0)
            explanation = item.get("explanation", "")

            if not rec_id:
                continue  # skip entries without ID

            try:
                rank = int(rank)
            except (TypeError, ValueError):
                rank = 0

            rankings.append(LLMRanking(
                id=rec_id,
                rank=rank,
                explanation=str(explanation),
            ))

        # Sort by rank
        rankings.sort(key=lambda r: r.rank)

        return summary, rankings


# ── LLM Client ──────────────────────────────────────────────────────────────

class LLMClient:
    """Groq API client with retry logic and heuristic fallback.

    Usage::

        client = LLMClient()
        response = client.complete(messages)
    """

    # Retry configuration
    MAX_JSON_RETRIES = 1
    MAX_RATE_LIMIT_RETRIES = 3
    RETRY_TEMPERATURE = 0.1
    BACKOFF_BASE_SECONDS = 1.0

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
    ) -> None:
        self._api_key = api_key or settings.GROQ_API_KEY
        self._model = model or settings.GROQ_MODEL
        self._temperature = temperature if temperature is not None else settings.GROQ_TEMPERATURE
        self._parser = ResponseParser()
        self._client = None  # lazy init

    def _get_client(self) -> Any:
        """Lazily initialize the Groq client."""
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self._api_key)
            except ImportError:
                raise ImportError(
                    "The 'groq' package is required. Install it with: pip install groq"
                )
            except Exception as exc:
                logger.error("Failed to initialize Groq client: %s", exc)
                raise
        return self._client

    def complete(self, messages: list[dict[str, str]]) -> LLMResponse:
        """Send messages to Groq and return a parsed LLMResponse.

        Handles retries for invalid JSON and rate-limiting. Falls back
        to a heuristic response if all retries are exhausted.

        Args:
            messages: List of message dicts with 'role' and 'content'.

        Returns:
            LLMResponse with parsed rankings, or a fallback response.
        """
        if not self._api_key:
            logger.warning("No GROQ_API_KEY set — using heuristic fallback.")
            return self._heuristic_fallback()

        # Try primary model
        response = self._try_completion(messages, self._model, self._temperature)
        if response is not None:
            return response

        # Try fallback model if primary failed
        fallback_model = settings.GROQ_FALLBACK_MODEL
        if fallback_model != self._model:
            logger.info("Trying fallback model: %s", fallback_model)
            response = self._try_completion(messages, fallback_model, self._temperature)
            if response is not None:
                return response

        logger.warning("All Groq attempts failed — using heuristic fallback.")
        return self._heuristic_fallback()

    def _try_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
    ) -> LLMResponse | None:
        """Attempt a completion with retry logic.

        Returns:
            LLMResponse on success, None if all retries exhausted.
        """
        client = self._get_client()
        last_error = None

        for attempt in range(1 + self.MAX_JSON_RETRIES):
            temp = temperature if attempt == 0 else self.RETRY_TEMPERATURE

            try:
                raw_response = self._call_groq(client, messages, model, temp)
            except RateLimitError:
                # Handle rate limiting with exponential backoff
                if not self._handle_rate_limit(client, messages, model, temp):
                    return None
                continue
            except GroqAPIError as exc:
                logger.error("Groq API error (attempt %d): %s", attempt + 1, exc)
                last_error = exc
                continue
            except Exception as exc:
                logger.error("Unexpected error calling Groq (attempt %d): %s", attempt + 1, exc)
                last_error = exc
                continue

            # Try to parse the response
            try:
                raw_text = raw_response["text"]
                summary, rankings = self._parser.parse(raw_text)
                return LLMResponse(
                    summary=summary,
                    rankings=rankings,
                    model=raw_response.get("model", model),
                    latency_ms=raw_response.get("latency_ms", 0),
                    prompt_tokens=raw_response.get("prompt_tokens", 0),
                    completion_tokens=raw_response.get("completion_tokens", 0),
                )
            except ValueError as exc:
                logger.warning(
                    "JSON parse failed (attempt %d): %s — retrying with lower temperature",
                    attempt + 1, exc,
                )
                last_error = exc
                continue

        if last_error:
            logger.error("All attempts exhausted. Last error: %s", last_error)
        return None

    def _call_groq(
        self,
        client: Any,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
    ) -> dict[str, Any]:
        """Make the actual Groq API call and return raw response data.

        Returns:
            Dict with keys: text, model, latency_ms, prompt_tokens, completion_tokens.

        Raises:
            RateLimitError: On 429 status.
            GroqAPIError: On other API errors.
        """
        start = time.monotonic()
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            # Detect rate-limit errors
            exc_str = str(exc).lower()
            if "429" in exc_str or "rate" in exc_str:
                raise RateLimitError(str(exc)) from exc
            raise GroqAPIError(str(exc)) from exc

        latency_ms = int((time.monotonic() - start) * 1000)

        text = completion.choices[0].message.content if completion.choices else ""
        usage = getattr(completion, "usage", None)

        result = {
            "text": text or "",
            "model": getattr(completion, "model", model),
            "latency_ms": latency_ms,
            "prompt_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
            "completion_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
        }

        logger.info(
            "Groq call: model=%s, latency=%dms, prompt_tokens=%d, completion_tokens=%d",
            result["model"], result["latency_ms"],
            result["prompt_tokens"], result["completion_tokens"],
        )

        return result

    def _handle_rate_limit(
        self,
        client: Any,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
    ) -> bool:
        """Retry with exponential backoff on rate-limit errors.

        Returns:
            True if a successful response was obtained (stored in self._last_response).
        """
        for retry in range(self.MAX_RATE_LIMIT_RETRIES):
            wait = self.BACKOFF_BASE_SECONDS * (2 ** retry)
            logger.warning(
                "Rate limited — backing off %.1fs (retry %d/%d)",
                wait, retry + 1, self.MAX_RATE_LIMIT_RETRIES,
            )
            time.sleep(wait)

            try:
                self._call_groq(client, messages, model, temperature)
                return True
            except RateLimitError:
                continue
            except Exception as exc:
                logger.error("Error during rate-limit retry: %s", exc)
                return False

        logger.error("Rate-limit retries exhausted.")
        return False

    @staticmethod
    def _heuristic_fallback() -> LLMResponse:
        """Return a minimal fallback response when Groq is unavailable."""
        return LLMResponse(
            summary="Ranked by rating — AI explanation unavailable.",
            rankings=[],
            model="heuristic-fallback",
            is_fallback=True,
        )


# ── Custom exceptions ──────────────────────────────────────────────────────

class RateLimitError(Exception):
    """Raised when Groq returns a 429 rate-limit error."""


class GroqAPIError(Exception):
    """Raised on non-rate-limit Groq API errors."""
