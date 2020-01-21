import pytest

from sv_mini_atlas.library.urn import URN


def test_urn_no_passage():
    urn = "urn:cts:0:0.0.0:"
    assert URN(urn).to_no_passage == urn


def test_urn_invalid():
    urn = "not:a.urn:"
    with pytest.raises(ValueError) as excinfo:
        URN(urn)
        assert str(excinfo.value) == f"Invalid URN: {urn}"


def test_urn_invalid_label():
    urn = "urn:cts:0:0.0.0:1.1"
    key = 12345
    with pytest.raises(KeyError) as excinfo:
        URN(urn).up_to(key)
        assert str(excinfo.value) == f"Provided key is not recognized: {key}"


def test_urn_invalid_component():
    urn = "urn:cts:0:0.0.0:1.1"
    key = 5
    with pytest.raises(ValueError) as excinfo:
        URN(urn).up_to(key)
        assert str(excinfo.value) == "URN has no component: exemplar"
