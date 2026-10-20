"""R06-B: format-lock credit requires an actual associated package origin."""

from pathlib import Path
from typing import Any

import pytest

from reprollm.core.context import AuditContext
from reprollm.rules.env import LlmCriticalDepsPinnedRule, LockfilePresentRule
from reprollm.schemas.finding import Evidence, Finding, FindingStatus, Severity


@pytest.fixture(autouse=True)
def fixed_installed_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})


def _write(root: Path, files: dict[str, str]) -> None:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _torch_warning(path: str = "requirements.txt", line: int = 1) -> Finding:
    return Finding(
        rule_id="env.llm_critical_deps_pinned",
        category="env",
        severity=Severity.WARNING,
        status=FindingStatus.FAIL,
        level=0,
        message=("torch is used but not pinned to an exact version (suggestion: torch==<version>)"),
        evidence=[
            Evidence(
                kind="file",
                path=path,
                line=line,
                value="(no version)",
                note="declared as unversioned",
            )
        ],
        fix_hint="Pin torch exactly, e.g. `torch==<version>`.",
    )


def test_orphan_nested_uv_lock_keeps_inventory_but_does_not_pin_root(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "requirements.txt": "torch\n",
            "tools/uv.lock": '[[package]]\nname = "torch"\n',
        },
    )
    context = AuditContext(tmp_path)

    assert LlmCriticalDepsPinnedRule().check(context) == [_torch_warning()]
    assert [(lock.path, lock.packages) for lock in context.deps.lockfiles] == [
        ("tools/uv.lock", frozenset({"torch"}))
    ]
    assert context.deps.manifest_present
    assert LockfilePresentRule().check(context) == []


@pytest.mark.parametrize(
    ("manifest", "declaration", "lock", "packages"),
    [
        (
            "pyproject.toml",
            '[project]\ndependencies = ["torch"]\n',
            "uv.lock",
            '[[package]]\nname = "torch"\n',
        ),
        (
            "pyproject.toml",
            '[tool.poetry.dependencies]\ntorch = "*"\n',
            "poetry.lock",
            '[[package]]\nname = "torch"\n',
        ),
        (
            "Pipfile",
            '[packages]\ntorch = "*"\n',
            "Pipfile.lock",
            '{"default": {"torch": {}}}\n',
        ),
        (
            "environment.yml",
            "dependencies:\n  - pytorch\n",
            "conda-lock.yml",
            "package:\n  - name: torch\n",
        ),
    ],
    ids=["uv", "poetry", "pipfile", "conda"],
)
def test_lock_credits_its_same_directory_manager_declaration(
    tmp_path: Path, manifest: str, declaration: str, lock: str, packages: str
) -> None:
    _write(tmp_path, {f"project/{manifest}": declaration, f"project/{lock}": packages})

    assert LlmCriticalDepsPinnedRule().check(AuditContext(tmp_path)) == []


@pytest.mark.parametrize(
    ("manifest", "empty_project", "lock", "packages"),
    [
        ("pyproject.toml", "[project]\n", "uv.lock", '[[package]]\nname="torch"\n'),
        ("pyproject.toml", "[tool.poetry]\n", "poetry.lock", '[[package]]\nname="torch"\n'),
        ("Pipfile", "[dev-packages]\n", "Pipfile.lock", '{"develop":{"torch":{}}}\n'),
        ("environment.yaml", "dependencies: []\n", "conda-lock.yml", "package:\n - name: torch\n"),
    ],
    ids=["uv", "poetry", "pipfile", "conda"],
)
def test_import_uses_its_nearest_empty_runtime_project_pair(
    tmp_path: Path, manifest: str, empty_project: str, lock: str, packages: str
) -> None:
    _write(
        tmp_path,
        {
            f"project/{manifest}": empty_project,
            f"project/{lock}": packages,
            "project/src/train.py": "import torch\n",
        },
    )

    assert LlmCriticalDepsPinnedRule().check(AuditContext(tmp_path)) == []


def _torch_import_warning(path: str) -> Finding:
    return _torch_warning().model_copy(
        update={"evidence": [Evidence(kind="file", path=path, line=1, note="imported")]}
    )


@pytest.mark.parametrize(
    ("manifest", "broken"),
    [
        ("pyproject.toml", "[project broken\n"),
        ("Pipfile", "[packages broken\n"),
        ("environment.yml", "dependencies: [broken\n"),
        ("pyproject.toml", "project = 42\n"),
        ("pyproject.toml", "[tool]\npoetry = 42\n"),
        ("pyproject.toml", "tool = 0\n"),
        ("Pipfile", "packages = 0\n"),
        ("environment.yaml", "dependencies: 0\n"),
    ],
    ids=[
        "toml-syntax",
        "pipfile-syntax",
        "yaml-syntax",
        "project-type",
        "poetry-type",
        "tool-type",
        "packages-type",
        "dependencies-type",
    ],
)
def test_uncertain_manifest_blocks_ancestor_import_credit(
    tmp_path: Path, manifest: str, broken: str
) -> None:
    _write(
        tmp_path,
        {
            "pyproject.toml": "[project]\n",
            "uv.lock": '[[package]]\nname="torch"\n',
            f"sub/{manifest}": broken,
            "sub/train.py": "import torch\n",
        },
    )

    assert LlmCriticalDepsPinnedRule().check(AuditContext(tmp_path)) == [
        _torch_import_warning("sub/train.py")
    ]


@pytest.mark.parametrize("alternative", ["dependencies: []\n", "dependencies: [broken\n"])
def test_two_conda_environment_basenames_never_guess_a_lock_owner(
    tmp_path: Path, alternative: str
) -> None:
    _write(
        tmp_path,
        {
            "environment.yml": "dependencies:\n  - torch\n",
            "environment.yaml": alternative,
            "conda-lock.yml": "package:\n  - name: torch\n",
        },
    )
    context = AuditContext(tmp_path)

    assert LlmCriticalDepsPinnedRule().check(context) == [_torch_warning("environment.yml")]
    assert LockfilePresentRule().check(context) == []


@pytest.mark.parametrize(
    ("manifest", "content"),
    [
        ("pyproject.toml", "[project]\n"),
        ("pyproject.toml", "[tool.poetry]\n"),
        ("Pipfile", "[packages]\n"),
        ("environment.yml", "dependencies: []\n"),
    ],
    ids=["project", "poetry", "pipfile", "conda"],
)
def test_nearer_runtime_project_prevents_borrowing_an_ancestor_lock(
    tmp_path: Path, manifest: str, content: str
) -> None:
    _write(
        tmp_path,
        {
            "pyproject.toml": "[project]\n",
            "uv.lock": '[[package]]\nname="torch"\n',
            f"sub/{manifest}": content,
            "sub/train.py": "import torch\n",
        },
    )

    assert LlmCriticalDepsPinnedRule().check(AuditContext(tmp_path)) == [
        _torch_import_warning("sub/train.py")
    ]


@pytest.mark.parametrize(
    "nonproject",
    [
        {"sub/pyproject.toml": "[tool.ruff]\n"},
        {"sub/pyproject.toml": "[build-system]\nrequires=[]\n"},
        {"sub/requirements.txt": "requests\n"},
    ],
    ids=["tool-only", "build-only", "requirements"],
)
def test_nonproject_files_do_not_block_the_actual_nearest_runtime_project(
    tmp_path: Path, nonproject: dict[str, str]
) -> None:
    _write(
        tmp_path,
        {
            "pyproject.toml": "[project]\n",
            "uv.lock": '[[package]]\nname="torch"\n',
            "sub/train.py": "import torch\n",
            **nonproject,
        },
    )

    assert LlmCriticalDepsPinnedRule().check(AuditContext(tmp_path)) == []


@pytest.mark.parametrize("declared", [False, True], ids=["import", "declaration"])
def test_same_directory_uncertainty_only_blocks_inferred_import_credit(
    tmp_path: Path, declared: bool
) -> None:
    _write(
        tmp_path,
        {
            "pyproject.toml": "[project]\n" + ('dependencies=["torch"]\n' if declared else ""),
            "uv.lock": '[[package]]\nname="torch"\n',
            "Pipfile": "[packages broken\n",
            "train.py": "import torch\n",
        },
    )
    expected = [] if declared else [_torch_import_warning("train.py")]

    assert LlmCriticalDepsPinnedRule().check(AuditContext(tmp_path)) == expected


def test_clean_deeper_project_uses_own_pair_below_an_outer_uncertain_manifest(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        {
            "pyproject.toml": "[project broken\n",
            "sub/pyproject.toml": "[project]\n",
            "sub/uv.lock": '[[package]]\nname="torch"\n',
            "sub/train.py": "import torch\n",
        },
    )

    assert LlmCriticalDepsPinnedRule().check(AuditContext(tmp_path)) == []


@pytest.mark.parametrize("manifest", ["pyproject.toml", "Pipfile", "environment.yml"])
def test_unreadable_observed_manifest_cannot_borrow_ancestor_credit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manifest: str
) -> None:
    _write(
        tmp_path,
        {
            "pyproject.toml": "[project]\n",
            "uv.lock": '[[package]]\nname="torch"\n',
            f"sub/{manifest}": "unreadable fixture\n",
            "sub/train.py": "import torch\n",
        },
    )
    blocked = tmp_path / "sub" / manifest
    original_open = Path.open

    def open_with_unreadable_candidate(path: Path, *args: Any, **kwargs: Any) -> Any:
        if path == blocked:
            raise PermissionError("synthetic unreadable candidate")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_with_unreadable_candidate)
    context = AuditContext(tmp_path)

    assert LlmCriticalDepsPinnedRule().check(context) == [_torch_import_warning("sub/train.py")]
    assert context.deps.unparsed == [f"sub/{manifest}:0: unreadable"]


@pytest.mark.parametrize("nested_origin", ["declaration", "import"])
def test_one_nested_associated_origin_still_provides_repository_evidence(
    tmp_path: Path, nested_origin: str
) -> None:
    files = {
        "requirements.txt": "torch\n",
        "sub/pyproject.toml": "[project]\n",
        "sub/uv.lock": '[[package]]\nname="torch"\n',
    }
    if nested_origin == "declaration":
        files["sub/pyproject.toml"] += 'dependencies=["torch"]\n'
    else:
        files["sub/train.py"] = "import torch\n"
    _write(tmp_path, files)

    assert LlmCriticalDepsPinnedRule().check(AuditContext(tmp_path)) == []


@pytest.mark.parametrize(
    ("manifest", "empty", "lock", "packages"),
    [
        ("pyproject.toml", "[project]\n", "uv.lock", '[[package]]\nname="torch"\n'),
        ("pyproject.toml", "[tool.poetry]\n", "poetry.lock", '[[package]]\nname="torch"\n'),
        ("Pipfile", "[packages]\n", "Pipfile.lock", '{"default":{"torch":{}}}\n'),
        ("environment.yml", "dependencies: []\n", "conda-lock.yml", "package:\n - name: torch\n"),
    ],
    ids=["uv", "poetry", "pipfile", "conda"],
)
def test_a_lock_entry_and_empty_owner_are_not_an_actual_package_origin(
    tmp_path: Path, manifest: str, empty: str, lock: str, packages: str
) -> None:
    _write(
        tmp_path,
        {"requirements.txt": "torch\n", f"sub/{manifest}": empty, f"sub/{lock}": packages},
    )

    assert LlmCriticalDepsPinnedRule().check(AuditContext(tmp_path)) == [_torch_warning()]


@pytest.mark.parametrize(
    ("foreign", "text"),
    [
        ("requirements.txt", "torch\n"),
        ("Pipfile", '[packages]\ntorch="*"\n'),
        ("environment.yml", "dependencies:\n - torch\n"),
    ],
    ids=["requirements", "pipfile", "conda"],
)
def test_same_directory_other_manager_declaration_cannot_borrow_uv_credit(
    tmp_path: Path, foreign: str, text: str
) -> None:
    _write(
        tmp_path,
        {"pyproject.toml": "[project]\n", "uv.lock": '[[package]]\nname="torch"\n', foreign: text},
    )
    findings = LlmCriticalDepsPinnedRule().check(AuditContext(tmp_path))

    assert len(findings) == 1
    assert findings[0].rule_id == "env.llm_critical_deps_pinned"
    assert findings[0].severity == Severity.WARNING
    assert findings[0].evidence[0].path == foreign


def test_logical_directory_components_do_not_treat_app_as_parent_of_app2(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "app/pyproject.toml": "[project]\n",
            "app/uv.lock": '[[package]]\nname="torch"\n',
            "app2/train.py": "import torch\n",
        },
    )

    assert LlmCriticalDepsPinnedRule().check(AuditContext(tmp_path)) == [
        _torch_import_warning("app2/train.py")
    ]


def test_internal_source_alias_uses_its_logical_project_not_physical_target(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "physical/pyproject.toml": "[project]\n",
            "physical/uv.lock": '[[package]]\nname="torch"\n',
            "physical/source.txt": "import torch\n",
        },
    )
    try:
        (tmp_path / "alias.py").symlink_to(tmp_path / "physical/source.txt")
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks unavailable: {type(exc).__name__}")

    assert LlmCriticalDepsPinnedRule().check(AuditContext(tmp_path)) == [
        _torch_import_warning("alias.py")
    ]


def test_allowed_internal_alias_can_use_its_actual_logical_project_pair(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "project/pyproject.toml": "[project]\n",
            "project/uv.lock": '[[package]]\nname="torch"\n',
            "physical/source.txt": "import torch\n",
        },
    )
    try:
        (tmp_path / "project/train.py").symlink_to(tmp_path / "physical/source.txt")
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks unavailable: {type(exc).__name__}")

    assert LlmCriticalDepsPinnedRule().check(AuditContext(tmp_path)) == []


@pytest.mark.parametrize(
    "files",
    [
        {"requirements.txt": "torch\n", "other/requirements.txt": "torch==1.0\nrequests>=2\n"},
        {"requirements.txt": "torch==1.0\n", "other/requirements.txt": "torch==2.0\n"},
        {"requirements.txt": "torch==1.0\n-r requirements.txt\n"},
    ],
    ids=["unreferenced-nested-exact", "conflicting-exacts", "exact-in-incomplete-cycle"],
)
def test_repository_exact_evidence_is_independent_of_ownership_and_closure_qualification(
    tmp_path: Path, files: dict[str, str]
) -> None:
    _write(tmp_path, files)

    assert LlmCriticalDepsPinnedRule().check(AuditContext(tmp_path)) == []


def test_workspace_members_do_not_borrow_the_parent_uv_lock(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "pyproject.toml": '[project]\n[tool.uv.workspace]\nmembers=["member"]\n',
            "uv.lock": '[[package]]\nname="torch"\n',
            "member/pyproject.toml": '[project]\ndependencies=["torch"]\n',
            "member/train.py": "from torch import nn\n",
        },
    )

    assert LlmCriticalDepsPinnedRule().check(AuditContext(tmp_path)) == [
        _torch_warning("member/pyproject.toml", 2)
    ]


@pytest.mark.parametrize(
    ("pyproject", "lock", "pinned"),
    [
        ('[tool.poetry.dependencies]\ntorch="*"\n', "uv.lock", False),
        ('[project]\n[tool.poetry.dependencies]\ntorch="*"\n', "uv.lock", True),
        ('[project]\ndependencies=["torch"]\n', "poetry.lock", True),
    ],
    ids=["uv-rejects-poetry-only", "uv-paired-file-supported-declarations", "poetry-project"],
)
def test_pyproject_pair_qualification_respects_manager_tables_without_new_table_scopes(
    tmp_path: Path, pyproject: str, lock: str, pinned: bool
) -> None:
    _write(tmp_path, {"pyproject.toml": pyproject, lock: '[[package]]\nname="torch"\n'})
    expected = []
    if not pinned:
        expected = [
            _torch_warning().model_copy(
                update={
                    "evidence": [
                        Evidence(
                            kind="file",
                            path="pyproject.toml",
                            line=2,
                            value="*",
                            note="declared as *",
                        )
                    ]
                }
            )
        ]

    assert LlmCriticalDepsPinnedRule().check(AuditContext(tmp_path)) == expected


@pytest.mark.parametrize(
    ("manifest", "content", "lock", "packages"),
    [
        (
            "pyproject.toml",
            "[project]\ndependencies=42\n",
            "uv.lock",
            '[[package]]\nname="torch"\n',
        ),
        ("Pipfile", "[packages]\ntorch=42\n", "Pipfile.lock", '{"default":{"torch":{}}}\n'),
        (
            "environment.yml",
            "dependencies:\n - pip: 42\n",
            "conda-lock.yml",
            "package:\n - name: torch\n",
        ),
    ],
    ids=["unsupported-project-entry", "unsupported-pipfile-entry", "unsupported-conda-entry"],
)
def test_unsupported_declarations_inside_valid_runtime_structure_do_not_create_barriers(
    tmp_path: Path, manifest: str, content: str, lock: str, packages: str
) -> None:
    _write(tmp_path, {manifest: content, lock: packages, "train.py": "import torch\n"})

    assert LlmCriticalDepsPinnedRule().check(AuditContext(tmp_path)) == []


@pytest.mark.parametrize("declared", [False, True], ids=["import", "declaration"])
def test_uncertain_tool_container_preserves_an_independent_explicit_project_declaration(
    tmp_path: Path, declared: bool
) -> None:
    _write(
        tmp_path,
        {
            "pyproject.toml": "tool=0\n[project]\n"
            + ('dependencies=["torch"]\n' if declared else ""),
            "uv.lock": '[[package]]\nname="torch"\n',
            "train.py": "import torch\n",
        },
    )
    expected = [] if declared else [_torch_import_warning("train.py")]

    assert LlmCriticalDepsPinnedRule().check(AuditContext(tmp_path)) == expected


@pytest.mark.parametrize("lock_text", ["", "[[package broken\n"], ids=["empty", "malformed"])
def test_empty_or_malformed_lock_keeps_presence_without_package_credit(
    tmp_path: Path, lock_text: str
) -> None:
    _write(tmp_path, {"requirements.txt": "torch\n", "uv.lock": lock_text})
    context = AuditContext(tmp_path)

    assert LlmCriticalDepsPinnedRule().check(context) == [_torch_warning()]
    assert [(lock.path, lock.packages) for lock in context.deps.lockfiles] == [
        ("uv.lock", frozenset())
    ]
    assert LockfilePresentRule().check(context) == []


def test_one_qualified_import_can_credit_a_different_manager_declaration(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "Pipfile": '[packages]\ntorch="*"\n',
            "pyproject.toml": "[project]\n",
            "uv.lock": '[[package]]\nname="torch"\n',
            "train.py": "import torch\n",
        },
    )

    assert LlmCriticalDepsPinnedRule().check(AuditContext(tmp_path)) == []


def test_multiple_origins_still_emit_one_warning_with_original_first_evidence(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        {
            "requirements.txt": "torch\n",
            "a.py": "import torch\n",
            "b.py": "from torch import nn\n",
            "orphan/uv.lock": '[[package]]\nname="torch"\n',
        },
    )

    assert LlmCriticalDepsPinnedRule().check(AuditContext(tmp_path)) == [_torch_warning()]
