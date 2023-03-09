# -*- coding: utf-8 -*-
"""
Created on Tue Apr  5 16:44:46 2022

@author: stevo
"""

import calliope
import cal_graph as gg

try:
    calliope.set_log_level('Error')
except:
    calliope.set_log_verbosity('Error')
    
model = calliope.Model('model.yaml')
model.run()

model.to_csv(r'results')

my_graphs = gg.C_Graph(model=model,ex_path=r'Graph_inputs.xlsx',unit='kW')

my_graphs.node_pie(rational = 'consumption')

my_graphs.node_dispatch()

my_graphs.sys_dispatch()

my_graphs.ins_cap_plot()