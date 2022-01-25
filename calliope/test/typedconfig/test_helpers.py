from io import StringIO
from pathlib import Path

import pytest
import yaml

from calliope.typedconfig.helpers import _Names, merge_dicts, merge_rules
from calliope.typedconfig.parsers.tree import get_config_t


def test_nonexistent_module():
    # Importing the singleton namespace and misconfiguring it meant all
    # following tests would be affected, and those depending on it would fail.
    # So create an isolated singleton object.
    NS = _Names()
    NS._type_modules = ("nonexistent",)
    with pytest.raises(ValueError):
        NS.types


def test_edit_module_list():
    NS = _Names()
    NS._type_modules = ["typing"]
    assert hasattr(NS.types, "List")
    assert not hasattr(NS.types, "PositiveInt")

    NS.add_modules("type", ["pydantic.types"])
    assert hasattr(NS.types, "PositiveInt")

    with pytest.raises(ValueError, match="types.+"):
        NS.add_modules("types", ["pydantic.types"])


def test_nonconformant_module():
    # modules in the module list are required to have __all__ defined; simulate
    # a non-conformant module by importing one of the internal modules
    NS = _Names()
    NS._type_modules = ("calliope.typedconfig.helpers",)
    with pytest.raises(TypeError):
        NS.types


def test_reload():
    NS = _Names()
    # all default modules loaded
    assert hasattr(NS.types, "List")
    assert hasattr(NS.types, "PositiveInt")
    NS._type_modules = ["typing"]
    NS.reset()
    # pydantic.types is not loaded, so PositiveInt isn't available
    assert hasattr(NS.types, "List")
    assert not hasattr(NS.types, "PositiveInt")


def test_set_confdir():
    NS = _Names()
    spec = {"path": {"type": "ConfFilePath"}}

    config_t = get_config_t(spec)
    with pytest.warns(RuntimeWarning, match=".+confdir not set.+"):
        with pytest.raises(ValueError):
            config_t(path="foo.yaml")

    confdir = Path(__file__).parent / "conf"
    NS.set_confdir(confdir)
    config_t = get_config_t(spec)
    assert config_t.from_yaml(f"{confdir}/main.yaml").path


def test_merge():
    # merg_dicts is tested in docstring
    d1 = {"a": 1, "b": {"c": 3, "d": 4}, "e": True}
    d2 = {"c": 3, "b": {"e": 5, "d": 40}, "e": {"g": True, "h": "foo"}}
    # - e & b.d tests overwriting values
    # - b, e & b.d tests key ordering
    # - e & e.* tests adding new sub-keys
    expected = {
        "a": 1,
        "b": {"c": 3, "d": 40, "e": 5},
        "e": {"g": True, "h": "foo"},
        "c": 3,
    }

    streams = [StringIO(), StringIO()]
    for i, d in enumerate((d1, d2)):
        yaml.dump(d, streams[i])
        streams[i].seek(0)

    result = merge_rules(streams, yaml.safe_load)
    assert result == expected
    # check order
    assert list(result) == list(expected)
    assert list(result["b"]) == list(expected["b"])
