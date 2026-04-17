"""Shared utility for converting SQLAlchemy models to Pydantic response schemas."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def model_to_dict(obj: Any, exclude: Optional[set] = None) -> Dict[str, Any]:
    """Convert a SQLAlchemy model instance to a dict with auto-converted types.

    - UUIDs → str
    - datetimes/dates → isoformat str
    - Decimals → float
    - Enums → .value str
    """
    exclude = exclude or set()
    result = {}

    for col in obj.__table__.columns:
        if col.key in exclude:
            continue
        value = getattr(obj, col.key, None)
        result[col.key] = _convert_value(value)

    return result


def model_to_response(obj: Any, schema_cls: Type[T], exclude: Optional[set] = None, **overrides: Any) -> T:
    """Convert a SQLAlchemy model to a Pydantic response schema.

    Usage:
        return model_to_response(company, CompanyResponse, company_name=company.name)
    """
    data = model_to_dict(obj, exclude=exclude)
    data.update(overrides)
    return schema_cls(**data)


def _convert_value(value: Any) -> Any:
    """Convert a single value to JSON-serializable form."""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, 'value') and isinstance(value.value, str):
        # SQLAlchemy enum
        return value.value
    return value
