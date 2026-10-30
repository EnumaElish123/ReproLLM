"""SK10: independently specified installation identities and rejection boundaries."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "skills/reprollm/scripts/install_catalog.py"
CATALOG_PATH = ROOT / "skills/reprollm/assets/install-catalog.json"
SPEC = importlib.util.spec_from_file_location("skill_install_catalog", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
catalog_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = catalog_module
SPEC.loader.exec_module(catalog_module)

COMMIT = "0e0de760fc098634b73bdc64558b5a1086c31232"
SHA_HELLO = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def document() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "default_candidate": "source-test",
        "candidates": [
            {
                "id": "source-test",
                "version": "0.7.0",
                "source": {
                    "commit": COMMIT,
                    "url": f"https://codeload.github.com/EnumaElish123/ReproLLM/tar.gz/{COMMIT}",
                    "sha256": SHA_HELLO,
                },
                "wheel_filename": "reprollm-0.7.0-py3-none-any.whl",
                "python": {"min": [3, 10], "max": [3, 12]},
                "platforms": ["linux", "darwin", "win32"],
                "capabilities": ["audit", "saved_commands"],
                "runtime_artifacts": [
                    {
                        "name": "httpx",
                        "version": "0.28.1",
                        "filename": "httpx-0.28.1-py3-none-any.whl",
                        "url": "https://files.pythonhosted.org/packages/ab/httpx-0.28.1-py3-none-any.whl",
                        "sha256": SHA_HELLO,
                    }
                ],
                "build_artifacts": [
                    {
                        "name": "hatchling",
                        "version": "1.27.0",
                        "filename": "hatchling-1.27.0-py3-none-any.whl",
                        "url": "https://files.pythonhosted.org/packages/cd/hatchling-1.27.0-py3-none-any.whl",
                        "sha256": SHA_HELLO,
                    }
                ],
            }
        ],
    }


def load(tmp_path: Path, data: dict[str, Any]) -> Any:
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return catalog_module.load_catalog(path)


def test_fixed_source_and_dependency_stages(tmp_path: Path) -> None:
    catalog = load(tmp_path, document())
    candidate = catalog.get_candidate()
    assert candidate == catalog.get_candidate("source-test")
    assert candidate.source_commit == COMMIT
    assert candidate.requirements("runtime") == (f"httpx==0.28.1 --hash=sha256:{SHA_HELLO}",)
    assert candidate.requirements("build") == (f"hatchling==1.27.0 --hash=sha256:{SHA_HELLO}",)
    assert candidate.supports((3, 10), "linux")
    assert candidate.supports((3, 12), "win32")
    assert not candidate.supports((3, 9), "linux")
    assert not candidate.supports((3, 13), "linux")
    assert not candidate.supports((3, 12), "freebsd")
    with pytest.raises(catalog_module.CatalogError):
        catalog.get_candidate("missing")
    with pytest.raises(catalog_module.CatalogError):
        candidate.requirements("project")


def test_blob_integrity_for_source_and_dependency(tmp_path: Path) -> None:
    candidate = load(tmp_path, document()).get_candidate()
    for identity in (candidate, candidate.runtime_artifacts[0]):
        assert catalog_module.validate_blob(identity, b"hello") is None
        with pytest.raises(catalog_module.CatalogError, match="artifact_hash_mismatch"):
            catalog_module.validate_blob(identity, b"hello!")


@pytest.mark.parametrize(
    ("where", "key", "value"),
    [
        ("root", "schema_version", True),
        ("root", "schema_version", 2),
        ("root", "default_candidate", "unknown"),
        ("candidate", "id", "../../project"),
        ("candidate", "version", "0.7.0;touch pwn"),
        ("candidate", "wheel_filename", "../reprollm.whl"),
        ("candidate", "wheel_filename", "other-0.7.0-py3-none-any.whl"),
        ("candidate", "python", {"min": [3, 12], "max": [3, 10]}),
        ("candidate", "python", {"min": [True, 10], "max": [3, 12]}),
        ("candidate", "platforms", ["linux", "linux"]),
        ("candidate", "capabilities", ["audit", "audit"]),
        ("candidate", "runtime_artifacts", []),
        ("source", "commit", "main"),
        ("source", "sha256", "0" * 40),
        ("source", "url", "https://codeload.github.com/attacker/project/tar.gz/" + COMMIT),
        ("source", "url", "https://github.com/EnumaElish123/ReproLLM/archive/main.tar.gz"),
        ("artifact", "name", "torch"),
        ("artifact", "name", "transformers"),
        ("artifact", "name", "huggingface-hub"),
        ("artifact", "version", ">=0.28"),
        ("artifact", "filename", "../../httpx.whl"),
        ("artifact", "filename", "httpx-0.28.1.tar.gz"),
        ("artifact", "sha256", "x" * 64),
        (
            "artifact",
            "url",
            "http://files.pythonhosted.org/packages/ab/httpx-0.28.1-py3-none-any.whl",
        ),
        (
            "artifact",
            "url",
            "https://user:secret@files.pythonhosted.org/packages/ab/httpx-0.28.1-py3-none-any.whl",
        ),
        (
            "artifact",
            "url",
            "https://files.pythonhosted.org.evil/packages/httpx-0.28.1-py3-none-any.whl",
        ),
        (
            "artifact",
            "url",
            "https://files.pythonhosted.org/packages/ab/httpx-0.28.1-py3-none-any.whl?token=secret",
        ),
    ],
)
def test_untrusted_catalog_values_are_rejected(
    tmp_path: Path, where: str, key: str, value: Any
) -> None:
    data = document()
    candidate = data["candidates"][0]
    target = {
        "root": data,
        "candidate": candidate,
        "source": candidate["source"],
        "artifact": candidate["runtime_artifacts"][0],
    }[where]
    target[key] = value
    with pytest.raises(catalog_module.CatalogError) as caught:
        load(tmp_path, data)
    assert "secret" not in str(caught.value)
    assert str(tmp_path) not in str(caught.value)


def test_duplicate_candidate_and_contradictory_dependency_rejected(tmp_path: Path) -> None:
    data = document()
    data["candidates"].append(data["candidates"][0])
    with pytest.raises(catalog_module.CatalogError):
        load(tmp_path, data)
    data = document()
    conflict = dict(data["candidates"][0]["runtime_artifacts"][0])
    conflict["version"] = "0.28.0"
    data["candidates"][0]["runtime_artifacts"].append(conflict)
    with pytest.raises(catalog_module.CatalogError):
        load(tmp_path, data)


def test_all_platform_wheel_hashes_are_preserved_in_one_exact_requirement(tmp_path: Path) -> None:
    data = document()
    variants = data["candidates"][0]["runtime_artifacts"]
    other = dict(variants[0])
    other["filename"] = "httpx-0.28.1-py2.py3-none-any.whl"
    other["url"] = "https://files.pythonhosted.org/packages/ab/" + other["filename"]
    other["sha256"] = "0" * 64
    variants.append(other)
    requirement = load(tmp_path, data).get_candidate().requirements("runtime")
    assert len(requirement) == 1
    assert requirement[0] == f"httpx==0.28.1 --hash=sha256:{'0' * 64} --hash=sha256:{SHA_HELLO}"


def test_committed_catalog_pins_current_source_without_false_release() -> None:
    catalog = catalog_module.load_catalog(CATALOG_PATH)
    candidate = catalog.get_candidate()
    assert candidate.source_commit == COMMIT
    assert (
        candidate.source_sha256
        == "f8a4613cb346d8ad2bcf7f5a4f8c973c410fe69aa07552f4e6f600db030e3c2c"
    )
    assert candidate.version == "0.7.0"
    assert candidate.wheel_filename == "reprollm-0.7.0-py3-none-any.whl"
    runtime_names = {artifact.name for artifact in candidate.runtime_artifacts}
    assert {"httpx", "typer", "pydantic", "pyyaml", "socksio", "tomli"} <= runtime_names
    assert "hatchling" not in runtime_names
    assert "hatchling" in {artifact.name for artifact in candidate.build_artifacts}
    assert {"audit", "run_v2", "saved_commands", "task_inventory", "discover"} <= set(
        candidate.capabilities
    )
