"""Shared model cache configuration for local HuggingFace-backed models."""

import os


def configure_model_cache(cache_folder: str) -> None:
    """Route HuggingFace model cache to a stable external directory."""
    os.environ.setdefault("HF_HOME", cache_folder)
    os.environ.setdefault("HF_HUB_CACHE", os.path.join(cache_folder, "hub"))
    os.environ.setdefault("TRANSFORMERS_CACHE", os.path.join(cache_folder, "transformers"))
