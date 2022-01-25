from dataclasses import fields
import os
from pathlib import Path

import pytest
from rich.pretty import pprint

from calliope.typedconfig.helpers import NS, merge_rules, read_yaml
from calliope.typedconfig.parsers import get_property
from calliope.typedconfig.parsers.tree import get_config_t, resolve_optional
from calliope.typedconfig.parsers.graph import attr_defaults
from calliope.typedconfig.parsers.graph import properties
from calliope.typedconfig.parsers.graph import nodes
from calliope.typedconfig.parsers.graph import edges

srcdir = Path(__file__).parents[1]


@pytest.fixture
def w_tmp_path(tmp_path):
    cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(cwd)


def test_config(w_tmp_path):
    rules = {
        "backend": {"type": "Literal", "opts": ["pyomo", "gurobi"], "default": "pyomo"},
        "bigM": {"type": "PositiveFloat", "default": 1e9},
        "ensure_feasibility": {"type": "bool", "default": "false"},
        "objective": {
            "type": "Literal",
            "opts": ["minmax_cost_optimization"],
            "default": "minmax_cost_optimization",
        },
        "objective_options": {
            "validator": "minmax_cost_options",
            "cost_class": {
                "type": "Dict",
                "default": {"monetary": 1},
            },
            "sense": {
                "type": "Literal",
                "opts": ["minimize", "maximize"],
                "default": "minimize",
            },
        },
        "operation": {
            "window": {"type": "PositiveInt", "default": 0},
            "horizon": {
                "validator": "range_check",
                "validator_params": {"min_key": "window"},
                "type": "PositiveInt",
                "default": 0,
            },
        },
        "solver": {
            "type": "Literal",
            "opts": ["cbc", "glpk", "gurobi", "cplex"],
            "default": "cbc",
        },
        "zero_threshold": {"type": "PositiveFloat", "default": 1e-10},
        "mode": {
            "type": "Literal",
            "opts": ["plan", "operate"],
            "default": "plan",
        },
        "save_logs": {"type": "DirectoryPath"},  # relative to cwd
        "data_path": {"type": "ConfFilePath"},  # relative to confdir
    }

    conf = {
        "solver": "cbc",
        "ensure_feasibility": True,
        "bigM": "1e6",
        "zero_threshold": "1e-10",
        "mode": "plan",
        "objective": "minmax_cost_optimization",
        "objective_options": {"cost_class": {"monetary": 1}},
        "operation": {"window": 12, "horizon": 24},
        "save_logs": "logs",  # relative to cwd
        "data_path": "foo.csv",  # relative to confdir
    }

    # directories
    (w_tmp_path / "logs").mkdir()
    (w_tmp_path / "conf").mkdir()
    (w_tmp_path / "conf/foo.csv").touch()
    NS.set_confdir("conf/")

    config_t = get_config_t(resolve_optional(rules, conf))
    config = config_t(**conf)

    assert config
    assert config.save_logs.exists()


def test_property():
    prop_confs = [
        srcdir / "typedconfig/conf/techs.yaml",
        srcdir / "test/conf/techs.yaml",
    ]
    prop_conf = merge_rules(prop_confs, read_yaml)
    prop_rules = read_yaml(srcdir / "typedconfig/rules/techs.yaml")

    attrs, defaults = attr_defaults(prop_rules)
    props = properties(attrs, defaults, prop_conf)
    propnames = tuple(props.keys())
    assert "baseprop" == propnames[0]
    assert all(tuple(prop in prop_conf for prop in propnames[1:]))

    node_conf = merge_rules(srcdir / "test/conf/nodes.yaml", read_yaml)
    node_rules = read_yaml(srcdir / "typedconfig/rules/nodes.yaml")
    locations = nodes(node_rules, props, node_conf)
    _locations = {k: v for k, v in locations.items() if k != "basenode"}
    assert len(_locations) == 5
    assert all(
        tuple(
            isinstance(tech, get_property(name))
            for node in _locations.values()
            for name, tech in node.techs.items()
        )
    )
    assert all(tuple(node.coordinates for node in _locations.values()))

    edge_conf = merge_rules(srcdir / "test/conf/links.yaml", read_yaml)
    edge_rules = read_yaml(srcdir / "typedconfig/rules/links.yaml")
    links = edges(edge_rules, props, edge_conf)
    linknames = tuple(links.keys())
    _links = {k: v for k, v in links.items() if k != linknames[0]}
    assert linknames[0] == ("baseedge", "")
    assert len(_links) == 4
    assert all(
        tuple(
            isinstance(tech, get_property(name))
            for edge in _links.values()
            for name, tech in edge.techs.items()
        )
    )
