"""Manifest schema tests: V-01 … V-08 positive and negative cases (spec §3.1)."""

import pytest
from pydantic import ValidationError

from reprollm.schemas.manifest import Manifest, validate_field_path


def manifest(**overrides: object) -> dict:
    data: dict = {
        "schema_version": 1,
        "project": {"name": "eval-mmlu"},
        "experiment": {"profiles": ["inference"]},
    }
    data.update(overrides)
    return data


# --- V-01 required keys -----------------------------------------------------


def test_v01_missing_project_fails() -> None:
    with pytest.raises(ValidationError):
        Manifest.model_validate({"schema_version": 1, "experiment": {"profiles": []}})


def test_v01_missing_profiles_fails() -> None:
    with pytest.raises(ValidationError):
        Manifest.model_validate(manifest(experiment={"name": "x"}))


def test_v01_empty_profiles_allowed() -> None:
    m = Manifest.model_validate(manifest(experiment={"profiles": []}))
    assert m.experiment.profiles == []


def test_v01_project_name_pattern() -> None:
    assert Manifest.model_validate(manifest(project={"name": "a" * 64}))
    with pytest.raises(ValidationError):
        Manifest.model_validate(manifest(project={"name": "a" * 65}))
    with pytest.raises(ValidationError):
        Manifest.model_validate(manifest(project={"name": "bad name!"}))


# --- V-02 profile names -----------------------------------------------------


def test_v02_core_must_not_be_listed() -> None:
    with pytest.raises(ValidationError, match="core"):
        Manifest.model_validate(manifest(experiment={"profiles": ["core", "inference"]}))


def test_v02_profile_name_pattern() -> None:
    with pytest.raises(ValidationError):
        Manifest.model_validate(manifest(experiment={"profiles": ["Inference"]}))


# --- V-03 path fields -------------------------------------------------------


@pytest.mark.parametrize(
    "bad_path",
    ["/abs/path", "../escape", "a/../../b", "C:\\models\\qwen", "dir\\file", ""],
)
def test_v03_bad_paths_rejected(bad_path: str) -> None:
    data = manifest(prompts={"system": {"path": bad_path}})
    with pytest.raises(ValidationError, match="prompts.system.path|path"):
        Manifest.model_validate(data)


def test_v03_good_relative_path_passes() -> None:
    m = Manifest.model_validate(manifest(prompts={"system": {"path": "prompts/system.txt"}}))
    assert m.prompts["system"].path == "prompts/system.txt"


def test_v03_path_rules_apply_to_execution_and_datasets() -> None:
    with pytest.raises(ValidationError):
        Manifest.model_validate(manifest(execution={"cwd": "/root"}))
    with pytest.raises(ValidationError):
        Manifest.model_validate(
            manifest(datasets={"eval": {"provider": "local", "id": "data", "files": ["../x"]}})
        )


# --- V-04 prompts exactly one source ---------------------------------------


def test_v04_both_path_and_text_rejected() -> None:
    with pytest.raises(ValidationError, match="path.*text|only one"):
        Manifest.model_validate(manifest(prompts={"system": {"path": "p.txt", "text": "hello"}}))


def test_v04_text_only_allowed() -> None:
    m = Manifest.model_validate(manifest(prompts={"system": {"text": "hello"}}))
    assert m.prompts["system"].text == "hello"


def test_v04_neither_is_the_todo_state_and_loads() -> None:
    m = Manifest.model_validate(manifest(prompts={"system": {}}))
    assert m.prompts["system"].path is None


def test_v04_prompt_format_enum() -> None:
    m = Manifest.model_validate(manifest(prompts={"system": {"text": "hi", "format": "jinja"}}))
    assert m.prompts["system"].format == "jinja"
    with pytest.raises(ValidationError):
        Manifest.model_validate(manifest(prompts={"system": {"text": "hi", "format": "mustache"}}))


# --- V-05 judge references --------------------------------------------------


def test_v05_judge_refs_must_exist() -> None:
    data = manifest(
        evaluation={"metrics": [], "judge": {}},
    )
    with pytest.raises(ValidationError, match="model_ref"):
        Manifest.model_validate(data)


def test_v05_judge_refs_pass_when_keys_exist() -> None:
    m = Manifest.model_validate(
        manifest(
            models={"judge": {"provider": "openai", "id": "gpt-4o"}},
            prompts={"judge": {"text": "grade"}},
            evaluation={"metrics": [], "judge": {}},
        )
    )
    assert m.evaluation is not None
    assert m.evaluation.judge is not None
    assert m.evaluation.judge.model_ref == "judge"


def test_v05_judge_refs_custom_names() -> None:
    m = Manifest.model_validate(
        manifest(
            models={"grader": {"provider": "openai", "id": "gpt-4o"}},
            prompts={"rubric": {"text": "grade"}},
            evaluation={
                "metrics": [],
                "judge": {"model_ref": "grader", "prompt_ref": "rubric"},
            },
        )
    )
    assert m.evaluation is not None
    assert m.evaluation.judge is not None
    assert m.evaluation.judge.model_ref == "grader"


# --- V-06 bindings field paths ----------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "models.primary.id",
        "models.primary.revision",
        "generation.temperature",
        "generation.stop",
        "datasets.eval.sampling.seed",
        "evaluation.judge.params.temperature",
        "custom.privacy_method.alpha",
        "models.primary.params.rotary_scale",
        "artifacts.metadata.note",
        "privacy.mechanism.params.alpha",
    ],
)
def test_v06_valid_field_paths(path: str) -> None:
    validate_field_path(path)


@pytest.mark.parametrize(
    "path",
    [
        "models.*.id",
        "nonexistent.field",
        "generation.nope",
        "generation",
        "models",
        "models.primary",
        "generation.temperature.deeper",
        "",
        "a..b",
    ],
)
def test_v06_invalid_field_paths(path: str) -> None:
    with pytest.raises(ValueError):
        validate_field_path(path)


def test_v06_invalid_binding_key_rejected_in_manifest() -> None:
    data = manifest(bindings={"models.*.id": {"cli": "--model"}})
    with pytest.raises(ValidationError, match="bindings key"):
        Manifest.model_validate(data)


def test_v06_valid_binding_key_accepted() -> None:
    m = Manifest.model_validate(
        manifest(
            bindings={
                "generation.temperature": {
                    "cli": "--temperature",
                    "config": "configs/eval.yaml:sampling.temperature",
                }
            }
        )
    )
    assert m.bindings["generation.temperature"].cli == "--temperature"


# --- V-07 local provider paths ----------------------------------------------


def test_v07_local_model_requires_relative_path() -> None:
    with pytest.raises(ValidationError, match="models.primary.id"):
        Manifest.model_validate(
            manifest(models={"primary": {"provider": "local", "id": "/data/models/qwen"}})
        )
    with pytest.raises(ValidationError, match="local"):
        Manifest.model_validate(manifest(models={"primary": {"provider": "local"}}))


def test_v07_local_model_with_relative_path_passes() -> None:
    m = Manifest.model_validate(
        manifest(models={"primary": {"provider": "local", "id": "models/qwen"}})
    )
    assert m.models["primary"].id == "models/qwen"


# --- V-08 numeric ranges ----------------------------------------------------


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("generation", "temperature", 2.5),
        ("generation", "temperature", -0.1),
        ("generation", "top_p", 0),
        ("generation", "top_p", 1.5),
        ("generation", "max_tokens", 0),
    ],
)
def test_v08_generation_ranges(section: str, field: str, value: float) -> None:
    with pytest.raises(ValidationError):
        Manifest.model_validate(manifest(**{section: {field: value}}))


def test_v08_generation_boundary_values_pass() -> None:
    m = Manifest.model_validate(
        manifest(generation={"temperature": 2.0, "top_p": 1.0, "max_tokens": 1})
    )
    assert m.generation is not None
    assert m.generation.temperature == 2.0


def test_v08_gpu_memory_utilization_range() -> None:
    assert Manifest.model_validate(manifest(inference={"gpu_memory_utilization": 1.0}))
    with pytest.raises(ValidationError):
        Manifest.model_validate(manifest(inference={"gpu_memory_utilization": 0}))
    with pytest.raises(ValidationError):
        Manifest.model_validate(manifest(inference={"gpu_memory_utilization": 1.2}))


# --- structure: unknown keys, role names, custom, ordering -------------------


def test_unknown_top_level_key_names_the_key() -> None:
    with pytest.raises(ValidationError, match="modelz"):
        Manifest.model_validate(manifest(modelz={"x": "y"}))


def test_unknown_nested_key_rejected() -> None:
    with pytest.raises(ValidationError):
        Manifest.model_validate(
            manifest(models={"primary": {"provider": "openai", "id": "gpt-4o", "weight": 1}})
        )


def test_role_key_pattern() -> None:
    assert Manifest.model_validate(manifest(models={"judge_2": {}}))
    with pytest.raises(ValidationError):
        Manifest.model_validate(manifest(models={"1bad": {}}))
    with pytest.raises(ValidationError):
        Manifest.model_validate(manifest(models={"Bad-Role": {}}))


def test_custom_accepts_arbitrary_structure() -> None:
    m = Manifest.model_validate(
        manifest(custom={"privacy_method": {"alpha": 0.25, "notes": ["a", "b"]}})
    )
    assert m.custom["privacy_method"]["alpha"] == 0.25


def test_params_blocks_accept_arbitrary_keys() -> None:
    m = Manifest.model_validate(
        manifest(models={"primary": {"provider": "other", "id": "x", "params": {"k": [1, 2]}}})
    )
    assert m.models["primary"].params == {"k": [1, 2]}


def test_adapter_requires_provider_id_type() -> None:
    ok = manifest(
        models={
            "primary": {
                "provider": "huggingface",
                "id": "Qwen/Qwen3-32B",
                "adapter": {
                    "provider": "peft",
                    "id": "org/qwen-lora",
                    "type": "lora",
                    "rank": 16,
                    "alpha": 32.0,
                    "target_modules": ["q_proj"],
                },
            }
        }
    )
    assert Manifest.model_validate(ok)
    with pytest.raises(ValidationError):
        Manifest.model_validate(
            manifest(
                models={
                    "primary": {
                        "provider": "huggingface",
                        "id": "Qwen/Qwen3-32B",
                        "adapter": {"provider": "peft", "id": "org/qwen-lora"},
                    }
                }
            )
        )


def test_full_manifest_loads_and_keeps_spec_field_order() -> None:
    data = manifest(
        models={
            "primary": {
                "provider": "huggingface",
                "id": "Qwen/Qwen3-32B",
                "revision": "8fa23e7c",
                "tokenizer": {"id": "Qwen/Qwen3-32B", "revision": "8fa23e7c"},
                "dtype": "bfloat16",
                "quantization": "none",
                "trust_remote_code": False,
                "chat_template": {"path": "templates/chat.jinja"},
                "params": {"rope_scaling": None},
            }
        },
        datasets={
            "eval": {
                "provider": "huggingface",
                "id": "cais/mmlu",
                "revision": "b77a9100",
                "subset": "abstract_algebra",
                "split": "test",
                "preprocessing": {"description": "as loaded"},
                "sampling": {"n": 100, "method": "first_n", "seed": 0},
            }
        },
        prompts={"system": {"path": "prompts/system.txt", "format": "plain"}},
        generation={"temperature": 0.0, "top_p": 1.0, "max_tokens": 2048, "seed": 42},
        inference={"backend": "vllm", "dtype": "bfloat16", "tensor_parallel_size": 2},
        training={"method": "lora", "learning_rate": 0.0001, "batch_size": 8},
        evaluation={
            "metrics": [{"name": "accuracy", "implementation": "eval.py"}],
            "aggregation": "mean",
            "repetitions": 1,
            "definitions": {"refusal": "defs/refusal.txt"},
            "query_budget": 100,
        },
        privacy={"threat_model": "honest-but-curious", "mechanism": {"name": "orth_noise"}},
        execution={"command": "python eval.py", "cwd": ".", "seed": 42},
        bindings={"generation.seed": {"cli": "--seed"}},
        custom={"privacy_method": {"alpha": 0.25}},
        artifacts={"outputs": ["outputs/results.json"], "metadata": {"venue": "neurips"}},
    )
    m = Manifest.model_validate(data)
    assert list(m.model_dump().keys()) == [
        "schema_version",
        "project",
        "experiment",
        "models",
        "datasets",
        "prompts",
        "generation",
        "inference",
        "training",
        "evaluation",
        "privacy",
        "execution",
        "bindings",
        "custom",
        "artifacts",
    ]


def test_yaml_round_trip_preserves_field_order() -> None:
    import yaml

    from reprollm.core.yaml_io import dump_yaml

    data = manifest(
        models={"primary": {"provider": "openai", "id": "gpt-4o"}},
        generation={"temperature": 0.7},
    )
    text = dump_yaml(Manifest.model_validate(data))
    reloaded = Manifest.model_validate(yaml.safe_load(text))
    assert reloaded == Manifest.model_validate(data)
    assert dump_yaml(reloaded) == text
