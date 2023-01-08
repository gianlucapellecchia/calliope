import pandas as pd
import pytest  # noqa: F401

import calliope
from calliope import exceptions
from calliope.time import funcs
from calliope.test.common.util import (
    build_test_model,
    check_error_or_warning,
)


class TestResampling:
    def test_15min_resampling_to_6h(self):
        # The data is identical for '2005-01-01' and '2005-01-03' timesteps,
        # it is only different for '2005-01-02'
        override = {
            "techs.test_demand_elec.constraints.resource": "file=demand_elec_15mins.csv",
            "model.subset_time": None,
            "model.time": {
                "function": "resample",
                "function_options": {"resolution": "6H"},
            },
        }

        model = build_test_model(override, scenario="simple_supply,one_day")
        data = model._model_data

        dtindex = pd.DatetimeIndex(
            [
                "2005-01-01 00:00:00",
                "2005-01-01 06:00:00",
                "2005-01-01 12:00:00",
                "2005-01-01 18:00:00",
                "2005-01-02 00:00:00",
                "2005-01-02 06:00:00",
                "2005-01-02 12:00:00",
                "2005-01-02 18:00:00",
                "2005-01-03 00:00:00",
                "2005-01-03 06:00:00",
                "2005-01-03 12:00:00",
                "2005-01-03 18:00:00",
            ]
        )

        assert dtindex.equals(data.timesteps.to_index())

    def test_15min_to_2h_resampling_to_2h(self):
        """
        CSV has daily timeseries varying from 15min to 2h resolution, resample all to 2h
        """
        override = {
            "techs.test_demand_elec.constraints.resource": "file=demand_elec_15T_to_2h.csv",
            "model.subset_time": None,
            "model.time": {
                "function": "resample",
                "function_options": {"resolution": "2H"},
            },
        }

        model = build_test_model(override, scenario="simple_supply,one_day")
        data = model._model_data

        dtindex = pd.DatetimeIndex(
            [
                "2005-01-01 00:00:00",
                "2005-01-01 02:00:00",
                "2005-01-01 04:00:00",
                "2005-01-01 06:00:00",
                "2005-01-01 08:00:00",
                "2005-01-01 10:00:00",
                "2005-01-01 12:00:00",
                "2005-01-01 14:00:00",
                "2005-01-01 16:00:00",
                "2005-01-01 18:00:00",
                "2005-01-01 20:00:00",
                "2005-01-01 22:00:00",
                "2005-01-02 00:00:00",
                "2005-01-02 02:00:00",
                "2005-01-02 04:00:00",
                "2005-01-02 06:00:00",
                "2005-01-02 08:00:00",
                "2005-01-02 10:00:00",
                "2005-01-02 12:00:00",
                "2005-01-02 14:00:00",
                "2005-01-02 16:00:00",
                "2005-01-02 18:00:00",
                "2005-01-02 20:00:00",
                "2005-01-02 22:00:00",
                "2005-01-03 00:00:00",
                "2005-01-03 02:00:00",
                "2005-01-03 04:00:00",
                "2005-01-03 06:00:00",
                "2005-01-03 08:00:00",
                "2005-01-03 10:00:00",
                "2005-01-03 12:00:00",
                "2005-01-03 14:00:00",
                "2005-01-03 16:00:00",
                "2005-01-03 18:00:00",
                "2005-01-03 20:00:00",
                "2005-01-03 22:00:00",
            ]
        )

        assert dtindex.equals(data.timesteps.to_index())


class TestFuncs:
    @pytest.fixture
    def model_national(self, scope="module"):
        return calliope.examples.national_scale(
            override_dict={"model.subset_time": ["2005-01", "2005-01"]}
        )

    def test_drop_invalid_timesteps(self, model_national):
        data = model_national._model_data_pre_resampling.copy()
        timesteps = ["XXX2005-01-01 23:00"]

        with pytest.raises(exceptions.ModelError):
            funcs.drop(data, timesteps)

    def test_drop(self, model_national):
        data = model_national._model_data_pre_resampling.copy()
        timesteps = ["2005-01-01 23:00", "2005-01-01 22:00"]

        data_dropped = funcs.drop(data, timesteps)

        assert len(data_dropped.timesteps) == 742

        result_timesteps = list(data_dropped.coords["timesteps"].values)

        assert "2005-01-01 21:00" not in result_timesteps
        assert "2005-01-01 22:00" not in result_timesteps


class TestLoadTimeseries:
    def test_invalid_csv_columns(self):
        override = {
            "nodes": {
                "c.techs": {"test_supply_elec": None, "test_demand_elec": None},
                "d.techs": {"test_supply_elec": None, "test_demand_elec": None},
            },
            "links": {
                "a,b": {"exists": False},
                "c,d.techs": {"test_transmission_elec": None},
            },
        }
        with pytest.raises(exceptions.ModelError) as excinfo:
            build_test_model(override_dict=override, scenario="one_day")

        assert check_error_or_warning(
            excinfo,
            [
                "file:column combinations `[('demand_elec.csv', 'c') ('demand_elec.csv', 'd')]` not found, but are requested by parameter `resource`."
            ],
        )
