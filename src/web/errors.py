"""
Standardized Error Handling for Gmail Cleanup API

Provides consistent error responses across all endpoints.
"""

from functools import wraps
from dataclasses import dataclass
from typing import Optional
import traceback

from flask import jsonify


@dataclass
class APIError(Exception):
    """Standardized API error."""
    message: str
    code: str
    status_code: int = 400
    details: Optional[dict] = None


class ErrorCode:
    """Standard error codes."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    RATE_LIMITED = "RATE_LIMITED"
    GMAIL_ERROR = "GMAIL_API_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


def error_response(error: APIError):
    """Create standardized error response."""
    response = {
        "success": False,
        "error": {
            "code": error.code,
            "message": error.message,
        }
    }
    if error.details:
        response["error"]["details"] = error.details
    return jsonify(response), error.status_code


def success_response(data: dict, meta: dict = None):
    """Create standardized success response."""
    response = {
        "success": True,
        "data": data
    }
    if meta:
        response["meta"] = meta
    return jsonify(response)


def handle_errors(f):
    """Decorator for consistent error handling."""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except APIError as e:
            return error_response(e)
        except ValueError as e:
            return error_response(APIError(
                message=str(e),
                code=ErrorCode.VALIDATION_ERROR,
                status_code=400
            ))
        except Exception as e:
            # Log the full traceback
            print(f"Unhandled error: {traceback.format_exc()}")
            return error_response(APIError(
                message="An internal error occurred",
                code=ErrorCode.INTERNAL_ERROR,
                status_code=500
            ))
    return decorated
