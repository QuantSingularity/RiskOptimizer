"""
Pagination utilities for optimized data retrieval.
Provides utilities for paginating large datasets in API responses.
"""

import logging
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Union

from flask import request, url_for
from riskoptimizer.core.exceptions import ValidationError
from sqlalchemy.orm import Query

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

T = TypeVar("T")


class PaginatedResult(Generic[T]):
    """Generic paginated result container."""

    def __init__(self, items: List[T], page: int, per_page: int, total: int) -> None:
        """
        Initialize paginated result.

        Args:
            items: List of items in current page
            page: Current page number (1-based)
            per_page: Number of items per page
            total: Total number of items
        """
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        self.has_prev = page > 1
        self.has_next = page < self.pages
        self.prev_page = page - 1 if self.has_prev else None
        self.next_page = page + 1 if self.has_next else None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert paginated result to dictionary.

        Returns:
            Dictionary representation of paginated result
        """
        return {
            "items": self.items,
            "pagination": {
                "page": self.page,
                "per_page": self.per_page,
                "total": self.total,
                "pages": self.pages,
                "has_prev": self.has_prev,
                "has_next": self.has_next,
                "prev_page": self.prev_page,
                "next_page": self.next_page,
            },
        }


def paginate_query(query: Query, page: int = 1, per_page: int = 20) -> PaginatedResult:
    """
    Paginate a SQLAlchemy query.

    Args:
        query: SQLAlchemy query object
        page: Page number (1-based)
        per_page: Number of items per page

    Returns:
        Paginated result

    Raises:
        ValidationError: If pagination parameters are invalid
    """
    if page < 1:
        raise ValidationError("Page number must be positive", "page", page)
    if per_page < 1:
        raise ValidationError("Items per page must be positive", "per_page", per_page)
    if per_page > 100:
        raise ValidationError("Items per page cannot exceed 100", "per_page", per_page)
    total = query.count()
    items = query.limit(per_page).offset((page - 1) * per_page).all()
    return PaginatedResult(items, page, per_page, total)


def paginate_list(
    items: List[T], page: int = 1, per_page: int = 20
) -> PaginatedResult[T]:
    """
    Paginate a list of items.

    Args:
        items: List of items to paginate
        page: Page number (1-based)
        per_page: Number of items per page

    Returns:
        Paginated result

    Raises:
        ValidationError: If pagination parameters are invalid
    """
    if page < 1:
        raise ValidationError("Page number must be positive", "page", page)
    if per_page < 1:
        raise ValidationError("Items per page must be positive", "per_page", per_page)
    if per_page > 100:
        raise ValidationError("Items per page cannot exceed 100", "per_page", per_page)
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    page_items = items[start:end]
    return PaginatedResult(page_items, page, per_page, total)


def get_pagination_params() -> Dict[str, int]:
    """
    Get pagination parameters from request.

    Returns:
        Dictionary with page and per_page parameters
    """
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 20
        if per_page > 100:
            per_page = 100
        return {"page": page, "per_page": per_page}
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid pagination parameters: {str(e)}")
        return {"page": 1, "per_page": 20}


def get_pagination_links(
    endpoint: str, page: int, per_page: int, total: int, **kwargs
) -> Dict[str, Optional[str]]:
    """
    Generate pagination links for API responses.

    Args:
        endpoint: Flask endpoint name
        page: Current page number
        per_page: Number of items per page
        total: Total number of items
        **kwargs: Additional query parameters

    Returns:
        Dictionary with pagination links
    """
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    links: Dict[str, Optional[str]] = {
        "self": None,
        "first": None,
        "prev": None,
        "next": None,
        "last": None,
    }
    if pages > 0:
        links["self"] = url_for(
            endpoint, page=page, per_page=per_page, **kwargs, _external=True
        )
        links["first"] = url_for(
            endpoint, page=1, per_page=per_page, **kwargs, _external=True
        )
        links["last"] = url_for(
            endpoint, page=pages, per_page=per_page, **kwargs, _external=True
        )
        if page > 1:
            links["prev"] = url_for(
                endpoint, page=page - 1, per_page=per_page, **kwargs, _external=True
            )
        if page < pages:
            links["next"] = url_for(
                endpoint, page=page + 1, per_page=per_page, **kwargs, _external=True
            )
    return links


def create_paginated_response(
    items: Union[List[T], Query],
    transform_func: Optional[Callable[[T], Any]] = None,
    page: Optional[int] = None,
    per_page: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Create a standardized paginated response.

    Args:
        items: List of items or SQLAlchemy query to paginate
        transform_func: Function to transform each item (optional)
        page: Page number (optional, defaults to request parameter)
        per_page: Number of items per page (optional, defaults to request parameter)

    Returns:
        Standardized paginated response
    """
    pagination_params = get_pagination_params()
    page = page or pagination_params["page"]
    per_page = per_page or pagination_params["per_page"]
    if isinstance(items, Query):
        paginated = paginate_query(items, page, per_page)
    else:
        paginated = paginate_list(items, page, per_page)
    result_items = paginated.items
    if transform_func:
        result_items = [transform_func(item) for item in result_items]
    response = {
        "status": "success",
        "data": result_items,
        "meta": {
            "pagination": {
                "page": paginated.page,
                "per_page": paginated.per_page,
                "total": paginated.total,
                "pages": paginated.pages,
            }
        },
    }
    if request.endpoint:
        links = get_pagination_links(
            request.endpoint,
            paginated.page,
            paginated.per_page,
            paginated.total,
            **{
                k: v
                for k, v in dict(request.args).items()
                if k not in ["page", "per_page"]
            },
        )
        response["meta"]["links"] = links
    return response
