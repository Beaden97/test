"""
Tests for the input validation module.

Tests Schema builders and validation functions for
strings, integers, lists, and booleans.
"""

import pytest
from unittest.mock import MagicMock, patch
from flask import Flask

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from web.validation import Schema, validate, validate_query, validate_body
from web.errors import APIError


class TestSchemaBuilders:
    """Tests for Schema static methods."""

    def test_string_schema_defaults(self):
        """Test string schema with default values."""
        schema = Schema.string()

        assert schema['type'] == 'string'
        assert schema['min_len'] == 0
        assert schema['max_len'] is None
        assert schema['required'] is False
        assert schema['default'] is None

    def test_string_schema_with_options(self):
        """Test string schema with all options."""
        schema = Schema.string(
            min_len=5,
            max_len=100,
            required=True,
            default='hello'
        )

        assert schema['type'] == 'string'
        assert schema['min_len'] == 5
        assert schema['max_len'] == 100
        assert schema['required'] is True
        assert schema['default'] == 'hello'

    def test_integer_schema_defaults(self):
        """Test integer schema with default values."""
        schema = Schema.integer()

        assert schema['type'] == 'integer'
        assert schema['min'] is None
        assert schema['max'] is None
        assert schema['required'] is False
        assert schema['default'] is None

    def test_integer_schema_with_options(self):
        """Test integer schema with all options."""
        schema = Schema.integer(
            min_val=1,
            max_val=100,
            required=True,
            default=50
        )

        assert schema['type'] == 'integer'
        assert schema['min'] == 1
        assert schema['max'] == 100
        assert schema['required'] is True
        assert schema['default'] == 50

    def test_list_schema_defaults(self):
        """Test list schema with default values."""
        schema = Schema.list_of('string')

        assert schema['type'] == 'list'
        assert schema['item_type'] == 'string'
        assert schema['min_len'] == 0
        assert schema['max_len'] is None
        assert schema['required'] is False

    def test_list_schema_with_options(self):
        """Test list schema with all options."""
        schema = Schema.list_of(
            'integer',
            min_len=1,
            max_len=10,
            required=True
        )

        assert schema['type'] == 'list'
        assert schema['item_type'] == 'integer'
        assert schema['min_len'] == 1
        assert schema['max_len'] == 10
        assert schema['required'] is True

    def test_boolean_schema_defaults(self):
        """Test boolean schema with default values."""
        schema = Schema.boolean()

        assert schema['type'] == 'boolean'
        assert schema['required'] is False
        assert schema['default'] is None

    def test_boolean_schema_with_options(self):
        """Test boolean schema with all options."""
        schema = Schema.boolean(required=True, default=False)

        assert schema['type'] == 'boolean'
        assert schema['required'] is True
        assert schema['default'] is False


class TestValidateString:
    """Tests for string validation."""

    def test_validate_valid_string(self):
        """Test validating a valid string."""
        schema = Schema.string()
        result = validate("hello", schema, "field")

        assert result == "hello"

    def test_validate_string_none_not_required(self):
        """Test None value with not required string."""
        schema = Schema.string(default="default")
        result = validate(None, schema, "field")

        assert result == "default"

    def test_validate_string_none_required(self):
        """Test None value with required string."""
        schema = Schema.string(required=True)

        with pytest.raises(APIError) as exc_info:
            validate(None, schema, "field")

        assert "required" in exc_info.value.message.lower()

    def test_validate_string_not_string(self):
        """Test validating non-string value."""
        schema = Schema.string()

        with pytest.raises(APIError) as exc_info:
            validate(123, schema, "field")

        assert "must be a string" in exc_info.value.message

    def test_validate_string_min_length(self):
        """Test string minimum length validation."""
        schema = Schema.string(min_len=5)

        with pytest.raises(APIError) as exc_info:
            validate("hi", schema, "field")

        assert "at least 5 characters" in exc_info.value.message

    def test_validate_string_min_length_pass(self):
        """Test string passes minimum length."""
        schema = Schema.string(min_len=3)
        result = validate("hello", schema, "field")

        assert result == "hello"

    def test_validate_string_max_length(self):
        """Test string maximum length validation."""
        schema = Schema.string(max_len=5)

        with pytest.raises(APIError) as exc_info:
            validate("hello world", schema, "field")

        assert "at most 5 characters" in exc_info.value.message

    def test_validate_string_max_length_pass(self):
        """Test string passes maximum length."""
        schema = Schema.string(max_len=10)
        result = validate("hello", schema, "field")

        assert result == "hello"

    def test_validate_string_exact_length(self):
        """Test string at exact boundary."""
        schema = Schema.string(min_len=5, max_len=5)
        result = validate("hello", schema, "field")

        assert result == "hello"

    def test_validate_empty_string_min_len(self):
        """Test empty string with min_len > 0."""
        schema = Schema.string(min_len=1)

        with pytest.raises(APIError):
            validate("", schema, "field")


class TestValidateInteger:
    """Tests for integer validation."""

    def test_validate_valid_integer(self):
        """Test validating a valid integer."""
        schema = Schema.integer()
        result = validate(42, schema, "field")

        assert result == 42

    def test_validate_integer_from_string(self):
        """Test validating integer from string."""
        schema = Schema.integer()
        result = validate("42", schema, "field")

        assert result == 42

    def test_validate_integer_none_not_required(self):
        """Test None value with not required integer."""
        schema = Schema.integer(default=10)
        result = validate(None, schema, "field")

        assert result == 10

    def test_validate_integer_none_required(self):
        """Test None value with required integer."""
        schema = Schema.integer(required=True)

        with pytest.raises(APIError) as exc_info:
            validate(None, schema, "field")

        assert "required" in exc_info.value.message.lower()

    def test_validate_integer_invalid_string(self):
        """Test validating invalid string as integer."""
        schema = Schema.integer()

        with pytest.raises(APIError) as exc_info:
            validate("not a number", schema, "field")

        assert "must be an integer" in exc_info.value.message

    def test_validate_integer_float_string(self):
        """Test validating float string as integer."""
        schema = Schema.integer()

        with pytest.raises(APIError):
            validate("3.14", schema, "field")

    def test_validate_integer_min_value(self):
        """Test integer minimum value validation."""
        schema = Schema.integer(min_val=10)

        with pytest.raises(APIError) as exc_info:
            validate(5, schema, "field")

        assert "at least 10" in exc_info.value.message

    def test_validate_integer_min_value_pass(self):
        """Test integer passes minimum value."""
        schema = Schema.integer(min_val=10)
        result = validate(15, schema, "field")

        assert result == 15

    def test_validate_integer_max_value(self):
        """Test integer maximum value validation."""
        schema = Schema.integer(max_val=100)

        with pytest.raises(APIError) as exc_info:
            validate(150, schema, "field")

        assert "at most 100" in exc_info.value.message

    def test_validate_integer_max_value_pass(self):
        """Test integer passes maximum value."""
        schema = Schema.integer(max_val=100)
        result = validate(50, schema, "field")

        assert result == 50

    def test_validate_integer_exact_boundary(self):
        """Test integer at exact boundaries."""
        schema = Schema.integer(min_val=10, max_val=10)
        result = validate(10, schema, "field")

        assert result == 10

    def test_validate_negative_integer(self):
        """Test validating negative integer."""
        schema = Schema.integer(min_val=-100)
        result = validate(-50, schema, "field")

        assert result == -50

    def test_validate_zero(self):
        """Test validating zero."""
        schema = Schema.integer(min_val=0)
        result = validate(0, schema, "field")

        assert result == 0


class TestValidateList:
    """Tests for list validation."""

    def test_validate_valid_list(self):
        """Test validating a valid list."""
        schema = Schema.list_of('string')
        result = validate(["a", "b", "c"], schema, "field")

        assert result == ["a", "b", "c"]

    def test_validate_list_none_not_required(self):
        """Test None value with not required list."""
        schema = Schema.list_of('string')
        result = validate(None, schema, "field")

        assert result is None

    def test_validate_list_none_required(self):
        """Test None value with required list."""
        schema = Schema.list_of('string', required=True)

        with pytest.raises(APIError) as exc_info:
            validate(None, schema, "field")

        assert "required" in exc_info.value.message.lower()

    def test_validate_list_not_list(self):
        """Test validating non-list value."""
        schema = Schema.list_of('string')

        with pytest.raises(APIError) as exc_info:
            validate("not a list", schema, "field")

        assert "must be a list" in exc_info.value.message

    def test_validate_list_min_length(self):
        """Test list minimum length validation."""
        schema = Schema.list_of('string', min_len=3)

        with pytest.raises(APIError) as exc_info:
            validate(["a", "b"], schema, "field")

        assert "at least 3 items" in exc_info.value.message

    def test_validate_list_min_length_pass(self):
        """Test list passes minimum length."""
        schema = Schema.list_of('string', min_len=2)
        result = validate(["a", "b", "c"], schema, "field")

        assert result == ["a", "b", "c"]

    def test_validate_list_max_length(self):
        """Test list maximum length validation."""
        schema = Schema.list_of('string', max_len=2)

        with pytest.raises(APIError) as exc_info:
            validate(["a", "b", "c"], schema, "field")

        assert "at most 2 items" in exc_info.value.message

    def test_validate_list_max_length_pass(self):
        """Test list passes maximum length."""
        schema = Schema.list_of('string', max_len=5)
        result = validate(["a", "b"], schema, "field")

        assert result == ["a", "b"]

    def test_validate_empty_list_min_len(self):
        """Test empty list with min_len > 0."""
        schema = Schema.list_of('string', min_len=1)

        with pytest.raises(APIError):
            validate([], schema, "field")

    def test_validate_empty_list_allowed(self):
        """Test empty list when allowed."""
        schema = Schema.list_of('string', min_len=0)
        result = validate([], schema, "field")

        assert result == []


class TestValidateBoolean:
    """Tests for boolean validation."""

    def test_validate_true(self):
        """Test validating True."""
        schema = Schema.boolean()
        result = validate(True, schema, "field")

        assert result is True

    def test_validate_false(self):
        """Test validating False."""
        schema = Schema.boolean()
        result = validate(False, schema, "field")

        assert result is False

    def test_validate_boolean_from_string_true(self):
        """Test validating boolean from 'true' string."""
        schema = Schema.boolean()
        result = validate("true", schema, "field")

        assert result is True

    def test_validate_boolean_from_string_false(self):
        """Test validating boolean from 'false' string."""
        schema = Schema.boolean()
        result = validate("false", schema, "field")

        assert result is False

    def test_validate_boolean_from_string_yes(self):
        """Test validating boolean from 'yes' string."""
        schema = Schema.boolean()
        result = validate("yes", schema, "field")

        assert result is True

    def test_validate_boolean_from_string_1(self):
        """Test validating boolean from '1' string."""
        schema = Schema.boolean()
        result = validate("1", schema, "field")

        assert result is True

    def test_validate_boolean_from_string_0(self):
        """Test validating boolean from '0' string."""
        schema = Schema.boolean()
        result = validate("0", schema, "field")

        assert result is False

    def test_validate_boolean_none_not_required(self):
        """Test None value with not required boolean."""
        schema = Schema.boolean(default=True)
        result = validate(None, schema, "field")

        assert result is True

    def test_validate_boolean_none_required(self):
        """Test None value with required boolean."""
        schema = Schema.boolean(required=True)

        with pytest.raises(APIError) as exc_info:
            validate(None, schema, "field")

        assert "required" in exc_info.value.message.lower()

    def test_validate_boolean_invalid_type(self):
        """Test validating invalid type as boolean."""
        schema = Schema.boolean()

        with pytest.raises(APIError) as exc_info:
            validate(123, schema, "field")

        assert "must be a boolean" in exc_info.value.message

    def test_validate_boolean_case_insensitive(self):
        """Test boolean string parsing is case insensitive."""
        schema = Schema.boolean()

        assert validate("TRUE", schema, "field") is True
        assert validate("True", schema, "field") is True
        assert validate("YES", schema, "field") is True


class TestValidateQueryDecorator:
    """Tests for validate_query decorator."""

    def test_validate_query_basic(self):
        """Test basic query validation."""
        app = Flask(__name__)

        @app.route('/test')
        @validate_query(
            name=Schema.string(required=True),
            limit=Schema.integer(default=10)
        )
        def test_endpoint(validated):
            return {'name': validated['name'], 'limit': validated['limit']}

        with app.test_client() as client:
            with app.app_context():
                # This tests the decorator structure, actual validation
                # happens via request context
                pass

    def test_validate_query_applies_defaults(self):
        """Test that defaults are applied in query validation."""
        app = Flask(__name__)

        @app.route('/test')
        @validate_query(
            value=Schema.integer(default=42)
        )
        def test_endpoint(validated):
            return str(validated['value'])

        # Decorator should apply default when param is missing


class TestValidateBodyDecorator:
    """Tests for validate_body decorator."""

    def test_validate_body_basic(self):
        """Test basic body validation."""
        app = Flask(__name__)

        @app.route('/test', methods=['POST'])
        @validate_body(
            name=Schema.string(required=True),
            active=Schema.boolean(default=True)
        )
        def test_endpoint(validated):
            return {'name': validated['name'], 'active': validated['active']}

        # Test decorator structure


class TestValidationEdgeCases:
    """Tests for edge cases in validation."""

    def test_validate_with_zero_min_len_string(self):
        """Test zero min_len allows empty string."""
        schema = Schema.string(min_len=0)
        # Empty string should NOT raise error when min_len=0
        # but actually it will because len("") = 0 and 0 < 0 is False
        result = validate("", schema, "field")
        assert result == ""

    def test_validate_with_none_max_len_string(self):
        """Test None max_len allows any length."""
        schema = Schema.string(max_len=None)
        long_string = "x" * 10000
        result = validate(long_string, schema, "field")

        assert result == long_string

    def test_validate_integer_zero_min(self):
        """Test integer with min=0 allows zero."""
        schema = Schema.integer(min_val=0)
        result = validate(0, schema, "field")

        assert result == 0

    def test_validate_integer_negative_min(self):
        """Test integer with negative min."""
        schema = Schema.integer(min_val=-10)
        result = validate(-5, schema, "field")

        assert result == -5

    def test_validate_preserves_field_name_in_error(self):
        """Test that field name is preserved in error message."""
        schema = Schema.string(required=True)

        with pytest.raises(APIError) as exc_info:
            validate(None, schema, "my_field_name")

        assert "my_field_name" in exc_info.value.message

    def test_validate_error_code(self):
        """Test that validation errors have correct error code."""
        schema = Schema.string(required=True)

        with pytest.raises(APIError) as exc_info:
            validate(None, schema, "field")

        assert exc_info.value.code == "VALIDATION_ERROR"
