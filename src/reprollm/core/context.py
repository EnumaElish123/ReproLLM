"""AuditContext (spec §11): lazy view of everything rules may inspect."""

from __future__ import annotations

from pathlib import Path

from reprollm.core.deps import Declarations, scan_dependencies
from reprollm.core.git import GitInfo, inspect_git
from reprollm.core.pyscan import PyScanResult, scan_python
from reprollm.core.scanner import RepoScanner
from reprollm.schemas.config import Config
from reprollm.schemas.finding import DetectionResult
from reprollm.schemas.lock import Lock
from reprollm.schemas.manifest import Manifest
from reprollm.schemas.project_rules import ProjectRules
from reprollm.schemas.run_record import RunRecord


class AuditContext:
    """Input to every rule's ``applies``/``check``.

    Expensive facts (git state, file listing, detection) are computed lazily and
    cached. Fields scheduled for later sprints default to ``None``/empty until
    their producers land (state in M6, real detection in M2, runs in M5).
    """

    def __init__(
        self,
        root: Path,
        *,
        level: int = 0,
        target: str = ".",
        manifest: Manifest | None = None,
        lock: Lock | None = None,
        runs: list[RunRecord] | None = None,
        config: Config | None = None,
        project_rules: ProjectRules | None = None,
    ) -> None:
        self.root = root
        #: The user-supplied path argument, as given ("." by default). Findings
        #: reference this, never the absolute root (no absolute paths persisted).
        self.target = target
        self.level = level
        self.manifest = manifest
        self.lock = lock
        self.runs = runs or []
        self.config = config
        self.project_rules = project_rules
        self.state: object | None = None  # ExperimentState (M6)
        self.env: object | None = None  # EnvInfo (Level 0 env rules, M2)
        #: Profiles the user declared (manifest or --profiles); set by the engine
        #: before rules run; feeds exec.profile_detection_mismatch.
        self.declared_profiles: list[str] = []
        self._git: GitInfo | None = None
        self._fs: RepoScanner | None = None
        self._deps: Declarations | None = None
        self._pyscan: PyScanResult | None = None
        self._detection: DetectionResult | None = None

    @property
    def git(self) -> GitInfo:
        if self._git is None:
            self._git = inspect_git(self.root)
        return self._git

    @property
    def fs(self) -> RepoScanner:
        if self._fs is None:
            self._fs = RepoScanner(self.root, self.git)
        return self._fs

    @property
    def deps(self) -> Declarations:
        """Parsed dependency declarations and lockfiles (M2-T03)."""
        if self._deps is None:
            self._deps = scan_dependencies(self.fs)
        return self._deps

    @property
    def pyscan(self) -> PyScanResult:
        """AST scan of Python sources (imports, HF ids, trust_remote_code)."""
        if self._pyscan is None:
            self._pyscan = scan_python(self.fs)
        return self._pyscan

    @property
    def detection(self) -> DetectionResult:
        if self._detection is None:
            from reprollm.profiles.detect import run_detection

            self._detection = run_detection(self.fs, self.pyscan, self.deps)
        return self._detection

    @property
    def latest_run(self) -> RunRecord | None:
        return self.runs[-1] if self.runs else None
