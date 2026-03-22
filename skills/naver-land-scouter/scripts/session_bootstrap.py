from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List
from urllib.parse import urljoin

import httpx

DEFAULT_BOOTSTRAP_PATH = (
    "/complexes?ms=37.269736,127.075797,17&a=APT:ABYG:JGC:PRE&e=RETAIL"
)
DEFAULT_ARTICLE_BOOTSTRAP_PATH = (
    "/complexes/10359?ms=37.269736,127.075797,17&a=APT:ABYG:JGC:PRE&e=RETAIL"
)


class SessionBootstrapError(Exception):
    pass


@dataclass
class SessionBootstrapResult:
    strategy: str
    visited_paths: List[str] = field(default_factory=list)
    cookies: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)


def bootstrap_http_session(
    client: httpx.Client,
    bootstrap_path: str = DEFAULT_BOOTSTRAP_PATH,
) -> SessionBootstrapResult:
    visited_paths: List[str] = []
    for path in _iter_bootstrap_paths(bootstrap_path):
        try:
            client.get(path, follow_redirects=True)
        except httpx.HTTPError as exc:
            raise SessionBootstrapError(
                f"HTTP 세션 부트스트랩에 실패했습니다: {path}"
            ) from exc
        visited_paths.append(path)

    return SessionBootstrapResult(
        strategy="http",
        visited_paths=visited_paths,
        cookies=_extract_cookie_map(client.cookies),
    )


def bootstrap_browser_session(
    base_url: str,
    headers: Dict[str, str],
    bootstrap_path: str = DEFAULT_BOOTSTRAP_PATH,
    capture_api_path_prefixes: List[str] | None = None,
    timeout_ms: int = 15000,
) -> SessionBootstrapResult:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SessionBootstrapError(
            "Playwright가 설치되어 있지 않아 브라우저 부트스트랩을 사용할 수 없습니다."
        ) from exc

    visited_paths: List[str] = []
    bootstrap_url = _build_absolute_url(base_url, bootstrap_path)
    root_url = _build_absolute_url(base_url, "/")
    captured_request_headers: Dict[str, str] = {}

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=headers.get("User-Agent"),
                locale="ko-KR",
                extra_http_headers=_filter_browser_headers(headers),
            )
            page = context.new_page()
            if capture_api_path_prefixes:
                page.on(
                    "request",
                    lambda request: _capture_request_headers(
                        captured_request_headers,
                        request.url,
                        request.headers,
                        capture_api_path_prefixes,
                    ),
                )
            page.goto(root_url, wait_until="domcontentloaded", timeout=timeout_ms)
            visited_paths.append("/")
            page.goto(bootstrap_url, wait_until="domcontentloaded", timeout=timeout_ms)
            visited_paths.append(bootstrap_path)
            # 네이버 측 스크립트가 쿠키를 심을 시간을 짧게 준다.
            page.wait_for_timeout(1500)

            cookies = {
                cookie["name"]: cookie["value"] for cookie in context.cookies()
            }
            runtime_headers = {
                "User-Agent": page.evaluate("() => navigator.userAgent"),
                "Referer": bootstrap_url,
            }
            if "authorization" in captured_request_headers:
                runtime_headers["Authorization"] = captured_request_headers[
                    "authorization"
                ]
            browser.close()
    except PlaywrightError as exc:
        raise SessionBootstrapError("브라우저 세션 부트스트랩에 실패했습니다.") from exc

    return SessionBootstrapResult(
        strategy="browser",
        visited_paths=visited_paths,
        cookies=cookies,
        headers=runtime_headers,
    )


def _iter_bootstrap_paths(bootstrap_path: str) -> Iterable[str]:
    seen: set[str] = set()
    for path in ["/", bootstrap_path]:
        if path in seen:
            continue
        seen.add(path)
        yield path


def _extract_cookie_map(cookies: httpx.Cookies) -> Dict[str, str]:
    return {cookie.name: cookie.value for cookie in cookies.jar}


def _build_absolute_url(base_url: str, path: str) -> str:
    normalized_base_url = base_url.rstrip("/") + "/"
    return urljoin(normalized_base_url, path.lstrip("/"))


def _filter_browser_headers(headers: Dict[str, str]) -> Dict[str, str]:
    allowed_keys = {"Accept-Language", "Referer"}
    return {
        key: value
        for key, value in headers.items()
        if key in allowed_keys and value
    }


def _capture_request_headers(
    captured_headers: Dict[str, str],
    request_url: str,
    request_headers: Dict[str, str],
    path_prefixes: List[str],
) -> None:
    if captured_headers.get("authorization"):
        return
    if not any(prefix in request_url for prefix in path_prefixes):
        return
    authorization = request_headers.get("authorization")
    if authorization:
        captured_headers["authorization"] = authorization
