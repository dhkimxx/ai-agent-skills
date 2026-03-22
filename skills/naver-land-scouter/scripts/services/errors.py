from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..naver_land_client import (
    NaverLandHttpError,
    NaverLandNetworkError,
    NaverLandParseError,
)


@dataclass
class ServiceError(Exception):
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        return f"{self.error_code}: {self.message}"


def build_service_error(
    exc: Exception,
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> ServiceError:
    merged_details: Dict[str, Any] = {}
    if details:
        merged_details.update(details)

    if isinstance(exc, NaverLandHttpError):
        merged_details.update(
            {
                "http_status": exc.status_code,
                "endpoint": exc.endpoint,
                "response_snippet": exc.response_snippet,
            }
        )
        if exc.status_code == 429:
            message = "요청이 너무 많습니다. 헤더/쿠키를 확인하거나 잠시 후 재시도하세요."
        elif exc.status_code == 403:
            message = "접근이 차단되었습니다. 헤더/쿠키를 확인하세요."
        elif exc.status_code == 401:
            message = "익명 인증 헤더 확보에 실패했습니다. 브라우저 부트스트랩을 확인하세요."
    elif isinstance(exc, NaverLandNetworkError):
        merged_details.update({"endpoint": exc.endpoint})
        message = "네트워크 오류가 발생했습니다."
    elif isinstance(exc, NaverLandParseError):
        merged_details.update({"endpoint": exc.endpoint})
        message = "응답 파싱에 실패했습니다."

    return ServiceError(
        error_code=error_code,
        message=message,
        details=merged_details or None,
    )
