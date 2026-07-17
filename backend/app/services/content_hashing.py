"""Hulpfuncties voor wijzigingsdetectie."""

import hashlib


def calculate_content_hash(content: str) -> str:
    """Bereken een SHA-256-hash van ruwe tekstinhoud."""

    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()