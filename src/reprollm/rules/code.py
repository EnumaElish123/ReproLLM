"""``code.*`` rules: repository and code state (spec §12.1).

M1 implements ``code.git_repo`` and ``code.git_commit``; the remaining rules
(clean_tree, no_untracked, submodules_initialized, remote_recorded) arrive in
M2-T02.
"""

from __future__ import annotations

from reprollm.core.context import AuditContext
from reprollm.core.registry import Rule, register_rule
from reprollm.schemas.finding import Evidence, Finding, Severity


@register_rule
class GitRepoRule(Rule):
    id = "code.git_repo"
    category = "code"
    default_severity = Severity.CRITICAL
    min_level = 0
    description = "The experiment code lives in a git repository."
    fix_hint = "Run `git init` and commit the experiment code so its state is recorded."

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def check(self, ctx: AuditContext) -> list[Finding]:
        if ctx.git.is_repo:
            return []
        return [
            self.finding(
                ctx,
                message=f"{ctx.target} is not inside a git work tree",
                evidence=[
                    Evidence(
                        kind="git",
                        path=ctx.target,
                        note="git rev-parse --is-inside-work-tree failed",
                    )
                ],
            )
        ]


@register_rule
class GitCommitRule(Rule):
    id = "code.git_commit"
    category = "code"
    default_severity = Severity.CRITICAL
    min_level = 0
    description = "HEAD points at a committed revision (no unborn branch)."
    fix_hint = "Commit the current state: `git add -A && git commit -m 'experiment'`."

    def applies(self, ctx: AuditContext) -> bool:
        return ctx.git.is_repo

    def skip_reason(self, ctx: AuditContext) -> str | None:
        return "not a git repository" if not ctx.git.is_repo else None

    def check(self, ctx: AuditContext) -> list[Finding]:
        if ctx.git.commit is not None:
            return []
        branch = ctx.git.branch or "HEAD"
        return [
            self.finding(
                ctx,
                message=f"git repository has no commits (unborn branch {branch})",
                evidence=[
                    Evidence(
                        kind="git",
                        field="commit",
                        note="git rev-parse HEAD failed (unborn branch)",
                    )
                ],
            )
        ]


def _path_evidence(paths: list[str], note_template: str) -> list[Evidence]:
    """Evidence for the first 10 paths plus a count summary."""
    evidence = [
        Evidence(kind="git", path=path, note=note_template.format(path=path))
        for path in paths[:10]
    ]
    if len(paths) > 10:
        evidence.append(Evidence(kind="git", note=f"…and {len(paths) - 10} more"))
    return evidence


@register_rule
class CleanTreeRule(Rule):
    id = "code.clean_tree"
    category = "code"
    default_severity = Severity.WARNING
    min_level = 0
    description = "Tracked files have no uncommitted modifications."
    fix_hint = "Commit or stash your changes: `git add -A && git commit` or `git stash`."

    def applies(self, ctx: AuditContext) -> bool:
        return ctx.git.is_repo

    def skip_reason(self, ctx: AuditContext) -> str | None:
        return "not a git repository" if not ctx.git.is_repo else None

    def check(self, ctx: AuditContext) -> list[Finding]:
        modified = ctx.git.modified
        if not modified:
            return []
        return [
            self.finding(
                ctx,
                message=(
                    f"working tree has {len(modified)} modified/staged tracked file(s): "
                    f"{', '.join(modified[:3])}{'…' if len(modified) > 3 else ''}"
                ),
                evidence=_path_evidence(modified, "{path} modified vs HEAD"),
            )
        ]


@register_rule
class NoUntrackedRule(Rule):
    id = "code.no_untracked"
    category = "code"
    default_severity = Severity.WARNING
    min_level = 0
    description = "No untracked, non-ignored files are left in the tree."
    fix_hint = "Commit them, delete them, or add them to .gitignore."

    def applies(self, ctx: AuditContext) -> bool:
        return ctx.git.is_repo

    def skip_reason(self, ctx: AuditContext) -> str | None:
        return "not a git repository" if not ctx.git.is_repo else None

    def check(self, ctx: AuditContext) -> list[Finding]:
        untracked = ctx.git.untracked
        if not untracked:
            return []
        return [
            self.finding(
                ctx,
                message=(
                    f"{len(untracked)} untracked non-ignored file(s): "
                    f"{', '.join(untracked[:3])}{'…' if len(untracked) > 3 else ''}"
                ),
                evidence=_path_evidence(untracked, "{path} untracked"),
            )
        ]


@register_rule
class SubmodulesInitializedRule(Rule):
    id = "code.submodules_initialized"
    category = "code"
    default_severity = Severity.WARNING
    min_level = 0
    description = "All declared submodules have a checked-out commit."
    fix_hint = "Run `git submodule update --init --recursive`."

    def applies(self, ctx: AuditContext) -> bool:
        return ctx.git.is_repo and (ctx.root / ".gitmodules").is_file()

    def skip_reason(self, ctx: AuditContext) -> str | None:
        if not ctx.git.is_repo:
            return "not a git repository"
        if not (ctx.root / ".gitmodules").is_file():
            return "no .gitmodules"
        return None

    def check(self, ctx: AuditContext) -> list[Finding]:
        uninitialized = [s.path for s in ctx.git.submodules if not s.initialized]
        if not uninitialized:
            return []
        return [
            self.finding(
                ctx,
                message=(
                    f"{len(uninitialized)} submodule(s) not initialized: "
                    f"{', '.join(uninitialized)}"
                ),
                evidence=[
                    Evidence(kind="git", path=path, note="git submodule status prefix '-'")
                    for path in uninitialized[:10]
                ],
            )
        ]


@register_rule
class RemoteRecordedRule(Rule):
    id = "code.remote_recorded"
    category = "code"
    default_severity = Severity.INFO
    min_level = 0
    description = "An origin remote records where this code is published."
    fix_hint = "Run `git remote add origin <url>` so the experiment's code source is recorded."

    def applies(self, ctx: AuditContext) -> bool:
        return ctx.git.is_repo

    def skip_reason(self, ctx: AuditContext) -> str | None:
        return "not a git repository" if not ctx.git.is_repo else None

    def check(self, ctx: AuditContext) -> list[Finding]:
        if ctx.git.remote_origin is not None:
            return []
        return [
            self.finding(
                ctx,
                message="no 'origin' remote is configured",
                evidence=[Evidence(kind="git", note="git remote get-url origin failed")],
            )
        ]
