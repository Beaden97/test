"""
Input Validation for Gmail Cleanup API

Simple schema-based validation for request parameters.
"""

from functools import wraps
from flask import request
from .errors import APIError, ErrorCode


class Schema:
    """Simple validation schema builders."""

    @staticmethod
    def string(min_len=0, max_len=None, required=False, default=None):
        return {
            'type': 'string',
            'min_len': min_len,
            'max_len': max_len,
            'required': required,
            'default': default
        }

    @staticmethod
    def integer(min_val=None, max_val=None, required=False, default=None):
        return {
            'type': 'integer',
            'min': min_val,
            'max': max_val,
            'required': required,
            'default': default
        }

    @staticmethod
    def list_of(item_type, min_len=0, max_len=None, required=False):
        return {
            'type': 'list',
            'item_type': item_type,
            'min_len': min_len,
            'max_len': max_len,
            'required': required
        }

    @staticmethod
    def boolean(required=False, default=None):
        return {'type': 'boolean', 'required': required, 'default': default}


def validate(value, schema, field_name):
    """Validate a single value against schema."""
    if value is None:
        if schema.get('required'):
            raise APIError(
                message=f"Field '{field_name}' is required",
                code=ErrorCode.VALIDATION_ERROR
            )
        return schema.get('default')

    if schema['type'] == 'string':
        if not isinstance(value, str):
            raise APIError(
                message=f"Field '{field_name}' must be a string",
                code=ErrorCode.VALIDATION_ERROR
            )
        if schema.get('min_len') and len(value) < schema['min_len']:
            raise APIError(
                message=f"Field '{field_name}' must be at least {schema['min_len']} characters",
                code=ErrorCode.VALIDATION_ERROR
            )
        if schema.get('max_len') and len(value) > schema['max_len']:
            raise APIError(
                message=f"Field '{field_name}' must be at most {schema['max_len']} characters",
                code=ErrorCode.VALIDATION_ERROR
            )

    elif schema['type'] == 'integer':
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise APIError(
                message=f"Field '{field_name}' must be an integer",
                code=ErrorCode.VALIDATION_ERROR
            )
        if schema.get('min') is not None and value < schema['min']:
            raise APIError(
                message=f"Field '{field_name}' must be at least {schema['min']}",
                code=ErrorCode.VALIDATION_ERROR
            )
        if schema.get('max') is not None and value > schema['max']:
            raise APIError(
                message=f"Field '{field_name}' must be at most {schema['max']}",
                code=ErrorCode.VALIDATION_ERROR
            )

    elif schema['type'] == 'list':
        if not isinstance(value, list):
            raise APIError(
                message=f"Field '{field_name}' must be a list",
                code=ErrorCode.VALIDATION_ERROR
            )
        if schema.get('min_len') and len(value) < schema['min_len']:
            raise APIError(
                message=f"Field '{field_name}' must have at least {schema['min_len']} items",
                code=ErrorCode.VALIDATION_ERROR
            )
        if schema.get('max_len') and len(value) > schema['max_len']:
            raise APIError(
                message=f"Field '{field_name}' must have at most {schema['max_len']} items",
                code=ErrorCode.VALIDATION_ERROR
            )

    elif schema['type'] == 'boolean':
        if isinstance(value, str):
            value = value.lower() in ('true', '1', 'yes')
        elif not isinstance(value, bool):
            raise APIError(
                message=f"Field '{field_name}' must be a boolean",
                code=ErrorCode.VALIDATION_ERROR
            )

    return value


def validate_query(**schemas):
    """Decorator to validate query parameters."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            validated = {}
            for field, schema in schemas.items():
                value = request.args.get(field)
                validated[field] = validate(value, schema, field)
            kwargs['validated'] = validated
            return f(*args, **kwargs)
        return decorated
    return decorator


def validate_body(**schemas):
    """Decorator to validate JSON body."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            body = request.get_json() or {}
            validated = {}
            for field, schema in schemas.items():
                value = body.get(field)
                validated[field] = validate(value, schema, field)
            kwargs['validated'] = validated
            return f(*args, **kwargs)
        return decorated
    return decorator
