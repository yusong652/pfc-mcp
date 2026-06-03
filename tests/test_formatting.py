"""Unit tests for pfc_mcp.formatting display helpers."""

from pfc_mcp.formatting import format_elapsed_seconds


def test_rounds_full_precision_float_to_two_decimals():
    # The bridge reports elapsed wall-clock at full float precision.
    assert format_elapsed_seconds(0.010000944137573242) == 0.01
    assert format_elapsed_seconds(5.236) == 5.24


def test_keeps_value_numeric_not_stringified():
    result = format_elapsed_seconds(1.5)
    assert isinstance(result, float)


def test_integer_input_is_accepted():
    assert format_elapsed_seconds(3) == 3.0


def test_none_passes_through():
    assert format_elapsed_seconds(None) is None


def test_unparseable_value_becomes_none():
    assert format_elapsed_seconds("5.0s") is None
