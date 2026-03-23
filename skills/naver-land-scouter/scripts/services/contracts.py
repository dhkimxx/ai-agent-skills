from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, Tuple

from ..schemas import ApiRequestContext


class NaverLandRepository(Protocol):
    def fetch_articles_by_complex(
        self, complex_no: str, params: Dict[str, Any]
    ) -> Tuple[Any, ApiRequestContext]:
        ...

    def fetch_article_detail(
        self, article_no: str, params: Optional[Dict[str, Any]] = None
    ) -> Tuple[Any, ApiRequestContext]:
        ...

    def fetch_complex_overview(
        self, complex_no: str
    ) -> Tuple[Any, ApiRequestContext]:
        ...

    def fetch_complex_detail(
        self, complex_no: str, params: Optional[Dict[str, Any]] = None
    ) -> Tuple[Any, ApiRequestContext]:
        ...

    def fetch_complex_prices(
        self, complex_no: str, params: Dict[str, Any]
    ) -> Tuple[Any, ApiRequestContext]:
        ...

    def fetch_real_trade_records(
        self, complex_no: str, params: Dict[str, Any]
    ) -> Tuple[Any, ApiRequestContext]:
        ...

    def fetch_schools(self, complex_no: str) -> Tuple[Any, ApiRequestContext]:
        ...

    def fetch_neighborhoods(
        self, params: Dict[str, Any]
    ) -> Tuple[Any, ApiRequestContext]:
        ...

    def fetch_cortars(
        self, params: Dict[str, Any]
    ) -> Tuple[Any, ApiRequestContext]:
        ...

    def fetch_complex_markers(
        self, params: Dict[str, Any]
    ) -> Tuple[Any, ApiRequestContext]:
        ...

    def fetch_search(
        self, params: Dict[str, Any]
    ) -> Tuple[Any, ApiRequestContext]:
        ...
