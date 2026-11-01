import httpx
import pytest
from typer.testing import CliRunner

from vigilant_turtle import cli
from vigilant_turtle.sources.ebay import EbayAuthError

runner = CliRunner()


class FailingSource:
    name = "ebay"

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def search(self, keyword: str, limit: int = 50):
        raise self._exc


def _status_error(code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://api.ebay.com/buy/browse/v1/item_summary/search")
    response = httpx.Response(code, request=request)
    return httpx.HTTPStatusError(f"{code}", request=request, response=response)


def _run(monkeypatch, exc: Exception):
    monkeypatch.setattr(cli, "_build_source", lambda name: FailingSource(exc))
    return runner.invoke(cli.app, ["scan", "airpods", "--source", "ebay"])


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (_status_error(401), "eBay returned 401 Unauthorized. Check EBAY_CLIENT_ID and EBAY_CLIENT_SECRET."),
        (_status_error(429), "eBay returned 429 Too Many Requests."),
        (_status_error(500), "eBay returned 500 Internal Server Error."),
        (httpx.ConnectError("connection refused"), "Could not reach eBay: connection refused"),
        (EbayAuthError("eBay auth failed: 401"), "Check EBAY_CLIENT_ID and EBAY_CLIENT_SECRET."),
    ],
)
def test_http_errors_print_clean_message(monkeypatch, exc, expected):
    result = _run(monkeypatch, exc)
    assert result.exit_code == 1
    assert expected in result.output
    assert "Traceback" not in result.output
    assert not isinstance(result.exception, httpx.HTTPError)
