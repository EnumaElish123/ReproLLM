"""OpenAI and OpenRouter integration."""

from __future__ import annotations

import getpass
import socket
from datetime import datetime
from pathlib import Path

import httpx

from reprollm.core.envinfo import installed_versions
from reprollm.core.paths import resolve_project_file
from reprollm.core.pyscan import PyScanResult, scan_python
from reprollm.core.scanner import RepoScanner
from reprollm.integrations._static import import_evidence
from reprollm.integrations.base import LockFragment, ProviderIntegration
from reprollm.lock.api_resolver import resolve_api_model
from reprollm.run.privacy import RunPrivacy
from reprollm.schemas.finding import Evidence
from reprollm.schemas.manifest import Manifest


class OpenAIIntegration(ProviderIntegration):
    name = "openai"

    def __init__(
        self, root: Path | None = None, *, now: datetime | None = None, verify_api: bool = False
    ) -> None:
        super().__init__(root, now=now)
        self.verify_api = verify_api

    def detect(self, scanner: RepoScanner, *, pyscan: PyScanResult | None = None) -> list[Evidence]:
        scanned = pyscan if pyscan is not None else scan_python(scanner)
        evidence = import_evidence(scanner, "openai", scanned) + import_evidence(
            scanner, "anthropic", scanned
        )
        privacy = RunPrivacy(
            scanner.root, hostname=socket.gethostname(), username=getpass.getuser()
        )
        evidence.extend(
            Evidence(
                kind="detection", path=endpoint.path, line=endpoint.line, note="provider openrouter"
            )
            for endpoint in scanned.endpoints
            if endpoint.provider == "openrouter"
            and resolve_project_file(scanner.root, endpoint.path) is not None
            and privacy.text(endpoint.path)[1] == 0
        )
        return evidence

    def capture(self) -> dict[str, str]:
        return installed_versions([self.name])

    def resolve(
        self, manifest: Manifest, *, offline: bool, http: httpx.Client | None
    ) -> LockFragment:
        return LockFragment(
            models={
                role: resolve_api_model(
                    spec, http=http, verify_api=self.verify_api and not offline, now=self.now
                )
                for role, spec in sorted(manifest.models.items())
                if spec.provider not in {"huggingface", "local"}
            }
        )
