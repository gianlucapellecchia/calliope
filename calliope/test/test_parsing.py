from io import StringIO

import pytest
import ruamel.yaml as yaml
import pyparsing as pp
import xarray as xr

from calliope.backend import parsing, equation_parser
from calliope.test.common.util import check_error_or_warning


SET_NAMES = ["A", "A1"]


def string_to_dict(yaml_string):
    yaml_loader = yaml.YAML(typ="safe", pure=True)
    return yaml_loader.load(StringIO(yaml_string))


def constraint_string(equation_expr):
    setup_string = f"""
    foreach: [a in A, a1 in A1]
    where: []
    equation: "{equation_expr}"
    """

    return string_to_dict(setup_string)


def constraint_string_with_components(n_foo, n_bar):
    foos = ", ".join(
        [f"{{where: ['{i}'], expression: '{i + 1}'}}" for i in range(n_foo)]
    )
    bars = ", ".join(
        [f"{{where: ['{i * 10}'], expression: '{i + 1}0'}}" for i in range(n_bar)]
    )
    setup_string = f"""
    foreach: [a in A, a1 in A1]
    where: []
    equation: "$foo == $bar"
    components:
        foo: [{foos}]
        bar: [{bars}]
    """

    return string_to_dict(setup_string)


@pytest.fixture
def dummy_model_data():
    d = {
        "A": {"dims": ("A"), "data": [1, 2]},
        "A1": {"dims": ("A1"), "data": [10, 20, 30]},
        "A_1": {"dims": ("A_1"), "data": [-1, -2, -3]},
        "techs": {"dims": ("techs"), "data": ["foo1", "bar1", "foobar1"]},
        "foo": {"dims": ("A", "A1"), "data": [["a", "b", "c"], ["d", "e", "f"]]},
        "bar": {"dims": ("A"), "data": [100, 200]},
    }
    return xr.Dataset.from_dict(d)


@pytest.fixture
def dummy_constraint_obj():
    constraint_data = constraint_string("1 == 1")
    return parsing.ParsedConstraint(constraint_data, "foo")


@pytest.fixture
def expression_parser():
    return equation_parser.generate_equation_parser()


@pytest.fixture
def index_item_parser():
    return equation_parser.generate_index_item_parser()


@pytest.fixture
def component_parser():
    return equation_parser.generate_arithmetic_parser()


@pytest.fixture(scope="function")
def constraint_obj_with_sets():
    constraint_obj = parsing.ParsedConstraint(constraint_string("foo == 1"), "foo")
    constraint_obj._get_sets_from_foreach(SET_NAMES)

    return constraint_obj


@pytest.fixture
def constraint_expression_dict():
    def _constraint_expression_dict(parse_string, where_list=None):
        expression_dict = {"expression": parse_string}
        if where_list is not None:
            expression_dict["where"] = where_list
        return expression_dict

    return _constraint_expression_dict


@pytest.fixture
def parsed_equation_list(constraint_obj_with_sets, expression_parser):
    def _parsed_equation_list(expression_list, **kwargs):
        return constraint_obj_with_sets._parse_where_expression(
            expression_parser, expression_list, "my_expr", **kwargs
        )

    return _parsed_equation_list


class TestParsingForEach:
    @pytest.fixture(
        params=[
            ("[a in A]", {"a": "A"}, []),
            ("[a in A, a1 in A1]", {"a": "A", "a1": "A1"}, []),
            ("[a in A, a_2 in A_2]", {"a": "A", "a_2": "A_2"}, ["A_2"]),
            (
                "[a in A, a_2 in A_2, foo in foos]",
                {"a": "A", "a_2": "A_2", "foo": "foos"},
                ["A_2", "foos"],
            ),
        ]
    )
    def constraint_data(self, request, dummy_model_data):
        foreach_string, expected_sets, missing_sets = request.param
        setup_string = f"""
        foreach: {foreach_string}
        where: []
        equation: foo == 0
        """
        constraint_obj = parsing.ParsedConstraint(string_to_dict(setup_string), "foo")
        sets = constraint_obj._get_sets_from_foreach(dummy_model_data.dims)
        return (
            constraint_obj,
            sets,
            expected_sets,
            missing_sets,
        )

    @pytest.fixture
    def foreach_parser(self, dummy_constraint_obj):
        return dummy_constraint_obj._foreach_parser()

    @pytest.mark.parametrize(
        ("input_string", "expected_result"),
        [
            ("a in A", ["a", "A"]),
            ("a1 in A1", ["a1", "A1"]),
            ("a_1 in A_1", ["a_1", "A_1"]),
            # TODO: decide if this should be allowed:
            ("techs in techs", ["techs", "techs"]),
        ],
    )
    def test_parse_foreach(self, foreach_parser, input_string, expected_result):
        parsed_string = foreach_parser.parse_string(input_string, parse_all=True)
        assert parsed_string.as_dict() == {
            "set_iterator": expected_result[0],
            "set_name": expected_result[1],
        }

    @pytest.mark.parametrize(
        "input_string",
        [
            "1 in foo",  # number as iterator
            "foo in 1",  # number as set name
            "1 in 2",  # numbers for both
            "in B",  # missing iterator
            "in",  # missing iterator and set name
            "foo bar",  # missing "in"
            "foo.bar in B",  # unallowed character in iterator .
            "a in foo.bar",  # unallowed character in set name .
            "ainA",  # missing whitespace
            "1a in 2b",  # invalid python identifiers
            "a in A b in B",  # missing deliminator between two set items
            "a in in A",  # duplicated "in"
            "a in in"  # Cannot have "in" as a set iterator/name
            "in in A"  # Cannot have "in" as a set iterator/name
            "in in in",  # Cannot have "in" as a set iterator/name
        ],
    )
    def test_parse_foreach_fail(self, foreach_parser, input_string):
        with pytest.raises(pp.ParseException):
            foreach_parser.parse_string(input_string, parse_all=True)

    def test_parse_foreach_to_sets(self, constraint_data):
        (
            _,
            sets,
            expected_sets,
            _,
        ) = constraint_data
        assert sets == expected_sets

    def test_parse_foreach_to_sets_unknown_set(self, constraint_data):
        constraint_obj, _, _, missing_sets = constraint_data

        if len(missing_sets) == 0:
            assert not constraint_obj._errors
        else:
            assert check_error_or_warning(
                constraint_obj._errors, "not a valid model set name."
            )

    def test_parse_foreach_duplicate_iterators(self):
        setup_string = """
        foreach: [a in A, a in A1]
        where: []
        equation: foo == 0
        """
        constraint_obj = parsing.ParsedConstraint(string_to_dict(setup_string), "foo")
        constraint_obj._get_sets_from_foreach(["A", "A1"])
        assert check_error_or_warning(
            constraint_obj._errors,
            "(foreach, a in A1): Found duplicate set iterator `a`",
        )


class TestParsingEquations:
    @pytest.mark.parametrize(
        "parse_string",
        [
            "foo + bar == 1",
            "foo - $bar + baz[a, a1] <= 1",
            "-1**foo + dummy_func_1(2) + baz[a, a1] >= foobar",
        ],
    )
    def test_parse_string(
        self, constraint_obj_with_sets, expression_parser, parse_string
    ):
        parsed_ = constraint_obj_with_sets._parse_string(
            expression_parser, parse_string, "foo"
        )
        assert isinstance(parsed_, pp.ParseResults)
        assert not constraint_obj_with_sets._errors

    @pytest.mark.parametrize(
        "parse_string",
        ["foo bar == 1", "foo - $bar + baz[foobar] = 1", "1foo == 1", "_foo >= foobar"],
    )
    def test_parse_string_malformed(
        self, constraint_obj_with_sets, expression_parser, parse_string
    ):
        parsed_ = constraint_obj_with_sets._parse_string(
            expression_parser, parse_string, "foo"
        )
        assert parsed_ is None
        assert check_error_or_warning(constraint_obj_with_sets._errors, "Expected")

    @pytest.mark.parametrize(
        "parse_string",
        ["foo == 1", "$foo + (bar + foobar[a1])**2 >= (dummy_func_1(foo) + 1)"],
    )
    @pytest.mark.parametrize(
        ["where_list", "expected_where_list"],
        [
            (None, []),
            ([], []),
            (["bar"], ["bar"]),
            (["bar", "and", "foobar"], ["bar", "and", "foobar"]),
        ],
    )
    def test_parse_where_expression(
        self,
        constraint_obj_with_sets,
        expression_parser,
        constraint_expression_dict,
        parse_string,
        where_list,
        expected_where_list,
    ):
        expression_dict = constraint_expression_dict(parse_string, where_list)
        parsed_list = constraint_obj_with_sets._parse_where_expression(
            expression_parser, [expression_dict], "foo"
        )

        assert parsed_list[0]["where"] == expected_where_list
        assert isinstance(parsed_list[0]["expression"], pp.ParseResults)

    @pytest.mark.parametrize("n_dicts", [1, 2, 3])
    @pytest.mark.parametrize("id_prefix", ["foo", 1])
    def test_parse_where_expression_id_prefix(
        self,
        parsed_equation_list,
        constraint_expression_dict,
        n_dicts,
        id_prefix,
    ):
        expression_dict = constraint_expression_dict("foo == 1", ["bar"])
        parsed_list = parsed_equation_list(
            [expression_dict] * n_dicts, id_prefix=id_prefix
        )

        for expr_num in range(n_dicts):
            assert parsed_list[expr_num]["id"] == (id_prefix, expr_num)

    @pytest.mark.parametrize("n_dicts", [1, 2, 3])
    def test_parse_where_expression_no_id_prefix(
        self,
        parsed_equation_list,
        constraint_expression_dict,
        n_dicts,
    ):
        expression_dict = constraint_expression_dict("foo == 1", "bar")
        parsed_list = parsed_equation_list([expression_dict] * n_dicts)
        for expr_num in range(n_dicts):
            assert parsed_list[expr_num]["id"] == expr_num

    def test_parse_where_expression_error(
        self, constraint_obj_with_sets, parsed_equation_list, constraint_expression_dict
    ):
        expression_dict = constraint_expression_dict("foo = 1")
        parsed_list = parsed_equation_list([expression_dict])

        assert parsed_list[0]["expression"] is None
        assert check_error_or_warning(
            constraint_obj_with_sets._errors, "(my_expr, foo = 1): Expected"
        )

    @pytest.mark.parametrize("error_position", [0, 1])
    def test_parse_where_expression_one_error(
        self,
        constraint_obj_with_sets,
        parsed_equation_list,
        constraint_expression_dict,
        error_position,
    ):
        expression_list = [constraint_expression_dict("foo == 1")]
        expression_list.insert(error_position, constraint_expression_dict("foo = 1"))

        parsed_list = parsed_equation_list(expression_list)

        assert parsed_list[error_position]["expression"] is None
        assert isinstance(
            parsed_list[error_position - 1]["expression"], pp.ParseResults
        )

        assert len(constraint_obj_with_sets._errors) == 1
        assert check_error_or_warning(
            constraint_obj_with_sets._errors, "(my_expr, foo = 1): Expected"
        )

    def test_parse_where_expression_two_error(
        self, constraint_obj_with_sets, parsed_equation_list, constraint_expression_dict
    ):
        expression_list = [
            constraint_expression_dict("foo = 1"),
            constraint_expression_dict("foo = 2"),
        ]
        parsed_list = parsed_equation_list(expression_list)

        assert all(parsed_list[i]["expression"] is None for i in range(2))

        assert len(constraint_obj_with_sets._errors) == 2
        assert check_error_or_warning(
            constraint_obj_with_sets._errors,
            ["(my_expr, foo = 1): Expected", "(my_expr, foo = 2): Expected"],
        )


class TestParsingEquationComponent:
    @pytest.fixture
    def parsed_component_dict(self, constraint_obj_with_sets, component_parser):
        def _parsed_component_dict(n_foo, n_bar):
            components = constraint_string_with_components(n_foo, n_bar)["components"]

            return {
                c_name: constraint_obj_with_sets._parse_where_expression(
                    component_parser, c_list, "component", c_name
                )
                for c_name, c_list in components.items()
            }

        return _parsed_component_dict

    @pytest.mark.parametrize(
        "parse_string",
        [
            "$foo == $bar",
            "$foo + $bar >= 1",
            "$foo * $bar == 1",
            "($foo * 1) + $bar == 1",
            "(1**$bar) <= $foo + $bar",
            "(1 / $bar) <= $foo",
            "($foo - $bar) * ($foo + $bar) <= 2",
        ],
    )
    def test_find_components(
        self, expression_parser, constraint_obj_with_sets, parse_string
    ):
        parsed = expression_parser.parse_string(parse_string, parse_all=True)
        found_components = constraint_obj_with_sets._find_items_in_expression(
            parsed[0].value,
            equation_parser.EvalComponent,
            (equation_parser.EvalOperatorOperand),
        )
        assert found_components == set(["foo", "bar"])

    @pytest.mark.parametrize("n_foos", [0, 1, 2])
    @pytest.mark.parametrize("n_bars", [0, 1, 2])
    def test_get_expression_group_product(
        self,
        constraint_obj_with_sets,
        parsed_component_dict,
        parsed_equation_list,
        constraint_expression_dict,
        n_foos,
        n_bars,
    ):
        equation_ = parsed_equation_list([constraint_expression_dict("$foo == $bar")])
        component_product = list(constraint_obj_with_sets._get_expression_group_product(
            equation_[0], parsed_component_dict(n_foos, n_bars), "components"
        ))
        assert len(component_product) == n_foos * n_bars
        assert not constraint_obj_with_sets._errors

    def test_get_expression_group_product_missing_component(
        self,
        constraint_obj_with_sets,
        parsed_equation_list,
        parsed_component_dict,
        constraint_expression_dict,
    ):
        equation_ = parsed_equation_list(
            [constraint_expression_dict("$foo == $bar + $baz")]
        )
        component_product = constraint_obj_with_sets._get_expression_group_product(
            equation_[0], parsed_component_dict(1, 2), "components"
        )
        assert len(list(component_product)) == 2
        assert check_error_or_warning(
            constraint_obj_with_sets._errors,
            "Undefined components found in equation: {'baz'}",
        )

    @pytest.mark.parametrize(
        ["equation_", "expected"],
        [("$foo == $bar", False), ("$foo <= $bar", True), ("$foo + 10 >= $bar", True)],
    )
    def test_add_exprs_to_equation_data(
        self,
        constraint_obj_with_sets,
        parsed_equation_list,
        parsed_component_dict,
        constraint_expression_dict,
        equation_,
        expected,
    ):
        component_dict = parsed_component_dict(1, 1)
        component_product = [component_dict["foo"][0], component_dict["bar"][0]]
        equation_ = parsed_equation_list([constraint_expression_dict(equation_)])[0]

        combined_expression_dict = constraint_obj_with_sets._add_exprs_to_equation_data(
            equation_, component_product, "components"
        )
        component_sub_dict = combined_expression_dict["components"]
        assert not set(component_sub_dict.keys()).symmetric_difference(["foo", "bar"])
        assert (
            combined_expression_dict["expression"][0].eval(
                component_expressions=component_sub_dict
            )
            is expected
        )

    @pytest.mark.parametrize(
        ["equation_", "expected"],
        [("$foo == $bar", False), ("$foo <= $bar", True), ("$foo * 20 >= $bar", True)],
    )
    def test_add_exprs_to_equation_data_multi(
        self,
        constraint_obj_with_sets,
        parsed_equation_list,
        parsed_component_dict,
        constraint_expression_dict,
        equation_,
        expected,
    ):
        component_dict = parsed_component_dict(2, 2)

        equation_ = parsed_equation_list([constraint_expression_dict(equation_)])[0]
        component_product = constraint_obj_with_sets._get_expression_group_product(
            equation_, component_dict, "components"
        )
        combined_expression_list = [
            constraint_obj_with_sets._add_exprs_to_equation_data(
                equation_, component_, "components"
            )
            for component_ in component_product
        ]
        # All IDs should be unique
        assert len(set(expr["id"] for expr in combined_expression_list)) == 4

        for constraint_eq in combined_expression_list:
            component_sub_dict = constraint_eq["components"]
            assert not set(component_sub_dict.keys()).symmetric_difference(
                ["foo", "bar"]
            )
            assert (
                constraint_eq["expression"][0].eval(
                    component_expressions=component_sub_dict
                )
                is expected
            )

    def test_add_sub_exprs_per_equation_expr(
        self,
        constraint_obj_with_sets,
        parsed_equation_list,
        parsed_component_dict,
        constraint_expression_dict,
    ):
        equation_list = parsed_equation_list(
            [
                constraint_expression_dict("$foo == 1"),  # contributes 3
                constraint_expression_dict("$bar == 1"),  # contributes 2
                constraint_expression_dict("$foo == $bar"),  # contributes 6
                constraint_expression_dict("$foo == ($bar * $foo)**2"),  # contributes 6
            ]
        )

        final_equation_list = constraint_obj_with_sets._add_sub_exprs_per_equation_expr(
            equations=equation_list,
            expression_dict=parsed_component_dict(3, 2),
            expression_group="components",
        )
        assert len(final_equation_list) == 17
        assert len(set(eq_["id"] for eq_ in final_equation_list)) == len(
            final_equation_list
        )


class TestParsingEquationIndexItems:
    def constraint_string_with_idx_items(self, n_tech1, n_tech2):
        techs1 = ", ".join(
            [f"{{where: ['{i}'], expression: foo}}" for i in range(n_tech1)]
        )
        techs2 = ", ".join(
            [f"{{where: ['{i * 10}'], expression: bar}}" for i in range(n_tech2)]
        )
        setup_string = f"""
        foreach: [a in A, a1 in A1]
        where: []
        equation: "foo[techs=tech1] == bar[techs=tech2]"
        index_items:
            tech1: [{techs1}]
            tech2: [{techs2}]
        """

        return string_to_dict(setup_string)

    def constraint_string_with_components_and_idx_items(self, equation_expr):
        setup_string = f"""
        foreach: [a in A, a1 in A1]
        where: [0]
        equations:
            - expression: {equation_expr}
              where: [x]
        components:
            foo:
                - expression: 1 + foo
                  where: [a]
                - expression: 2 + foo[techs=tech2]
                  where: [b]
            bar:
                - expression: 1 + foo[techs=tech1]
                  where: [c]
                - expression: 2 + foo[techs=tech2]
                  where: [d]
        index_items:
            tech1:
                - expression: dummy_func_1(wind)
                  where: [1]
                - expression: dummy_func_1(pv)
                  where: [2]
            tech2:
                - expression: lookup_table[a]
                  where: [3]
                - expression: lookup_table[a1]
                  where: [4]
        """

        return string_to_dict(setup_string)

    @pytest.fixture
    def parsed_index_item_dict(self, constraint_obj_with_sets, index_item_parser):
        def _parsed_index_item_dict(n_1, n_2):
            index_items = self.constraint_string_with_idx_items(n_1, n_2)["index_items"]

            return {
                idx_name: constraint_obj_with_sets._parse_where_expression(
                    index_item_parser, idx_list, "index_items", idx_name
                )
                for idx_name, idx_list in index_items.items()
            }

        return _parsed_index_item_dict

    @pytest.fixture
    def parsed_index_item_component_dict(
        self, constraint_obj_with_sets, index_item_parser, component_parser
    ):
        def _parsed_index_item_component_dict(expr):
            unparsed_ = self.constraint_string_with_components_and_idx_items(expr)
            return {
                expr_group: {
                    expr_name: constraint_obj_with_sets._parse_where_expression(
                        index_item_parser
                        if expr_group == "index_items"
                        else component_parser,
                        expr_list,
                        expr_group,
                        expr_name,
                    )
                    for expr_name, expr_list in unparsed_[expr_group].items()
                }
                for expr_group in ["index_items", "components"]
            }

        return _parsed_index_item_component_dict

    @pytest.mark.parametrize(
        "parse_string",
        [
            "foo[techs=tech1] == bar[techs=tech2]",
            "foo[techs=tech1] + bar[techs=tech2] >= 1",
            "foo[techs=tech1] * bar[techs=tech2] == 1",
            "(foo[techs=tech1] * 1) + bar[techs=tech2] == 1",
            "(1**bar[techs=tech2]) <= foo[techs=tech1] + bar[techs=tech2]",
            "(1 / bar[techs=tech2]) <= foo[techs=tech1]",
            "(foo[techs=tech1] - bar[techs=tech2]) * (foo[techs=tech1] + bar[techs=tech2]) <= 2",
        ],
    )
    def test_find_index_items(
        self, expression_parser, constraint_obj_with_sets, parse_string
    ):
        parsed = expression_parser.parse_string(parse_string, parse_all=True)
        found_index_items = constraint_obj_with_sets._find_items_in_expression(
            parsed[0].value,
            equation_parser.EvalIndexItems,
            (equation_parser.EvalOperatorOperand, equation_parser.EvalIndexedParameterOrVariable),
        )
        assert found_index_items == set(["tech1", "tech2"])

    @pytest.mark.parametrize("n_1", [0, 1, 2])
    @pytest.mark.parametrize("n_2", [0, 1, 2])
    def test_get_expression_group_product(
        self,
        constraint_obj_with_sets,
        parsed_index_item_dict,
        parsed_equation_list,
        constraint_expression_dict,
        n_1,
        n_2,
    ):
        equation_ = parsed_equation_list(
            [constraint_expression_dict("foo[techs=tech1] == bar[techs=tech2]")]
        )
        product_ = list(constraint_obj_with_sets._get_expression_group_product(
            equation_[0], parsed_index_item_dict(n_1, n_2), "index_items"
        ))
        assert len(product_) == n_1 * n_2
        assert not constraint_obj_with_sets._errors

    def test_get_expression_group_product_missing_index_items(
        self,
        constraint_obj_with_sets,
        parsed_equation_list,
        parsed_index_item_dict,
        constraint_expression_dict,
    ):
        equation_ = parsed_equation_list(
            [
                constraint_expression_dict(
                    "foo[techs=tech1] == bar[techs=tech2, nodes=node1]"
                )
            ]
        )
        index_item_product = constraint_obj_with_sets._get_expression_group_product(
            equation_[0], parsed_index_item_dict(1, 2), "index_items"
        )
        assert len(list(index_item_product)) == 2
        assert check_error_or_warning(
            constraint_obj_with_sets._errors,
            "Undefined index_items found in equation: {'node1'}",
        )

    @pytest.mark.parametrize(
        ["eq_string", "expected_n_equations"],
        [
            ("1 == bar[techs=tech2]", 2),
            ("$foo == bar[techs=tech2]", 4),
            ("$bar == 1", 4),
            ("$bar == bar[techs=tech2]", 6),
            ("$bar + $foo == bar[techs=tech2]", 12),
            ("$bar + $foo == bar[techs=tech2] + foo[techs=tech1]", 16),
        ],
    )
    def test_index_items_and_components(
        self,
        constraint_obj_with_sets,
        parsed_equation_list,
        parsed_index_item_component_dict,
        constraint_expression_dict,
        eq_string,
        expected_n_equations,
    ):
        equation_list = parsed_equation_list([constraint_expression_dict(eq_string)])

        component_equation_list = (
            constraint_obj_with_sets._add_sub_exprs_per_equation_expr(
                equations=equation_list,
                expression_dict=parsed_index_item_component_dict("")["components"],
                expression_group="components",
            )
        )
        index_item_and_component_equation_list = (
            constraint_obj_with_sets._add_sub_exprs_per_equation_expr(
                equations=component_equation_list,
                expression_dict=parsed_index_item_component_dict("")["index_items"],
                expression_group="index_items",
            )
        )
        assert len(index_item_and_component_equation_list) == expected_n_equations