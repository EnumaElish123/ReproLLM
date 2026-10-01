"""Transformers integration."""

from __future__ import annotations

from reprollm.core.envinfo import installed_versions
from reprollm.core.pyscan import PyScanResult, scan_python
from reprollm.core.scanner import RepoScanner
from reprollm.integrations._static import import_evidence
from reprollm.integrations.base import ProviderIntegration
from reprollm.schemas.finding import Evidence


class TransformersIntegration(ProviderIntegration):
    name = "transformers"

    def detect(self, scanner: RepoScanner, *, pyscan: PyScanResult | None = None) -> list[Evidence]:
        scanned = pyscan if pyscan is not None else scan_python(scanner)
        evidence = import_evidence(scanner, self.name, scanned)
        if scanned.trainer_import:
            hits = [info for info in scanned.imports if info.module == self.name]
            evidence.append(
                Evidence(
                    kind="detection",
                    path=hits[0].path if hits else "",
                    line=hits[0].line if hits else None,
                    note="from transformers import Trainer|Seq2SeqTrainer|TrainingArguments",
                )
            )
        return evidence

    def capture(self) -> dict[str, str]:
        return installed_versions(["transformers", "tokenizers", "accelerate"])
