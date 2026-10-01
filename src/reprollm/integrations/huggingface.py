"""Hugging Face Hub integration over the HTTP API; never imports the library."""

from __future__ import annotations

import httpx

from reprollm.core.pyscan import PyScanResult, scan_python
from reprollm.core.scanner import RepoScanner
from reprollm.integrations._static import import_evidence
from reprollm.integrations.base import LockFragment, ProviderIntegration
from reprollm.integrations.peft import PeftIntegration
from reprollm.lock.hf_client import HfClient
from reprollm.lock.hf_resolver import resolve_hf_dataset, resolve_hf_model
from reprollm.schemas.finding import Evidence
from reprollm.schemas.lock import DatasetLock, ModelLock
from reprollm.schemas.manifest import Manifest


class HuggingFaceIntegration(ProviderIntegration):
    name = "huggingface"

    def detect(self, scanner: RepoScanner, *, pyscan: PyScanResult | None = None) -> list[Evidence]:
        scanned = pyscan if pyscan is not None else scan_python(scanner)
        evidence = import_evidence(scanner, "datasets", scanned)
        evidence.extend(
            Evidence(
                kind="detection",
                path=hint.path,
                line=hint.line,
                note="HF repository id",
                value=hint.value,
            )
            for hint in scanned.hf_ids
        )
        return evidence

    def resolve(
        self, manifest: Manifest, *, offline: bool, http: httpx.Client | None
    ) -> LockFragment:
        assert offline or http is not None
        client = HfClient(http, token=None) if http is not None and not offline else None
        peft = PeftIntegration(self.root, now=self.now, client=client)
        models: dict[str, ModelLock] = {}
        for role, spec in sorted(manifest.models.items()):
            if spec.provider != "huggingface":
                continue
            # PEFT owns the adapter resolution; preserve the old helper's
            # standalone behavior without issuing a second adapter request.
            model = resolve_hf_model(
                self.root,
                spec.model_copy(update={"adapter": None}),
                client=client,
                offline=offline,
                now=self.now,
            )
            if spec.adapter is not None:
                adapter_manifest = manifest.model_copy(update={"models": {role: spec}})
                adapters = peft.resolve(adapter_manifest, offline=offline, http=http)
                model.adapter = adapters.adapters[role]
            models[role] = model
        datasets: dict[str, DatasetLock] = {}
        for role, dataset_spec in sorted(manifest.datasets.items()):
            if dataset_spec.provider == "huggingface":
                datasets[role] = resolve_hf_dataset(
                    dataset_spec, client=client, offline=offline, now=self.now
                )
        return LockFragment(models=models, datasets=datasets)
