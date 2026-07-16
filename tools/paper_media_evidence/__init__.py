"""Evidence manifest contracts for paper-media pipeline runs.

The completion derivation has no third-party dependencies and is also used by
small experiment inventories.  Keep the heavier schema/projection imports lazy
so those inventories do not need the publication toolchain just to derive a
completion state.
"""

from .completion import derive_completion

__all__ = [
    "ManifestValidationError",
    "derive_completion",
    "migrate_legacy_baseline",
    "project_public_manifest",
    "validate_canonical",
    "validate_public",
]


def __getattr__(name: str):
    if name == "migrate_legacy_baseline":
        from .migration import migrate_legacy_baseline

        return migrate_legacy_baseline
    if name == "project_public_manifest":
        from .projection import project_public_manifest

        return project_public_manifest
    if name in {"ManifestValidationError", "validate_canonical", "validate_public"}:
        from .validation import ManifestValidationError, validate_canonical, validate_public

        return {
            "ManifestValidationError": ManifestValidationError,
            "validate_canonical": validate_canonical,
            "validate_public": validate_public,
        }[name]
    raise AttributeError(name)
