"""Shared constants for AlaskaAir Visa ...2971 duplicate-charge study."""

from __future__ import annotations

# Monarch connections that represent the same physical ...2971 card (not ...6857).
ALLOWED_ACCOUNT_IDS: frozenset[str] = frozenset(
    {
        "236286630114078574",  # primary
        "250762376149708284",
        "249213882022735355",
    }
)

# Stray institution link to exclude even if account name matches.
EXCLUDED_ACCOUNT_ID = "167850494376521428"

CARD_MARKER = "...2971)"

# Default study window (partial year + optional tail); override via CLI.
DEFAULT_START = "2025-10-21"
DEFAULT_END = "2026-03-09"

CANONICAL_FIELDS = (
    "id",
    "date",
    "amount",
    "merchant",
    "merchant_id",
    "account",
    "account_id",
    "category",
    "original_transaction_id",
)
