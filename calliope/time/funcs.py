"""
Copyright (C) since 2013 Calliope contributors listed in AUTHORS.
Licensed under the Apache 2.0 License (see LICENSE file).

funcs.py
~~~~~~~~

Functions to process time series data.

"""

import logging
import datetime

import numpy as np
import pandas as pd
import xarray as xr

from calliope import exceptions

logger = logging.getLogger(__name__)


def _copy_non_t_vars(data0, data1):
    """Copies non-t-indexed variables from data0 into data1, then
    returns data1"""
    non_t_vars = [
        varname
        for varname, vardata in data0.data_vars.items()
        if "timesteps" not in vardata.dims
    ]
    # Manually copy over variables not in `timesteps`. If we don't do this,
    # these vars get polluted with a superfluous `timesteps` dimension
    for v in non_t_vars:
        data1[v] = data0[v]
    return data1


def _combine_datasets(data0, data1):
    """Concatenates data0 and data1 along the time dimension"""
    data_new = xr.concat([data0, data1], dim="timesteps")
    # Ensure time dimension is ordered
    data_new = data_new.loc[{"timesteps": data_new.timesteps.to_index().sort_values()}]

    return data_new


def _drop_timestep_vars(data, timesteps):
    timeseries_data = data.copy(deep=True)
    # Save all coordinates, to ensure they can be added back in after clustering
    data_coords = data.copy().coords
    del data_coords["timesteps"]

    if timesteps is not None:
        timeseries_data = timeseries_data.loc[{"timesteps": timesteps}]

    timeseries_data = timeseries_data.drop_vars(
        [
            varname
            for varname, vardata in data.data_vars.items()
            if "timesteps" not in vardata.dims
        ]
    )

    return timeseries_data, data_coords


def resample(data, timesteps, resolution):
    """
    Function to resample timeseries data from the input resolution (e.g. 1H), to
    the given resolution (e.g. 2H)

    Parameters
    ----------
    data : xarray.Dataset
        calliope model data, containing only timeseries data variables
    timesteps : str or list; optional
        If given, apply resampling to a subset of the timeseries data
    resolution : str
        time resolution of the output data, given in Pandas time frequency format.
        E.g. 1H = 1 hour, 1W = 1 week, 1M = 1 month, 1T = 1 minute. Multiples allowed.

    """

    def _resample(var, how):
        return getattr(var.resample(timesteps=resolution, keep_attrs=True), how)(
            "timesteps"
        )

    # get a copy of the dataset with only timeseries variables,
    # and get all coordinates of the original dataset, to reinstate later
    data_new, data_coords = _drop_timestep_vars(data, timesteps)

    # First create a new resampled dataset of the correct size by
    # using first-resample, which should be a quick way to achieve this

    data_rs = _resample(data_new, how="first")

    for var in data_rs.data_vars:
        if var in ["timestep_resolution", "resource"]:
            data_rs[var] = _resample(data_new[var], how="sum")
        else:
            try:
                data_rs[var] = _resample(data_new[var], how="mean")
            except TypeError:
                # If the var has a datatype of strings, it can't be resampled
                logger.error(
                    "Dropping {} because it has a {} data type when integer or "
                    "float is expected for timeseries resampling.".format(
                        var, data_rs[var].dtype
                    )
                )
                data_rs = data_rs.drop_vars(var)

    # Get rid of the filled-in NaN timestamps
    data_rs = data_rs.dropna(dim="timesteps", how="all")

    data_rs.attrs["allow_operate_mode"] = 1  # Resampling still permits operational mode

    # It's now safe to add the original coordinates back in (preserving all the
    # loc_tech sets that aren't used to index a variable in the DataArray)
    data_rs.update(data_coords)

    data_rs = _copy_non_t_vars(data, data_rs)  # add back in non timeseries data

    if timesteps is not None:
        # Combine leftover parts of passed in data with new data
        data_rs = _combine_datasets(data.drop_sel(timesteps=timesteps), data_rs)
        data_rs = _copy_non_t_vars(data, data_rs)
        # Having timesteps with different lengths does not permit operational mode
        data_rs.attrs["allow_operate_mode"] = 0

    return data_rs


def drop(data, timesteps):
    """
    Drop timesteps from data, adjusting the timestep weight of remaining
    timesteps accordingly. Returns updated dataset.

    Parameters
    ----------
    data : xarray.Dataset
        Calliope model data.
    timesteps : str or list or other iterable
        Pandas-compatible timestep strings.

    """
    # Turn timesteps into a pandas datetime index for subsetting, which also
    # checks whether they are actually valid
    try:
        timesteps_pd = pd.to_datetime(timesteps)
    except Exception as e:
        raise exceptions.ModelError("Invalid timesteps: {}".format(timesteps))

    # 'Distribute weight' of the dropped timesteps onto the remaining ones
    dropped_weight = data.timestep_weights.loc[{"timesteps": timesteps_pd}].sum()

    data = data.drop_sel(timesteps=timesteps_pd)

    data["timestep_weights"] = data["timestep_weights"] + (
        dropped_weight / len(data["timestep_weights"])
    )

    return data

