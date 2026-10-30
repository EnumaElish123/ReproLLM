"""SK17: exact native review content across the real worker JSON boundary."""

from __future__ import annotations

import dataclasses
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "skills/reprollm/scripts"
sys.path.insert(0, str(SCRIPTS))
import skill_runtime as runtime  # noqa: E402
from skill_request import Request  # noqa: E402
from skill_runtime_frame import validate_frame  # noqa: E402


def native_messages(root: Path, max_chars: int | None = None) -> list[dict[str, str]]:
    argv = ["discover", str(root), "--experimental", "--dry-run", "--show-content"]
    if max_chars is not None:
        argv.extend(["--max-chars", str(max_chars)])
    result = runtime.invoke_cli(argv, root)
    assert result.exit_code == 0 and not result.stderr
    return json.loads(result.stdout.split("Request messages (nothing sent):\n", 1)[1])


def worker(request: Request, cache: Path) -> bytes:
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(SCRIPTS / "skill_runtime.py"),
            "--worker",
            "--cache-home",
            str(cache),
            "--identity",
            "b" * 64,
        ],
        input=json.dumps(dataclasses.asdict(request)).encode(),
        capture_output=True,
        timeout=30,
        env={
            "PATH": os.defpath,
            "LANG": "C.UTF-8",
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "HOME": str(cache.parent / "synthetic-home"),
            "USERPROFILE": str(cache.parent / "synthetic-home"),
            "USER": "public-user",
            "USERNAME": "public-user",
        },
        check=False,
    )
    assert result.returncode == 0 and not result.stderr
    return result.stdout


def test_real_worker_preview_matches_native_public_source_bytes(tmp_path: Path) -> None:
    root = tmp_path / "public-research"
    root.mkdir()
    (root / "docs").mkdir()
    (root / "docs/run.md").write_text("# Public guide\n", encoding="utf-8")
    (root / "README.md").write_text(
        "# Public experiment\nRead [guide](/docs/run.md).\n"
        "Use ~/models/reference and /api/chat/completions or /v1/models.\n"
        "```sh\nsource /opt/toolchain/env.sh\nsource /usr/local/toolchain/env.sh\n```\n",
        encoding="utf-8",
    )
    expected = native_messages(root)
    request = Request("discover.preview", str(root), {"experimental": True, "show_content": True})
    raw = worker(request, tmp_path / "cache")
    reply = validate_frame(raw, expected_action=request.action)
    assert reply.invocation == "handled_result" and reply.complete
    assert reply.data["messages"] == expected
    from skill_discover_guard import identity

    assert reply.data["approval_requirements"]["messages_sha256"] == identity(expected)
    assert identity(reply.data["messages"]) == identity(expected)


@pytest.mark.parametrize(
    "text",
    [
        "/home/foreign-person/project/config.yaml",
        "/private/research/config.yaml",
        "/mnt/shared/research/config.yaml",
        "/srv/team/research/config.yaml",
        "/unknown-research-root/config.yaml",
        r"C:\Users\foreign-person\config.yaml",
        r"\\private-host\research\config.yaml",
        "file:///private/research/config.yaml",
        "~foreign-person/config.yaml",
        "safe text\x1b[31m unsafe terminal",
        "safe text\u202eunsafe direction",
    ],
)
def test_unreviewable_native_content_is_blocked_without_approval_or_cache(
    tmp_path: Path, text: str
) -> None:
    root = tmp_path / "research"
    root.mkdir()
    path = root / "README.md"
    original = ("# Research\n" + text + "\n").encode()
    path.write_bytes(original)
    expected = native_messages(root)
    assert text in expected[1]["content"]
    request = Request("discover.preview", str(root), {"experimental": True, "show_content": True})
    result = runtime.execute(request, cache_home=tmp_path / "cache", identity="b" * 64)
    assert result.invocation == "blocked" and not result.complete
    assert result.data is None
    assert result.diagnostics[0]["code"] in {
        "discover_review_content_unsafe",
        "discover_review_content_controls",
    }
    assert not (tmp_path / "cache").exists()
    assert path.read_bytes() == original


def test_private_root_collision_in_repo_link_still_refuses(tmp_path: Path) -> None:
    root = tmp_path / "research"
    root.mkdir()
    (root / "home/foreign-person").mkdir(parents=True)
    (root / "home/foreign-person/config.yaml").write_text("public: true\n")
    (root / "README.md").write_text(
        "[private location](/home/foreign-person/config.yaml)\n", encoding="utf-8"
    )
    request = Request("discover.preview", str(root), {"experimental": True, "show_content": True})
    result = runtime.execute(request, cache_home=tmp_path / "cache", identity="b" * 64)
    assert result.invocation == "blocked" and result.data is None
    assert result.diagnostics == [{"code": "discover_review_content_unsafe"}]


def test_nominal_source_role_is_only_for_original_discover_preview(tmp_path: Path) -> None:
    import skill_discover as discover
    from skill_request import Reply

    root = tmp_path / "research"
    root.mkdir()
    (root / "README.md").write_text("source /usr/local/toolchain/env.sh\n")
    request = Request("discover.preview", str(root), {"experimental": True, "show_content": True})
    original = discover.preview(
        request, root=root, state_home=tmp_path / "state", helper_identity="b" * 64
    )
    raw_messages = json.loads(json.dumps(original.data["messages"]))
    forged = dataclasses.replace(original, data={**original.data, "messages": raw_messages})
    assert discover.finalize_preview(forged, root).invocation == "blocked"
    wrong_action = dataclasses.replace(original, action="audit")
    result = discover.finalize_preview(wrong_action, root)
    assert result.invocation == "blocked" and result.data is None
    ordinary = runtime.sanitize_reply(Reply("audit", data=original.data), root)
    assert "/usr/local/toolchain" not in json.dumps(ordinary.as_dict())


def test_source_role_never_exempts_reports_diagnostics_or_questions(tmp_path: Path) -> None:
    import skill_discover as discover

    root = tmp_path / "research"
    root.mkdir()
    (root / "README.md").write_text("Use /usr/local/public-tool/env.sh.\n")
    request = Request("discover.preview", str(root), {"experimental": True, "show_content": True})
    result = discover.preview(
        request, root=root, state_home=tmp_path / "state", helper_identity="b" * 64
    )
    expected = json.loads(json.dumps(result.data["messages"]))
    result.data["report"] = "/usr/local/private-metadata/report.txt"
    result.data["input_files"] = ["/private/machine/input.txt"]
    result.diagnostics = [{"code": "synthetic", "note": "/opt/private-metadata/log.txt"}]
    result.questions = ["Read /private/machine/config.yaml"]
    safe = discover.finalize_preview(result, root)
    assert safe.data["messages"] == expected
    assert safe.data["report"] == "<REDACTED:path>"
    assert safe.data["input_files"] == ["<REDACTED:path>"]
    assert safe.diagnostics[0]["note"] == "<REDACTED:path>"
    assert safe.questions == ["Read <REDACTED:path>"]


@pytest.mark.parametrize("kind", ["identity", "root", "structured-secret"])
def test_current_machine_or_key_context_conflicts_block_source_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    root = tmp_path / "research"
    root.mkdir()
    monkeypatch.setattr(runtime.getpass, "getuser", lambda: "private-person")
    monkeypatch.setattr(runtime.socket, "gethostname", lambda: "private-machine")
    content = {
        "identity": "Use /usr/local/private-person/private-machine/env.sh",
        "root": str(root / "private-config.yaml"),
        "structured-secret": '{"password": "/usr/local/not-a-public-password"}',
    }[kind]
    (root / "README.md").write_text(content + "\n", encoding="utf-8")
    assert content in native_messages(root)[1]["content"]
    result = runtime.execute(
        Request("discover.preview", str(root), {"experimental": True}),
        cache_home=tmp_path / "cache",
        identity="b" * 64,
    )
    assert result.invocation == "blocked" and result.data is None
    assert result.diagnostics == [{"code": "discover_review_content_unsafe"}]


def test_real_worker_unsafe_source_returns_no_body_or_approval(tmp_path: Path) -> None:
    root = tmp_path / "research"
    root.mkdir()
    content = "# Public header\n/private/private-research/config.yaml\n"
    path = root / "README.md"
    path.write_text(content, encoding="utf-8")
    request = Request("discover.preview", str(root), {"experimental": True, "show_content": True})
    raw = worker(request, tmp_path / "cache")
    reply = validate_frame(raw, expected_action=request.action)
    assert reply.invocation == "blocked" and reply.data is None
    assert reply.diagnostics == [{"code": "discover_review_content_unsafe"}]
    assert b"private-research" not in raw and b"approval_requirements" not in raw
    assert path.read_text() == content and not (tmp_path / "cache").exists()


def test_native_secret_drop_is_unchanged_in_exact_preview(tmp_path: Path) -> None:
    root = tmp_path / "research"
    root.mkdir()
    secret = "sk-proj-" + "SyntheticSecretDropCanary12345"
    (root / "README.md").write_text("secret: " + secret + "\n")
    (root / "README-public.md").write_text("Public API /api/completions\n")
    expected = native_messages(root)
    request = Request("discover.preview", str(root), {"experimental": True, "show_content": True})
    reply = validate_frame(worker(request, tmp_path / "cache"), expected_action=request.action)
    assert reply.invocation == "handled_result" and reply.data["messages"] == expected
    assert reply.data["dropped_files"] == ["README.md"]
    assert secret not in json.dumps(reply.as_dict())


def test_real_parent_does_not_reproject_validated_worker_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import contextlib
    from types import SimpleNamespace

    import bootstrap

    root = tmp_path / "research"
    root.mkdir()
    (root / "README.md").write_text("Public route /api/completions\n")
    expected = native_messages(root)
    status = {
        "state": "READY",
        "environment": "owned-dev",
        "capabilities": ["contextual_word_scan"],
    }
    monkeypatch.setattr(
        bootstrap, "Bootstrap", lambda *args: SimpleNamespace(status=lambda: status)
    )

    @contextlib.contextmanager
    def lease(*args):
        yield SimpleNamespace(status=status, environment=Path(sys.prefix), cleanup_failed=False)

    monkeypatch.setattr(runtime, "_worker_lease", lease)
    monkeypatch.setattr(
        runtime.os,
        "environ",
        {
            "PATH": os.defpath,
            "LANG": "C.UTF-8",
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "HOME": str(tmp_path / "synthetic-home"),
            "USERPROFILE": str(tmp_path / "synthetic-home"),
            "USER": "public-user",
            "USERNAME": "public-user",
        },
    )
    request = Request("discover.preview", str(root), {"experimental": True, "show_content": True})
    result = runtime.RuntimeExecutor(tmp_path / "owned-home")(request)
    assert result.invocation == "handled_result" and result.complete
    assert result.data["messages"] == expected


def test_real_worker_cached_pages_preserve_exact_source_and_bind_changed_inputs(
    tmp_path: Path,
) -> None:
    from skill_request import ResponseOptions

    root = tmp_path / "research"
    root.mkdir()
    for index in range(6):
        (root / f"README-{index}.md").write_text(
            ("Public API /api/completions and /usr/local/tool/env.sh.\n" * 950), encoding="utf-8"
        )
    expected = native_messages(root, 500000)
    request = Request(
        "discover.preview",
        str(root),
        {"experimental": True, "show_content": True, "max_chars": 500000},
    )
    cache = tmp_path / "cache"
    reply = validate_frame(worker(request, cache), expected_action=request.action)
    assert not reply.complete and reply.next_cursor and reply.snapshot
    first_cursor = reply.next_cursor
    fragments = []
    while True:
        assert reply.data["scope"] == "partial_document"
        fragments.append(reply.data["text"])
        if not reply.next_cursor:
            break
        request = dataclasses.replace(request, response=ResponseOptions(cursor=reply.next_cursor))
        reply = validate_frame(worker(request, cache), expected_action=request.action)
        assert reply.invocation == "handled_result"
    full = json.loads("".join(fragments))
    assert full["data"]["messages"] == expected
    from skill_discover_guard import identity

    assert full["data"]["approval_requirements"]["messages_sha256"] == identity(expected)
    (root / "README-0.md").write_text("Changed private /private/research/config.yaml\n")
    stale = dataclasses.replace(request, response=ResponseOptions(cursor=first_cursor))
    denied = validate_frame(worker(stale, cache), expected_action=request.action)
    assert denied.invocation == "blocked" and denied.data is None
    assert denied.diagnostics == [{"code": "response_snapshot_stale"}]


def test_source_route_never_shields_a_nested_local_file_uri(tmp_path: Path) -> None:
    root = tmp_path / "research"
    root.mkdir()
    (root / "README.md").write_text("/api/file:///private/research/config.yaml\n")
    result = runtime.execute(
        Request("discover.preview", str(root), {"experimental": True, "show_content": True}),
        cache_home=tmp_path / "cache",
        identity="b" * 64,
    )
    assert result.invocation == "blocked" and result.data is None
    assert result.diagnostics == [{"code": "discover_review_content_unsafe"}]


@pytest.mark.parametrize("kind", ["home-data", "comment-separator", "unicode-template"])
def test_native_non_machine_source_syntax_survives_worker_exactly(
    tmp_path: Path, kind: str
) -> None:
    root = tmp_path / "research"
    root.mkdir()
    if kind == "home-data":
        (root / "README.md").write_text("Use ~/datasets/reference/train.jsonl\n")
    else:
        source = "from dataclasses import dataclass\n@dataclass\nclass Args:\n" + (
            "    # compare `image_values`/`other_values`\n    count: int = 1\n"
            if kind == "comment-separator"
            else '    label: str = "中文"; path: str = f"/tmp/{label}/dataset"\n'
        )
        (root / "train.py").write_text(source, encoding="utf-8")
    expected = native_messages(root)
    request = Request("discover.preview", str(root), {"experimental": True, "show_content": True})
    result = validate_frame(worker(request, tmp_path / "cache"), expected_action=request.action)
    assert result.invocation == "handled_result" and result.complete
    assert result.data["messages"] == expected


def test_derived_source_parser_does_not_echo_or_double_count_native_warnings(
    tmp_path: Path,
) -> None:
    root = tmp_path / "research"
    root.mkdir()
    (root / "train.py").write_text(
        'import argparse\np=argparse.ArgumentParser()\np.add_argument("--pattern", default="\\D")\n'
    )
    request = Request("discover.preview", str(root), {"experimental": True, "show_content": True})
    result = validate_frame(worker(request, tmp_path / "cache"), expected_action=request.action)
    assert result.invocation == "handled_result" and result.complete
    assert result.diagnostics == [
        {
            "code": "discover_collection_warning",
            "category": "syntax_warning" if sys.version_info >= (3, 12) else "deprecation_warning",
            "count": 1,
            "count_is_lower_bound": False,
        }
    ]


@pytest.mark.parametrize(
    "expression",
    [
        "f\"/tmp/{'/home/foreign-person/config'}\"",
        "f\"/tmp/{'/unknown-root/config'}\"",
        "f\"/tmp/{'/tmp/private-name'}\"",
        'f"/home/{label}"',
        'f"/unknown-root/{label}"',
        'f"/tmp/{label:/private/research}"',
        r'f"/tmp/{label:\u002fhome\u002fforeign-person}"',
        r'f"/tmp/{label:\x1b}"',
        r'f"/tmp/{label:\u0073\u006b-SyntheticEncodedCanary12345}"',
    ],
)
def test_template_proof_never_hides_private_decoded_expression_content(
    tmp_path: Path, expression: str
) -> None:
    root = tmp_path / "research"
    root.mkdir()
    source = (
        "from dataclasses import dataclass\n@dataclass\nclass Args:\n"
        "    label: str = 'public'\n    path: str = " + expression + "\n"
    )
    (root / "train.py").write_text(source, encoding="utf-8")
    assert expression in native_messages(root)[1]["content"]
    request = Request("discover.preview", str(root), {"experimental": True, "show_content": True})
    result = runtime.execute(request, cache_home=tmp_path / "cache", identity="b" * 64)
    assert result.invocation == "blocked" and result.data is None
    assert result.diagnostics[0]["code"] in {
        "discover_review_content_unsafe",
        "discover_review_content_controls",
    }
    assert not (tmp_path / "cache").exists()


def test_unproven_template_is_rejected_without_evaluation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    name = "REPROLLM_TEMPLATE_EVALUATED"
    monkeypatch.delenv(name, raising=False)
    root = tmp_path / "research"
    root.mkdir()
    (root / "train.py").write_text(
        "from dataclasses import dataclass\n@dataclass\nclass Args:\n"
        "    path: str = f\"/tmp/{__import__('os').environ."
        "__setitem__('REPROLLM_TEMPLATE_EVALUATED', 'yes')}\"\n",
        encoding="utf-8",
    )
    request = Request("discover.preview", str(root), {"experimental": True, "show_content": True})
    result = runtime.execute(request, cache_home=tmp_path / "cache", identity="b" * 64)
    assert result.invocation == "blocked" and result.data is None
    assert name not in os.environ


@pytest.mark.linux_only
@pytest.mark.skipif(sys.platform != "linux", reason="Native bounded discovery request fixture")
def test_reviewed_source_and_actual_mock_post_have_identical_messages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import respx
    import skill_discover as discover
    from skill_discover_guard import identity
    from skill_request import Grants
    from tests.unit.skills.test_skill_discover import Context
    from tests.unit.skills.test_skill_discover_guard import (
        ENDPOINT,
        KEY,
        approval,
        policy,
        response,
    )

    root = tmp_path / "research"
    root.mkdir()
    (root / "README.md").write_text("Public route /api/completions and ~/datasets/reference\n")
    monkeypatch.setenv("REPROLLM_LLM_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("REPROLLM_LLM_API_KEY", KEY)
    monkeypatch.setenv("REPROLLM_LLM_MODEL", "deepseek-flash")
    context = Context(root, tmp_path / "home")
    reviewed = runtime.execute(
        Request("discover.preview", str(root), {"experimental": True, "show_content": True}),
        cache_home=context.home / "responses",
        identity=context.identity,
    )
    assert reviewed.invocation == "handled_result"
    bindings = reviewed.data["approval_requirements"]
    price = policy()
    approved = approval(
        price, source_sha256=bindings["source_sha256"], messages_sha256=bindings["messages_sha256"]
    )
    grant = {
        "schema_version": 1,
        "currency": "CNY",
        "policy": {**dataclasses.asdict(price), "served_models": list(price.served_models)},
        "approval": dataclasses.asdict(approved),
    }
    request = Request(
        "discover",
        str(root),
        {"experimental": True},
        Grants(install=False, write=True, network=True, paid_discover=grant),
    )
    route = respx.post(ENDPOINT).mock(return_value=response())
    result = discover.execute(request, context)
    assert result.cli_exit_code == 0 and route.call_count == 1
    sent = json.loads(route.calls[0].request.content)["messages"]
    assert sent == reviewed.data["messages"] == native_messages(root)
    assert identity(sent) == approved.messages_sha256
    (root / "README.md").write_text("Unsafe /unknown-root/private-config.yaml\n")
    import reprollm.cli.discover as native

    monkeypatch.setattr(
        native, "_endpoint_credentials", lambda *args: pytest.fail("read credentials")
    )
    monkeypatch.setattr(discover.Ledger, "__init__", lambda *args: pytest.fail("created ledger"))
    denied = discover.execute(request, dataclasses.replace(context, operation_id="2" * 32))
    assert denied.invocation == "blocked"
    assert denied.diagnostics == [{"code": "discover_review_content_unsafe"}]
    assert route.call_count == 1


def test_real_worker_preserves_single_relative_suffix_after_unexecuted_call(tmp_path: Path) -> None:
    root = tmp_path / "research"
    root.mkdir()
    (root / "train.py").write_text(
        "from dataclasses import dataclass\n@dataclass\nclass Args:\n"
        '    label: str = "中文"; path: str = f"{os.getcwd()}/results.json"\n',
        encoding="utf-8",
    )
    expected = native_messages(root)
    request = Request("discover.preview", str(root), {"experimental": True, "show_content": True})
    result = validate_frame(worker(request, tmp_path / "cache"), expected_action=request.action)
    assert result.invocation == "handled_result" and result.complete
    assert result.data["messages"] == expected


@pytest.mark.parametrize(
    "expression",
    [
        "f\"{unexecuted_base('/home/foreign-person')}/results\"",
        "f\"{unexecuted_base('/unknown-root/config')}/results\"",
        "f\"{unexecuted_base('public')}/nested/results\"",
        "f\"{unexecuted_base('public')}/..\"",
    ],
)
def test_relative_suffix_never_hides_private_expression_or_multiple_components(
    tmp_path: Path, expression: str
) -> None:
    root = tmp_path / "research"
    root.mkdir()
    (root / "train.py").write_text(
        "from dataclasses import dataclass\n@dataclass\nclass Args:\n    path: str = "
        + expression
        + "\n"
    )
    assert expression in native_messages(root)[1]["content"]
    result = runtime.execute(
        Request("discover.preview", str(root), {"experimental": True, "show_content": True}),
        cache_home=tmp_path / "cache",
        identity="b" * 64,
    )
    assert result.invocation == "blocked" and result.data is None
    assert result.diagnostics[0]["code"] == "discover_review_content_unsafe"
