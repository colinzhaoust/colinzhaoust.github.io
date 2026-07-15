"""Offline-first Manim backtranslation harness.

The package deliberately contains no network or provider client. Real model and
render execution must be supplied by adapters that satisfy the protocol.
"""

from .conditions import (
    AdapterCapabilities,
    ConditionTrace,
    FixtureRenderer,
    RecordingMockAdapter,
    run_one_shot,
    run_self_refined,
)
from .registry import load_registry, validate_registry, verify_source_root

__all__ = [
    "AdapterCapabilities",
    "ConditionTrace",
    "FixtureRenderer",
    "RecordingMockAdapter",
    "load_registry",
    "run_one_shot",
    "run_self_refined",
    "validate_registry",
    "verify_source_root",
]
