"""Refresh examples/ from the golden fixtures (M8-T03).

Copies each fixture tree plus its complete manifest as reprollm.yaml, then
records in the example README what the example demonstrates. Real lockfiles
are generated separately (network) by the maintainer; the script leaves any
existing reprollm.lock untouched.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "repos"
EXAMPLES = ROOT / "examples"

NOTES = {
    "hf_vllm_eval": (
        "HuggingFace + vLLM evaluation. Shows: dependency pinning warnings, "
        "profile detection (inference + evaluation), a fully-completed manifest."
    ),
    "openai_judge_eval": (
        "OpenAI LLM-as-a-judge. Shows: judge-profile detection, unpinnable "
        "closed-source models, the .env.example exemption."
    ),
    "privacy_custom_params": (
        "Privacy-preserving fine-tuning. Shows: privacy declarations and profile "
        "detection. The fixture's planted fake .env is omitted from this example."
    ),
}


def main() -> None:
    EXAMPLES.mkdir(exist_ok=True)
    for name, note in NOTES.items():
        target = EXAMPLES / name
        preserved = {}
        if target.exists():
            for path in target.iterdir():
                if path.name == "reprollm.lock" or (
                    path.name.startswith("REPRODUCIBILITY") and path.suffix == ".md"
                ):
                    preserved[path.name] = path.read_bytes()
            shutil.rmtree(target)
        shutil.copytree(FIXTURES / name / "tree", target)
        # the planted fake .env demonstrates detection but stays out of examples
        planted = target / ".env"
        if planted.exists():
            planted.unlink()
        manifest = FIXTURES / name / "manifests" / "complete.yaml"
        if manifest.is_file():
            (target / "reprollm.yaml").write_text(
                manifest.read_text(encoding="utf-8") + "\n", encoding="utf-8"
            )
        for filename, content in preserved.items():
            (target / filename).write_bytes(content)
        (target / "README.md").write_text(
            f"# Example: {name}\n\n{note}\n\n"
            "Inspect the completed declaration without executing the model script:\n\n"
            "```bash\nreprollm audit . --level 1\nreprollm lock . --check\n```\n\n"
            "Audit may exit 1 for the intentionally imperfect research repository; "
            "exit 2 means a usage or input error. The committed lock contains "
            "historical network metadata, not proof that the model ran here.\n\n"
            "To edit the declaration or generate an export, copy this directory "
            "outside the ReproLLM checkout first. `init --force` overwrites the "
            "completed manifest with a new scaffold. Follow the "
            "[resource-free quick start](../../docs/quickstart.md) for the full workflow.\n",
            encoding="utf-8",
        )
        print(f"refreshed {name}")
    index = EXAMPLES / "README.md"
    index.write_text(
        "# ReproLLM examples\n\n"
        "Example research repositories generated from the test fixtures.\n"
        "Each contains a completed `reprollm.yaml` and a reviewed historical lock.\n"
        "Use `audit --level 1` and `lock --check` to inspect them. Copy an example "
        "outside this checkout before editing it or generating artifacts. "
        "Running its model script requires its own dependencies and resources.\n\n"
        "The [quick start](../docs/quickstart.md) exercises capture, diff and export "
        "with only the Python standard library.\n\n"
        + "\n".join(f"- [{n}](./{n}/) — {d}" for n, d in NOTES.items())
        + "\n\nRegenerate with `uv run python scripts/refresh_examples.py`.\n",
        encoding="utf-8",
    )
    print("index written")


if __name__ == "__main__":
    main()
