"""Load accepted declarations without exposing parser input in diagnostics (§7)."""

from pathlib import Path

from pydantic import ValidationError

from reprollm.core.errors import UserError
from reprollm.core.paths import PROJECT_RULES, resolve_project_file
from reprollm.core.yaml_io import load_yaml
from reprollm.schemas.project_rules import ProjectRules


def load_project_rules(root: Path) -> ProjectRules | None:
    candidate = root / PROJECT_RULES
    if not candidate.exists() and not candidate.is_symlink():
        return None
    path = resolve_project_file(root, PROJECT_RULES)
    if path is None:
        raise UserError(f"{PROJECT_RULES} must be a file inside the repository")
    try:
        return ProjectRules.model_validate(load_yaml(path))
    except (UserError, ValueError, OSError, ValidationError) as exc:
        raise UserError(
            f"cannot read {PROJECT_RULES} ({type(exc).__name__}); fix this file"
        ) from None
