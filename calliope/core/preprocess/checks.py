"""
Copyright (C) 2013-2017 Calliope contributors listed in AUTHORS.
Licensed under the Apache 2.0 License (see LICENSE file).

preprocess_checks.py
~~~~~~~~~~~~~~~~~~~~

Checks for model consistency and possible errors during preprocessing.

"""

import os
import ruamel.yaml
import calliope
from calliope.core.attrdict import AttrDict
from calliope.core.util.tools import flatten_list
from calliope.core.preprocess.util import get_all_carriers
from calliope import exceptions

import numpy as np
import xarray as xr


_defaults_files = {
    k: os.path.join(os.path.dirname(calliope.__file__), 'config', k + '.yaml')
    for k in ['model', 'defaults']
}
defaults = AttrDict.from_yaml(_defaults_files['defaults'])
defaults_model = AttrDict.from_yaml(_defaults_files['model'])


def print_warnings_and_raise_errors(warnings=None, errors=None):
    """
    Print warnings and raise ModelError from errors.

    Params
    ------
    warnings : list, optional
    errors : list, optional

    """
    if warnings:
        exceptions.warn(
            'Possible issues found during pre-processing:\n' +
            '\n'.join(warnings)
        )

    if errors:
        raise exceptions.ModelError(
            'Errors during pre-processing:\n' +
            '\n'.join(errors)
        )

    return None


def check_initial(config_model):
    """
    Perform initial checks of model and run config dicts.

    Returns
    -------
    warnings : list
        possible problems that do not prevent the model run
        from continuing
    errors : list
        serious issues that should raise a ModelError

    """
    errors = []
    warnings = []

    # Check run configuration
    for k in config_model['run'].keys_nested():
        if k not in defaults_model['run'].keys_nested():
            warnings.append(
                'Unrecognized setting in run configuration: {}'.format(k)
            )

    # Only ['in', 'out', 'in_2', 'out_2', 'in_3', 'out_3']
    # are allowed as carrier tiers
    for key in config_model.as_dict_flat().keys():
        if ('.carrier_' in key and key.split('.carrier_')[-1].split('.')[0] not
                in ['in', 'out', 'in_2', 'out_2', 'in_3', 'out_3', 'ratios'] and
                'group_share' not in key):
            errors.append(
                "Invalid carrier tier found at {}. Only "
                "'carrier_' + ['in', 'out', 'in_2', 'out_2', 'in_3', 'out_3'] "
                "is valid.".format(key)
            )

    # No tech_groups/techs may have the same identifier as the built-in groups
    # tech_groups are checked in preprocess_model.process_config()
    name_overlap = (
        set(config_model.tech_groups.keys()) &
        set(config_model.techs.keys())
    )
    if name_overlap:
        errors.append(
            'tech_groups and techs with '
            'the same name exist: {}'.format(name_overlap)
        )

    # Checks for techs and tech_groups:
    # * All user-defined tech and tech_groups must specify a parent
    # * No carrier may be called 'resource'
    default_tech_groups = list(config_model.tech_groups.keys())
    for tg_name, tg_config in config_model.tech_groups.items():
        if tg_name in default_tech_groups:
            continue
        if not tg_config.get_key('essentials.parent'):
            errors.append(
                'tech_group {} does not define '
                '`essentials.parent`'.format(tg_name)
            )
        if 'resource' in get_all_carriers(tg_config):
            errors.append(
                'No carrier called `resource` may '
                'be defined (tech_group: {})'.format(tg_name)
            )

    for t_name, t_config in config_model.techs.items():
        if not t_config.get_key('essentials.parent'):
            errors.append(
                'tech {} does not define '
                '`essentials.parent`'.format(t_name)
            )
        if 'resource' in get_all_carriers(t_config):
            errors.append(
                'No carrier called `resource` may '
                'be defined (tech: {})'.format(t_name)
            )

        return errors, warnings


def _check_tech(model_run, tech_id, tech_config, loc_id, warnings, errors, comments):
    required = model_run.techs[tech_id].required_constraints
    allowed = model_run.techs[tech_id].allowed_constraints
    allowed_costs = model_run.techs[tech_id].allowed_costs
    all_defaults = list(defaults.default_tech.constraints.keys())

    # Error if required constraints are not defined
    for r in required:
        # If it's a string, it must be defined
        single_ok = isinstance(r, str) and r in tech_config.constraints
        # If it's a list of strings, one of them must be defined
        multiple_ok = (
            isinstance(r, list) and
            any([i in tech_config.constraints for i in r])
        )
        if not single_ok and not multiple_ok:
            errors.append(
                '`{}` at `{}` fails to define '
                'all required constraints: {}'.format(tech_id, loc_id, required)
            )
            # print('{} -- {}-{}: {}, {}'.format(r, loc_id, tech_id, single_ok, multiple_ok))

    # Flatten required list and gather remaining unallowed constraints
    required_f = flatten_list(required)
    remaining = set(tech_config.constraints) - set(required_f) - set(allowed)

    # Error if something is defined that's not allowed, but is in defaults
    # Warn if something is defined that's not allowed, but is not in defaults
    # (it could be a misspelling)
    for k in remaining:
        if k in all_defaults:
            errors.append(
                '`{}` at `{}` defines non-allowed '
                'constraint `{}`'.format(tech_id, loc_id, k)
            )
        else:
            warnings.append(
                '`{}` at `{}` defines unrecognised '
                'constraint `{}` - possibly a misspelling?'.format(tech_id, loc_id, k)
            )

    # Error if an `export` statement does not match the given carrier_outs
    if 'export' in tech_config.constraints:
        export = tech_config.constraints.export
        if export not in [tech_config.essentials.get_key(k) for k in ['carrier_out', 'carrier_out_2', 'carrier_out_3']]:
            errors.append(
                '`{}` at `{}` is attempting to export a carrier '
                'not given as an output carrier: `{}`'.format(tech_id, loc_id, export)
            )

    # Error if non-allowed costs are defined
    for cost_class in tech_config.get_key('costs', {}):
        for k in tech_config.costs[cost_class]:
            if k not in allowed_costs:
                errors.append(
                    '`{}` at `{}` defines non-allowed '
                    '{} cost: `{}`'.format(tech_id, loc_id, cost_class, k)
                )

    # Error if a constraint is loaded from file that must not be
    allowed_from_file = defaults['file_allowed']
    for k, v in tech_config.as_dict_flat().items():
        if 'file=' in str(v):
            constraint_name = k.split('.')[-1]
            if constraint_name not in allowed_from_file:
                errors.append(
                    '`{}` at `{}` is trying to load `{}` from file, '
                    'which is not allowed'.format(tech_id, loc_id, constraint_name)
                )

    return None


def check_final(model_run):
    """
    Perform final checks of the completely built model_run.

    Returns
    -------
    comments : AttrDict
        debug output
    warnings : list
        possible problems that do not prevent the model run
        from continuing
    errors : list
        serious issues that should raise a ModelError

    """
    warnings, errors = [], []
    comments = AttrDict()

    # Go through all loc-tech combinations and check validity
    for loc_id, loc_config in model_run.locations.items():
        if 'techs' in loc_config:
            for tech_id, tech_config in loc_config.techs.items():
                _check_tech(
                    model_run, tech_id, tech_config, loc_id,
                    warnings, errors, comments
                )

        if 'links' in loc_config:
            for link_id, link_config in loc_config.links.items():
                for tech_id, tech_config in link_config.techs.items():
                    _check_tech(
                        model_run, tech_id, tech_config,
                        'link {}:{}'.format(loc_id, link_id),
                        warnings, errors, comments
                    )

    # Either all locations or no locations must have coordinates
    all_locs = list(model_run.locations.keys())
    locs_with_coords = [
        k for k in model_run.locations.keys()
        if 'coordinates' in model_run.locations[k]
    ]
    if len(locs_with_coords) != 0 and len(all_locs) != len(locs_with_coords):
        errors.append(
            'Either all or no locations must have `coordinates` defined'
        )

    # If locations have coordinates, they must all be either lat/lon or x/y
    first_loc = list(model_run.locations.keys())[0]
    coord_keys = sorted(list(model_run.locations[first_loc].coordinates.keys()))
    if coord_keys != ['lat', 'lon'] and coord_keys != ['x', 'y']:
        errors.append(
            'Unidentified coordinate system. All locations must either'
            'use the format {lat: N, lon: M} or {x: N, y: M}.'
        )
    for loc_id, loc_config in model_run.locations.items():
        if sorted(list(loc_config.coordinates.keys())) != coord_keys:
            errors.append('All locations must use the same coordinate format.')
            break

    # FIXME: check that constraints are consistent with desired mode:
    # planning or operational
    # if operational, print a single warning, and
    # turn _max constraints into _equals constraints with added comments
    # make sure `comments` is at the the base level:
    # i.e. comments.model_run.xxxxx....

    # FIXME: check that any storage/supply_plus technologies correctly define
    # energy_cap, storage_cap, and charge_rate so as not to clash with each other
    # given that energy_cap = storage_cap * charge_rate

    return comments, warnings, errors

def check_model_data(model_data):
    """
    Perform final checks of the completely built xarray Dataset `model_data`.

    Returns
    -------
    comments : AttrDict
        debug output
    warnings : list
        possible problems that do not prevent the model run
        from continuing
    errors : list
        serious issues that should raise a ModelError

    """
    warnings, errors = [], []
    comments = AttrDict()
    # FIXME: verify timestep consistency a la verification in get_timeres of
    # old calliope

    # Ensure that no loc-tech specifies infinite resource and force_resource=True
    if "force_resource" in model_data.data_vars:
        relevant_loc_techs = [
            i.loc_techs_finite_resource.item()
            for i in model_data.force_resource if i.item() is True
        ]
        forced_resource = model_data.resource.loc[
            dict(loc_techs_finite_resource=relevant_loc_techs)
        ]
        conflict = forced_resource.where(forced_resource == np.inf).to_pandas().dropna()
        if conflict.values:
            errors.append(
                'loc_tech(s) {} cannot have `force_resource` set as infinite '
                'resource values are given'.format(', '.join(conflict.index))
            )

    # FIXME: raise error with time clustering if it no longer fits with opmode
    # a la last section of initialize_time in old calliope

    #

    # Ensure that if a tech has negative costs, there is a max cap defined
    # FIXME doesn't consider capapcity being set by a linked constraint e.g.
    # `resource_cap_per_energy_cap`.
    relevant_caps = [
        i for i in ['energy_cap', 'storage_cap', 'resource_cap', 'resource_area']
        if 'cost_' + i in model_data.data_vars
    ]
    for cap in relevant_caps:
        relevant_loc_techs = (model_data['cost_' + cap]
                              .where(model_data['cost_' + cap] < 0)
                              .to_pandas().dropna().index)
        cap_max = cap + '_max'
        cap_equals = cap + '_equals'
        for loc_tech in relevant_loc_techs:
            try:
                cap_val = model_data[cap_max][loc_tech].item()
            except KeyError:
                try:
                    cap_val = model_data[cap_equals][loc_tech].item()
                except KeyError:
                    cap_val = np.nan
            if np.isinf(cap_val) or np.isnan(cap_val):
                errors.append(
                    'loc_tech {} cannot have a negative cost_{} as the '
                    'corresponding capacity constraint is not set'
                    .format(loc_tech, cap)
                )

    return comments, warnings, errors

def check_operate_params(model_data):
    """
    if model mode = `operate`, check for clashes in capacity constraints.
    In this mode, all capacity constraints are set to parameters in the backend,
    so can easily lead to model infeasibility if not checked.

    Returns
    -------
    comments : AttrDict
        debug output
    warnings : list
        possible problems that do not prevent the model run
        from continuing
    errors : list
        serious issues that should raise a ModelError

    """
    warnings, errors = [], []
    comments = AttrDict()

    def get_param(loc_tech, var):
        if is_in(loc_tech, var):
            param = model_data[var].loc[loc_tech].item()
        else:
            param = defaults[var]
        return param


    def is_in(loc_tech, set_or_var):
        if set_or_var in model_data:
            try:
                model_data[set_or_var].loc[loc_tech]
                return True
            except KeyError:
                return False
        else:
            return False


    def get_cap(loc_tech, param):
        if is_in(loc_tech, param + '_equals'):
            cap = model_data[param + '_equals'].loc[loc_tech].item()
        elif is_in(loc_tech, param + '_max'):
            cap = model_data[param + '_max'].loc[loc_tech].item()
        else:
            cap = np.inf
        return cap


    if 'loc_techs_area' in model_data.dims:
        for loc_tech in model_data.loc_techs_area.values:
            if (is_in(loc_tech, 'loc_techs_store')
                or np.isinf(get_cap(loc_tech, 'energy_cap'))
                or not is_in(loc_tech, 'force_resource')):
                continue
            elif is_in(loc_tech, 'loc_techs_finite_resource'):
                area = get_cap(loc_tech, 'resource_area')
                resource_scale = get_param(loc_tech, 'resource_scale')
                energy_cap = get_cap(loc_tech, 'energy_cap')
                energy_cap_scale = get_param(loc_tech, 'energy_cap_scale')
                resource = model_data.resource.loc[loc_tech] * area
                print(energy_cap, energy_cap_scale)
                if any(resource * resource_scale > energy_cap * energy_cap_scale):
                    errors.append(
                        'resource is forced to be higher than fixed energy cap '
                        'for loc::tech `{}`'.format(loc_tech)
                    )

    if 'loc_techs_store' in model_data.dims:
        for loc_tech in model_data.loc_techs_store.values:
            if is_in(loc_tech, 'charge_rate'):
                storage_cap = get_cap(loc_tech, 'storage_cap')
                energy_cap = get_cap(loc_tech, 'energy_cap')
                energy_cap_scale = get_param(loc_tech, 'energy_cap_scale')
                if storage_cap and energy_cap:
                    charge_rate = model_data['charge_rate'].loc[loc_tech]
                    if storage_cap * charge_rate != energy_cap * energy_cap_scale:
                        errors.append(
                            'fixed storage capacity * charge rate is not equal '
                            'to fixed energy capacity for loc::tech {}'.format(loc_tech)
                        )
        if 'storage_initial' not in model_data.data_vars:
            model_data['storage_initial'] = (
                xr.DataArray([0 for loc_tech in model_data.loc_techsstore.values], dims='loc_techs_store')
            )
            warnings.append(
                'Initial stored energy not defined, set to zero for all loc::techs'
                'in loc_techs_store, for use in iterative optimisation'
            )

    if 'model.operation.safe' not in model_data.attrs.keys():
        daily_timesteps = [
            model_data.timestep_resolution.loc[i].values
            for i in np.unique(model_data.timesteps.to_index().strftime('%Y-%m-%d'))
        ]
        if not np.all(daily_timesteps == daily_timesteps[0]):
            model_data.attrs['model.operation.safe'] = False
            errors.append(
                'Operational mode requires the same timestep resolution profile '
                'to be emulated on each date'
            )
        else:
            model_data.attrs['model.operation.safe'] = True

    try:
        window = model_data.attrs['model.operation.window']
        horizon = model_data.attrs['model.operation.horizon']
    except KeyError:
        errors.append(
            'Operational mode requires a timestep window and horizon to be '
            'defined under model.operation'
        )
        window = horizon = None
    if window and horizon and horizon < window:
        errors.append(
            'Iteration horizon must be larger than iteration window, for operational mode'
        )
    return comments, warnings, errors
