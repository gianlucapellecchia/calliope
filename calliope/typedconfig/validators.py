"""Validators for config options

Some validators are stubs, to be implemented, while a few others are
incomplete, as in it uses calls non-exisent functions as place holders.

"""

from itertools import chain
from typing import List

import calliope
from calliope.typedconfig.parsers import get_property

__all__ = [
    "range_check",
    "quadrant",
    "threshold",
    "mult_of",
    "zero_sum",
    "sum_by_name",
    "inheritance",
    "carrier_validation",
    "not_in",
    "minmax_cost_options",
    "node_coordinate_validation",
    # WIP
    "energy_cap_per_unit",
    "gte_storage_discharge_depth",
    # "carrier_validation_root",
    # "cost_class_validation",
    # "node_validation",
    # "error_if_a_technology_is_defined_twice_in_opposite_directions",
    # "export_cost_validation",
    # "storage_cap_per_unit",
    # "require",
    # "finite_forced_resource",
    # "loc_tech_cannot_have_force_resource_and_infinite_resource",
    # "ensure_that_if_a_tech_has_negative_costs_there_is_a_max_cap_defined",
    # "check_resource_sign",
    # "supply_only_allowed_positive_resource",
    # "calliope_version_validator",
    # "contains_keys",
]


def trange_check(cls, _range, values):
    """Validator function for a range config object"""
    if len(_range) != 2:
        raise ValueError(f"range has too many elements: {len(_range)}")
    # TODO: check time range order
    return _range


def range_check(cls, _max, values, *, min_key):
    """Validator function for range config object"""
    if min_key in values and values[min_key] > _max:
        raise ValueError(f"{min_key}: {values[min_key]} > {_max}")
    return _max


def quadrant(cls, values, *, axes, signs):
    if all(k in values for k in axes) and all(
        values[k] * s > 0 for k, s in zip(axes, signs) if s != 0
    ):
        return values

    raise ValueError(f"{values} not in quadrant: {signs}")


def threshold(cls, val, values, *, threshold):
    if val > threshold:
        raise ValueError(f"above threshold: {val} > {threshold}")
    return val


def mult_of(cls, val, values, *, factor):
    if val % factor == 0:
        return val
    raise ValueError(f"{val} is not a multiple of {factor}")


def zero_sum(cls, values, *, total):
    mysum = sum(values.values())
    if mysum != total:
        raise ValueError(f"{list(values.values())} do not add up to {total}")
    return values


def sum_by_name(cls, values, *, total):
    mysum = values.get("first", 0) + values.get("second", 0)
    if mysum != total:
        raise ValueError(f"{list(values.values())} do not add up to {total}")
    return values


def inheritance(cls, val, values, *, allowed_in):
    if cls.inherits_from(allowed_in):
        return val
    raise TypeError(f"{cls} does not inherit from either of {allowed_in}")


def not_in(cls, val, values, *, excluded):
    """Ensure `excluded` values aren't present in `val`

    E.g. 'resource' is a special keyword, and a carrier cannot have that as name.

    """
    common = set(val).intersection(excluded)
    if common:
        raise ValueError(f"{common} disallowed in {cls}\ndisallowed values: {excluded}")
    return val


def carrier_validation(cls, val, values, *, direction):
    """Looks for carriers defined earlier that matches ``carrier_{direction}*``.

    It is dependent on the order of the configuration key rules.  If the
    carrier rules are not defined before this validator is used, it will fail.

    """
    # see checks.py:483
    carriers = chain(
        v for k, v in values.items() if k.startswith(f"carrier_{direction}")
    )
    if val in carriers:
        return val
    # `cls` is technology
    raise ValueError(f"{cls!r} is attempting to export an unknown output carrier")


def node_coordinate_validation(cls, val, values, *, coord_systems=[]):
    """Can only define [x, y] or [lat, lon], no other combination of keys,
    e.g. [x, y, lat, lon], [x, lat]

    """
    coord_systems = [{"x", "y"}, {"lat", "lon"}]

    coords = set(val.keys())
    if coords in coord_systems:
        return val
    raise ValueError(
        f"{coords}: incompatible coordinate system, should be one of {coord_systems}"
    )


def minmax_cost_options(cls, val, values):
    obj = values.get("objective", None)
    if obj == "minmax_cost_optimization":
        if "cost_class" in val or "sense" in val:
            return val
        else:
            raise ValueError(f"{obj!r}: define one of 'cost_class' or 'sense'")
    return val


# WIP: dummy validators
def carrier_validation_root(cls, values, /):
    carriers = {
        direction: chain(
            v for k, v in values.items() if k.startswith(f"carrier_{direction}")
        )
        for direction in ("in", "out")
    }
    if (
        values["carrier_export"] in carriers["out"]
        and values["carrier_primary_out"] in carriers["out"]
        and values["carrier_primary_in"] in carriers["in"]
    ):
        return values
    # `cls` is technology
    raise ValueError(f"{cls!r} is attempting to export an unknown output carrier")


def cost_class_validation():
    """
    Look back at config and check that the cost classes defined in the objective
    options match those defined as cost classes in the data.
    NOTE: this should cover all instances of CostClassDict!
    """


def node_validation():
    """
    If 'techs' key defined, 'transmission_node' cannot be set to True. Although
    'transmission_node' is somewhat exposing implementation to the user, and
    could possibly be removed entirely
    """


def error_if_a_technology_is_defined_twice_in_opposite_directions():
    """
    What the function name says.
    """


def export_cost_validation():
    """
    Can only define an export cost if an export carrier has been defined for the same technology
    """


def energy_cap_per_unit(cls, val, values, /):
    """
    If units are defined, then energy_cap_per_unit must be specified.
    """
    key = "energy_cap_per_unit"
    dependent_val = values.get(key, None)
    if dependent_val is not None:
        return val
    raise ValueError(f"Units are defined, {key!r} must be specified.")


def storage_cap_per_unit(cls, val, values, /):
    """
    If units are defined (and storage is in the inheritance...), then storage_cap_per_unit must be specified.
    """
    dependent_val = values.get("storage_cap_per_unit", None)
    storage_in_hierarchy = False  # TODO: Fixme, is a placeholder now
    if dependent_val is not None and storage_in_hierarchy:
        return val
    else:
        raise ValueError(
            "If units are defined (and storage is in the inheritance...), "
            "then storage_cap_per_unit must be specified."
        )


def require(cls, val, values, *, key: str, inherits_from: List[str] = []):
    dependent = values.get(key, None)
    # the if clauses are deliberately explicit instead of composed, so that
    # error messages are clearer
    if inherits_from:
        if cls.inherits_from(inherits_from) and dependent is None:
            raise ValueError(
                f"{cls} inherits from {inherits_from}, {key!r} must be specified."
            )
    else:
        if dependent is None:
            raise ValueError(f"{key!r} must be specified.")
    return val


def finite_forced_resource(cls, val, values, /):
    """
    If a resource value is forced, this value cannot be infinite.
    """
    resource_val = values.get("resource", None)
    if np.isinf(resource_val):
        raise ValueError("Can't be infinte")
    elif isinstance(resource_val, str):
        # TODO: get_timeseries_data should be a key in timeseries_dataframes dictionary
        resource_ts_val = get_timeseries_data(resource_val)
        if resource_ts_val.isinf().any():
            raise ValueError("Can't be infinte")
    else:
        return val


def gte_storage_discharge_depth(cls, val, values, /):
    """
    If defining both `storage_initial` and `storage_discharge_depth`
    then `storage_initial` >= `storage_discharge_depth`
    """
    storage_dod_val = values.get("storage_discharge_depth", 0)
    if val >= storage_dod_val:
        return val
    else:
        raise ValueError(
            """If defining both `storage_initial` and `storage_discharge_depth` then `storage_initial` >= `storage_discharge_depth`"""
        )


##
# Timeseries specific things follow below
##


def loc_tech_cannot_have_force_resource_and_infinite_resource():
    # TODO: Probably not needed, covered by finite_forced_resource
    pass


def ensure_that_if_a_tech_has_negative_costs_there_is_a_max_cap_defined():
    caps = ["energy_cap", "storage_cap", "resource_cap", "resource_area"]
    # if the costs for the above is negative, then ensure there is a *_max
    # if costs.*.$CAPS for $CAPS in caps (list above) is negative, then also
    # constraints.$CAPS_max need to be specified and finite
    costs = [f"cost_{key}" for key in model_data.data_vars.keys()]


# for loc_techs_demand see preprocess/checks.py:840
def check_resource_sign(cls, val, values, /):
    resource_ts_val = get_timeseries_data(val)
    # TODO: get_timeseries_data should be a key in timeseries_dataframes dictionary
    # demand is usually time series, but may also be fixed value
    # check if inherits from demand or supply(-like)
    demand = get_property("demand")
    if cls.inherits_from(demand):
        if (resource_ts_val > 0).any():
            # FIXME:
            raise ValueError(
                f"Positive resource given for demand loc_tech {loc_tech}. "
                "All demands must have negative resource"
            )
    else:  # inherits from supply
        if (resource_ts_val < 0).any():
            # FIXME:
            raise ValueError(
                f"Negative resource given for supply loc_tech {loc_tech}. "
                "All resources must have positive resource"
            )
    return val


# opposite logic as above
def supply_only_allowed_positive_resource():
    pass


def calliope_version_validator(cls, val, values, /):
    if calliope.__version__ != val:
        # currently raises a model warning, meaning you can still run, retain the behaviour
        # unit tests often check for specific errors/warnings, ensure error message doesn't change
        raise ValueError(
            f"Model configuration specifies calliope_version={val}, "
            f"but you are running {calliope.__version__}. Proceed with caution!"
        )
    return val


# this is a root validator to be applied at the technology definition level
def contains_keys(cls, val, *, desired_keys):
    # TODO: get techs with storage, assume it is in the following variable
    # tech_w_storage = ("supply_plus", ) # defined in calliope.preprocess.sets.loc_techs_store
    # if issubclass(cls, tech_w_storage):
    all_keys = set(val.keys())
    if any(i in desired_keys for i in all_keys):
        return val
    else:
        # change to log, current implementation doesn't throw error
        # loc + tech are part of the val name, so extract & split to match msg below
        raise ValueError(
            f"`{tech}` at `{loc}` has no constraint to explicitly connect `energy_cap` to "
            "`storage_cap`, consider defining a `energy_cap_per_storage_cap_min/max/equals` "
            "constraint"
        )
