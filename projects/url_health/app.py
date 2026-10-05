"""Check an HTTP(S) endpoint using the standard library and a bounded timeout."""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class HealthResult:
    url: str
    status_code: int | None
    elapsed_ms: float
    error: str | None = None

    @property
    def healthy(self) -> bool:
        return self.status_code is not None and 200 <= self.status_code < 400 and self.error is None


def validate_url(url: str) -> str:
    """Accept only absolute HTTP(S) URLs without embedded credentials."""
    candidate = url.strip()
    try:
        parsed = urlsplit(candidate)
        valid = (
            parsed.scheme.lower() in {"http", "https"}
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("provide an absolute http:// or https:// URL without embedded credentials")
    return candidate


def _status(url: str, method: str, timeout: float) -> int:
    request = Request(
        url, method=method, headers={"User-Agent": "python-playground-url-health/1.0"}
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return int(response.getcode())
    except HTTPError as exc:
        return int(exc.code)


def check_url(url: str, timeout: float = 5.0) -> HealthResult:
    candidate = validate_url(url)
    if not 0.1 <= timeout <= 60:
        raise ValueError("timeout must be between 0.1 and 60 seconds")
    start = time.monotonic()
    try:
        status = _status(candidate, "HEAD", timeout)
        if status in {405, 501}:
            status = _status(candidate, "GET", timeout)
        return HealthResult(candidate, status, (time.monotonic() - start) * 1000)
    except (URLError, TimeoutError, OSError) as exc:
        return HealthResult(candidate, None, (time.monotonic() - start) * 1000, str(exc))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="absolute HTTP(S) URL to check")
    parser.add_argument(
        "--timeout", type=float, default=5.0, help="per-request timeout in seconds (0.1–60)"
    )
    args = parser.parse_args(argv)
    try:
        result = check_url(args.url, args.timeout)
    except ValueError as exc:
        parser.error(str(exc))
    if result.error:
        print(f"ERROR {result.url}: {result.error} ({result.elapsed_ms:.1f} ms)")
    else:
        print(f"HTTP {result.status_code} {result.url} ({result.elapsed_ms:.1f} ms)")
    return 0 if result.healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
