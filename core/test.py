# standard modules
from datetime import datetime
from datetime import date
from dateutil import relativedelta
import time

# custom modules
import params
import portfolio
import optimize as op
import numpy as np
import pandas
from cvxopt import matrix

'''
def jump_by_month(start_date, end_date, month_step=1): 
    current_date = start_date 
    while current_date < end_date: 
        yield current_date 
        carry, new_month = divmod(current_date.month - 1 + month_step, 12)
        new_month += 1 
        current_date = current_date.replace(year=current_date.year + carry, month=new_month) 
'''

# get the portfolio parameters
port_params = params.get_portfolio_params()
bench_params = params.get_bench_params()

# instantiate the porfolio object
port = portfolio.Portfolio(port_params, bench_params, proxy={"http": "http://proxy.jpmchase.net:8443"})

print port.estimate_parameters()