# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import message_ix
import ixmp
import pyam

GROUP_IDX = pyam.IAMC_IDX + ['year']


class Reporting(object):
    """Execute reporting on a message_ix.Scenario

    Parameters
    ----------
    scenario : message_ix.Scenario
    """
    def __init__(self, scenario):
        if not isinstance(scenario, message_ix.Scenario):
            msg = 'Postprocess can only be used with a `message_ix.Scenario`'
            raise ValueError(msg)
        if np.isnan(scenario.var('OBJ')['lvl']):
            raise ValueError('this scenario has not been solved!')
        self.scenario = scenario
        self.reporting = pyam.IamDataFrame(scenario)

    def activity(self, variable, unit='', region='node_loc', year='year_act',
                 **kwargs):
        """Aggregates the activity level across technologies
        and converts results to the IAMC template

        Parameters
        ----------
        variable: str
            variable string following the IAMC convention,
            e.g. (`Category|Subcategory|Specification`)
        unit: str
            the unit in which the technology activity is modelled
        region: str
            the variable/parameter column to be used for the IAMC region column
        year: str
            the variable/parameter column to be used for the IAMC year column
        **kwargs
            filters for variable and parameter columns
        """
        act = self.scenario.var('ACT')

        df = _apply_filters(act, kwargs)
        df['model'] = self.scenario.model
        df['scenario'] = self.scenario.scenario
        df['variable'] = variable
        df['unit'] = unit
        df.rename(columns={region: 'region', year: 'year', 'lvl': 'value'},
                  inplace=True)
        df = df.groupby(GROUP_IDX).sum()['value'].to_frame()

        self.reporting.append(df, inplace=True)

    def finalize(self, comment=None):
        """Finalizes the reporting by committing to the modeling platform

        Parameters
        ----------
        comment: str, optional
            annotation for commit of timeseries to the database
        """
        try:
            self.scenario.check_out(timeseries_only=True)
            self.scenario.add_timeseries(self.reporting.data)
            self.scenario.commit(comment or 'MESSAGEix postprocessing')
        except Exception:
            self.scenario.discard_changes()
            ixmp.logger().error('Error saving timeseries data to the database')


# %%  auxiliary functions

def _apply_filters(data, filters):
    keep = np.array([True] * len(data))
    for col, values in filters.items():
        values = [values] if pyam.isstr(values) else values
        keep &= [i in values for i in data[col]]
    return data[keep].copy()
