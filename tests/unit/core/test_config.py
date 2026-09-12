"""Config loading defaults and safe validation diagnostics (spec §8, M3-T07)."""

from pathlib import Path

import pytest

from reprollm.core.config import load_config
from reprollm.core.errors import UserError
from reprollm.core.yaml_io import dump_yaml
from reprollm.schemas.config import Config


def _write(root: Path, text: str) -> Path:
    path = root / ".reprollm" / "config.yaml"
    path.parent.mkdir()
    path.write_text(text, encoding="utf-8")
    return path


def test_missing_config_returns_fresh_defaults_without_writing(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    assert config == Config()
    config.audit.show_passed = True
    assert load_config(tmp_path).audit.show_passed is False
    assert not (tmp_path / ".reprollm").exists()


@pytest.mark.parametrize("text", ["", "# use defaults\n", "null\n"])
def test_empty_config_uses_defaults(tmp_path: Path, text: str) -> None:
    _write(tmp_path, text)
    assert load_config(tmp_path) == Config()


def test_config_values_and_reason_are_preserved(tmp_path: Path) -> None:
    reason = "  generated notebooks  "
    _write(
        tmp_path,
        dump_yaml(
            {
                "audit": {
                    "fail_on": "never",
                    "show_passed": True,
                    "ignore": [{"rule": "code.no_untracked", "reason": reason}],
                }
            }
        ),
    )
    config = load_config(tmp_path)
    assert config.audit.fail_on == "never"
    assert config.audit.show_passed is True
    assert config.audit.ignore[0].reason == reason


@pytest.mark.parametrize("reason_entry", [{}, {"reason": ""}, {"reason": " \t\n"}])
def test_invalid_reason_names_its_index_and_rule_without_echoing_config(
    tmp_path: Path, reason_entry: dict[str, str]
) -> None:
    private_text = "PRIVATE_CONFIG_VALUE_DO_NOT_ECHO"
    _write(
        tmp_path,
        dump_yaml(
            {
                "audit": {
                    "ignore": [
                        {"rule": "code.clean_tree", "reason": private_text},
                        {"rule": "code.no_untracked", **reason_entry},
                    ]
                },
                "discover": {"api_key_env": private_text},
            }
        ),
    )
    with pytest.raises(UserError) as excinfo:
        load_config(tmp_path)
    message = str(excinfo.value)
    assert ".reprollm/config.yaml" in message
    assert "audit.ignore.1.reason" in message
    assert "code.no_untracked" in message
    assert private_text not in message
    assert "input_value" not in message
    assert excinfo.value.exit_code == 2


@pytest.mark.parametrize(
    "data,field",
    [
        ({"audit": {"fail_on": "PRIVATE_CONFIG_VALUE_DO_NOT_ECHO"}}, "audit.fail_on"),
        ({"audit": {"ignore": "PRIVATE_CONFIG_VALUE_DO_NOT_ECHO"}}, "audit.ignore"),
        ({"run": {"snapshot_max_bytes": 0}}, "run.snapshot_max_bytes"),
        ({"schema_version": 2}, "schema_version"),
    ],
)
def test_validation_errors_report_field_paths_without_input_values(
    tmp_path: Path, data: dict[str, object], field: str
) -> None:
    _write(tmp_path, dump_yaml(data))
    with pytest.raises(UserError) as excinfo:
        load_config(tmp_path)
    message = str(excinfo.value)
    assert field in message
    assert "PRIVATE_CONFIG_VALUE_DO_NOT_ECHO" not in message
    assert "input_value" not in message


def test_invalid_yaml_does_not_echo_source_lines(tmp_path: Path) -> None:
    _write(tmp_path, "audit: [PRIVATE_CONFIG_VALUE_DO_NOT_ECHO\n")
    with pytest.raises(UserError) as excinfo:
        load_config(tmp_path)
    message = str(excinfo.value)
    assert "YAML" in message
    assert ".reprollm/config.yaml" in message
    assert "PRIVATE_CONFIG_VALUE_DO_NOT_ECHO" not in message


def test_non_mapping_is_user_error(tmp_path: Path) -> None:
    _write(tmp_path, "- PRIVATE_CONFIG_VALUE_DO_NOT_ECHO\n")
    with pytest.raises(UserError, match="mapping") as excinfo:
        load_config(tmp_path)
    assert "PRIVATE_CONFIG_VALUE_DO_NOT_ECHO" not in str(excinfo.value)


def test_unreadable_config_is_user_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write(tmp_path, "schema_version: 1\n")

    def unreadable(*args: object, **kwargs: object) -> str:
        raise PermissionError("PRIVATE_CONFIG_VALUE_DO_NOT_ECHO")

    monkeypatch.setattr(Path, "read_text", unreadable)
    with pytest.raises(UserError) as excinfo:
        load_config(tmp_path)
    assert ".reprollm/config.yaml" in str(excinfo.value)
    assert "PRIVATE_CONFIG_VALUE_DO_NOT_ECHO" not in str(excinfo.value)


def test_directory_at_config_path_is_not_treated_as_absent(tmp_path: Path) -> None:
    (tmp_path / ".reprollm" / "config.yaml").mkdir(parents=True)
    with pytest.raises(UserError, match="config.yaml"):
        load_config(tmp_path)


def test_non_utf8_config_is_user_error(tmp_path: Path) -> None:
    path = _write(tmp_path, "")
    path.write_bytes(b"\xff\xfe")
    with pytest.raises(UserError, match="UTF-8"):
        load_config(tmp_path)
