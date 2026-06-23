"""Dataset loader — fetches the Zomato dataset from Hugging Face with local caching.

Supports:
  - First-load download from Hugging Face via the `datasets` library.
  - Local parquet cache to avoid repeated downloads.
  - Retry with exponential backoff on network errors.
  - Force-refresh via a flag.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd
from datasets import load_dataset

from src.config import settings

logger = logging.getLogger(__name__)

# Default split to load from the HF dataset
_DEFAULT_SPLIT = "train"


class DatasetLoader:
    """Loads the Zomato restaurant dataset, with local caching and retry logic.

    Usage::

        loader = DatasetLoader()
        df = loader.load()               # pandas DataFrame
        df = loader.load(force=True)     # re-download even if cache exists
    """

    def __init__(
        self,
        dataset_name: str | None = None,
        cache_path: Path | None = None,
        split: str = _DEFAULT_SPLIT,
        max_retries: int = 3,
    ) -> None:
        self._dataset_name = dataset_name or settings.HF_DATASET_NAME
        self._cache_path = cache_path or settings.DATA_CACHE_PATH
        self._split = split
        self._max_retries = max_retries
        self._cache_file = self._cache_path / f"{self._split}.parquet"

    # ── Public API ─────────────────────────────────────────────────────────

    def load(self, *, force: bool = False) -> pd.DataFrame:
        """Load the dataset as a pandas DataFrame.

        Args:
            force: If True, ignore the local cache and re-download.

        Returns:
            A pandas DataFrame with the raw dataset rows.

        Raises:
            RuntimeError: If the dataset cannot be loaded after retries.
        """
        if not force and self._cache_exists():
            logger.info("Loading dataset from local cache: %s", self._cache_file)
            return self._load_from_cache()

        logger.info("Downloading dataset '%s' (split=%s) from Hugging Face …", self._dataset_name, self._split)
        df = self._download_with_retry()

        # Persist to cache
        self._save_to_cache(df)

        return df

    # ── Cache helpers ──────────────────────────────────────────────────────

    def _cache_exists(self) -> bool:
        return self._cache_file.exists() and self._cache_file.stat().st_size > 0

    def _load_from_cache(self) -> pd.DataFrame:
        try:
            return pd.read_parquet(self._cache_file)
        except Exception as exc:
            logger.warning("Corrupted cache file %s — removing and re-downloading: %s", self._cache_file, exc)
            self._cache_file.unlink(missing_ok=True)
            return self._download_with_retry()

    def _save_to_cache(self, df: pd.DataFrame) -> None:
        try:
            self._cache_path.mkdir(parents=True, exist_ok=True)
            df.to_parquet(self._cache_file, index=False)
            logger.info("Dataset cached to %s (%d rows)", self._cache_file, len(df))
        except Exception as exc:
            logger.warning("Failed to cache dataset: %s. Continuing in-memory only.", exc)

    # ── Download with retry ───────────────────────────────────────────────

    def _download_with_retry(self) -> pd.DataFrame:
        last_exc: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                ds = load_dataset(self._dataset_name, split=self._split)
                df = ds.to_pandas()
                logger.info("Downloaded dataset: %d rows, %d columns", len(df), len(df.columns))
                return df
            except Exception as exc:
                last_exc = exc
                wait = 2**attempt  # 2s, 4s, 8s
                logger.error(
                    "Download attempt %d/%d failed: %s — retrying in %ds …",
                    attempt,
                    self._max_retries,
                    exc,
                    wait,
                )
                time.sleep(wait)

        raise RuntimeError(
            f"Failed to load dataset '{self._dataset_name}' after {self._max_retries} retries. "
            f"Last error: {last_exc}"
        )
