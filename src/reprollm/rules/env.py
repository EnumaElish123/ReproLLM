"""``env.*`` rules: dependency and environment declarations (spec §12.2)."""

from __future__ import annotations

import sys
from pathlib import Path

from reprollm.core.context import AuditContext
from reprollm.core.deps import canonical_dep_name
from reprollm.core.envinfo import LLM_CRITICAL_PACKAGES, installed_versions
from reprollm.core.pyscan import ImportInfo
from reprollm.core.redaction import is_forbidden_file
from reprollm.core.registry import Rule, register_rule
from reprollm.schemas.finding import Evidence, Finding, Severity

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

#: LLM-critical names in canonical (comparison) space.
_CRITICAL_CANON = {canonical_dep_name(name) for name in LLM_CRITICAL_PACKAGES}


def _display_name(canonical: str) -> str:
    for name in LLM_CRITICAL_PACKAGES:
        if canonical_dep_name(name) == canonical:
            return name
    return canonical


@register_rule
class DependencyManifestPresentRule(Rule):
    id = "env.dependency_manifest_present"
    category = "env"
    default_severity = Severity.CRITICAL
    min_level = 0
    description = "A dependency manifest declares the Python environment."
    fix_hint = (
        "Add a pyproject.toml, requirements*.txt, or environment.yml that declares "
        "the dependencies of this experiment."
    )

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def check(self, ctx: AuditContext) -> list[Finding]:
        if ctx.deps.manifest_present:
            return []
        return [
            self.finding(
                ctx,
                message=(
                    "no dependency manifest found (expected pyproject.toml, "
                    "requirements*.txt, environment.yml, uv.lock, poetry.lock, or Pipfile)"
                ),
                evidence=[Evidence(kind="file", note="none of the manifest names exist")],
            )
        ]


@register_rule
class LockfilePresentRule(Rule):
    id = "env.lockfile_present"
    category = "env"
    default_severity = Severity.WARNING
    min_level = 0
    description = "A lockfile (or fully pinned requirements) records exact versions."
    fix_hint = (
        "Commit a uv.lock/poetry.lock, or pin every dependency with `==` in "
        "requirements.txt so the environment can be rebuilt exactly."
    )

    def applies(self, ctx: AuditContext) -> bool:
        return ctx.deps.manifest_present

    def skip_reason(self, ctx: AuditContext) -> str | None:
        return "no dependency manifest" if not ctx.deps.manifest_present else None

    def check(self, ctx: AuditContext) -> list[Finding]:
        if ctx.deps.lockfiles:
            return []
        return [
            self.finding(
                ctx,
                message=(
                    "no lockfile found and not every declared dependency is pinned "
                    "with an exact version"
                ),
                evidence=[
                    Evidence(
                        kind="file",
                        note="no uv.lock/poetry.lock/Pipfile.lock/"
                        "conda-lock.yml/all-== requirements",
                    )
                ],
            )
        ]


@register_rule
class LlmCriticalDepsPinnedRule(Rule):
    id = "env.llm_critical_deps_pinned"
    category = "env"
    default_severity = Severity.WARNING
    min_level = 0
    description = "Every LLM-critical dependency in use is pinned to an exact version."
    fix_hint = "Pin the package exactly (see the message for the suggested version)."

    def applies(self, ctx: AuditContext) -> bool:
        return bool(self._critical_in_use(ctx))

    def skip_reason(self, ctx: AuditContext) -> str | None:
        return (
            "no LLM-critical package is declared or imported"
            if not self._critical_in_use(ctx)
            else None
        )

    def check(self, ctx: AuditContext) -> list[Finding]:
        findings: list[Finding] = []
        deps = ctx.deps
        locked = {name for lock in deps.lockfiles for name in lock.packages}
        installed = installed_versions()
        for canonical in self._critical_in_use(ctx):
            if canonical in locked:
                continue
            declarations = [d for d in deps.declarations if d.name == canonical and d.is_exact]
            if declarations:
                continue
            display = _display_name(canonical)
            version = installed.get(display)
            suggestion = f"{display}=={version}" if version else f"{display}==<version>"
            finding = self.finding(
                ctx,
                message=(
                    f"{display} is used but not pinned to an exact version "
                    f"(suggestion: {suggestion})"
                ),
                evidence=self._evidence(canonical, deps.declarations, ctx.pyscan.imports),
                fix_hint=f"Pin {display} exactly, e.g. `{suggestion}`.",
            )
            findings.append(finding)
        return findings

    def _critical_in_use(self, ctx: AuditContext) -> list[str]:
        deps = ctx.deps
        declared = {d.name for d in deps.declarations}
        imported = {canonical_dep_name(info.module.split(".", 1)[0]) for info in ctx.pyscan.imports}
        return sorted((declared | imported) & _CRITICAL_CANON)

    @staticmethod
    def _evidence(
        canonical: str,
        declarations: list,
        imports: list[ImportInfo],
    ) -> list[Evidence]:
        matching = [d for d in declarations if d.name == canonical]
        if matching:
            best = matching[0]
            return [
                Evidence(
                    kind="file",
                    path=best.source_file,
                    line=best.line,
                    value=best.specifier or "(no version)",
                    note=f"declared as {best.specifier or 'unversioned'}",
                )
            ]
        for info in imports:
            if canonical_dep_name(info.module.split(".", 1)[0]) == canonical:
                return [Evidence(kind="file", path=info.path, line=info.line, note="imported")]
        return []


@register_rule
class PythonVersionDeclaredRule(Rule):
    id = "env.python_version_declared"
    category = "env"
    default_severity = Severity.WARNING
    min_level = 0
    description = "The required Python version is declared."
    fix_hint = (
        "Add `requires-python` to pyproject.toml, a .python-version file, or a "
        "`python=3.x` entry in environment.yml."
    )

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def check(self, ctx: AuditContext) -> list[Finding]:
        found = self._declared_where(ctx)
        if found is not None:
            return []
        return [
            self.finding(
                ctx,
                message="no Python version requirement is declared",
                evidence=[
                    Evidence(
                        kind="file",
                        note="no requires-python / .python-version / conda python= found",
                    )
                ],
            )
        ]

    @staticmethod
    def _declared_where(ctx: AuditContext) -> Evidence | None:
        scanner = ctx.fs
        pyproject = next((p for p in scanner.files() if Path(p).name == "pyproject.toml"), None)
        if pyproject is not None:
            text = scanner.read_text(pyproject)
            if text is not None:
                try:
                    doc = tomllib.loads(text)
                    requires = (doc.get("project") or {}).get("requires-python")
                    if requires:
                        return Evidence(
                            kind="file", path=pyproject, note=f"requires-python {requires}"
                        )
                except tomllib.TOMLDecodeError:
                    pass
        if any(Path(p).name == ".python-version" for p in scanner.files()):
            return Evidence(kind="file", path=".python-version", note=".python-version present")
        env_yml = next(
            (p for p in scanner.files() if Path(p).name in {"environment.yml", "environment.yaml"}),
            None,
        )
        if env_yml is not None:
            text = scanner.read_text(env_yml)
            if text is not None and "python=" in text:
                return Evidence(kind="file", path=env_yml, note="conda python= entry present")
        return None


@register_rule
class SecretFilesIgnoredRule(Rule):
    id = "env.secret_files_ignored"
    category = "env"
    default_severity = Severity.CRITICAL
    min_level = 0
    description = "Secret-bearing files are not present or are gitignored."
    fix_hint = (
        "Remove the secret file from the repository, rotate the secret, and add the "
        "pattern to .gitignore (keep only .env.example-style templates)."
    )

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def check(self, ctx: AuditContext) -> list[Finding]:
        candidates = [p for p in ctx.fs.files() if is_forbidden_file(p)]
        if not candidates:
            return []
        # In a git repo the listing is `ls-files --cached --others
        # --exclude-standard`: ignored files never appear, and tracked files
        # count as not ignored by definition (§12.2) — so every listed
        # forbidden file fails.
        if ctx.git.is_repo:
            return [
                self.finding(
                    ctx,
                    message=(
                        f"{len(candidates)} secret-bearing file(s) tracked or not "
                        f"gitignored: {', '.join(candidates[:3])}"
                        f"{'…' if len(candidates) > 3 else ''}"
                    ),
                    evidence=[
                        Evidence(
                            kind="file", path=p, note="matches a forbidden file pattern (§16.4)"
                        )
                        for p in candidates[:10]
                    ],
                )
            ]
        return [
            self.finding(
                ctx,
                message=(
                    f"{len(candidates)} secret-bearing file(s) present: "
                    f"{', '.join(candidates[:3])}"
                    f"{'…' if len(candidates) > 3 else ''} (not a git repo; "
                    "gitignore status cannot be verified)"
                ),
                severity=Severity.WARNING,
                evidence=[
                    Evidence(
                        kind="file", path=p, note="matches a forbidden file pattern; not a git repo"
                    )
                    for p in candidates[:10]
                ],
            )
        ]


@register_rule
class ReprollmInitializedRule(Rule):
    id = "env.reprollm_initialized"
    category = "env"
    default_severity = Severity.INFO
    min_level = 0
    description = "The repository is initialized for ReproLLM."
    fix_hint = "Run `reprollm init` to create reprollm.yaml and .reprollm/."

    def applies(self, ctx: AuditContext) -> bool:
        return ctx.level == 0

    def skip_reason(self, ctx: AuditContext) -> str | None:
        return "audit level > 0; reprollm.yaml exists" if ctx.level > 0 else None

    def check(self, ctx: AuditContext) -> list[Finding]:
        if (ctx.root / "reprollm.yaml").is_file() or (ctx.root / ".reprollm").is_dir():
            return []
        detected = [
            entry
            for entry in ctx.detection.profiles
            if entry.confidence in {"high", "medium"}
            if getattr(entry, "shipped", True)
        ]
        names = ", ".join(f"{entry.profile} ({entry.confidence})" for entry in detected)
        message = "no reprollm.yaml or .reprollm/ found; run `reprollm init` to scaffold one"
        evidence = [Evidence(kind="file", note="reprollm.yaml absent")]
        if detected:
            profile_list = ",".join(entry.profile for entry in detected)
            message += (
                f" (detected experiment profiles: {names} — start with "
                f"`reprollm init --profiles {profile_list}`)"
            )
            evidence.extend(
                Evidence(kind="detection", note=f"{entry.profile}: {entry.confidence} confidence")
                for entry in detected[:5]
            )
        return [self.finding(ctx, message=message, evidence=evidence)]
