"""vLLM integration."""

from __future__ import annotations

import httpx

from reprollm.core.envinfo import installed_versions
from reprollm.core.pyscan import PyScanResult, scan_python
from reprollm.core.scanner import RepoScanner
from reprollm.integrations._resolution import resolve_inference
from reprollm.integrations._static import import_evidence
from reprollm.integrations.base import LockFragment, ProviderIntegration
from reprollm.schemas.finding import Evidence
from reprollm.schemas.manifest import Manifest


class VllmIntegration(ProviderIntegration):
    name = "vllm"

    def detect(self, scanner: RepoScanner, *, pyscan: PyScanResult | None = None) -> list[Evidence]:
        scanned = pyscan if pyscan is not None else scan_python(scanner)
        return import_evidence(scanner, "vllm", scanned) + import_evidence(
            scanner, "sglang", scanned
        )

    def capture(self) -> dict[str, str]:
        return installed_versions([self.name])

    def resolve(
        self, manifest: Manifest, *, offline: bool, http: httpx.Client | None
    ) -> LockFragment:
        inference = (
            resolve_inference(manifest, self.now)
            if manifest.inference is not None and manifest.inference.backend == self.name
            else None
        )
        return LockFragment(inference=inference)
