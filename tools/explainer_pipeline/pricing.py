from __future__ import annotations

from typing import Any, Optional


RATE_CARDS = (
    {
        "rate_card_id": "aws-bedrock-gpt-5.5-us-east-2026-07-22",
        "model_contains": "gpt-5.5",
        "provider": "bedrock_mantle",
        "input_per_million_usd": 5.50,
        "output_per_million_usd": 33.00,
        "source_url": "https://aws.amazon.com/bedrock/pricing/",
        "note": "AWS in-region on-demand price for US East; output includes reasoning tokens.",
    },
    {
        "rate_card_id": "vertex-gemini-3.1-pro-standard-2026-07-22",
        "model_contains": "gemini-3.1-pro",
        "provider": "google_vertex",
        "input_per_million_usd": 2.00,
        "output_per_million_usd": 12.00,
        "source_url": "https://cloud.google.com/vertex-ai/generative-ai/pricing",
        "note": "Standard tier at or below 200K input tokens; output includes reasoning tokens.",
    },
)


def estimate_cost(provider: str, model: str, usage: Optional[dict[str, int]]) -> dict[str, Any]:
    if usage is None:
        return {"status": "not_recorded", "estimated_usd": None, "rate_card": None}
    normalized_provider = "bedrock_mantle" if provider in {"bedrock_mantle", "amazon_bedrock_mantle"} else provider
    card = next(
        (
            item
            for item in RATE_CARDS
            if item["provider"] == normalized_provider and item["model_contains"] in model.lower()
        ),
        None,
    )
    if card is None:
        return {"status": "rate_unavailable", "estimated_usd": None, "rate_card": None}
    estimated = (
        usage.get("input_tokens", 0) * card["input_per_million_usd"]
        + usage.get("output_tokens", 0) * card["output_per_million_usd"]
    ) / 1_000_000
    return {
        "status": "estimated",
        "estimated_usd": round(estimated, 6),
        "rate_card": {key: value for key, value in card.items() if key != "model_contains"},
    }
