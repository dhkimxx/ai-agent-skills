from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .naver_land_client import NaverLandApiClient
from .schemas import ApiRequestContext


class DefaultNaverLandRepository:
    def __init__(self, client: NaverLandApiClient) -> None:
        self._client = client

    def fetch_articles_by_complex(
        self, complex_no: str, params: Dict[str, Any]
    ) -> Tuple[Any, ApiRequestContext]:
        endpoint = f"/api/articles/complex/{complex_no}"
        return self._client.get_json(endpoint, params=params)

    def fetch_article_detail(
        self, article_no: str, params: Optional[Dict[str, Any]] = None
    ) -> Tuple[Any, ApiRequestContext]:
        endpoint = f"/api/articles/{article_no}"
        return self._client.get_json(endpoint, params=params)

    def fetch_complex_overview(
        self, complex_no: str
    ) -> Tuple[Any, ApiRequestContext]:
        endpoint = f"/api/complexes/overview/{complex_no}"
        # 동일 엔드포인트가 complexNo 파라미터를 요구하는 케이스가 있어 항상 포함한다.
        return self._client.get_json(endpoint, params={"complexNo": complex_no})

    def fetch_complex_detail(
        self, complex_no: str, params: Optional[Dict[str, Any]] = None
    ) -> Tuple[Any, ApiRequestContext]:
        endpoint = f"/api/complexes/{complex_no}"
        # 기본 파라미터에 complexNo를 넣어 응답 변형을 최소화한다.
        request_params = {"complexNo": complex_no}
        if params:
            request_params.update(params)
        return self._client.get_json(endpoint, params=request_params)

    def fetch_complex_prices(
        self, complex_no: str, params: Dict[str, Any]
    ) -> Tuple[Any, ApiRequestContext]:
        endpoint = f"/api/complexes/{complex_no}/prices"
        return self._client.get_json(endpoint, params=params)

    def fetch_real_trade_records(
        self, complex_no: str, params: Dict[str, Any]
    ) -> Tuple[Any, ApiRequestContext]:
        endpoint = f"/api/complexes/{complex_no}/prices/real"
        return self._client.get_json(endpoint, params=params)

    def fetch_schools(self, complex_no: str) -> Tuple[Any, ApiRequestContext]:
        endpoint = f"/api/complexes/{complex_no}/schools"
        return self._client.get_json(endpoint)

    def fetch_neighborhoods(
        self, params: Dict[str, Any]
    ) -> Tuple[Any, ApiRequestContext]:
        endpoint = "/api/regions/neighborhoods"
        return self._client.get_json(endpoint, params=params)

    def fetch_cortars(
        self, params: Dict[str, Any]
    ) -> Tuple[Any, ApiRequestContext]:
        endpoint = "/api/cortars"
        return self._client.get_json(endpoint, params=params)

    def fetch_complex_markers(
        self, params: Dict[str, Any]
    ) -> Tuple[Any, ApiRequestContext]:
        endpoint = "/api/complexes/single-markers/2.0"
        return self._client.get_json(endpoint, params=params)
