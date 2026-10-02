"""Metadata-only model API classification (spec §§4.3, 12.4)."""

from __future__ import annotations

import getpass
import socket
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

from reprollm.run.privacy import RunPrivacy

_API_PROVIDERS = frozenset({"openai", "openrouter", "anthropic"})


def is_api_model(provider: object, endpoint: object, root: Path) -> bool:
    """Accept an opaque API declaration only when its original endpoint is safe."""
    if not isinstance(provider, str):
        return False
    if provider in _API_PROVIDERS:
        return True
    if provider != "other" or not isinstance(endpoint, str) or not endpoint:
        return False
    # urlsplit strips some controls; reject them before parsing can change identity.
    if any(
        character.isspace() or unicodedata.category(character) in {"Cc", "Cf", "Zl", "Zp"}
        for character in endpoint
    ):
        return False
    if "#" in endpoint or "\\" in endpoint:
        return False
    try:
        parsed = urlsplit(endpoint)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            return False
        # Accessing port validates malformed and out-of-range authorities too.
        _ = parsed.port
    except ValueError:
        return False
    privacy = RunPrivacy(root, hostname=socket.gethostname(), username=getpass.getuser())
    return privacy.text(endpoint)[1] == 0
