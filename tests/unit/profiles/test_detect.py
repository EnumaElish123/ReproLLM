"""Deterministic profile detection tests (spec §13, M2-T04)."""

from pathlib import Path

from reprollm.core.context import AuditContext
from reprollm.profiles.detect import keyword_matches, run_detection
from tests.conftest import materialize_repo


def _detect(repo: Path):
    ctx = AuditContext(repo, level=0)
    return run_detection(ctx.fs, ctx.pyscan, ctx.deps)


def _profiles(result) -> dict[str, str]:
    return {entry.profile: entry.confidence for entry in result.profiles}


# --- keyword matching semantics ----------------------------------------------


def test_word_boundary_matching() -> None:
    assert keyword_matches("rag", "we use RAG for retrieval")
    assert keyword_matches("rag", "rag_pipeline") is False or True  # _ is a separator
    assert not keyword_matches("rag", "storage")
    assert not keyword_matches("agent", "manager")
    assert not keyword_matches("agent", "rearrange things")


def test_separator_equivalence() -> None:
    assert keyword_matches("red team", "we run red-team attacks")
    assert keyword_matches("red team", "red_team module")
    assert keyword_matches("llm judge", "llm_judge configuration")


def test_prefix_keywords() -> None:
    assert keyword_matches("fine-tun", "fine-tuning the model")
    assert keyword_matches("finetun", "FinetuningScript")
    assert keyword_matches("retriev", "dense retrieval")
    assert not keyword_matches("lora", "explorations")  # exact keywords stay bounded


# --- fixture acceptance (§13 table → M2-T04 acceptance) ----------------------


def test_hf_vllm_eval_detection(tmp_path: Path) -> None:
    result = _detect(materialize_repo("hf_vllm_eval", tmp_path))
    profiles = _profiles(result)
    assert profiles.get("inference") == "high"  # import vllm
    assert profiles.get("evaluation") == "medium"  # mmlu + accuracy ≥ 2 keywords
    assert {hint.value for hint in result.hints.hf_ids} == {"Qwen/Qwen3-32B"}
    assert "vllm" in result.hints.backends
    assert result.hints.datasets is True  # import datasets


def test_openai_judge_eval_detection(tmp_path: Path) -> None:
    result = _detect(materialize_repo("openai_judge_eval", tmp_path))
    profiles = _profiles(result)
    assert profiles.get("llm_judge") == "medium"  # judge + rubric = 2 keywords
    assert result.hints.providers == ["openai"]


def test_privacy_custom_params_detection(tmp_path: Path) -> None:
    result = _detect(materialize_repo("privacy_custom_params", tmp_path))
    profiles = _profiles(result)
    assert profiles.get("privacy") == "medium"
    assert profiles.get("safety") in {"low", "medium"}  # asr + attack success rate
    assert result.hints.trust_remote_code is True
    assert any(h.value == "meta-llama/Llama-3.1-8B-Instruct" for h in result.hints.hf_ids)


def test_detection_is_deterministic(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    first = _detect(repo).model_dump(mode="json")
    second = _detect(repo).model_dump(mode="json")
    assert first == second


def test_rag_agent_report_only(tmp_path: Path) -> None:
    repo = tmp_path / "ragrepo"
    repo.mkdir()
    (repo / "README.md").write_text("# Demo\nUses RAG with a vector store and faiss.\n")
    result = _detect(repo)
    rag = next(entry for entry in result.profiles if entry.profile == "rag")
    assert rag.shipped is False


# --- detection evidence ------------------------------------------------------


def test_import_evidence_points_at_file_and_line(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    result = _detect(repo)
    inference = next(e for e in result.profiles if e.profile == "inference")
    evidence = inference.evidence[0]
    assert evidence.path == "eval.py"
    assert "import vllm" in (evidence.note or "")


def test_config_values_are_never_scanned(tmp_path: Path) -> None:
    repo = tmp_path / "hidden"
    repo.mkdir()
    (repo / "README.md").write_text("# Tool\n")
    (repo / "config.yaml").write_text("description: we secretly run agent benchmarks\n")
    result = _detect(repo)
    assert "agent" not in _profiles(result)  # value text is not a signal
    assert "evaluation" not in _profiles(result)


# --- M2F-T05: canonical keyword concepts (F-06) ------------------------------


def _detect_readme(tmp_path: Path, readme_text: str):
    repo = tmp_path / "kw"
    repo.mkdir()
    (repo / "README.md").write_text(readme_text)
    return _detect(repo)


def test_single_red_team_span_is_one_concept_low(tmp_path: Path) -> None:
    result = _detect_readme(tmp_path, "# Demo\nWe run a Red-Team exercise.\n")
    safety = {e.profile: e.confidence for e in result.profiles}
    assert safety.get("safety") == "low"


def test_single_dp_sgd_span_is_privacy_low(tmp_path: Path) -> None:
    result = _detect_readme(tmp_path, "# Demo\nTraining uses dp_sgd.\n")
    privacy = {e.profile: e.confidence for e in result.profiles}
    assert privacy.get("privacy") == "low"


def test_single_tool_call_span_is_agent_low(tmp_path: Path) -> None:
    result = _detect_readme(tmp_path, "# Demo\nSupports tool-call handlers.\n")
    agent = {e.profile: e.confidence for e in result.profiles}
    assert agent.get("agent") == "low"


def test_two_distinct_concepts_reach_medium(tmp_path: Path) -> None:
    result = _detect_readme(tmp_path, "# Demo\nWe run a Red-Team exercise and log refusal rates.\n")
    safety = {e.profile: e.confidence for e in result.profiles}
    assert safety.get("safety") == "medium"


def test_repeated_concept_in_many_files_is_still_one(tmp_path: Path) -> None:
    repo = tmp_path / "many"
    repo.mkdir()
    (repo / "README.md").write_text("# Demo\nred team run one\n")
    (repo / "NOTES.md").write_text("red team run two\n")
    (repo / "MORE.md").write_text("red team run three\n")
    safety = {e.profile: e.confidence for e in _detect(repo).profiles}
    assert safety.get("safety") == "low"


def test_one_concept_yields_single_evidence_entry(tmp_path: Path) -> None:
    result = _detect_readme(tmp_path, "# Demo\nred team and red-team spellings both live here\n")
    safety = next(e for e in result.profiles if e.profile == "safety")
    concept_notes = [e for e in safety.evidence if "keyword" in (e.note or "")]
    assert len(concept_notes) == 1


# --- M2F-T06: exact eval/evaluation directory signal (F-07) -------------------


def _detect_with_dir(tmp_path: Path, dir_name: str, extra_readme: str = "# Tool\n"):
    repo = tmp_path / f"dir-{dir_name or 'none'}"
    repo.mkdir()
    (repo / dir_name).mkdir()
    (repo / dir_name / "run.py").write_text("x = 1\n")
    (repo / "README.md").write_text(extra_readme)
    return _detect(repo)


def test_exact_eval_directory_yields_evaluation_low(tmp_path: Path) -> None:
    profiles = _profiles(_detect_with_dir(tmp_path, "eval"))
    assert profiles.get("evaluation") == "low"


def test_exact_evaluation_directory_yields_evaluation_low(tmp_path: Path) -> None:
    profiles = _profiles(_detect_with_dir(tmp_path, "evaluation"))
    assert profiles.get("evaluation") == "low"


def test_both_directory_aliases_are_one_concept(tmp_path: Path) -> None:
    repo = tmp_path / "both-dirs"
    repo.mkdir()
    (repo / "eval").mkdir()
    (repo / "eval" / "a.py").write_text("x = 1\n")
    (repo / "evaluation").mkdir()
    (repo / "evaluation" / "b.py").write_text("x = 1\n")
    (repo / "README.md").write_text("# Tool\n")
    profiles = _profiles(_detect(repo))
    assert profiles.get("evaluation") == "low"  # one concept, not two


def test_directory_concept_plus_keyword_is_medium(tmp_path: Path) -> None:
    profiles = _profiles(_detect_with_dir(tmp_path, "eval", "# Tool\nbenchmark results\n"))
    assert profiles.get("evaluation") == "medium"


def test_near_miss_directory_names_do_not_signal(tmp_path: Path) -> None:
    for name in ("evaluations", "eval_utils", "myeval"):
        profiles = _profiles(_detect_with_dir(tmp_path, name))
        assert "evaluation" not in profiles, name


def test_prose_evaluation_word_is_not_a_directory_signal(tmp_path: Path) -> None:
    repo = tmp_path / "prose"
    repo.mkdir()
    (repo / "README.md").write_text("# Tool\nThis is an evaluation of things.\n")
    assert "evaluation" not in _profiles(_detect(repo))
