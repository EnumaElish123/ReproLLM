"""PEFT adapter integration."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import httpx

from reprollm.core.envinfo import installed_versions
from reprollm.core.pyscan import PyScanResult
from reprollm.core.scanner import RepoScanner
from reprollm.integrations._static import import_evidence
from reprollm.integrations.base import LockFragment, ProviderIntegration
from reprollm.lock.hf_client import HfClient
from reprollm.lock.hf_resolver import _resolve_adapter
from reprollm.schemas.finding import Evidence
from reprollm.schemas.manifest import Manifest


class PeftIntegration(ProviderIntegration):
    name = "peft"

    def __init__(
        self,
        root: Path | None = None,
        *,
        now: datetime | None = None,
        client: HfClient | None = None,
    ) -> None:
        super().__init__(root, now=now)
        self.client = client

    def detect(self, scanner: RepoScanner, *, pyscan: PyScanResult | None = None) -> list[Evidence]:
        return import_evidence(scanner, self.name, pyscan)

    def capture(self) -> dict[str, str]:
        return installed_versions([self.name])

    def resolve(
        self, manifest: Manifest, *, offline: bool, http: httpx.Client | None
    ) -> LockFragment:
        assert offline or http is not None
        client = self.client
        if client is None and not offline:
            assert http is not None
            client = HfClient(http, token=None)
        adapters = {
            role: _resolve_adapter(
                self.root, spec.adapter, client=client, offline=offline, now=self.now
            )
            for role, spec in sorted(manifest.models.items())
            if spec.provider == "huggingface" and spec.adapter is not None
        }
        return LockFragment(adapters=adapters)
