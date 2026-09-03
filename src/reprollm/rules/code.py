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
