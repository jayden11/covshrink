# standard modules
from math import sqrt
from datetime import datetime
import time

# application specific modules
import matplotlib.finance as fin
import numpy as np
import pandas
import tables

# custom modules
import yahoo
import inspricehist as ph
import createdailytable

__all__ = ['_get_historic_data', '_get_historic_returns', '_build_portfolio', 'get_benchmark_weights', 
                'get_active_weights', 'get_portfolio_weights', 'get_holding_period_returns', 'get_expected_stock_returns',
                'get_active_returns', 'get_expected_excess_stock_returns', 'get_covariance_matrix',
                'get_expected_benchmark_return', 'get_benchmark_variance', 'get_expected_portfolio_return',
                'get_portfolio_variance', 'get_expected_excess_portfolio_return', 'get_tracking_error_variance', 'get_portfolio_size']

__version__ = '0.1'

__author__ = 'Jason Strimpel'

class Portfolio(object):

    def __init__(self, portfolio, benchmark, start=None, end=None, proxy=None):
        """Initializest the portfolio by creating and populating the data table
        
        Parameters
        ----------
        portfolio : a dictionary which contains all the information required to build the portfolio
            This includes:
                expected_returns : the expected return for each ticker; future enhancements allow
                    an alogrithm to build thid
                holding_periods : start and end date of holding for each position
                shares : number of shares held in each position
                constraints : constraints on the portfolio
                defaults : miscellaneous default values
        benchmark : a dictionary of weights of shares in the benchmark index
        
        Usage
        -------
        import params
        
        port_params = params.get_portfolio_params();
        bench_params = params.get_bench_params();
        
        port = Portfolio(port_params, bench_params)
        
        # internal (private) methods
        print port._get_historic_data(ticker, start, end)
        print port._get_historic_returns(ticker, start, end, offset=1)
        print port._build_portfolio(shares)
        
        #  public methods
        print port.get_benchmark_weights()
        print port.get_active_weights()
        print port.get_portfolio_weights()
        print port.get_holding_period_returns()
        print port.get_expected_stock_returns()
        print port.get_active_returns()
        print port.get_expected_excess_stock_returns()
        print port.get_covariance_matrix()
        print port.get_expected_benchmark_return()
        print port.get_benchmark_variance()
        print port.get_expected_portfolio_return()
        print port.get_portfolio_variance()
        print port.get_expected_excess_portfolio_return()
        print port.get_tracking_error_variance()
        """
        # do error checking here
        
        if start is not None:
            if type(start) == str or type(start) == datetime:
                start = time.mktime(time.strptime(start.strftime("%Y-%m-%d"), "%Y-%m-%d"))
            else:
                raise ValueError('Start date must be string (yyyy-mm-dd) or datetime object')
        else:
            start = portfolio['defaults']['start']
        
        if end is not None:
            if type(end) == str or type(end) == datetime:
                end = time.mktime(time.strptime(end.strftime("%Y-%m-%d"), "%Y-%m-%d"))
            else:
                raise ValueError('End date must be string (yyyy-mm-dd) or datetime object')
        else:
            start = portfolio['defaults']['end']
        
        holding_periods = portfolio['holding_periods']
        
        frequency = portfolio['defaults']['frequency']
        
        self._exp_ret = portfolio['expected_returns']
        self._hld_per = holding_periods
        self._shrs = portfolio['shares']
        self._freq = frequency
        self._start = start
        self._end = end
        
        self._proxy = proxy
    
        self._bench_wts = benchmark
        
        # build the table for the data
        createdailytable.reset_table()
        
        phobj = ph.InsertPriceHist(self._proxy)
        
        # load the data into the data table
        for symbol in holding_periods.keys():
            phobj.insert(symbol, holding_periods[symbol]['start'], holding_periods[symbol]['end'], frequency)

    def _get_historic_data(self, ticker, start, end):
        """
        
        Parameters
        ----------

        
        Returns
        -------
        
        """
        frequency = self._freq
        
        h5f = tables.openFile('price_data.h5', 'r')
        price_data = h5f.getNode('/price_data')
        
        cols = tuple([n for n in price_data.colnames])
        colnames = cols

        if type(start) == str or type(start) == datetime:
            start = time.mktime(time.strptime(start.strftime("%Y-%m-%d"), "%Y-%m-%d"))
        else:
            raise ValueError('Start date must be string (yyyy-mm-dd) or datetime object')
        
        if type(end) == str or type(end) == datetime:
            end = time.mktime(time.strptime(end.strftime("%Y-%m-%d"), "%Y-%m-%d"))
        else:
            raise ValueError('End date must be string (yyyy-mm-dd) or datetime object')

        condition = '(frequency == \'%s\') & (ticker == \'%s\') & (date >= start) & (date <= end)' % (frequency, ticker)
        res = price_data.readWhere(condition)
        
        h5f.close()
        
        cols = zip(*[row for row in res])
        data = dict(zip(colnames, cols))
        
        dates = pandas.Index([datetime.fromtimestamp(d) for d in data['date']])
        return pandas.DataFrame(data, index=dates, dtype='float').sort(ascending=True)

    def _get_historic_returns(self, ticker, start, end, offset=1):
        """
        
        Parameters
        ----------

        
        Returns
        -------

        
        """

        prices = self._get_historic_data(ticker, start, end)
        return pandas.Series(prices['adjustedClose'] / prices['adjustedClose'].shift(offset) - 1)

    def _build_portfolio(self, shares):
        """
        
        Parameters
        ----------
        
        Returns
        -------
        
        
        """
        positions = shares.keys()
        proxy = self._proxy
        yh = yahoo.Yahoo(positions, proxy)
        
        prices = {}; portfolio = {}
        for position in positions:
            prices[position] = yh.get_LastTradePriceOnly(position)
        
        portfolio['shares'] = shares
        portfolio['price'] = prices

        return pandas.DataFrame(portfolio)

    def get_trading_dates(self):
        """
        
        Parameters
        ----------
        
        Returns
        -------
        
        
        """
        return self.get_portfolio_historic_returns().index
        

    def get_portfolio_historic_returns(self):
        """
        
        Parameters
        ----------
        
        Returns
        -------
        
        
        """
        shares = self._shrs
        positions = shares.keys()
        periods = self._hld_per 
        
        returns = {}
        for position in positions:
            returns[position] = self._get_historic_returns(position, periods[position]['start'], periods[position]['end'])
        
        return pandas.DataFrame(returns)

    def get_portfolio_historic_position_values(self, start=None, end=None, shares=1):
        """
        
        Parameters
        ----------
        
        Returns
        -------
        
        
        """
        shares = self._shrs
        positions = shares.keys()
        periods = self._hld_per 

        prices = {}; portfolio = {}
        for position in positions:
            frame = self._get_historic_data(position, periods[position]['start'], periods[position]['end'])
            prices[position] = frame['adjustedClose'] * shares[position]
 
        return pandas.DataFrame(prices)

    def get_portfolio_historic_values(self, shares=None):
        """
        
        Parameters
        ----------
        
        Returns
        -------
        
        
        """
        if shares is None:
            shares = self._shrs
        
        positions = shares.keys()
        periods = self._hld_per 
        
        values = {}
        for position in positions:
            prices = self._get_historic_data(position, periods[position]['start'], periods[position]['end'])
            values[position] = prices['adjustedClose'] * shares[position]
 
        portfolio = pandas.DataFrame(values).sum(axis=1)
 
        return pandas.Series(portfolio)

    def get_benchmark_weights(self):
        """
        
        Parameters
        ----------
        
        Returns
        -------
        
        
        """
        return pandas.DataFrame({
            'bench_weights': self._bench_wts
        })

    def get_active_weights(self):
        """
        
        Parameters
        ----------
        
        Returns
        -------
        
        
        """
        portfolio = self.get_portfolio_weights()
        bench = self.get_benchmark_weights()
        
        return pandas.DataFrame({
            'active_weights': portfolio['port_weights'] - bench['bench_weights']
        })

    def get_portfolio_weights(self):
        """
        
        Parameters
        ----------
        
        Returns
        -------
        
        
        """
        shares = self._shrs
        portfolio = self._build_portfolio(shares)
        
        mkt_val = portfolio['shares'] * portfolio['price']
        portfolio_val = mkt_val.sum()
        
        return pandas.DataFrame({
            'port_weights': mkt_val / portfolio_val
        })

    def get_holding_period_returns(self):
        """
        
        Parameters
        ----------
        
        Returns
        -------
        
        
        """
        holding_periods = self._hld_per
        positions = holding_periods.keys()
        
        holding_period_returns = {}
        for position in positions:
            prices = self._get_historic_data(position, holding_periods[position]['start'], holding_periods[position]['end'])
            holding_period_returns[position] = (prices['adjustedClose'][-1] / prices['adjustedClose'][0]) - 1
        
        return pandas.DataFrame({
            'holding_period_return': holding_period_returns
        })

    def get_expected_stock_returns(self, start=None, end=None):
        """
        
        Parameters
        ----------
        
        Returns
        -------
        
        
        """
        return pandas.DataFrame({
            'expected_returns': self._exp_ret
        })

    def get_active_returns(self):
        """
        
        Parameters
        ----------
        
        Returns
        -------
        
        
        """
        active_weights = self.get_active_weights()
        holding_period_returns = self.get_holding_period_returns()
        
        return pandas.DataFrame({
            'active_return': active_weights['active_weights'] * holding_period_returns['holding_period_return']
        })

    def get_expected_excess_stock_returns(self, freq='m'):
        """
        
        Parameters
        ----------
        
        Returns
        -------
        
        
        """
        if freq == 'y':
            f = 1
        elif freq == 'm':
            f = 12
        elif freq == 'w':
            f = 52
        elif freq == 'd':
            f = 252
        
        expected_returns = self.get_expected_stock_returns()
        bench_weights = self.get_benchmark_weights()
        
        portvalue = self.get_portfolio_historic_position_values()
        total = portvalue.sum(axis=1)
        port_weights = portvalue / total
        
        excess_returns = self.get_portfolio_historic_returns() * (port_weights - bench_weights['bench_weights'])
        
        # one period lognormal model for noise
        # assumes ln(S / S_0) = m + s * randn
        # assumes mean = 0.03 and sigma = 0.05
        # could enhance by using estimates generated by CAPM
        N = self.get_portfolio_size()
        m = 0.03
        s = 0.05
        noise = m + s * np.random.randn(np.shape(excess_returns)[0], np.shape(excess_returns)[1])
        raw = excess_returns + noise
        
        # IR ~ IC * sqrt(breadth)
        # breadth = freq * N where N is the benchmark size
        # the authors fix the IR at 1.5 so IC = 1.5 / sqrt(freq * N)
        ic = 1.5 / sqrt(f * N)
        
        # step 2.
        score = (raw - raw.mean()) / raw.std()
        alpha = (excess_returns.std() * ic * score).dropna()

        '''
        return pandas.DataFrame({
            'expected_excess_returns': expected_returns['expected_returns'] - (bench_weights['bench_weights'] * expected_returns['expected_returns'])
        })
        '''
        
        return alpha

    def get_covariance_matrix(self, historic_returns, start=None, end=None):
        """
        
        Parameters
        ----------
        
        Returns
        -------
        
        
        """
        '''
        holding_periods = self._hld_per
        positions = holding_periods.keys()

        historic_returns = {}
        for position in positions:
            
            if start is None:
                start = holding_periods[position]['start']
            
            if end is None:
                end = holding_periods[position]['end']

            historic_returns[position] = self._get_historic_returns(position, start, end)
        '''
        frame = pandas.DataFrame(historic_returns).dropna()
        return pandas.DataFrame(np.cov(frame,  rowvar=0), index=frame.columns, columns=frame.columns)

    def get_shrunk_covariance_matrix(self, x, shrink=None):
        """Computes a covariance matrix that is "shrunk" towards a structured estimator. Code
            borrows heavily from the MATLAB implementation available by the authors online.
        
        Parameters
        ----------
        x : N x N sample covariance matrix of stock returns
        shrink : given shrinkage intensity factor; if none, code calculates
        
        Returns
        -------
        tuple : pandas.DataFrame which contains the shrunk covariance matrix
                : float shrinkage intensity factor
        
        """
        if x is None:
            raise ValueError('No covariance matrix defined')
        
        if type(x) == pandas.core.frame.DataFrame:
            cov = x.as_matrix()
        elif type(x) == np.ndarray:
            cov = x
        else:
            raise ValueError('Covariance matrix passed must be numpy.ndarray or pandas.DataFrame')
        
        if shrink is not None:
            shrinkage = shrink

        index = x.index
        columns = x.columns
        
        [t, n] = np.shape(cov)
        meanx = cov.mean(axis=0)
        cov = cov - np.tile(meanx, (t, 1))
        
        sample = (1.0 / t) * np.dot(cov.T, cov)
        
        var = np.diag(sample)
        sqrtvar = np.sqrt(var)

        a = np.tile(sqrtvar, (n, 1))
        rho = (sum(sum(sample / (a * a.T))) - n) / (n*(n-1))
        
        prior = rho * (a * a.T)
        prior[np.eye(t, n)==1] = var
        
        # Frobenius-norm of matrix cov, sqrt(sum(diag(dot(cov.T, cov))))
        # have to research this
        c = np.linalg.norm(sample-prior, 'fro')**2
        y = cov**2.0
        p = np.dot((1.0 / t), sum(sum(np.dot(y.T, y))))-sum(sum(sample**2.0))
        rdiag = np.dot((1.0 / t), sum(sum(y**2.0))) - sum(var**2.0)
        v = np.dot((cov**3.0).T, cov) / t - ((var*sample).T)
        v[np.eye(t, n)==1] = 0.0
        roff = sum(sum(v * (a  / a.T)))
        r = rdiag + np.dot(rho, roff)
        
        # compute shrinkage constant
        k = (p - r) / c
        shrinkage = max(0.0, min(1.0, k/t))
        sigma = np.dot(shrinkage, prior) + np.dot((1 - shrinkage), sample)
        
        return pandas.DataFrame(sigma, index=index, columns=columns), shrinkage

    def get_expected_benchmark_return(self):
        """
        
        Parameters
        ----------
        
        Returns
        -------
        
        
        """
        bench_weights = self.get_benchmark_weights()
        expected_portfolio_returns = self.get_expected_stock_returns()
        
        return pandas.DataFrame({
            'expected_benchmark_return': bench_weights['bench_weights'] * expected_portfolio_returns['expected_returns']
        })

    def get_benchmark_variance(self):
        """
        
        Parameters
        ----------
        
        Returns
        -------
        
        
        """
        bench_weights = self.get_benchmark_weights()
        cov_matrix = self.get_covariance_matrix()
        
        return pandas.DataFrame({
            'benchmark_variance': np.dot(bench_weights.T, np.dot(cov_matrix, bench_weights))
        })

    def get_expected_portfolio_return(self):
        """
        
        Parameters
        ----------
        
        Returns
        -------
        
        
        """
        portfolio_weights = self.get_portfolio_weights()
        expected_portfolio_returns = self.get_expected_stock_returns()
        
        return pandas.DataFrame({
            'expected_portfolio_return': portfolio_weights['port_weights'] * expected_portfolio_returns['expected_returns']
        })

    def get_portfolio_variance(self):
        """
        
        Parameters
        ----------
        
        Returns
        -------
        
        
        """
        port_weights = self.get_portfolio_weights()
        cov_matrix = self.get_covariance_matrix()
        
        return pandas.DataFrame({
            'portfolio_variance': np.dot(port_weights.T, np.dot(cov_matrix, port_weights))
        })

    def get_expected_excess_portfolio_return(self):
        """
        
        Parameters
        ----------
        
        Returns
        -------
        
        
        """
        active_weights = self.get_active_weights()
        expected_portfolio_returns = self.get_expected_stock_returns()
        
        return pandas.DataFrame({
            'expected_excess_portfolio_return': active_weights['active_weights'] * expected_portfolio_returns['expected_returns']
        })

    def get_tracking_error_variance(self):
        """
        
        Parameters
        ----------
        
        Returns
        -------
        
        
        """
        active_weights = self.get_active_weights()
        cov_matrix = self.get_covariance_matrix()
        
        return pandas.DataFrame({
            'tracking_error_variance': np.dot(active_weights.T, np.dot(cov_matrix, active_weights))
        })

    def get_portfolio_size(self):
        """
        
        Parameters
        ----------
        
        Returns
        -------
        
        
        """
        holding_periods = self._hld_per
        positions = holding_periods.keys()
        return len(positions)
    
    def information_ratio(self, returns, freq='m'):
        """Computes the information ratio
        IR ~ IC * sqrt(breadth)
        In our case, breadth is the number of bets per year. Bets per year is the frequency
        provided. By default, monthly.
        
        Parameters
        ----------
        
        Returns
        -------
        
        
        """
        if freq == 'y':
            f = 1
        elif freq == 'm':
            f = 12
        elif freq == 'w':
            f = 52
        elif freq == 'd':
            f = 252
        
        mean = returns.mean()
        stdev = returns.std()
        
        return (sqrt(f) * mean) / stdev