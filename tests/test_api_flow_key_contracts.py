from __future__ import annotations

import ast
import re
from pathlib import Path


TEST_API_FLOW_PATH = Path(__file__).with_name("test_api_flow.py")

REGISTER_WEB_PASSWORD_PATTERN = re.compile(
    r'register_web_password\([\s\S]*?chave="([A-Z0-9]{3,})"',
    re.S,
)

ENSURE_WEB_USER_EXISTS_PATTERN = re.compile(
    r'ensure_web_user_exists\([\s\S]*?chave="([A-Z0-9]{3,})"',
    re.S,
)


def _iter_test_segments(source: str):
    module = ast.parse(source)
    lines = source.splitlines()
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            yield node.name, "\n".join(lines[node.lineno - 1 : node.end_lineno])


def _collect_duplicate_helper_keys(pattern: re.Pattern[str], source: str) -> dict[str, list[str]]:
    seen: dict[str, list[str]] = {}
    for test_name, segment in _iter_test_segments(source):
        helper_keys = {match.group(1) for match in pattern.finditer(segment)}
        for key in helper_keys:
            seen.setdefault(key, []).append(test_name)
    return {key: tests for key, tests in seen.items() if len(tests) > 1}


def _format_duplicates(duplicates: dict[str, list[str]]) -> str:
    return "\n".join(f"{key}: {' | '.join(tests)}" for key, tests in sorted(duplicates.items()))


def test_test_api_flow_register_web_password_keys_are_unique_across_tests():
    source = TEST_API_FLOW_PATH.read_text(encoding="utf-8")
    duplicates = _collect_duplicate_helper_keys(REGISTER_WEB_PASSWORD_PATTERN, source)

    assert duplicates == {}, (
        "register_web_password(...) nao deve reutilizar chaves fixas entre testes em test_api_flow.py\n"
        f"{_format_duplicates(duplicates)}"
    )


def test_test_api_flow_ensure_web_user_exists_keys_are_unique_across_tests():
    source = TEST_API_FLOW_PATH.read_text(encoding="utf-8")
    duplicates = _collect_duplicate_helper_keys(ENSURE_WEB_USER_EXISTS_PATTERN, source)

    assert duplicates == {}, (
        "ensure_web_user_exists(...) nao deve reutilizar chaves fixas entre testes em test_api_flow.py\n"
        f"{_format_duplicates(duplicates)}"
    )