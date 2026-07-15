"""Shared contract constants."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas" / "paper-media"

CANONICAL_SCHEMA_VERSION = "paper-media-manifest/0.1.0"
PUBLIC_SCHEMA_VERSION = "paper-media-public-manifest/0.1.0"
COMPLETION_CONTRACT_VERSION = "paper-media-completion-contract/0.1.0"
PROJECTION_POLICY_ID = "paper-media-public-projection/0.1.0"

CANONICAL_SCHEMA_PATH = SCHEMA_DIR / "canonical-manifest-0.1.0.schema.json"
PUBLIC_SCHEMA_PATH = SCHEMA_DIR / "public-manifest-0.1.0.schema.json"
COMPLETION_SCHEMA_PATH = SCHEMA_DIR / "completion-contract-0.1.0.schema.json"
PROJECTION_POLICY_PATH = SCHEMA_DIR / "public-projection-policy-0.1.0.json"
