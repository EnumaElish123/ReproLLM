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
        "Privacy-preserving fine-tuning. Shows: secret-file detection (the "
        "tracked .env is a planted fake), custom parameters via project rules, "
        "the privacy profile."
    ),
}


def main() -> None:
    EXAMPLES.mkdir(exist_ok=True)
    for name, note in NOTES.items():
        target = EXAMPLES / name
        if target.exists():
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
        (target / "README.md").write_text(
            f"# Example: {name}\n\n{note}\n\n"
            "Try:\n\n```bash\nreprollm audit .\n"
            "reprollm init . --force\nreprollm export .\n```\n",
            encoding="utf-8",
        )
        print(f"refreshed {name}")
    index = EXAMPLES / "README.md"
    index.write_text(
        "# ReproLLM examples\n\n"
        "Runnable example repositories generated from the test fixtures.\n"
        "Each contains a complete `reprollm.yaml`; audit it, re-init it, export it.\n\n"
        + "\n".join(
            f"- [{n}](./{n}/) — {d.split('. Shows: ')[1].rstrip('.')}" for n, d in NOTES.items()
        )
        + "\n\nRegenerate with `uv run python scripts/refresh_examples.py`.\n",
        encoding="utf-8",
    )
    print("index written")


if __name__ == "__main__":
    main()
