import os
import calliope
import pytest  # pylint: disable=unused-import

from calliope.core.attrdict import AttrDict
import calliope.exceptions as exceptions


HTML_STRINGS = AttrDict.from_yaml(
    os.path.join(os.path.dirname(__file__), 'common', 'html_strings.yaml')
)


class TestPlotting:
    @pytest.fixture(scope="module")
    def national_scale_example(self):
        model = calliope.examples.national_scale(
            override_dict={'model.subset_time': '2005-01-01'}
        )
        model.run()
        return model

    def test_national_scale_plotting(self, national_scale_example):
        model = national_scale_example

        plot_html_outputs = {
            'capacity': model.plot.capacity(html_only=True),
            'timeseries': model.plot.timeseries(html_only=True),
            'transmission': model.plot.transmission(html_only=True),
        }

        for plot_type in HTML_STRINGS['national_scale']:
            for string in HTML_STRINGS['national_scale'][plot_type]:
                assert string in plot_html_outputs[plot_type]

        # Also just try plotting the summary
        model.plot.summary()

    def test_milp_plotting(self):
        override = {'model.subset_time': '2005-01-01'}
        model = calliope.examples.milp(override_dict=override)
        model.run()

        plot_html_outputs = {
            'capacity': model.plot.capacity(html_only=True),
            'timeseries': model.plot.timeseries(html_only=True),
            'transmission': model.plot.transmission(html_only=True),
        }

        for plot_type in HTML_STRINGS['milp']:
            for string in HTML_STRINGS['milp'][plot_type]:
                assert string in plot_html_outputs[plot_type]

        # Also just try plotting the summary
        model.plot.summary()

    def test_failed_cap_plotting(self, national_scale_example):
        model = national_scale_example

        # should fail, not in array
        with pytest.raises(exceptions.ModelError):
            model.plot.capacity(array='carrier_prod')
            model.plot.capacity(array=['energy_eff', 'energy_cap'])
            # orient has to be 'v', 'vertical', 'h', or 'horizontal'
            model.plot.capacity(orient='g')

    def test_failed_timeseries_plotting(self, national_scale_example):
        model = national_scale_example

        # should fail, not in array
        with pytest.raises(exceptions.ModelError):
            model.plot.timeseries(array='energy_cap')
            model.plot.timeseries(squeeze=False)
            model.plot.timeseries(sum_dims=None)

    def test_clustered_plotting(self):
        override = {'model.time.function_options.k': 2}
        model = calliope.examples.time_clustering(override_dict=override)

        plot_html = model.plot.timeseries(html_only=True)
        for string in HTML_STRINGS['clustering']['timeseries']:
            assert string in plot_html

    def test_subset_plotting(self, national_scale_example):
        model = national_scale_example

        model.plot.capacity(html_only=True, subset={'timeseries': ['2015-01-01 01:00']})

        # FIXME: sum_dims doesn't seem to work at all
        # model.plot.capacity(html_only=True, sum_dims=['locs'])

        # FIXME: this should raise an error!
        # model.plot.capacity(html_only=True, subset={'timeseries': ['2016-01-01 01:00']})
