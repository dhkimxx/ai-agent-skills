from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ServiceError(Exception):
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        return f"{self.error_code}: {self.message}"
