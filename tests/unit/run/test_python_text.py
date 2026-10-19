"""Python snapshots use lexical scalar boundaries, never cross-statement contexts."""

from pathlib import Path

import pytest

from reprollm.run.privacy import RunPrivacy

pytestmark = pytest.mark.security


def test_python_symbolic_assignment_after_nested_quotes_keeps_exact_source(tmp_path: Path) -> None:
    source = 'print(f"x: {a[\'b\']}")\nopenai.api_key = api_dict["api_key"]\n'
    privacy = RunPrivacy(tmp_path, hostname="", username="")
    assert privacy.text(source, python_source=True) == (source, 0)


def _sanitize(tmp_path: Path, source: str) -> tuple[str, int]:
    from reprollm.run.python_text import redact_python_source

    privacy = RunPrivacy(tmp_path, hostname="private_node", username="private_owner")
    result = redact_python_source(source, lambda value, keys: privacy.text(value, keys=keys))
    assert result is not None
    return result


@pytest.mark.parametrize(
    "source",
    [
        'print(f"x: {a[\'b\']}")\nopenai.api_key = api_dict["api_key"]\n',
        'openai.api_key = api_dict["api_key"]\nprint(f"x: {a[\'b\']}")\n',
        'openai.api_key = api_dict["long_symbolic_lookup_key"]\n',
        "def f(api_key):\n    return api_key\n",
        "message = f\"x: {a['b']} result {value:.2f}\"\n",
        "message = f\"nested {f'x: {a[0]}'}\"\n",
        'path = f"data/{args.bench_name}/model_answer/{args.model_id}.jsonl"\n',
        '"""Save {save_dir}/test_cases.json and {save_dir}/method_config.json."""\n',
        "count //=2\nratio = count /2\nvalue = f\"{count /2} {['[/INST]']}\"\n",
        '值 = "中文"; message = f"x: {a[\'b\']}"\n',
        "safe = r'\\d+\\.\\d+'\n",
        "safe = 'outputs/' 'result.json'\n",
        "# source comment\n\n# another comment\nvalue = None\n",
        'def f(first, second="safe", *, third="safe"):\n    return first\n',
        "def f(first):\n    return first\n",
    ],
)
def test_safe_python_keeps_every_original_byte(tmp_path: Path, source: str) -> None:
    assert _sanitize(tmp_path, source) == (source, 0)


@pytest.mark.parametrize(
    "source, sensitive",
    [
        ('api_key = "demoSecret123"\n', "demoSecret123"),
        ('openai.api_key = "demoSecret123"\n', "demoSecret123"),
        ('config["api_key"] = "demoSecret123"\n', "demoSecret123"),
        ('config = {"api_key": {"nested": ["demoSecret123"]}}\n', "demoSecret123"),
        ('api_key: str = "demoSecret123"\n', "demoSecret123"),
        ('if password := "demoSecret123":\n    pass\n', "demoSecret123"),
        ('def f(password="demoSecret123", *, api_key="demoSecret456"):\n    pass\n', "demoSecret"),
        ('client(password="demoSecret123")\n', "demoSecret123"),
        ("password = 123456789\n", "123456789"),
        ("password = -1234567\n", "1234567"),
        ('password = b"demoSecret123"\n', "demoSecret123"),
        ('password = r"demoSecret123"\n', "demoSecret123"),
        ('password = """demoSecret123"""\n', "demoSecret123"),
        ('password = "demo" "Secret123"\n', "demoSecret123"),
        ('password, safe = "demoSecret123", "keep_this_value"\n', "demoSecret123"),
        ('payload = \'{"api_key": "demoSecret123"}\'\n', "demoSecret123"),
        ('payload = "api_key=demoSecret123"\n', "demoSecret123"),
        ("# api_key=demoSecret123\nvalue = 1\n", "demoSecret123"),
        ('"""api_key=demoSecret123"""\nvalue = 1\n', "demoSecret123"),
        ('值 = "中文"; password = "demoSecret123"\n', "demoSecret123"),
        ("password = f\"demoSecret123{api_dict['api_key']}\"\n", "demoSecret123"),
        ("message = f\"value {'hf_012345678901234567890123'}\"\n", "hf_012345678901234567890123"),
        ("hf_012345678901234567890123 = 1\n", "hf_012345678901234567890123"),
        ('message = f"{hf_012345678901234567890123}"\n', "hf_012345678901234567890123"),
        ("value = private_owner\n", "private_owner"),
        ('message = f"{private_owner.attribute}"\n', "private_owner"),
        ('value = "private_node private_owner"\n', "private_owner"),
    ],
)
def test_python_scalar_context_and_patterns_remain_private(
    tmp_path: Path, source: str, sensitive: str
) -> None:
    import ast

    safe, count = _sanitize(tmp_path, source)
    assert sensitive not in safe and count > 0
    assert _sanitize(tmp_path, safe) == (safe, 0)
    ast.parse(safe)
    if "keep_this_value" in source:
        assert "keep_this_value" in safe


@pytest.mark.parametrize(
    "literal",
    [
        '"/private_owner/cache"',
        'r"C:\\private_owner\\cache"',
        '"C:\\\\private_owner\\\\cache"',
        'r"\\\\private_node\\share\\file"',
        '"file:///private_owner/cache"',
        'f"/private_owner/cache/{name}/suffix"',
        'f"{name}/suffix /private_owner/cache"',
    ],
)
def test_decoded_paths_are_private_and_escaped_syntax_stays_valid(
    tmp_path: Path, literal: str
) -> None:
    safe, count = _sanitize(tmp_path, f"path = {literal}\n")
    assert "private_owner" not in safe and "private_node" not in safe and count > 0
    assert _sanitize(tmp_path, safe) == (safe, 0)


@pytest.mark.parametrize(
    "source",
    [
        'value = "-----BEGIN PRIVATE KEY-----\\nprivate_body\\n-----END PRIVATE KEY-----"\n',
        'value = "-----BEGIN PRIVATE KEY-----\\nprivate_body"\nsafe = "preserve_sibling"\n',
        "# -----BEGIN PRIVATE KEY-----\n# private_body\n# -----END PRIVATE KEY-----\nsafe = 1\n",
        '# -----BEGIN PRIVATE KEY-----\n# private_body\nsafe = "preserve_sibling"\n',
    ],
)
def test_decoded_scalars_and_consecutive_comments_discard_pem_body(
    tmp_path: Path, source: str
) -> None:
    safe, count = _sanitize(tmp_path, source)
    assert "private_body" not in safe and "BEGIN PRIVATE KEY" not in safe and count > 0
    assert _sanitize(tmp_path, safe) == (safe, 0)
    if "preserve_sibling" in source:
        assert "preserve_sibling" in safe


def test_malformed_embedded_context_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        _sanitize(tmp_path, 'payload = \'{"api_key": ["demoSecret123"\'\n')


@pytest.mark.parametrize(
    "source",
    [
        'password = "unfinished',
        "x = " + "[" * 70 + "1" + "]" * 70,
        "x = '" + "a" * 1_048_576 + "'\n",
    ],
)
def test_unsupported_or_excessive_python_returns_no_partial_result(source: str) -> None:
    from reprollm.run.python_text import redact_python_source

    called = []
    assert (
        redact_python_source(source, lambda value, keys: (called.append(value) or value, 0)) is None
    )
    assert called == []


def test_parser_warnings_never_echo_source(tmp_path: Path) -> None:
    import warnings

    source = 'pattern = "\\["\n'
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert _sanitize(tmp_path, source) == (source, 0)
    assert caught == []


@pytest.mark.parametrize(
    "source",
    [
        'password = str("demoSecret123")\n',
        'api_key = helper({"value": "demoSecret123"})\n',
        'password = "demoSecret123".format()\n',
        "password = f\"{str('demoSecret123')}\"\n",
        'password = os.environ.get("ACCESS_TOKEN", "demoSecret123")\n',
        'password = credentials["password"] or "demoSecret123"\n',
    ],
)
def test_nested_rhs_literal_values_keep_secret_assignment_context(
    tmp_path: Path, source: str
) -> None:
    safe, count = _sanitize(tmp_path, source)
    assert "demoSecret123" not in safe and count > 0
    assert _sanitize(tmp_path, safe) == (safe, 0)


@pytest.mark.parametrize(
    "source",
    [
        'api_key = api_dict["access_token"]\n',
        'api_key = os.environ.get("ACCESS_TOKEN")\n',
        'api_key = getattr(config, "access_token")\n',
        "api_key = f\"{api_dict['access_token']}\"\n",
        "api_key = f\"{os.environ.get('ACCESS_TOKEN')}\"\n",
    ],
)
def test_symbolic_lookup_keys_are_locations_under_secret_assignment(
    tmp_path: Path, source: str
) -> None:
    assert _sanitize(tmp_path, source) == (source, 0)


def test_pep701_expression_comments_still_receive_privacy(tmp_path: Path) -> None:
    import sys

    if sys.version_info < (3, 12):
        pytest.skip("PEP 701 expression comments require Python 3.12")
    source = 'text = f"{value  # api_key=demoSecret123\n}"\n'
    safe, count = _sanitize(tmp_path, source)
    assert "demoSecret123" not in safe and count > 0
    assert _sanitize(tmp_path, safe) == (safe, 0)


def test_pep701_comments_do_not_overlap_another_fstring_rewrite(tmp_path: Path) -> None:
    import sys

    if sys.version_info < (3, 12):
        pytest.skip("PEP 701 expression comments require Python 3.12")
    source = 'text = f"private_owner {value  # api_key=demoSecret123\n}"\n'
    safe, count = _sanitize(tmp_path, source)
    assert "demoSecret123" not in safe and "private_owner" not in safe and count > 0
    assert _sanitize(tmp_path, safe) == (safe, 0)


@pytest.mark.parametrize(
    "source",
    [
        'api_key = f"{value}ok"\n',
        'api_key = f"{value}/short"\n',
    ],
)
def test_interpolation_context_never_increases_secret_minimum_length(
    tmp_path: Path, source: str
) -> None:
    assert _sanitize(tmp_path, source) == (source, 0)


@pytest.mark.parametrize("ending", ["\r\n", "\r", "\n"])
def test_python_line_positions_match_actual_lexer_newlines(tmp_path: Path, ending: str) -> None:
    source = f'值 = "first\u2028second"{ending}password = "demoSecret123"{ending}'
    safe, count = _sanitize(tmp_path, source)
    assert "demoSecret123" not in safe and count > 0
    assert f'值 = "first\u2028second"{ending}' in safe
    assert _sanitize(tmp_path, safe) == (safe, 0)


@pytest.mark.parametrize("source", ["number = +True\n", "number = -False\n"])
def test_unary_boolean_is_not_evaluated_as_literal_number(tmp_path: Path, source: str) -> None:
    assert _sanitize(tmp_path, source) == (source, 0)


@pytest.mark.parametrize(
    "expression",
    ["sk-abcdefghijklmnop", "xoxb-abcdefghijklmnop", "sk-proj-abcdefghijklmnop"],
)
def test_value_patterns_crossing_identifier_tokens_remain_private(
    tmp_path: Path, expression: str
) -> None:
    for source in (f"value = {expression}\n", f'value = f"{{{expression}}}"\n'):
        safe, count = _sanitize(tmp_path, source)
        assert "abcdefghijklmnop" not in safe and count > 0
        assert _sanitize(tmp_path, safe) == (safe, 0)


@pytest.mark.parametrize("identity", ["private-node-7", "private.node.test"])
def test_identity_crossing_identifier_tokens_remains_private(tmp_path: Path, identity: str) -> None:
    from reprollm.run.python_text import redact_python_source

    privacy = RunPrivacy(tmp_path, hostname=identity, username="")
    source = f"value = {identity}\n"
    result = redact_python_source(source, lambda value, keys: privacy.text(value, keys=keys))
    assert result is not None
    safe, count = result
    assert identity not in safe and count > 0
    assert privacy.text(safe, python_source=True) == (safe, 0)


def test_jwt_dot_chain_is_checked_as_one_source_value(tmp_path: Path) -> None:
    token = "eyJabcdefghijk.abcdefghijk.abcdefghijk"
    safe, count = _sanitize(tmp_path, f"value = {token}\n")
    assert token not in safe and "abcdefghijk" not in safe and count > 0
    assert _sanitize(tmp_path, safe) == (safe, 0)


@pytest.mark.parametrize(
    "source",
    [
        "api_key = api_dict.method\n",
        "api_key = settings.credentials.access_token\n",
        "value = ordinary_namespace.field.attribute\n",
        "value = first-second-third\n",
    ],
)
def test_safe_identifier_chains_keep_original_bytes(tmp_path: Path, source: str) -> None:
    assert _sanitize(tmp_path, source) == (source, 0)


def test_ast_node_limit_is_checked_before_any_scalar_callback() -> None:
    from reprollm.run.python_text import redact_python_source

    called = []
    source = "value = 1\n" * 3000
    assert (
        redact_python_source(source, lambda value, keys: (called.append(value) or value, 0)) is None
    )
    assert called == []


@pytest.mark.parametrize("callee", ["os.getenv", "os.environ.get"])
def test_stdlib_environment_lookup_keyword_key_is_source_location(
    tmp_path: Path, callee: str
) -> None:
    source = f'api_key = {callee}(key="ACCESS_TOKEN")\n'
    assert _sanitize(tmp_path, source) == (source, 0)


@pytest.mark.parametrize("callee", ["os.getenv", "os.environ.get"])
def test_stdlib_environment_lookup_keyword_default_keeps_secret_context(
    tmp_path: Path, callee: str
) -> None:
    source = f'api_key = {callee}(key="ACCESS_TOKEN", default="demoSecret123")\n'
    safe, count = _sanitize(tmp_path, source)
    assert 'key="ACCESS_TOKEN"' in safe and "demoSecret123" not in safe and count > 0
    assert _sanitize(tmp_path, safe) == (safe, 0)


@pytest.mark.parametrize("method", ["get", "pop", "setdefault", "__getitem__", "getenv"])
def test_unknown_callee_literal_never_loses_secret_assignment_context(
    tmp_path: Path, method: str
) -> None:
    source = f'api_key = unknown.{method}("demoSecret123")\n'
    safe, count = _sanitize(tmp_path, source)
    assert "demoSecret123" not in safe and count > 0
    assert _sanitize(tmp_path, safe) == (safe, 0)


@pytest.mark.parametrize(
    "source",
    [
        'api_key = api_dict.get("demoSecret123")\n',
        'api_key = getenv("demoSecret123")\n',
        'api_key = os.getenv(*["ACCESS_TOKEN", "demoSecret123"])\n',
        'api_key = os.environ.get(*["ACCESS_TOKEN", "demoSecret123"])\n',
        'api_key = builtins.getattr(config, name="demoSecret123")\n',
        'api_key = getattr(config, name="demoSecret123")\n',
    ],
)
def test_unknown_or_ambiguous_lookup_arguments_remain_conservative(
    tmp_path: Path, source: str
) -> None:
    safe, count = _sanitize(tmp_path, source)
    assert "demoSecret123" not in safe and count > 0
    assert _sanitize(tmp_path, safe) == (safe, 0)


@pytest.mark.parametrize("callee", ["getattr", "builtins.getattr"])
def test_builtin_attribute_lookup_positional_name_and_default_are_separate(
    tmp_path: Path, callee: str
) -> None:
    source = f'api_key = {callee}(config, "ACCESS_TOKEN", "demoSecret123")\n'
    safe, count = _sanitize(tmp_path, source)
    assert '"ACCESS_TOKEN"' in safe and "demoSecret123" not in safe and count > 0
    assert _sanitize(tmp_path, safe) == (safe, 0)
