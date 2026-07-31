import pytest

from debug_terminal import parse_request_tokens


def test_parse_request_tokens_supports_json_query_and_headers():
    spec = parse_request_tokens(
        [
            "post",
            "/api/v1/auth/login",
            "--json",
            '{"username":"admin","password":"admin123"}',
            "--query",
            "debug=true",
            "--header",
            "X-Trace-Id=local",
        ]
    )

    assert spec.method == "POST"
    assert spec.json_body == {"username": "admin", "password": "admin123"}
    assert spec.query == {"debug": "true"}
    assert spec.headers == {"X-Trace-Id": "local"}


def test_parse_request_tokens_normalizes_path_and_supports_multipart():
    spec = parse_request_tokens(
        [
            "POST",
            "api/v1/data/upload?source=terminal",
            "--file",
            "data.xlsx",
            "--file-field",
            "upload",
            "--form",
            "mode=replace",
            "--no-auth",
        ]
    )

    assert spec.path == "/api/v1/data/upload?source=terminal"
    assert spec.file_path.name == "data.xlsx"
    assert spec.file_field == "upload"
    assert spec.form == {"mode": "replace"}
    assert spec.use_auth is False


@pytest.mark.parametrize(
    "tokens, message",
    [
        (["GET"], "用法"),
        (["TRACE", "/health"], "不支持"),
        (["GET", "/health", "--query", "page"], "key=value"),
        (["POST", "/x", "--json", "{}", "--form", "x=y"], "不能"),
        (["GET", "https://example.test/api"], "当前 Flask 应用"),
    ],
)
def test_parse_request_tokens_rejects_invalid_input(tokens, message):
    with pytest.raises(ValueError, match=message):
        parse_request_tokens(tokens)
