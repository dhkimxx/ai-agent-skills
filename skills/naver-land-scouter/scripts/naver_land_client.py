from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, MutableMapping, Optional, Tuple

import httpx

from .schemas import ApiRequestContext
from .session_bootstrap import (
    DEFAULT_ARTICLE_BOOTSTRAP_PATH,
    DEFAULT_BOOTSTRAP_PATH,
    SessionBootstrapError,
    bootstrap_browser_session,
    bootstrap_http_session,
)

DEFAULT_BASE_URL = "https://new.land.naver.com"
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_BACKOFF_BASE_SECONDS = 0.5
DEFAULT_BACKOFF_JITTER_SECONDS = 0.3

DEFAULT_HEADERS: Dict[str, str] = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://new.land.naver.com",
    "Referer": "https://new.land.naver.com/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
}

RETRYABLE_STATUS_CODES = {403, 429, 500, 502, 503, 504}


class NaverLandApiError(Exception):
    pass


class NaverLandHttpError(NaverLandApiError):
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        endpoint: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        response_snippet: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.endpoint = endpoint
        self.params = params
        self.response_snippet = response_snippet


class NaverLandNetworkError(NaverLandApiError):
    def __init__(self, message: str, endpoint: Optional[str] = None) -> None:
        super().__init__(message)
        self.endpoint = endpoint


class NaverLandParseError(NaverLandApiError):
    def __init__(self, message: str, endpoint: Optional[str] = None) -> None:
        super().__init__(message)
        self.endpoint = endpoint


@dataclass
class RetryPolicy:
    max_retries: int = DEFAULT_MAX_RETRIES
    backoff_base_seconds: float = DEFAULT_BACKOFF_BASE_SECONDS
    backoff_jitter_seconds: float = DEFAULT_BACKOFF_JITTER_SECONDS


class NaverLandApiClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        retry_policy: Optional[RetryPolicy] = None,
        cache_store: Optional[MutableMapping[str, Any]] = None,
        bootstrap_mode: str = "auto",
        bootstrap_path: str = DEFAULT_BOOTSTRAP_PATH,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._headers = {**DEFAULT_HEADERS, **(headers or {})}
        self._cookies = cookies or {}
        self._retry_policy = retry_policy or RetryPolicy()
        self._cache_store = cache_store
        self._bootstrap_mode = bootstrap_mode
        self._bootstrap_path = bootstrap_path
        self._manual_cookies_provided = bool(cookies)
        self._http_bootstrapped = False
        self._browser_bootstrapped = False
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=self._timeout_seconds,
            headers=self._headers,
            cookies=self._cookies,
            transport=transport,
        )

    def __enter__(self) -> "NaverLandApiClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def set_headers(self, headers: Dict[str, str]) -> None:
        self._headers.update(headers)
        self._client.headers.update(headers)

    def set_cookies(self, cookies: Dict[str, str]) -> None:
        self._cookies.update(cookies)
        self._client.cookies.update(cookies)

    def get_json(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Any, ApiRequestContext]:
        url = self._normalize_endpoint(endpoint)
        self._prepare_api_session(url)
        cache_key = self._build_cache_key(url, params)

        if self._cache_store is not None and cache_key in self._cache_store:
            cached = self._cache_store[cache_key]
            return cached["data"], cached["context"]

        for attempt in range(self._retry_policy.max_retries + 1):
            try:
                response = self._client.get(url, params=params)
                if response.status_code >= 400:
                    if self._should_upgrade_session(response.status_code):
                        self._upgrade_api_session()
                        continue
                    if (
                        response.status_code in RETRYABLE_STATUS_CODES
                        and attempt < self._retry_policy.max_retries
                    ):
                        # 차단/제한 응답은 즉시 중단보다 지수 백오프가 더 안전하다.
                        self._sleep_with_backoff(attempt)
                        continue
                    raise NaverLandHttpError(
                        "HTTP 오류 응답",
                        status_code=response.status_code,
                        endpoint=url,
                        params=params,
                        response_snippet=response.text[:300],
                    )

                try:
                    data = response.json()
                except json.JSONDecodeError as exc:
                    raise NaverLandParseError(
                        f"JSON 파싱 실패: {exc}", endpoint=url
                    ) from exc

                context = ApiRequestContext(
                    endpoint=url,
                    params=params,
                    http_status=response.status_code,
                    fetched_at=self._utc_now(),
                )

                if self._cache_store is not None:
                    self._cache_store[cache_key] = {"data": data, "context": context}

                return data, context
            except httpx.TimeoutException as exc:
                if attempt < self._retry_policy.max_retries:
                    self._sleep_with_backoff(attempt)
                    continue
                raise NaverLandNetworkError("요청 타임아웃", endpoint=url) from exc
            except httpx.RequestError as exc:
                if attempt < self._retry_policy.max_retries:
                    self._sleep_with_backoff(attempt)
                    continue
                raise NaverLandNetworkError("네트워크 오류", endpoint=url) from exc

        raise NaverLandNetworkError("재시도 한도 초과", endpoint=url)

    def _prepare_api_session(self, endpoint: str) -> None:
        if not endpoint.startswith("/api/"):
            return
        if self._bootstrap_mode == "none":
            return
        if self._manual_cookies_provided:
            return
        if self._bootstrap_mode in {"auto", "http"} and not self._http_bootstrapped:
            self._run_http_bootstrap()
            return
        if self._bootstrap_mode == "browser" and not self._browser_bootstrapped:
            self._run_browser_bootstrap()

    def _should_upgrade_session(self, status_code: int) -> bool:
        if status_code not in {401, 403, 429}:
            return False
        if self._bootstrap_mode == "none":
            return False
        if self._bootstrap_mode == "browser":
            return not self._browser_bootstrapped
        if self._bootstrap_mode == "auto":
            return not self._browser_bootstrapped
        return False

    def _upgrade_api_session(self) -> None:
        if self._bootstrap_mode == "browser":
            self._run_browser_bootstrap()
            return
        if self._bootstrap_mode == "auto":
            self._run_browser_bootstrap()

    def _run_http_bootstrap(self) -> None:
        try:
            bootstrap_http_session(
                client=self._client,
                bootstrap_path=self._bootstrap_path,
            )
            self._cookies = {
                **self._cookies,
                **{cookie.name: cookie.value for cookie in self._client.cookies.jar},
            }
            self._http_bootstrapped = True
        except SessionBootstrapError:
            # 초기 부트스트랩 실패는 치명적이지 않으므로 본 요청에서 한 번 더 판단한다.
            self._http_bootstrapped = False

    def _run_browser_bootstrap(self) -> None:
        bootstrap_path, capture_api_path_prefixes = self._build_browser_bootstrap_context()
        try:
            result = bootstrap_browser_session(
                base_url=self._base_url,
                headers=self._headers,
                bootstrap_path=bootstrap_path,
                capture_api_path_prefixes=capture_api_path_prefixes,
            )
        except SessionBootstrapError:
            self._browser_bootstrapped = False
            return

        if result.headers:
            self.set_headers(result.headers)
        if result.cookies:
            self.set_cookies(result.cookies)
        self._browser_bootstrapped = True

    def _build_browser_bootstrap_context(self) -> tuple[str, list[str]]:
        authorization = self._headers.get("Authorization")
        if authorization:
            return self._bootstrap_path, []

        referer = self._headers.get("Referer", "")
        if "/complexes/" in referer:
            return self._extract_path_from_referer(referer), ["/api/articles/complex/"]

        return DEFAULT_ARTICLE_BOOTSTRAP_PATH, ["/api/articles/complex/"]

    def _extract_path_from_referer(self, referer: str) -> str:
        if referer.startswith(self._base_url):
            return referer[len(self._base_url) :] or "/"
        return self._bootstrap_path

    def _normalize_endpoint(self, endpoint: str) -> str:
        if not endpoint.startswith("/"):
            return f"/{endpoint}"
        return endpoint

    def _build_cache_key(
        self, endpoint: str, params: Optional[Dict[str, Any]]
    ) -> str:
        if not params:
            return endpoint
        normalized_items = sorted((key, str(value)) for key, value in params.items())
        return f"{endpoint}?{normalized_items}"

    def _sleep_with_backoff(self, attempt: int) -> None:
        base = self._retry_policy.backoff_base_seconds
        jitter = self._retry_policy.backoff_jitter_seconds
        sleep_seconds = base * (2**attempt) + random.uniform(0, jitter)
        time.sleep(sleep_seconds)

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
