"""Evaluation integrations shared by profile detection and manifest planning."""

from __future__ import annotations

from reprollm.core.pyscan import PyScanResult
from reprollm.core.scanner import RepoScanner
from reprollm.integrations.inspect_ai import InspectAIIntegration
from reprollm.integrations.lighteval import LightEvalIntegration
from reprollm.integrations.lm_eval import LmEvalIntegration
from reprollm.schemas.finding import Evidence

EvaluationIntegration = LmEvalIntegration | LightEvalIntegration | InspectAIIntegration


def detected_frameworks(
    scanner: RepoScanner, pyscan: PyScanResult
) -> list[tuple[EvaluationIntegration, list[Evidence]]]:
    integrations: tuple[EvaluationIntegration, ...] = (
        InspectAIIntegration(),
        LightEvalIntegration(),
        LmEvalIntegration(),
    )
    detected: list[tuple[EvaluationIntegration, list[Evidence]]] = []
    for integration in integrations:
        evidence = integration.detect(scanner, pyscan=pyscan)
        if evidence:
            detected.append((integration, evidence))
    return detected
