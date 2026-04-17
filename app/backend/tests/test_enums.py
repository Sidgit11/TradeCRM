"""Tests for enum consistency — ensures all enums are proper string enums with lowercase values."""
import enum

import pytest

from app.models import enums


class TestEnumConsistency:
    """All enums must be string enums with lowercase values."""

    def _get_all_enums(self):
        result = []
        for name in dir(enums):
            obj = getattr(enums, name)
            if isinstance(obj, type) and issubclass(obj, enum.Enum) and obj is not enum.Enum:
                result.append((name, obj))
        return result

    def test_all_enums_are_string_enums(self):
        for name, enum_cls in self._get_all_enums():
            assert issubclass(enum_cls, str), f"{name} must be a str enum"

    def test_all_enum_values_lowercase(self):
        for name, enum_cls in self._get_all_enums():
            for member in enum_cls:
                assert member.value == member.value.lower(), (
                    f"{name}.{member.name} value '{member.value}' must be lowercase"
                )

    def test_all_enums_have_at_least_two_values(self):
        for name, enum_cls in self._get_all_enums():
            members = list(enum_cls)
            assert len(members) >= 2, f"{name} must have at least 2 values"

    def test_enum_count(self):
        """Ensure we have all expected enums defined."""
        all_enums = self._get_all_enums()
        assert len(all_enums) >= 18, f"Expected at least 18 enums, got {len(all_enums)}"
