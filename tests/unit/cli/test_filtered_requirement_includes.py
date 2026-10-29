"""Excluded requirements include targets through public CLI commands."""

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from reprollm.cli.main import app
from tests.conftest import commit_all, make_git_repo

runner = CliRunner()


def test_audit_skips_missing_pin_when_supported_include_target_is_excluded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "filtered-include"
    (repo / "build").mkdir(parents=True)
    (repo / "requirements.txt").write_text("torch>=2.5.1\n-r build/pins.txt\n", encoding="utf-8")
    (repo / "build" / "pins.txt").write_text("torch==2.5.1\n", encoding="utf-8")
    before = {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file()
    }
    monkeypatch.chdir(repo)

    result = runner.invoke(app, ["-v", "audit", ".", "--format", "json", "--fail-on", "never"])

    assert result.exit_code == 0, result.output
    assert result.stderr == "scan: requirements.txt:2: include unreadable\n"
    report = json.loads(result.stdout)
    assert report["target"] == "."
    assert report["level"] == 0
    findings = [
        item for item in report["findings"] if item["rule_id"] == "env.llm_critical_deps_pinned"
    ]
    assert findings == [
        {
            "rule_id": "env.llm_critical_deps_pinned",
            "aliases": [],
            "category": "env",
            "severity": "INFO",
            "status": "skipped",
            "level": 0,
            "message": (
                "torch is used; a supported requirements include target was excluded from static "
                "analysis, so missing pin evidence is not established"
            ),
            "evidence": [
                {
                    "kind": "file",
                    "path": "requirements.txt",
                    "field": None,
                    "line": 1,
                    "value": ">=2.5.1",
                    "expected": None,
                    "note": "declared as >=2.5.1",
                },
                {
                    "kind": "file",
                    "path": "build/pins.txt",
                    "field": None,
                    "line": None,
                    "value": None,
                    "expected": None,
                    "note": "torch include target excluded from static analysis",
                },
            ],
            "fix_hint": (
                "Review torch declarations and excluded requirements include targets; make "
                "intended dependency sources eligible for static analysis before deciding that "
                "exact pin evidence is absent."
            ),
            "profile_origin": [],
            "severity_origin": "default",
            "suppressed_reason": None,
        }
    ]
    assert str(repo) not in result.stdout + result.stderr
    assert {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file()
    } == before
    assert not (repo / "reprollm.yaml").exists()
    assert not (repo / ".reprollm").exists()


def _write(root: Path, name: str, body: str | bytes) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body.encode("utf-8") if isinstance(body, str) else body)


def _inputs(root: Path) -> dict[str, bytes | tuple[str, str]]:
    result: dict[str, bytes | tuple[str, str]] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if ".git" in relative.parts:
            continue
        if path.is_symlink():
            result[relative.as_posix()] = ("symlink", str(path.readlink()))
        elif path.is_file():
            result[relative.as_posix()] = path.read_bytes()
    return result


def _project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str = "build/pins.txt",
    body: str | bytes | None = "torch==2.5.1\n",
) -> Path:
    repo = tmp_path / "filtered-include"
    repo.mkdir()
    _write(repo, "requirements.txt", f"torch>=2.5.1\n-r {target}\n")
    if body is not None:
        _write(repo, target, body)
    monkeypatch.chdir(repo)
    return repo


def _audit(*, verbose: bool = True) -> tuple[Any, dict[str, Any]]:
    argv = ["audit", ".", "--format", "json", "--fail-on", "never"]
    result = runner.invoke(app, ["-v", *argv] if verbose else argv)
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["target"] == "."
    return result, report


def _findings(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        finding
        for finding in report["findings"]
        if finding["rule_id"] == "env.llm_critical_deps_pinned"
    ]


def _declaration_evidence() -> dict[str, Any]:
    return {
        "kind": "file",
        "path": "requirements.txt",
        "field": None,
        "line": 1,
        "value": ">=2.5.1",
        "expected": None,
        "note": "declared as >=2.5.1",
    }


def _excluded_finding(
    targets: tuple[str, ...],
    *,
    package: str = "torch",
    use: dict[str, Any] | None = None,
    level: int = 0,
) -> dict[str, Any]:
    return {
        "rule_id": "env.llm_critical_deps_pinned",
        "aliases": [],
        "category": "env",
        "severity": "INFO",
        "status": "skipped",
        "level": level,
        "message": (
            f"{package} is used; a supported requirements include target was excluded from static "
            "analysis, so missing pin evidence is not established"
        ),
        "evidence": [
            _declaration_evidence() if use is None else use,
            *[
                {
                    "kind": "file",
                    "path": target,
                    "field": None,
                    "line": None,
                    "value": None,
                    "expected": None,
                    "note": f"{package} include target excluded from static analysis",
                }
                for target in targets
            ],
        ],
        "fix_hint": (
            f"Review {package} declarations and excluded requirements include targets; make "
            "intended dependency sources eligible for static analysis before deciding that "
            "exact pin evidence is absent."
        ),
        "profile_origin": [],
        "severity_origin": "default",
        "suppressed_reason": None,
    }


@pytest.mark.parametrize("body", ["torch>=2\n", "", "not a requirement !\n", None])
def test_excluded_target_contents_or_absence_do_not_grant_pin_credit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str | None
) -> None:
    repo = _project(tmp_path, monkeypatch, body=body)
    before = _inputs(repo)

    result, report = _audit()

    assert _findings(report) == [_excluded_finding(("build/pins.txt",))]
    assert result.stderr == "scan: requirements.txt:2: include unreadable\n"
    assert _inputs(repo) == before


@pytest.mark.parametrize(
    "target", ["dist/pins.data", ".venv/pins.data", ".reprollm/runs/pins.data", "vendor/pins.data"]
)
def test_existing_candidate_exclusions_apply_to_supported_arbitrary_extension_targets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    repo = _project(tmp_path, monkeypatch, target=target)
    if target == "vendor/pins.data":
        _write(repo, "vendor/pyvenv.cfg", "home = synthetic-env\n")
    before = _inputs(repo)

    result, report = _audit()

    assert _findings(report) == [_excluded_finding((target,))]
    assert result.stderr == "scan: requirements.txt:2: include unreadable\n"
    assert _inputs(repo) == before


def test_shared_normalized_excluded_targets_have_distinct_sorted_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch)
    _write(
        repo,
        "requirements.txt",
        "torch>=2.5.1\n-r dist/z.data\n-r build/a.data\n-r ./build/a.data\n-r dist/z.data\n",
    )
    _write(repo, "build/a.data", "torch==2.5.1\n")
    _write(repo, "dist/z.data", "torch==2.5.1\n")
    before = _inputs(repo)

    result, report = _audit()

    assert _findings(report) == [_excluded_finding(("build/a.data", "dist/z.data"))]
    assert set(result.stderr.splitlines()) == {
        "scan: requirements.txt:2: include unreadable",
        "scan: requirements.txt:3: include unreadable",
    }
    assert _inputs(repo) == before


def test_an_unrelated_excluded_target_conservatively_affects_known_used_packages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "filtered-include"
    repo.mkdir()
    _write(repo, "main.py", "import torch\nimport vllm\n")
    _write(repo, "tools/requirements.txt", "unrelated>=1\n-r build/pins.data\n")
    _write(repo, "tools/build/pins.data", "unrelated==1\n")
    monkeypatch.chdir(repo)
    before = _inputs(repo)

    result, report = _audit()

    assert _findings(report) == [
        _excluded_finding(
            ("tools/build/pins.data",),
            package=package,
            use={
                "kind": "file",
                "path": "main.py",
                "field": None,
                "line": line,
                "value": None,
                "expected": None,
                "note": "imported",
            },
        )
        for package, line in [("torch", 1), ("vllm", 2)]
    ]
    assert result.stderr == "scan: tools/requirements.txt:2: include unreadable\n"
    assert _inputs(repo) == before


def test_a_tracked_git_include_target_stays_excluded_from_static_analysis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_git_repo(tmp_path / "filtered-include")
    _write(repo, "requirements.txt", "torch>=2.5.1\n-r build/pins.txt\n")
    _write(repo, "build/pins.txt", "torch==2.5.1\n")
    commit_all(repo)
    monkeypatch.chdir(repo)
    before = _inputs(repo)

    result, report = _audit()

    assert _findings(report) == [_excluded_finding(("build/pins.txt",))]
    assert result.stderr == "scan: requirements.txt:2: include unreadable\n"
    assert all(
        finding["status"] == "pass"
        for finding in report["findings"]
        if finding["rule_id"] in {"code.clean_tree", "code.no_untracked"}
    )
    assert _inputs(repo) == before


@pytest.mark.security
def test_an_existing_environment_marker_check_failure_keeps_safe_excluded_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch, target="vendor/pins.data")
    marker = repo / "vendor" / "pyvenv.cfg"
    original_exists = Path.exists

    def unavailable_marker(path: Path, *args: Any, **kwargs: Any) -> bool:
        if path == marker:
            raise PermissionError(f"controlled marker failure: {marker}")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", unavailable_marker)
    before = _inputs(repo)

    result, report = _audit()

    assert _findings(report) == [_excluded_finding(("vendor/pins.data",))]
    assert "scan: vendor: cannot inspect environment marker; skipped\n" in result.stderr
    assert "scan: requirements.txt:2: include unreadable\n" in result.stderr
    assert str(repo) not in result.stdout + result.stderr
    assert "controlled marker failure" not in result.stdout + result.stderr
    assert _inputs(repo) == before


def _symlink_or_skip(alias: Path, target: Path) -> None:
    try:
        alias.symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"filesystem cannot create the required file symlink: {type(exc).__name__}")


@pytest.mark.security
@pytest.mark.parametrize("destination", ["excluded", "eligible", "outside"])
def test_include_aliases_retain_candidate_and_physical_read_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, destination: str
) -> None:
    repo = _project(tmp_path, monkeypatch, target="alias.data", body=None)
    target = (
        repo / "build" / "pins.data"
        if destination == "excluded"
        else repo / "pins.data"
        if destination == "eligible"
        else tmp_path / "outside.data"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("torch==2.5.1\n", encoding="utf-8")
    _symlink_or_skip(repo / "alias.data", target)
    before = _inputs(repo)
    outside_before = target.read_bytes()

    result, report = _audit()

    finding = _findings(report)
    if destination == "excluded":
        assert finding == [_excluded_finding(("alias.data",))]
    elif destination == "eligible":
        assert len(finding) == 1
        assert finding[0]["status"] == "pass"
        assert finding[0]["severity"] == "PASS"
        assert result.stderr == ""
    else:
        assert len(finding) == 1
        assert finding[0]["status"] == "skipped"
        assert finding[0]["severity"] == "INFO"
        assert finding[0]["message"] == (
            "torch is used; a dependency declaration body could not be read or parsed, "
            "so missing pin evidence is not established"
        )
        assert [(item["path"], item["note"]) for item in finding[0]["evidence"]] == [
            ("requirements.txt", "declared as >=2.5.1"),
            ("alias.data", "torch possible exact declaration unverified"),
        ]
        assert "path resolves outside project root" in result.stderr
    assert str(tmp_path) not in result.stdout + result.stderr
    assert _inputs(repo) == before
    assert target.read_bytes() == outside_before


def test_a_readable_nonexact_include_keeps_the_existing_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch, target="pins.data", body="torch>=2\n")
    before = _inputs(repo)

    result, report = _audit()

    finding = _findings(report)
    assert len(finding) == 1
    assert (finding[0]["status"], finding[0]["severity"]) == ("fail", "WARNING")
    assert finding[0]["message"].startswith("torch is used but not pinned to an exact version ")
    assert finding[0]["evidence"] == [_declaration_evidence()]
    assert result.stderr == ""
    assert _inputs(repo) == before


@pytest.mark.parametrize("failure", ["missing", "binary", "oversize"])
def test_actual_eligible_body_failures_keep_the_existing_declaration_failure_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    body = (
        None
        if failure == "missing"
        else b"torch==2.5.1\x00"
        if failure == "binary"
        else b"#" * (512 * 1024 + 1)
    )
    repo = _project(tmp_path, monkeypatch, target="pins.data", body=body)
    before = _inputs(repo)

    result, report = _audit()

    finding = _findings(report)
    assert len(finding) == 1
    assert (finding[0]["status"], finding[0]["severity"]) == ("skipped", "INFO")
    assert finding[0]["message"] == (
        "torch is used; a dependency declaration body could not be read or parsed, "
        "so missing pin evidence is not established"
    )
    assert [(item["path"], item["note"]) for item in finding[0]["evidence"]] == [
        ("requirements.txt", "declared as >=2.5.1"),
        ("pins.data", "torch possible exact declaration unverified"),
    ]
    assert "scan: requirements.txt:2: include unreadable\n" in result.stderr
    assert str(repo) not in result.stdout + result.stderr
    assert _inputs(repo) == before


def test_unsupported_includes_without_a_normalized_target_do_not_gain_exclusion_credit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch, body=None)
    _write(
        repo,
        "requirements.txt",
        "torch>=2.5.1\n-r\n-r https://example.invalid/pins.txt\n-r ../outside.data\n"
        "-r /synthetic-absolute.data\n",
    )
    before = _inputs(repo)

    result, report = _audit()

    finding = _findings(report)
    assert len(finding) == 1
    assert (finding[0]["status"], finding[0]["severity"]) == ("fail", "WARNING")
    assert finding[0]["message"].startswith("torch is used but not pinned to an exact version ")
    assert finding[0]["evidence"] == [_declaration_evidence()]
    assert set(result.stderr.splitlines()) == {
        "scan: requirements.txt:2: include malformed",
        "scan: requirements.txt:3: include unsupported syntax",
        "scan: requirements.txt:4: include unreadable",
        "scan: requirements.txt:5: include unreadable",
    }
    assert _inputs(repo) == before


def _chain(repo: Path, length: int, target: str) -> None:
    _write(repo, "requirements.txt", "torch>=2.5.1\n-r chain/1.data\n")
    for index in range(1, length + 1):
        child = f"{index + 1}.data" if index < length else "../" + target
        _write(repo, f"chain/{index}.data", f"-r {child}\n")


@pytest.mark.parametrize("length", [9, 10])
def test_only_actually_reached_excluded_targets_use_the_new_branch_at_the_depth_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, length: int
) -> None:
    repo = _project(tmp_path, monkeypatch, target="build/pins.data")
    _chain(repo, length, "build/pins.data")
    before = _inputs(repo)

    result, report = _audit()

    if length == 9:
        assert _findings(report) == [_excluded_finding(("build/pins.data",))]
        assert "scan: chain/9.data:1: include unreadable\n" in result.stderr
    else:
        finding = _findings(report)
        assert len(finding) == 1
        assert (finding[0]["status"], finding[0]["severity"]) == ("skipped", "INFO")
        assert finding[0]["message"] == (
            "torch is used; a supported requirements include was not expanded within the depth "
            "budget, so missing pin evidence is not established"
        )
        assert [(item["path"], item["note"]) for item in finding[0]["evidence"]] == [
            ("requirements.txt", "declared as >=2.5.1"),
            ("build/pins.data", "torch include target unexpanded at the depth limit"),
        ]
        assert "scan: chain/10.data:1: include depth limit\n" in result.stderr
    assert _inputs(repo) == before


def test_an_existing_depth_frontier_finding_wins_without_lower_priority_exclusion_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch, target="build/pins.data")
    _chain(repo, 10, "frontier.data")
    _write(repo, "frontier.data", "torch==2.5.1\n")
    before = _inputs(repo)

    first_result, first = _audit()

    assert _inputs(repo) == before
    original = _findings(first)
    assert len(original) == 1
    assert original[0]["message"] == (
        "torch is used; a supported requirements include was not expanded within the depth "
        "budget, so missing pin evidence is not established"
    )
    assert [item["path"] for item in original[0]["evidence"]] == [
        "requirements.txt",
        "frontier.data",
    ]
    _write(repo, "requirements.txt", "torch>=2.5.1\n-r chain/1.data\n-r build/pins.data\n")
    changed = _inputs(repo)

    second_result, second = _audit()

    assert _findings(second) == original
    assert "include depth limit" in first_result.stderr
    assert "include unreadable" in second_result.stderr
    assert _inputs(repo) == changed


def test_a_later_shallow_root_replaces_the_missing_frontier_with_actual_excluded_target_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch, target="build/pins.data")
    _chain(repo, 10, "build/pins.data")
    _write(repo, "z/requirements-extra.txt", "-r ../chain/10.data\n")
    before = _inputs(repo)

    result, report = _audit()

    assert _findings(report) == [_excluded_finding(("build/pins.data",))]
    assert "scan: chain/10.data:1: include depth limit\n" in result.stderr
    assert "include unreadable" in result.stderr
    assert _inputs(repo) == before


def test_a_root_rejected_after_listing_without_an_include_edge_does_not_create_global_skip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch)
    _write(repo, "requirements.txt", "torch>=2.5.1\n")
    _write(repo, "z/requirements.txt", "torch==2.5.1\n")
    marker = repo / "z" / "pyvenv.cfg"
    marker_body = b"home = synthetic-environment\n"
    original_open = Path.open

    def create_marker_before_body_read(path: Path, *args: Any, **kwargs: Any) -> Any:
        if path == repo / "requirements.txt" and not marker.exists():
            marker.write_bytes(marker_body)
        return original_open(path, *args, **kwargs)

    before = _inputs(repo)
    # A separate filesystem actor changes eligibility after listing, without an include edge.
    monkeypatch.setattr(Path, "open", create_marker_before_body_read)

    result, report = _audit()

    finding = _findings(report)
    assert len(finding) == 1
    assert (finding[0]["status"], finding[0]["severity"]) == ("fail", "WARNING")
    assert finding[0]["message"].startswith("torch is used but not pinned to an exact version ")
    assert finding[0]["evidence"] == [_declaration_evidence()]
    assert "scan: z/requirements.txt:0: unreadable\n" in result.stderr
    assert _inputs(repo) == {**before, "z/pyvenv.cfg": marker_body}


@pytest.mark.parametrize("credit", ["exact-declaration", "requirements-lock", "associated-lock"])
def test_existing_positive_credit_wins_over_excluded_targets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credit: str
) -> None:
    repo = _project(tmp_path, monkeypatch)
    if credit == "exact-declaration":
        _write(repo, "requirements.txt", "torch==2.5.1\n-r build/pins.txt\n")
    elif credit == "requirements-lock":
        _write(repo, "requirements-locked.txt", "torch==2.5.1\n")
    else:
        _write(
            repo, "pyproject.toml", '[project]\nname = "research"\ndependencies = ["torch>=2"]\n'
        )
        _write(repo, "uv.lock", '[[package]]\nname = "torch"\nversion = "2.5.1"\n')
    before = _inputs(repo)

    result, report = _audit()

    findings = _findings(report)
    assert len(findings) == 1
    assert (findings[0]["status"], findings[0]["severity"]) == ("pass", "PASS")
    assert (
        findings[0]["message"]
        == "Every LLM-critical dependency in use is pinned to an exact version."
    )
    assert findings[0]["evidence"] == []
    assert "scan: requirements.txt:2: include unreadable\n" in result.stderr
    assert _inputs(repo) == before


def _python_gap(repo: Path) -> None:
    for index in range(501):
        _write(repo, f"sources/n{index:03}.py", "pass\n")


@pytest.mark.parametrize(
    "prior", ["failed-format-lock", "invalid-format-lock", "python-gap-lock", "failed-declaration"]
)
def test_existing_skip_branches_preserve_their_entire_finding_when_an_excluded_edge_is_added(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, prior: str
) -> None:
    repo = _project(tmp_path, monkeypatch)
    _write(repo, "requirements.txt", "torch>=2.5.1\n")
    if prior in {"failed-format-lock", "invalid-format-lock"}:
        _write(
            repo, "pyproject.toml", '[project]\nname = "research"\ndependencies = ["torch>=2"]\n'
        )
        _write(repo, "uv.lock", "[broken\n" if prior == "failed-format-lock" else "package = 42\n")
        expected_message = (
            "torch is used; an associated format lock could not be read or parsed, "
            "so missing pin evidence is not established"
        )
    elif prior == "python-gap-lock":
        _write(repo, "uv.lock", '[[package]]\nname = "torch"\nversion = "2.5.1"\n')
        _python_gap(repo)
        expected_message = (
            "torch is used; Python analysis is incomplete or unavailable and a captured "
            "format lock lists the package, so missing pin evidence is not established"
        )
    else:
        _write(repo, "requirements.txt", "torch>=2.5.1\n-r missing.data\n")
        expected_message = (
            "torch is used; a dependency declaration body could not be read or parsed, "
            "so missing pin evidence is not established"
        )
    before = _inputs(repo)

    _, first = _audit()

    assert _inputs(repo) == before
    original = _findings(first)
    assert len(original) == 1
    assert (original[0]["status"], original[0]["severity"]) == ("skipped", "INFO")
    assert original[0]["message"] == expected_message
    _write(
        repo,
        "requirements.txt",
        (repo / "requirements.txt").read_text(encoding="utf-8") + "-r build/pins.txt\n",
    )
    changed = _inputs(repo)

    result, second = _audit()

    assert _findings(second) == original
    assert "include unreadable" in result.stderr
    assert _inputs(repo) == changed


def test_an_excluded_target_does_not_infer_use_of_its_hidden_critical_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch)
    _write(repo, "requirements.txt", "unrelated>=1\n-r build/pins.txt\n")
    before = _inputs(repo)

    _, report = _audit()

    findings = _findings(report)
    assert len(findings) == 1
    assert (findings[0]["status"], findings[0]["severity"]) == ("skipped", "INFO")
    assert findings[0]["message"] == "no LLM-critical package is declared or imported"
    assert findings[0]["evidence"] == []
    assert _inputs(repo) == before


def test_all_credited_packages_keep_the_existing_python_gap_empty_result_veto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch)
    _write(repo, "requirements.txt", "torch==2.5.1\n-r build/pins.txt\n")
    _python_gap(repo)
    before = _inputs(repo)

    result, report = _audit()

    findings = _findings(report)
    assert len(findings) == 1
    assert (findings[0]["status"], findings[0]["severity"]) == ("skipped", "INFO")
    assert findings[0]["message"] == (
        "Python candidate analysis incomplete: parsed 500 of 501 candidate files; "
        "selected 500 (limit 500); no rule-wide PASS is established."
    )
    assert findings[0]["evidence"] == []
    assert result.stderr.count("scan: Python analysis incomplete:") == 1
    assert _inputs(repo) == before


def _isolated_core(repo: Path, severity: str, *, independent_warning: bool = False) -> None:
    rules = ["env.llm_critical_deps_pinned"]
    if independent_warning:
        rules.append("env.python_version_declared")
    _write(
        repo,
        ".reprollm/profiles/core.yaml",
        yaml.safe_dump(
            {
                "schema_version": 1,
                "name": "core",
                "description": "Filtered include public CLI validation.",
                "rules": rules,
                "severity_overrides": {"env.llm_critical_deps_pinned": severity},
            }
        ),
    )


@pytest.mark.parametrize("severity", ["WARNING", "CRITICAL"])
def test_exclusion_skip_keeps_fail_only_overrides_thresholds_and_text_visibility(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, severity: str
) -> None:
    repo = _project(tmp_path, monkeypatch)
    _isolated_core(repo, severity)
    before = _inputs(repo)
    reports = []
    for threshold in ["warning", "critical", "never"]:
        result = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", threshold])
        assert result.exit_code == 0, result.output
        assert result.stderr == ""
        report = json.loads(result.stdout)
        assert _findings(report) == [_excluded_finding(("build/pins.txt",))]
        assert report["summary"] == {
            "critical": 0,
            "warning": 0,
            "info": 0,
            "pass": 0,
            "suppressed": 0,
            "skipped": 1,
        }
        report.pop("generated_at")
        reports.append(report)
    assert reports[0] == reports[1] == reports[2]
    default = runner.invoke(app, ["audit", ".", "--no-color", "--fail-on", "warning"])
    shown = runner.invoke(
        app, ["audit", ".", "--no-color", "--show-skipped", "--fail-on", "warning"]
    )
    message = _excluded_finding(("build/pins.txt",))["message"]
    assert default.exit_code == shown.exit_code == 0
    assert default.stderr == shown.stderr == ""
    assert "Findings: PASS" in default.stdout
    assert message not in default.stdout
    assert "skipped: " + message in shown.stdout
    assert _inputs(repo) == before


def test_an_independent_warning_still_fails_and_suppression_retains_exclusion_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch)
    _isolated_core(repo, "CRITICAL", independent_warning=True)
    before = _inputs(repo)
    warning = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "warning"])
    critical = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "critical"])
    assert warning.exit_code == 1, warning.output
    assert critical.exit_code == 0, critical.output
    assert warning.stderr == critical.stderr == ""
    report = json.loads(warning.stdout)
    assert _findings(report) == [_excluded_finding(("build/pins.txt",))]
    assert [
        (finding["rule_id"], finding["severity"])
        for finding in report["findings"]
        if finding["status"] == "fail"
    ] == [("env.python_version_declared", "WARNING")]
    assert _inputs(repo) == before
    _write(
        repo,
        ".reprollm/config.yaml",
        "schema_version: 1\naudit:\n  ignore:\n"
        "    - rule: env.llm_critical_deps_pinned\n"
        "      reason: Reviewed excluded include source.\n",
    )
    changed = _inputs(repo)
    ignored = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "warning"])
    assert ignored.exit_code == 1, ignored.output
    assert ignored.stderr == ""
    suppressed = _findings(json.loads(ignored.stdout))
    assert len(suppressed) == 1
    assert (suppressed[0]["status"], suppressed[0]["severity"]) == ("suppressed", "INFO")
    assert suppressed[0]["message"] == _excluded_finding(("build/pins.txt",))["message"]
    assert suppressed[0]["suppressed_reason"] == "Reviewed excluded include source."
    assert suppressed[0]["evidence"][:-1] == _excluded_finding(("build/pins.txt",))["evidence"]
    assert suppressed[0]["evidence"][-1]["path"] == ".reprollm/config.yaml"
    assert suppressed[0]["evidence"][-1]["note"] == (
        "suppressed: original severity INFO; reason: Reviewed excluded include source."
    )
    assert _inputs(repo) == changed


def test_init_task_listing_and_default_export_retain_inventory_and_owned_artifact_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _project(tmp_path, monkeypatch)
    _isolated_core(repo, "WARNING")
    _write(repo, "run.sh", "inspect eval tasks.py\n")
    _write(
        repo,
        "tasks.py",
        "from inspect_ai import task\n@task\ndef zeta():\n    return None\n"
        "@task\ndef alpha():\n    return None\n",
    )
    before = _inputs(repo)
    listed = runner.invoke(app, ["init", ".", "--list-tasks"])
    assert listed.exit_code == 0, listed.output
    assert listed.stdout == "alpha\nzeta\n"
    assert listed.stderr == ""
    assert _inputs(repo) == before
    initialized = runner.invoke(app, ["init", "."])
    assert initialized.exit_code == 0, initialized.output
    assert initialized.stderr == ""
    assert {name: _inputs(repo)[name] for name in before} == before
    assert set(_inputs(repo)) - set(before) == {
        "reprollm.yaml",
        ".reprollm/config.yaml",
        ".reprollm/project-rules.yaml",
    }
    manifest_bytes = (repo / "reprollm.yaml").read_bytes()
    manifest = yaml.safe_load(manifest_bytes)
    assert manifest["experiment"]["profiles"] == ["evaluation"]
    assert manifest["evaluation"]["metrics"] == []
    result, report = _audit()
    findings = _findings(report)
    assert len(findings) == 2
    for package, finding in zip(["inspect_ai", "torch"], findings, strict=True):
        assert (finding["status"], finding["severity"], finding["level"]) == ("skipped", "INFO", 1)
        expected = _excluded_finding(("build/pins.txt",), package=package)
        assert finding["message"] == expected["message"]
        assert finding["evidence"][-1] == expected["evidence"][-1]
    assert findings[0]["evidence"][0] == {
        "kind": "file",
        "path": "tasks.py",
        "field": None,
        "line": 1,
        "value": None,
        "expected": None,
        "note": "imported",
    }
    assert findings[1]["evidence"][0] == _declaration_evidence()
    assert "scan: requirements.txt:2: include unreadable\n" in result.stderr
    ready = _inputs(repo)
    exported = runner.invoke(app, ["export", "."])
    assert exported.exit_code == 0, exported.output
    assert exported.stderr == ""
    document = repo / "REPRODUCIBILITY.md"
    body = document.read_bytes()
    text = body.decode("utf-8")
    assert "## Audit summary" in text
    assert "No audit was embedded" not in text
    assert _excluded_finding(("build/pins.txt",))["message"] not in text
    assert str(repo) not in text
    document.unlink()
    assert _inputs(repo) == ready
    repeated = runner.invoke(app, ["export", "."])
    assert repeated.exit_code == 0, repeated.output
    assert repeated.stderr == ""
    assert document.read_bytes() == body
    document.unlink()
    assert _inputs(repo) == ready
    forced = runner.invoke(app, ["init", ".", "--force"])
    assert forced.exit_code == 0, forced.output
    assert forced.stderr == ""
    assert (repo / "reprollm.yaml").read_bytes() == manifest_bytes
    assert {name: _inputs(repo)[name] for name in before} == before
