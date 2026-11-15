# tests/rhosocial/activerecord_mariadb_test/feature/backend/adapters/test_json_adapter_hooks.py
"""DB-free coverage for the optional ``default`` / ``object_hook`` hooks.

``MariaDBJSONAdapter`` forwards these to ``json.dumps`` / ``json.loads`` so a
neutral-type codec (``rhosocial.activerecord.backend.adapters.json_codec``) can
be plugged in.  Every test here runs without a MariaDB connection.
"""

import json

import pytest

from rhosocial.activerecord.backend.impl.mariadb.adapters import MariaDBJSONAdapter


class FakePoint:
    """Minimal fake neutral type: ``to_json_value`` encodes, ``from_json_value`` decodes."""

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def to_json_value(self):
        return {"x": self.x, "y": self.y}

    @classmethod
    def from_json_value(cls, value):
        return cls(value["x"], value["y"])

    def __eq__(self, other):
        return isinstance(other, FakePoint) and (self.x, self.y) == (other.x, other.y)

    def __repr__(self):
        return f"FakePoint({self.x}, {self.y})"


_MARKER = "__fake_point__"


def _fake_default(obj):
    """Encode ``FakePoint`` under a marker so the hook can recognise it."""
    to_json_value = getattr(obj, "to_json_value", None)
    if not callable(to_json_value):
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
    value = to_json_value()
    return {_MARKER: value} if isinstance(value, dict) else value


def _fake_object_hook(payload):
    """Rebuild ``FakePoint`` when the marker is present; leave other dicts alone."""
    marker = payload.get(_MARKER)
    if not isinstance(marker, dict):
        return payload
    return FakePoint.from_json_value(marker)


SAMPLE = {"name": "zoe", "tags": ["a", "b"], "nested": {"answer": 42}}


class TestNoHooks:
    """An adapter built with no hooks must behave exactly as before."""

    @pytest.fixture
    def adapter(self):
        return MariaDBJSONAdapter()

    def test_serialization_matches_plain_json_dumps(self, adapter):
        assert adapter.to_database(SAMPLE, str) == json.dumps(SAMPLE, ensure_ascii=False)

    def test_non_ascii_is_not_escaped(self, adapter):
        text = adapter.to_database({"city": "北京"}, str)
        assert text == json.dumps({"city": "北京"}, ensure_ascii=False)
        assert "\\u" not in text

    def test_roundtrip(self, adapter):
        text = adapter.to_database(SAMPLE, str)
        assert adapter.from_database(text, dict) == SAMPLE

    def test_list_roundtrip(self, adapter):
        value = [1, "two", {"three": 3}]
        text = adapter.to_database(value, str)
        assert adapter.from_database(text, list) == value

    def test_none_is_preserved(self, adapter):
        assert adapter.to_database(None, str) is None
        assert adapter.from_database(None, dict) is None

    def test_already_decoded_value_passes_through(self, adapter):
        value = {"a": [1, 2]}
        assert adapter.from_database(value, dict) is value

    def test_plain_containers_are_returned(self, adapter):
        decoded = adapter.from_database('{"a": [1, 2]}', dict)
        assert type(decoded) is dict
        assert type(decoded["a"]) is list

    def test_unknown_object_still_raises(self, adapter):
        with pytest.raises(TypeError):
            adapter.to_database({"p": FakePoint(1, 2)}, str)


class TestCustomDefault:
    """``default=`` lets a non-JSON object contribute its own value."""

    def test_custom_value_is_serialized(self):
        adapter = MariaDBJSONAdapter(default=_fake_default)
        text = adapter.to_database({"p": FakePoint(1, 2)}, str)
        assert json.loads(text) == {"p": {_MARKER: {"x": 1, "y": 2}}}

    def test_default_is_not_applied_to_plain_values(self):
        adapter = MariaDBJSONAdapter(default=_fake_default)
        text = adapter.to_database(SAMPLE, str)
        assert json.loads(text) == SAMPLE

    def test_default_keeps_ensure_ascii_false(self):
        adapter = MariaDBJSONAdapter(default=_fake_default)
        text = adapter.to_database({"p": FakePoint("名", "字")}, str)
        assert "名" in text and "字" in text
        assert "\\u" not in text
        assert json.loads(text) == {"p": {_MARKER: {"x": "名", "y": "字"}}}

    def test_unsupported_object_still_raises(self):
        adapter = MariaDBJSONAdapter(default=_fake_default)

        with pytest.raises(TypeError):
            adapter.to_database({"s": {1, 2}}, str)


class TestCustomObjectHook:
    """``object_hook=`` rebuilds the custom value while decoding."""

    def test_hook_restores_custom_value(self):
        adapter = MariaDBJSONAdapter(object_hook=_fake_object_hook)
        decoded = adapter.from_database('{"p": {"__fake_point__": {"x": 1, "y": 2}}}', dict)
        assert decoded == {"p": FakePoint(1, 2)}

    def test_hook_ignores_plain_json(self):
        adapter = MariaDBJSONAdapter(object_hook=_fake_object_hook)
        decoded = adapter.from_database('{"a": [1, 2]}', dict)
        assert decoded == {"a": [1, 2]}
        assert type(decoded) is dict
        assert type(decoded["a"]) is list

    def test_hook_does_not_touch_already_decoded_values(self):
        adapter = MariaDBJSONAdapter(object_hook=_fake_object_hook)
        value = {"p": "still-a-string"}
        assert adapter.from_database(value, dict) is value

    def test_marker_with_unknown_shape_is_left_alone(self):
        adapter = MariaDBJSONAdapter(object_hook=_fake_object_hook)
        decoded = adapter.from_database('{"__fake_point__": "nope"}', dict)
        assert decoded == {"__fake_point__": "nope"}

    def test_default_and_hook_roundtrip(self):
        adapter = MariaDBJSONAdapter(default=_fake_default, object_hook=_fake_object_hook)
        value = {"p": FakePoint(3, 4), "list": [1, 2]}
        text = adapter.to_database(value, str)
        assert adapter.from_database(text, dict) == value


class TestCoreCodecIntegration:
    """The core ``AdapterJSONCodec`` can be used as the pair of hooks."""

    @pytest.fixture
    def codec(self):
        from rhosocial.activerecord.backend.adapters.json_codec import (
            AdapterJSONCodec,
            register_type,
            unregister_type,
        )

        register_type("fake_point", FakePoint)
        try:
            yield AdapterJSONCodec(tagged=True)
        finally:
            unregister_type("fake_point")

    def test_tagged_codec_roundtrip(self, codec):
        adapter = MariaDBJSONAdapter(default=codec.default, object_hook=codec.object_hook)
        text = adapter.to_database({"p": FakePoint(5, 6)}, str)
        assert json.loads(text) == {"p": {"__type__": "fake_point", "x": 5, "y": 6}}
        assert adapter.from_database(text, dict) == {"p": FakePoint(5, 6)}

    def test_tagged_codec_leaves_plain_json_alone(self, codec):
        adapter = MariaDBJSONAdapter(default=codec.default, object_hook=codec.object_hook)
        text = adapter.to_database(SAMPLE, str)
        assert adapter.from_database(text, dict) == SAMPLE
