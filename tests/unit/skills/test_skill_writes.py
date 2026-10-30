"""SK14: native configuration artifacts with guarded writes and explicit intent."""

from __future__ import annotations

import dataclasses
import hashlib
import html
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/reprollm/scripts"))
import skill_runtime as runtime  # noqa: E402
import skill_writes as writes  # noqa: E402
from skill_request import (  # noqa: E402
    Grants,
    Reply,
    Request,
    RequestError,
    ResponseOptions,
    encode_reply,
    parse_request,
    required_grants,
)
from skill_writes import execute_write  # noqa: E402


def request(root: Path, action: str = "init", *, write: bool = True, grants=None, **options):
    return Request(action, str(root), options, Grants(write=write, **(grants or {})))


def call(root: Path, state: Path, action: str = "init", *, write=True, grants=None, **options):
    return execute_write(
        request(root, action, write=write, grants=grants, **options),
        root=root,
        state_home=state,
        identity="fixed-test-helper-identity",
        cli_runner=runtime.invoke_cli,
        source_signature=runtime.input_signature,
    )


def inventory(root: Path):
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


@pytest.mark.parametrize("failure", ["chmod", "fsync"])
def test_owned_marker_failure_leaves_no_poisoned_state_and_retry_succeeds(
    tmp_path, monkeypatch, failure
):
    state = tmp_path / "owned"
    original = getattr(writes.os, failure)

    def unavailable(*a, **k):
        raise OSError("synthetic marker preparation failure")

    monkeypatch.setattr(writes.os, failure, unavailable)
    with pytest.raises(OSError):
        writes._owned_state(state)
    assert not (state / "owner.json").exists() and list(state.iterdir()) == []
    monkeypatch.setattr(writes.os, failure, original)
    assert writes._owned_state(state) == state.resolve()
    assert json.loads((state / "owner.json").read_bytes()) == writes._OWNER
    assert sorted(p.name for p in state.iterdir()) == ["locks", "owner.json", "staging"]


@pytest.mark.parametrize("competitor", ["owned", "foreign", "symlink"])
def test_owned_marker_exclusive_publication_preserves_competitor(tmp_path, monkeypatch, competitor):
    state = tmp_path / "owned"
    original = writes.os.link
    foreign = tmp_path / "foreign-marker"
    foreign.write_text("foreign private marker\n")

    def publish(source, target):
        target = Path(target)
        if target.name == "owner.json":
            assert json.loads(Path(source).read_bytes()) == writes._OWNER
            if competitor == "owned":
                target.write_text(json.dumps(writes._OWNER))
            elif competitor == "foreign":
                target.write_text("foreign private marker\n")
            else:
                try:
                    target.symlink_to(foreign)
                except OSError:
                    pytest.skip("File symlinks unavailable")
        return original(source, target)

    monkeypatch.setattr(writes.os, "link", publish)
    if competitor == "owned":
        assert writes._owned_state(state) == state.resolve()
        assert json.loads((state / "owner.json").read_bytes()) == writes._OWNER
    else:
        with pytest.raises(writes.WriteError, match="ownership_required"):
            writes._owned_state(state)
        assert (state / "owner.json").read_text() == "foreign private marker\n"
        assert (state / "owner.json").is_symlink() == (competitor == "symlink")
    assert not list(state.glob(".owner-*.tmp"))
    assert foreign.read_text() == "foreign private marker\n"


def test_concurrent_first_state_initialization_keeps_one_complete_marker(tmp_path, monkeypatch):
    state = tmp_path / "owned"
    barrier = threading.Barrier(2)
    original = writes.tempfile.mkstemp

    def prepare(*a, **k):
        barrier.wait(timeout=5)
        return original(*a, **k)

    monkeypatch.setattr(writes.tempfile, "mkstemp", prepare)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: writes._owned_state(state), range(2)))
    assert results == [state.resolve(), state.resolve()]
    assert json.loads((state / "owner.json").read_bytes()) == writes._OWNER
    assert sorted(p.name for p in state.iterdir()) == ["locks", "owner.json", "staging"]


@pytest.mark.parametrize("action", ["init", "export", "schema.export"])
def test_parsed_preview_needs_no_write_but_apply_does(tmp_path, action):
    payload = {
        "schema_version": 1,
        "action": action,
        "project": str(tmp_path),
        "options": {"preview": True},
        "grants": {"plan_hash": "a" * 64},
    }
    preview = parse_request(payload)
    assert not required_grants(preview) and preview.grants.plan_hash == "a" * 64
    applied = dataclasses.replace(preview, options={"preview": False})
    assert required_grants(applied) == frozenset({"write"})
    assert parse_request({**payload, "grants": {"plan_hash": None}}).grants.plan_hash is None


@pytest.mark.parametrize("value", ["", "a" * 63, "A" * 64, 1, False, []])
def test_parsed_plan_hash_is_strict(value):
    with pytest.raises(RequestError):
        parse_request({"schema_version": 1, "action": "init", "grants": {"plan_hash": value}})


@pytest.mark.parametrize("value", [1, "true", None, []])
def test_preview_requires_actual_boolean(value):
    with pytest.raises(RequestError):
        parse_request({"schema_version": 1, "action": "init", "options": {"preview": value}})


def test_parsed_runtime_init_can_preview_then_apply_without_new_approval(tmp_path):
    root = tmp_path / "experiment"
    root.mkdir()
    req = parse_request(
        {
            "schema_version": 1,
            "action": "init",
            "project": str(root),
            "options": {"preview": True, "profiles": ["inference"], "command": "python eval.py"},
        }
    )
    first = runtime.execute(req, cache_home=tmp_path / "helper/responses")
    assert first.invocation == "handled_result" and first.data["phase"] == "prepared"
    assert inventory(root) == {} and first.data["missing_required_fields"]
    req = dataclasses.replace(
        req,
        options={**req.options, "preview": False},
        grants=Grants(write=True, plan_hash=first.data["plan_hash"]),
    )
    applied = runtime.execute(req, cache_home=tmp_path / "helper/responses")
    assert applied.invocation == "handled_result" and applied.data["phase"] == "applied"
    assert not applied.needs_authorization and (root / "reprollm.yaml").is_file()


def test_write_reply_structure_is_stable_when_identity_matches_field_names(tmp_path, monkeypatch):
    root = tmp_path / "experiment"
    root.mkdir()
    monkeypatch.setattr(runtime.getpass, "getuser", lambda: "phase")
    monkeypatch.setattr(runtime.socket, "gethostname", lambda: "schema_count")
    reply = runtime.execute(
        request(root, "schema.export"), cache_home=tmp_path / "helper/responses"
    )
    assert reply.invocation == "handled_result" and reply.data["phase"] == "applied"
    assert reply.data["schema_count"] == 10 and len(reply.data["artifacts_written"]) == 10


def test_write_delivery_failure_retains_known_effects_without_raw_names(tmp_path, monkeypatch):
    root = tmp_path / "experiment"
    root.mkdir()

    def unavailable(*args, **kwargs):
        raise OSError("synthetic private delivery failure")

    monkeypatch.setattr(runtime, "_sanitize", unavailable)
    reply = runtime.execute(request(root, profiles=["inference"]), cache_home=tmp_path / "cache")
    assert not reply.complete and (root / "reprollm.yaml").is_file()
    assert reply.cli_exit_code == 0
    assert reply.data == {
        "scope": "incomplete_delivery",
        "artifact_written": True,
        "artifacts_written_count": 3,
        "artifact_publication_attempted": True,
        "safe_to_repeat": False,
    }
    assert "synthetic private" not in json.dumps(reply.as_dict())


def test_reply_budget_fallback_retains_publication_facts():
    reply = Reply(
        "init",
        cli_exit_code=0,
        data={"phase": "applied", "artifacts_written": ["reprollm.yaml"], "body": "x" * 300000},
    )
    final = json.loads(encode_reply(reply))
    assert not final["complete"] and final["cli_exit_code"] == 0
    assert final["data"]["artifact_written"] and final["data"]["artifacts_written_count"] == 1
    assert final["data"]["safe_to_repeat"] is False


def test_large_applied_result_pages_without_replaying_writes(tmp_path, monkeypatch):
    root = tmp_path / "experiment"
    root.mkdir()
    command = "python eval.py --label " + "public-value" * 1000
    req = request(root, profiles=["inference"], command=command)
    monkeypatch.setattr(runtime, "MAX_REPLY_BYTES", 4096)
    reply = runtime.execute(req, cache_home=tmp_path / "helper/responses")
    assert reply.next_cursor and (root / "reprollm.yaml").exists()
    before = inventory(root)
    monkeypatch.setattr(
        writes, "execute_write", lambda *a, **k: pytest.fail("Cursor replayed write")
    )
    fragments = []
    while True:
        assert not reply.complete and reply.data["scope"] == "partial_document"
        fragments.append(reply.data["text"])
        if not reply.next_cursor:
            break
        req = dataclasses.replace(req, response=ResponseOptions(cursor=reply.next_cursor))
        reply = runtime.execute(req, cache_home=tmp_path / "helper/responses")
    restored = json.loads("".join(fragments))
    assert restored["data"]["phase"] == "applied"
    assert restored["data"]["artifacts_written"] == sorted(before)
    assert command in restored["data"]["manifest_text"] and inventory(root) == before


@pytest.mark.parametrize("cursor", ["malformed", "a" * 64 + ":fragment:0"])
def test_forged_write_cursor_cannot_invoke_producer(tmp_path, monkeypatch, cursor):
    root = tmp_path / "experiment"
    root.mkdir()
    req = dataclasses.replace(request(root), response=ResponseOptions(cursor=cursor))
    monkeypatch.setattr(
        writes, "execute_write", lambda *a, **k: pytest.fail("Cursor replayed write")
    )
    result = runtime.execute(req, cache_home=tmp_path / "cache")
    assert result.invocation == "blocked" and not result.complete and inventory(root) == {}


def test_host_write_import_and_about_need_only_standard_library(tmp_path):
    program = (
        "import sys;sys.path.insert(0,sys.argv[1]);import skill_runtime,skill_writes;"
        "from skill_request import dispatch,Request;"
        "r=dispatch(Request('about'),available_actions=skill_runtime.AVAILABLE_ACTIONS);"
        "assert all(x['available'] for x in r.data['actions'] if x['action'] in "
        "{'init','export','schema.export'});"
        "assert not any(n=='reprollm' or n.startswith('reprollm.') or "
        "n=='pydantic' or n.startswith('pydantic.') for n in sys.modules)"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-S", "-c", program, str(ROOT / "skills/reprollm/scripts")],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0 and not result.stdout and not result.stderr
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("failure", ["timeout", "protocol", "oversized"])
def test_lost_write_worker_reply_reports_unknown_and_never_repeats(tmp_path, monkeypatch, failure):
    import bootstrap
    import install_catalog
    from tests.unit.skills.test_bootstrap import FakeBackend, candidate, source_blob

    blob = source_blob()
    selected = dataclasses.replace(
        candidate("write-worker", blob), capabilities=("contextual_word_scan",)
    )
    catalog = install_catalog.Catalog(1, selected.id, (selected,))
    manager = bootstrap.Bootstrap(tmp_path / "owned", catalog, backend=FakeBackend(blob))
    manager.ensure()
    monkeypatch.setattr(bootstrap, "Bootstrap", lambda *a: manager)
    monkeypatch.setattr(install_catalog, "load_catalog", lambda *a: catalog)
    root = tmp_path / "experiment"
    root.mkdir()
    calls = []

    def process(argv, **kwargs):
        calls.append(argv)
        (root / "reprollm.yaml").write_text("written before lost reply\n")
        if failure == "timeout":
            raise subprocess.TimeoutExpired(argv, 120)
        raw = b"x" * 300000 if failure == "oversized" else b"not-json"
        return subprocess.CompletedProcess(argv, 0, raw, b"")

    monkeypatch.setattr(runtime.subprocess, "run", process)
    reply = runtime.RuntimeExecutor(manager.home)(request(root))
    assert len(calls) == 1 and reply.invocation in {"blocked", "internal_error"}
    assert reply.cli_exit_code is None and not reply.complete
    assert reply.data == {
        "scope": "unknown_completion",
        "artifact_publication_unknown": True,
        "safe_to_repeat": False,
    }
    assert (root / "reprollm.yaml").read_text() == "written before lost reply\n"


def test_preview_is_complete_native_scaffold_without_project_writes(tmp_path):
    root = tmp_path / "研究 project"
    root.mkdir()
    before = inventory(root)
    reply = call(root, tmp_path / "helper", write=False, profiles=["inference"], preview=True)
    assert reply.invocation == "handled_result" and reply.cli_exit_code == 0
    assert reply.data["phase"] == "prepared" and reply.data["artifacts_written"] == []
    assert reply.data["missing_required_fields"] == [
        "models.primary.id",
        "inference.backend",
        "generation.temperature",
        "generation.max_tokens",
    ]
    assert inventory(root) == before
    assert "# TODO" in reply.data["manifest_text"]


def test_already_authorized_new_init_completes_without_extra_approval(tmp_path):
    root = tmp_path / "experiment"
    root.mkdir()
    reply = call(
        root,
        tmp_path / "helper",
        profiles=["inference"],
        answers={
            "models.primary.id": "org/model",
            "inference.backend": "other",
            "generation.temperature": "0",
            "generation.max_tokens": "32",
        },
    )
    assert reply.invocation == "handled_result" and not reply.needs_authorization
    assert reply.data["phase"] == "applied"
    assert set(inventory(root)) == {
        "reprollm.yaml",
        ".reprollm/config.yaml",
        ".reprollm/project-rules.yaml",
    }
    from reprollm.core.yaml_io import load_manifest

    manifest = load_manifest(root / "reprollm.yaml")
    assert manifest.generation.temperature == 0 and manifest.generation.max_tokens == 32
    assert reply.data["missing_required_fields"] == []


@pytest.mark.parametrize(
    "field,answer",
    [
        ("inference.backend", "wrong-backend-synthetic"),
        ("generation.temperature", "NaN"),
        ("generation.max_tokens", "0"),
    ],
)
def test_invalid_later_answer_preserves_accepted_answer_and_writes_nothing(tmp_path, field, answer):
    root = tmp_path / "experiment"
    root.mkdir()
    reply = call(
        root,
        tmp_path / "helper",
        profiles=["inference"],
        answers={"models.primary.id": "org/model", field: answer},
    )
    assert reply.invocation == "user_error" and reply.needs_input
    assert reply.data["accepted_answers"]["models.primary.id"] == "org/model"
    assert reply.data["invalid_field"] == field and inventory(root) == {}
    assert answer not in json.dumps(reply.diagnostics) or answer == "0"


@pytest.mark.parametrize("field", ["project.name", "evaluation.metrics", "arbitrary.new_field"])
def test_answers_do_not_create_a_generic_manifest_editor(tmp_path, field):
    root = tmp_path / "experiment"
    root.mkdir()
    reply = call(root, tmp_path / "helper", profiles=["inference"], answers={field: "invented"})
    assert reply.invocation == "user_error" and inventory(root) == {}


def test_saved_command_is_literal_and_never_runs(tmp_path):
    root = tmp_path / "experiment"
    root.mkdir()
    command = 'python eval.py --label "with space" ""'
    reply = call(root, tmp_path / "helper", profiles=["inference"], command=command)
    assert reply.invocation == "handled_result"
    from reprollm.core.yaml_io import load_manifest

    assert load_manifest(root / "reprollm.yaml").execution.command == command
    assert not (root / ".reprollm/runs").exists()


def test_force_preserves_auxiliary_bytes_and_modes(tmp_path):
    root = tmp_path / "experiment"
    root.mkdir()
    first = call(root, tmp_path / "helper", profiles=["inference"])
    assert first.invocation == "handled_result"
    files = [root / ".reprollm/config.yaml", root / ".reprollm/project-rules.yaml"]
    original = [(p.read_bytes(), p.stat().st_mode) for p in files]
    manifest = root / "reprollm.yaml"
    manifest.chmod(0o640)
    original_manifest_mode = manifest.stat().st_mode & 0o777
    reply = call(
        root,
        tmp_path / "helper",
        profiles=["inference"],
        force=True,
        grants={
            "expected_hashes": {"reprollm.yaml": hashlib.sha256(manifest.read_bytes()).hexdigest()}
        },
        command="python eval.py",
    )
    assert reply.invocation == "handled_result"
    assert [(p.read_bytes(), p.stat().st_mode) for p in files] == original
    assert manifest.stat().st_mode & 0o777 == original_manifest_mode


def test_external_preview_plan_rejects_new_inputs(tmp_path):
    root = tmp_path / "experiment"
    root.mkdir()
    preview = call(root, tmp_path / "helper", profiles=["inference"], preview=True, write=False)
    (root / "model.py").write_text("from transformers import AutoModel\n")
    before = inventory(root)
    reply = call(
        root,
        tmp_path / "helper",
        profiles=["inference"],
        grants={"plan_hash": preview.data["plan_hash"]},
    )
    assert reply.invocation == "blocked" and not reply.complete
    assert inventory(root) == before


def test_schema_output_matches_all_ten_native_committed_documents(tmp_path):
    root = tmp_path / "experiment"
    root.mkdir()
    reference = tmp_path / "native-schemas"
    native = runtime.invoke_cli(["schema", "export", "--out", str(reference)], root)
    assert native.exit_code == 0
    reply = call(root, tmp_path / "helper", "schema.export")
    assert reply.invocation == "handled_result"
    actual = root / "schemas"
    assert len(list(actual.glob("*.schema.json"))) == 10
    for reference in sorted((ROOT / "schemas").glob("*.schema.json")):
        emitted = actual / reference.name
        assert emitted.read_bytes() == (tmp_path / "native-schemas" / reference.name).read_bytes()
        # Native schema export uses the platform's newline translation; the
        # committed canonical text is LF, matching its existing freshness gate.
        assert emitted.read_text(encoding="utf-8") == reference.read_text(encoding="utf-8")


def test_existing_schema_requires_exact_authorized_hashes(tmp_path):
    root = tmp_path / "experiment"
    root.mkdir()
    first = call(root, tmp_path / "helper", "schema.export")
    assert first.invocation == "handled_result"
    before = inventory(root)
    denied = call(root, tmp_path / "helper", "schema.export")
    assert denied.invocation == "blocked" and inventory(root) == before
    expected = {name: digest for name, digest in before.items()}
    (root / "schemas/manifest.schema.json").write_text("external edit\n")
    changed = inventory(root)
    stale = call(root, tmp_path / "helper", "schema.export", grants={"expected_hashes": expected})
    assert stale.invocation == "blocked" and inventory(root) == changed


def task_candidates(root):
    tasks = root / "lm_eval/tasks"
    tasks.mkdir(parents=True)
    for name in ["beta", "alpha"]:
        (tasks / (name + ".yaml")).write_text("task: " + name + "\ndataset_path: org/data\n")


def test_multiple_real_tasks_need_selection_without_forcing_unknown_science_answers(tmp_path):
    root = tmp_path / "experiment"
    root.mkdir()
    task_candidates(root)
    before = inventory(root)
    reply = call(root, tmp_path / "helper", profiles=["safety"])
    assert reply.needs_input and inventory(root) == before
    assert reply.data["task_candidates"] == ["alpha", "beta"]
    assert (
        "choose" in json.dumps(reply.questions).lower()
        or "select" in json.dumps(reply.questions).lower()
    )


def test_explicit_selection_of_all_tasks_continues_with_unknown_values(tmp_path):
    root = tmp_path / "experiment"
    root.mkdir()
    task_candidates(root)
    reply = call(root, tmp_path / "helper", profiles=["safety"], tasks=["beta", "alpha"])
    assert reply.invocation == "handled_result" and not reply.needs_input
    from reprollm.core.yaml_io import load_manifest

    manifest = load_manifest(root / "reprollm.yaml")
    assert [m.name for m in manifest.evaluation.metrics] == ["alpha", "beta"]
    assert manifest.models["primary"].id is None
    assert "models.primary.id" in reply.data["missing_required_fields"]


def test_explicit_empty_task_selection_keeps_native_todo_without_reasking(tmp_path):
    root = tmp_path / "experiment"
    root.mkdir()
    task_candidates(root)
    reply = call(root, tmp_path / "helper", profiles=["safety"], tasks=[])
    assert reply.invocation == "handled_result" and not reply.needs_input
    assert reply.data["task_candidates"] == ["alpha", "beta"]
    assert reply.data["selected_tasks"] == []
    assert "evaluation.metrics" in reply.data["missing_required_fields"]


def test_unrelated_profile_does_not_request_eval_task_selection(tmp_path):
    root = tmp_path / "experiment"
    root.mkdir()
    task_candidates(root)
    reply = call(root, tmp_path / "helper", profiles=["inference"])
    assert reply.invocation == "handled_result" and not reply.needs_input
    assert reply.data["task_candidates"] == ["alpha", "beta"]


def test_validated_numeric_answers_can_be_resubmitted_after_a_later_error(tmp_path):
    from skill_request import parse_request

    root = tmp_path / "experiment"
    root.mkdir()
    failed = call(
        root,
        tmp_path / "helper",
        profiles=["inference"],
        command="python eval.py",
        answers={
            "models.primary.id": "org/model",
            "inference.backend": "other",
            "generation.temperature": "0",
            "generation.max_tokens": "0",
        },
    )
    assert failed.invocation == "user_error" and failed.needs_input
    retained = failed.data["accepted_answers"]
    assert retained["generation.temperature"] == "0"
    assert "execution.command" not in retained
    corrected = parse_request(
        {
            "schema_version": 1,
            "action": "init",
            "project": str(root),
            "options": {
                "profiles": ["inference"],
                "command": "python eval.py",
                "answers": {**retained, "generation.max_tokens": "32"},
            },
            "grants": {"write": True},
        }
    )
    reply = execute_write(corrected, root=root, state_home=tmp_path / "helper", identity="fixed")
    assert reply.invocation == "handled_result"


@pytest.mark.parametrize(
    "answer,command",
    [
        ("python first.py | python second.py", None),
        ("python eval.py --api-key OpaquePrivateCommand123456", None),
        ("python other.py", "python eval.py"),
    ],
)
def test_invalid_command_answer_keeps_prior_fields_for_a_corrected_retry(tmp_path, answer, command):
    from tests.unit.cli.test_init_guidance import _profile

    root = tmp_path / "experiment"
    root.mkdir()
    _profile(root, ["models.primary.id", "execution.command"])
    options = {
        "profiles": ["trial"],
        "answers": {"models.primary.id": "public/model", "execution.command": answer},
    }
    if command is not None:
        options["command"] = command
    before = inventory(root)
    failed = call(root, tmp_path / "helper", **options)
    assert failed.invocation == "user_error" and failed.needs_input
    assert failed.data["accepted_answers"] == {"models.primary.id": "public/model"}
    assert failed.data["invalid_field"] == "execution.command" and inventory(root) == before
    assert answer not in json.dumps(failed.as_dict())
    corrected = call(
        root,
        tmp_path / "helper",
        profiles=["trial"],
        answers={**failed.data["accepted_answers"], "execution.command": "python eval.py"},
        **({"command": command} if command is not None else {}),
    )
    assert corrected.invocation == "handled_result" and not corrected.needs_input


@pytest.mark.parametrize("preview", [True, False])
def test_native_project_name_fallback_review_is_preserved_without_extra_question(tmp_path, preview):
    root = tmp_path / "研究 project"
    root.mkdir()
    reference = tmp_path / "native" / root.name
    reference.mkdir(parents=True)
    native = runtime.invoke_cli(["init", str(reference), "--profiles", "inference"], reference)
    instruction = "Set project.name in reprollm.yaml; init used the safe default 'experiment'."
    assert native.exit_code == 0 and instruction in native.stdout
    reply = runtime.execute(
        request(root, profiles=["inference"], preview=preview, write=not preview),
        cache_home=tmp_path / "helper/responses",
    )
    assert reply.invocation == "handled_result" and not reply.needs_input
    assert reply.data["manifest_text"] == (reference / "reprollm.yaml").read_text()
    assert any(
        item.get("code") == "project_name_defaulted" and instruction in item.get("text", "")
        for item in reply.diagnostics
    )
    assert "models.primary.id" in reply.data["missing_required_fields"]
    assert (root / "reprollm.yaml").exists() == (not preview)


@pytest.mark.parametrize("value", ["true", "alpha: beta", '含空格 "引号"', "[literal]"])
def test_literal_scientific_text_preserves_native_quoting(tmp_path, value):
    from reprollm.core.yaml_io import load_manifest

    root = tmp_path / "experiment"
    root.mkdir()
    reply = call(
        root,
        tmp_path / "helper",
        profiles=["privacy"],
        answers={"models.primary.id": "org/model", "privacy.threat_model": value},
    )
    assert reply.invocation == "handled_result", reply.diagnostics
    assert load_manifest(root / "reprollm.yaml").privacy.threat_model == value
    assert "privacy.mechanism.name" in reply.data["missing_required_fields"]


@pytest.fixture
def export_root(tmp_path, stub_run_cmd):
    from tests.unit.cli.test_export import _assemble

    stub_run_cmd.on("git", returncode=1)
    stub_run_cmd.on("nvidia-smi", returncode=127)
    return _assemble(tmp_path / "fixture", "hf_vllm_eval")


@pytest.mark.parametrize("template", ["default", "neurips", "acl", "acm"])
def test_export_whole_document_matches_native_cli(export_root, tmp_path, template):
    reference = tmp_path / "native.md"
    result = runtime.invoke_cli(
        ["export", str(export_root), "--output", str(reference), "--template", template],
        export_root,
    )
    assert result.exit_code == 0, result.stderr
    reply = call(export_root, tmp_path / "helper", "export", template=template)
    assert reply.invocation == "handled_result", reply.diagnostics
    assert (export_root / "REPRODUCIBILITY.md").read_bytes() == reference.read_bytes()
    assert reply.data["document"].encode("utf-8") == reference.read_bytes()
    assert reply.data["selected_run_id"] == "20260101T000000Z-hf_vll"


@pytest.mark.parametrize("template", ["default", "neurips", "acl", "acm"])
def test_historical_export_keeps_recorded_snapshot_after_current_manifest_changes(
    export_root, tmp_path, template
):
    manifest = export_root / "reprollm.yaml"
    manifest.write_text(manifest.read_text().replace("max_tokens: 2048", "max_tokens: 3072"))
    reference = tmp_path / "native-historical.md"
    native = runtime.invoke_cli(
        ["export", str(export_root), "--output", str(reference), "--template", template],
        export_root,
    )
    assert native.exit_code == 0
    reply = call(export_root, tmp_path / "helper", "export", template=template)
    assert reply.invocation == "handled_result", reply.diagnostics
    assert reply.data["document"].encode("utf-8") == reference.read_bytes()
    assert "2048" in reply.data["document"]


def test_export_preview_does_not_write_and_authorized_old_hash_replaces(export_root, tmp_path):
    target = export_root / "report.md"
    target.write_text("reviewed old report\n")
    before = inventory(export_root)
    preview = call(
        export_root, tmp_path / "helper", "export", output="report.md", preview=True, write=False
    )
    assert preview.invocation == "handled_result" and inventory(export_root) == before
    assert preview.data["artifacts"][0]["approval_required"]
    old = hashlib.sha256(target.read_bytes()).hexdigest()
    applied = call(
        export_root,
        tmp_path / "helper",
        "export",
        output="report.md",
        grants={"plan_hash": preview.data["plan_hash"], "expected_hashes": {"report.md": old}},
    )
    assert applied.invocation == "handled_result", applied.diagnostics
    assert target.read_text() == preview.data["document"]


def test_long_inline_scientific_text_is_not_interpreted_as_a_filesystem_path(export_root, tmp_path):
    import yaml

    manifest = export_root / "reprollm.yaml"
    doc = yaml.safe_load(manifest.read_text())
    doc["privacy"] = {"threat_model": "A" * 5000}
    manifest.write_text(yaml.safe_dump(doc, sort_keys=False))
    reply = call(export_root, tmp_path / "helper", "export")
    assert reply.invocation == "handled_result", reply.diagnostics


@pytest.mark.parametrize("kind", ["manifest", "snapshot", "source", "shell_source"])
def test_export_never_replaces_research_inputs(export_root, tmp_path, kind):
    candidates = {
        "manifest": export_root / "reprollm.yaml",
        "source": export_root / "eval.py",
        "shell_source": export_root / "runner.sh",
        "snapshot": next((export_root / ".reprollm/runs").iterdir()) / "manifest.yaml",
    }
    target = candidates[kind]
    if not target.exists():
        target.write_text("synthetic source\n")
    before = inventory(export_root)
    reply = call(
        export_root,
        tmp_path / "helper",
        "export",
        output=str(target),
        grants={"expected_hashes": {str(target): hashlib.sha256(target.read_bytes()).hexdigest()}},
    )
    assert reply.invocation == "blocked" and inventory(export_root) == before
    assert any(d["code"] == "report_target_is_research_input" for d in reply.diagnostics)


@pytest.mark.parametrize("name", ["large-source.py", "large-source.sh", "large-source-alias"])
def test_research_source_outside_native_static_size_budget_is_still_protected(
    export_root, tmp_path, name
):
    target = export_root / name
    target.write_bytes(b"# Public synthetic scientific source\n" * 70000)
    if name == "large-source-alias":
        try:
            (export_root / "large_scientific_source.py").symlink_to(target)
        except OSError:
            pytest.skip("File symlinks unavailable")
    before = hashlib.sha256(target.read_bytes()).hexdigest()
    assert target.stat().st_size > 2 * 1024 * 1024
    reply = call(
        export_root,
        tmp_path / "helper",
        "export",
        output=name,
        grants={"expected_hashes": {name: before}},
    )
    assert reply.invocation == "blocked"
    assert hashlib.sha256(target.read_bytes()).hexdigest() == before
    assert any(d["code"] == "report_target_is_research_input" for d in reply.diagnostics)


def test_external_export_needs_exact_scope(export_root, tmp_path):
    target = tmp_path / "outside report.md"
    denied = call(export_root, tmp_path / "helper", "export", output=str(target))
    assert denied.invocation == "blocked" and denied.needs_authorization and not target.exists()
    applied = call(
        export_root,
        tmp_path / "helper",
        "export",
        output=str(target),
        grants={"external_paths": (str(target),)},
    )
    assert applied.invocation == "handled_result" and target.exists(), applied.diagnostics
    assert applied.data["artifacts_written"] == [target.name]


@pytest.mark.parametrize("name", ["report-output.json", "report-output.yaml", "README-report.md"])
@pytest.mark.parametrize("external", [False, True])
def test_generated_report_extension_does_not_prevent_exact_authorized_overwrite(
    export_root, tmp_path, name, external
):
    target = (tmp_path if external else export_root) / name
    grants = {"external_paths": (str(target),)} if external else {}
    first = call(export_root, tmp_path / "helper", "export", output=str(target), grants=grants)
    assert first.invocation == "handled_result" and target.is_file()
    old = hashlib.sha256(target.read_bytes()).hexdigest()
    reference = tmp_path / "native-overwrite-reference.md"
    native = runtime.invoke_cli(
        ["export", str(export_root), "--output", str(reference)], export_root
    )
    assert native.exit_code == 0
    again = call(
        export_root,
        tmp_path / "helper",
        "export",
        output=str(target),
        grants={**grants, "expected_hashes": {str(target): old}},
    )
    assert again.invocation == "handled_result" and not again.needs_authorization
    assert target.read_bytes() == reference.read_bytes()


@pytest.mark.parametrize(
    "binding", ["declared", "command", "source_alias", "historical_file", "lock_file"]
)
def test_actual_scientific_inputs_remain_protected_by_resolved_association(
    export_root, tmp_path, binding
):
    import yaml

    if binding == "source_alias":
        target = tmp_path / "external-source"
        target.write_text("print('scientific source')\n")
        try:
            (export_root / "actual_source.py").symlink_to(target)
        except OSError:
            pytest.skip("File symlinks unavailable")
    else:
        target = tmp_path / "report-output.json"
        first = call(
            export_root,
            tmp_path / "helper",
            "export",
            output=str(target),
            grants={"external_paths": (str(target),)},
        )
        assert first.invocation == "handled_result"
        alias = export_root / "actual-input"
        try:
            alias.symlink_to(target)
        except OSError:
            pytest.skip("File symlinks unavailable")
        manifest = export_root / "reprollm.yaml"
        doc = yaml.safe_load(manifest.read_text())
        if binding == "declared":
            doc.setdefault("execution", {})["config_files"] = [alias.name]
        elif binding == "command":
            doc.setdefault("execution", {})["command"] = "python eval.py actual-input"
        elif binding == "historical_file":
            record_path = next((export_root / ".reprollm/runs").glob("*/run.json"))
            record = json.loads(record_path.read_text())
            record.setdefault("files", []).append(
                {
                    "path": alias.name,
                    "sha256": "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest(),
                    "size_bytes": target.stat().st_size,
                    "origin": "declared",
                }
            )
            record_path.write_text(json.dumps(record))
        else:
            lock_path = export_root / "reprollm.lock"
            lock = yaml.safe_load(lock_path.read_text())
            lock.setdefault("files", []).append(
                {
                    "path": alias.name,
                    "sha256": "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest(),
                    "size_bytes": target.stat().st_size,
                }
            )
            lock_path.write_text(yaml.safe_dump(lock, sort_keys=False))
        manifest.write_text(yaml.safe_dump(doc, sort_keys=False))
    before = target.read_bytes()
    reply = call(
        export_root,
        tmp_path / "helper",
        "export",
        output=str(target),
        grants={
            "external_paths": (str(target),),
            "expected_hashes": {str(target): hashlib.sha256(before).hexdigest()},
        },
    )
    assert reply.invocation == "blocked" and target.read_bytes() == before
    assert any(item["code"] == "report_target_is_research_input" for item in reply.diagnostics)


@pytest.mark.parametrize(
    "name,content",
    [
        ("schema-output.json", '{"type":"object","properties":{"privacy":{"type":"string"}}}\n'),
        ("report-output.yaml", "title: Public report template\nsections: []\n"),
        ("README-report.md", "# Public report template\n\nAuthor fills this report.\n"),
    ],
)
def test_unrelated_explicit_report_template_is_not_a_scientific_input(
    export_root, tmp_path, name, content
):
    target = export_root / name
    target.write_text(content)
    before = target.read_bytes()
    reply = call(
        export_root,
        tmp_path / "helper",
        "export",
        output=name,
        grants={"expected_hashes": {name: hashlib.sha256(before).hexdigest()}},
    )
    assert reply.invocation == "handled_result" and target.read_bytes() != before
    assert target.read_text().startswith("# Reproducibility statement — ")


@pytest.mark.parametrize(
    "metadata",
    [
        {"$schema": "https://example.invalid/experiment.schema.json"},
        {
            "$schema": "https://example.invalid/experiment.schema.json",
            "type": "object",
            "properties": {},
        },
        {
            "$schema": "https://example.invalid/experiment.schema.json",
            "type": "object",
            "properties": {},
            "$defs": {},
        },
    ],
)
def test_experiment_instance_schema_metadata_does_not_authorize_config_overwrite(
    export_root, tmp_path, metadata
):
    target = export_root / "config.json"
    target.write_text(
        json.dumps({"epsilon": 8, "lora": {"rank": 8}, "temperature": 0.7, **metadata}),
        encoding="utf-8",
    )
    before = target.read_bytes()
    reply = call(
        export_root,
        tmp_path / "helper",
        "export",
        output=target.name,
        grants={"expected_hashes": {target.name: hashlib.sha256(before).hexdigest()}},
    )
    assert reply.invocation == "blocked"
    assert target.read_bytes() == before
    assert any(item["code"] == "report_target_is_research_input" for item in reply.diagnostics)


def test_actual_generated_json_schema_keeps_explicit_report_overwrite(export_root, tmp_path):
    target = export_root / "schema-output.json"
    target.write_bytes((ROOT / "schemas/manifest.schema.json").read_bytes())
    before = target.read_bytes()
    reply = call(
        export_root,
        tmp_path / "helper",
        "export",
        output=target.name,
        grants={"expected_hashes": {target.name: hashlib.sha256(before).hexdigest()}},
    )
    assert reply.invocation == "handled_result"
    assert target.read_bytes().startswith("# Reproducibility statement — ".encode())


@pytest.mark.parametrize("properties", [{"epsilon": 8}, {"lora": {"rank": 8}}])
def test_experiment_values_in_properties_are_not_schema_definitions(
    export_root, tmp_path, properties
):
    target = export_root / "config.json"
    target.write_text(
        json.dumps(
            {
                "$schema": "https://example.invalid/config.schema.json",
                "type": "object",
                "properties": properties,
            }
        ),
        encoding="utf-8",
    )
    before = target.read_bytes()
    reply = call(
        export_root,
        tmp_path / "helper",
        "export",
        output=target.name,
        grants={"expected_hashes": {target.name: hashlib.sha256(before).hexdigest()}},
    )
    assert reply.invocation == "blocked" and target.read_bytes() == before


@pytest.mark.parametrize(
    "metadata",
    [
        {"dependencies": {"alpha": {"epsilon": 8, "lora": {"rank": 8}}}},
        {"dependentRequired": {"alpha": {"epsilon": 8}}},
        {"allOf": [{"epsilon": 8}]},
        {"description": {"lora": {"rank": 8}}},
    ],
)
def test_schema_container_names_do_not_hide_experiment_values(export_root, tmp_path, metadata):
    target = export_root / "config.json"
    target.write_text(
        json.dumps(
            {
                "$schema": "https://example.invalid/config.schema.json",
                "type": "object",
                "properties": {},
                **metadata,
            }
        ),
        encoding="utf-8",
    )
    before = target.read_bytes()
    reply = call(
        export_root,
        tmp_path / "helper",
        "export",
        output=target.name,
        grants={"expected_hashes": {target.name: hashlib.sha256(before).hexdigest()}},
    )
    assert reply.invocation == "blocked" and target.read_bytes() == before


@pytest.mark.parametrize("position", [0, 1, 2])
def test_init_publication_failure_rolls_back_only_own_created_files(
    tmp_path, monkeypatch, position
):
    root = tmp_path / "experiment"
    root.mkdir()
    original = writes.publish_artifact
    count = 0

    def publish(artifact, published):
        nonlocal count
        if count == position:
            raise OSError("synthetic publication failure")
        count += 1
        original(artifact, published)

    monkeypatch.setattr(writes, "publish_artifact", publish)
    reply = call(root, tmp_path / "helper", profiles=["inference"])
    assert reply.invocation == "blocked" and not reply.complete
    assert inventory(root) == {} and not (root / ".reprollm").exists()
    assert not list(root.glob(".reprollm-skill-*"))


def test_init_rollback_preserves_external_edit_to_new_helper(tmp_path, monkeypatch):
    root = tmp_path / "experiment"
    root.mkdir()
    original = writes.publish_artifact

    def publish(artifact, published):
        if published:
            published[0].artifact.target.write_text("external edit\n")
            raise OSError("synthetic later failure")
        original(artifact, published)

    monkeypatch.setattr(writes, "publish_artifact", publish)
    reply = call(root, tmp_path / "helper", profiles=["inference"])
    assert reply.invocation == "blocked" and not reply.complete
    assert (root / ".reprollm/config.yaml").read_text() == "external edit\n"
    assert not (root / "reprollm.yaml").exists()
    assert reply.data["preserved_changed_targets"] == [".reprollm/config.yaml"]


def test_schema_failure_reports_exact_partial_set(tmp_path, monkeypatch):
    root = tmp_path / "experiment"
    root.mkdir()
    original = writes.publish_artifact

    def publish(artifact, published):
        if len(published) == 6:
            raise OSError("synthetic seventh write failure")
        original(artifact, published)

    monkeypatch.setattr(writes, "publish_artifact", publish)
    reply = call(root, tmp_path / "helper", "schema.export")
    assert reply.invocation == "blocked" and not reply.complete
    assert len(reply.data["artifacts_written"]) == 6
    assert set(reply.data["artifacts_written"]) == set(inventory(root))


def test_new_target_publication_is_exclusive_at_final_link(tmp_path, monkeypatch):
    root = tmp_path / "experiment"
    root.mkdir()
    original = writes.os.link

    def appearing(source, target):
        if Path(target).name != "owner.json":
            Path(target).write_text("external appeared\n")
        original(source, target)

    monkeypatch.setattr(writes.os, "link", appearing)
    reply = call(root, tmp_path / "helper", profiles=["inference"])
    assert reply.invocation == "blocked"
    assert (root / ".reprollm/config.yaml").read_text() == "external appeared\n"
    assert not (root / "reprollm.yaml").exists()


def test_existing_parent_directory_identity_is_guarded(tmp_path):
    root = tmp_path / "experiment"
    parent = root / "reports"
    parent.mkdir(parents=True)
    artifact = writes._artifact(
        request(root), root, parent / "report.md", b"prepared\n", role="report", mode=0o600
    )
    parent.rename(root / "old-reports")
    parent.mkdir()
    with pytest.raises(writes.WriteError, match="parent_changed"):
        writes.publish_artifact(artifact, [])
    assert not (parent / "report.md").exists()


def test_export_alias_retarget_during_render_does_not_publish(export_root, tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    alias = tmp_path / "destination"
    try:
        alias.symlink_to(first, target_is_directory=True)
    except OSError:
        pytest.skip("Directory symlinks are unavailable on this platform.")

    def render(argv, root):
        result = runtime.invoke_cli(argv, root)
        alias.unlink()
        alias.symlink_to(second, target_is_directory=True)
        return result

    payload = request(
        export_root,
        "export",
        output=str(alias / "report.md"),
        grants={"external_paths": (str(alias / "report.md"),)},
    )
    reply = execute_write(
        payload,
        root=export_root,
        state_home=tmp_path / "helper",
        identity="fixed",
        cli_runner=render,
        source_signature=runtime.input_signature,
    )
    assert reply.invocation == "blocked" and not reply.complete
    assert not (first / "report.md").exists() and not (second / "report.md").exists()


@pytest.fixture
def external_record(export_root, tmp_path):
    folder = next((export_root / ".reprollm/runs").iterdir())
    destination = tmp_path / "external-record"
    folder.rename(destination)
    try:
        folder.symlink_to(destination, target_is_directory=True)
    except OSError:
        pytest.skip("Directory symlinks are unavailable on this platform.")
    return destination


def test_external_selected_record_is_not_read_without_exact_authorization(
    export_root, external_record, tmp_path, monkeypatch
):
    from reprollm.cli import export as native_export

    original = native_export.read_run_record
    opened = []

    def read(path):
        opened.append(path)
        return original(path)

    monkeypatch.setattr(native_export, "read_run_record", read)
    reply = call(export_root, tmp_path / "helper", "export")
    assert reply.invocation == "blocked" and reply.needs_authorization
    assert opened == [] and not (export_root / "REPRODUCIBILITY.md").exists()


def test_explicit_external_run_bundle_uses_native_snapshot_and_remains_bound(
    export_root, external_record, tmp_path
):
    grants = {"external_paths": (str(external_record),)}
    preview = call(
        export_root, tmp_path / "helper", "export", preview=True, write=False, grants=grants
    )
    assert preview.invocation == "handled_result", preview.diagnostics
    assert preview.data["selected_run_id"] == "20260101T000000Z-hf_vll"
    snapshot = external_record / "manifest.yaml"
    snapshot.write_text(snapshot.read_text() + "\n# external input changed\n")
    applied = call(
        export_root,
        tmp_path / "helper",
        "export",
        grants={**grants, "plan_hash": preview.data["plan_hash"]},
    )
    assert applied.invocation == "blocked" and not (export_root / "REPRODUCIBILITY.md").exists()


def test_external_snapshot_change_during_native_render_prevents_publication(
    export_root, external_record, tmp_path
):
    def render(argv, root):
        result = runtime.invoke_cli(argv, root)
        snapshot = external_record / "manifest.yaml"
        snapshot.write_text(snapshot.read_text() + "\n# changed during render\n")
        return result

    payload = request(export_root, "export", grants={"external_paths": (str(external_record),)})
    reply = execute_write(
        payload,
        root=export_root,
        state_home=tmp_path / "helper",
        identity="fixed",
        cli_runner=render,
        source_signature=runtime.input_signature,
    )
    assert reply.invocation == "blocked" and not (export_root / "REPRODUCIBILITY.md").exists()


def test_actual_native_export_cannot_read_retargeted_unapproved_record(
    export_root, tmp_path, monkeypatch
):
    import importlib

    native_export = importlib.import_module("reprollm.cli.export")
    original = native_export.read_run_record
    opened = []
    folder = next((export_root / ".reprollm/runs").iterdir())
    external = tmp_path / "new-external-record"

    def reader(path):
        opened.append(path.resolve())
        return original(path)

    monkeypatch.setattr(native_export, "read_run_record", reader)

    def runner(argv, root):
        folder.rename(external)
        try:
            folder.symlink_to(external, target_is_directory=True)
        except OSError:
            pytest.skip("Directory symlinks unavailable")
        return runtime.invoke_cli(argv, root)

    reply = execute_write(
        request(export_root, "export"),
        root=export_root,
        state_home=tmp_path / "helper",
        identity="fixed",
        cli_runner=runner,
        source_signature=runtime.input_signature,
    )
    assert reply.invocation == "blocked" and not (export_root / "REPRODUCIBILITY.md").exists()
    assert external / "run.json" not in opened
    assert native_export.read_run_record is reader


@pytest.mark.parametrize("template", ["default", "neurips", "acl", "acm"])
@pytest.mark.parametrize(
    "source",
    [
        {"type": "cli", "key": "--api-key"},
        {"type": "config", "key": "credentials.password", "path": "configs/options.yaml"},
        {"type": "env", "key": "HF_TOKEN"},
    ],
)
def test_export_artifact_keeps_typed_secret_source_until_private_render(tmp_path, source, template):
    root = tmp_path / "experiment"
    root.mkdir()
    secret = "OpaqueHistoricalExportSecret123456"
    argv_secret = "OpaqueExportCommandSecret123456"
    (root / "reprollm.yaml").write_text(
        json.dumps(
            {"schema_version": 1, "project": {"name": "public"}, "experiment": {"profiles": []}}
        )
    )
    folder = root / ".reprollm/runs/20261030T010000Z-aaaaaa"
    folder.mkdir(parents=True)
    record = {
        "schema_version": 1,
        "reprollm_version": "0.6.1",
        "run_id": folder.name,
        "status": "completed",
        "exit_code": 0,
        "command": {"argv": ["python", "eval.py", "--api-key", argv_secret], "cwd": "."},
        "bindings_observed": {
            "evaluation.judge.params.label": [{"value": secret, "source": source}],
            "evaluation.judge.params.public_label": [
                {"value": "public-scientific-value", "source": {"type": "cli", "key": "--label"}}
            ],
            "generation.temperature": [
                {"value": 0, "source": {"type": "cli", "key": "--temperature"}}
            ],
        },
    }
    path = folder / "run.json"
    path.write_text(json.dumps(record))
    before = inventory(root)
    reference = tmp_path / "native-unsafe.md"
    native = runtime.invoke_cli(
        ["export", str(root), "--output", str(reference), "--template", template], root
    )
    assert (
        native.exit_code == 0
        and secret in reference.read_text()
        and argv_secret in reference.read_text()
    )
    reply = runtime.execute(
        request(root, "export", template=template), cache_home=tmp_path / "helper/responses"
    )
    assert reply.invocation == "handled_result" and reply.cli_exit_code == 0
    document = (root / "REPRODUCIBILITY.md").read_text()
    assert secret not in document and argv_secret not in document
    assert "<REDACTED:generic_kv>" in document and "public-scientific-value" in document
    assert reply.data["document"] == document and reply.diagnostics
    assert all(inventory(root)[name] == digest for name, digest in before.items())


def test_export_current_audit_is_private_after_original_conclusions(tmp_path):
    from tests.unit.skills.test_skill_audit_display import CANARY, bundle

    root = tmp_path / "experiment"
    root.mkdir()
    bundle(root)
    baseline = tmp_path / "native-audit-unsafe.md"
    native = runtime.invoke_cli(["export", str(root), "--output", str(baseline)], root)
    assert native.exit_code == 0 and CANARY in baseline.read_text()
    before = inventory(root)
    reply = runtime.execute(request(root, "export"), cache_home=tmp_path / "helper/responses")
    assert reply.invocation == "handled_result"
    document = (root / "REPRODUCIBILITY.md").read_text()
    assert CANARY not in document and "<REDACTED:generic_kv>" in html.unescape(document)
    assert "consistency.custom_fields" in document and "WARNING" in document
    assert all(inventory(root)[name] == digest for name, digest in before.items())


def test_export_cursor_binds_actual_external_snapshot_without_repeating(
    export_root, external_record, tmp_path, monkeypatch
):
    req = request(export_root, "export", grants={"external_paths": (str(external_record),)})
    monkeypatch.setattr(runtime, "MAX_REPLY_BYTES", 4096)
    first = runtime.execute(req, cache_home=tmp_path / "helper/responses")
    assert first.next_cursor and first.cli_exit_code == 0
    snapshot = external_record / "manifest.yaml"
    snapshot.write_text(snapshot.read_text() + "\n# external modified\n")
    before = inventory(export_root)
    monkeypatch.setattr(
        writes, "execute_write", lambda *a, **k: pytest.fail("Cursor replayed export")
    )
    req = dataclasses.replace(req, response=ResponseOptions(cursor=first.next_cursor))
    next_page = runtime.execute(req, cache_home=tmp_path / "helper/responses")
    assert next_page.invocation == "blocked" and not next_page.complete
    assert inventory(export_root) == before


@pytest.mark.parametrize("action", ["schema.export", "export"])
def test_runtime_authorized_artifacts_equal_complete_native_bytes(export_root, tmp_path, action):
    native = tmp_path / "native-reference"
    argv = (
        ["schema", "export", "--out", str(native)]
        if action == "schema.export"
        else ["export", str(export_root), "--output", str(native)]
    )
    assert runtime.invoke_cli(argv, export_root).exit_code == 0
    reply = runtime.execute(request(export_root, action), cache_home=tmp_path / "helper/responses")
    assert reply.invocation == "handled_result" and reply.cli_exit_code == 0
    if action == "schema.export":
        assert inventory(export_root / "schemas") == inventory(native)
        assert reply.data["schema_count"] == 10
    else:
        assert (export_root / "REPRODUCIBILITY.md").read_bytes() == native.read_bytes()


@pytest.mark.parametrize("failure", ["audit", "build", "render"])
def test_export_private_bindings_restore_after_each_native_failure(tmp_path, monkeypatch, failure):
    import importlib

    exporter = importlib.import_module("reprollm.export.exporter")
    consistency = importlib.import_module("reprollm.rules.consistency")
    native_export = importlib.import_module("reprollm.cli.export")
    root = tmp_path / "experiment"
    root.mkdir()
    (root / "reprollm.yaml").write_text(
        json.dumps(
            {"schema_version": 1, "project": {"name": "public"}, "experiment": {"profiles": []}}
        )
    )

    def unavailable(*a, **k):
        raise OSError("synthetic native failure")

    if failure == "audit":
        monkeypatch.setattr(native_export, "run_audit", unavailable)
    elif failure == "build":
        monkeypatch.setattr(exporter, "build_input", unavailable)
    else:
        monkeypatch.setattr(exporter, "render", unavailable)
    original_build = exporter.build_input
    original_binding = consistency._binding_finding
    before = inventory(root)
    reply = runtime.execute(request(root, "export"), cache_home=tmp_path / "helper/responses")
    assert reply.invocation in {"blocked", "internal_error"} and not reply.complete
    assert inventory(root) == before
    assert (
        exporter.build_input is original_build and consistency._binding_finding is original_binding
    )


@pytest.mark.parametrize("value", [None, False, 0, "", "public-scientific-value"])
def test_private_export_preserves_public_values_missing_fields_and_raw_inputs(tmp_path, value):
    import importlib

    from reprollm.diff.state import observed_state
    from reprollm.schemas.run_record import RunRecord
    from reprollm.schemas.state import State

    raw = RunRecord.model_validate(
        {
            "schema_version": 1,
            "reprollm_version": "0.6.1",
            "run_id": "20261030T010000Z-aaaaaa",
            "status": "completed",
            "command": {"argv": ["python", "eval.py", "--label", "public"], "cwd": "."},
            "bindings_observed": {
                "evaluation.judge.params.label": [
                    {"value": value, "source": {"type": "cli", "key": "--label"}}
                ]
            },
        }
    )
    state = State.merge(run=observed_state(raw))
    record_before = raw.model_dump(mode="json", exclude_unset=True)
    state_before = state.model_dump(mode="json", exclude_unset=True)
    exporter = importlib.import_module("reprollm.export.exporter")
    expected = exporter.build_input(None, None, raw, state, reprollm_version="synthetic")
    with writes._private_export(
        lambda item, notes: runtime._sanitize(item, tmp_path, action="runs.show", diagnostics=notes)
    ) as diagnostics:
        actual = exporter.build_input(None, None, raw, state, reprollm_version="synthetic")
    assert dataclasses.asdict(actual) == dataclasses.asdict(expected) and not diagnostics
    assert raw.model_dump(mode="json", exclude_unset=True) == record_before
    assert state.model_dump(mode="json", exclude_unset=True) == state_before
    assert "evaluation.judge.params.missing" not in state.flatten()


def test_private_export_keeps_public_copy_and_both_colliding_dynamic_members(tmp_path):
    import importlib

    from reprollm.diff.state import observed_state
    from reprollm.schemas.run_record import RunRecord
    from reprollm.schemas.state import State

    value = "OpaqueSameBytesDifferentExportSource123456"
    run = RunRecord.model_validate(
        {
            "schema_version": 1,
            "reprollm_version": "0.6.1",
            "run_id": "20261030T010000Z-aaaaaa",
            "status": "completed",
            "command": {"argv": ["python"], "cwd": "."},
            "bindings_observed": {
                "evaluation.judge.params.secret_label": [
                    {"value": value, "source": {"type": "cli", "key": "--api-key"}}
                ],
                "evaluation.judge.params.public_label": [
                    {"value": value, "source": {"type": "cli", "key": "--label"}}
                ],
                "evaluation.judge.params.options": [
                    {
                        "value": {"/private/a": "public-alpha", "/private/b": "public-bravo"},
                        "source": {"type": "cli", "key": "--options"},
                    }
                ],
            },
        }
    )
    state = State.merge(run=observed_state(run))
    exporter = importlib.import_module("reprollm.export.exporter")
    with writes._private_export(
        lambda item, notes: runtime._sanitize(item, tmp_path, action="runs.show", diagnostics=notes)
    ):
        data = exporter.build_input(None, None, run, state, reprollm_version="synthetic")
        document = exporter.render(data)
    details = {item["field"]: item["value"] for item in data.judge_details}
    assert details["params.secret_label"] == "<REDACTED:generic_kv>"
    assert details["params.public_label"] == value
    assert len(details["params.options"]) == 2
    assert set(details["params.options"].values()) == {"public-alpha", "public-bravo"}
    assert "/private/a" not in document and "/private/b" not in document
    assert "public-alpha" in document and "public-bravo" in document
