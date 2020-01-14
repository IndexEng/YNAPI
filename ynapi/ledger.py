import json
from datetime import datetime
from datetime import timedelta as tdelta
import logging
import locale
import requests
import pandas as pd
import time
import sys
from ynapi.ynapi import BudgetSession
locale.setlocale(locale.LC_ALL, '')

# TODO Calculate value of account at a particular date
# TODO Create a value history for each account by date


class Book:

    def __init__(self, ynab_api_token, av_key, budget_id, auto_populate=True):
        # TODO valuator vs unit evaluator is confusing
        self.budget_id = budget_id
        self.session = BudgetSession(ynab_api_token)
        self.unit_evaluator = Evaluation(av_key)
        self.account_list = []
        if auto_populate is True:
            self.populate_account_lists()

    def populate_account_lists(self):
        """Creates account objects and stores them in an list of objects"""
        json_account_list = self.session.retrieve_account_list(self.budget_id)
        for account in json_account_list:
            if account['note'] is not None:
                if account['note'][:1] == "{":
                    self.create_new_account(account)
        logging.debug("Account list populated")

    def create_new_account(self, account_json):
        """Creates specialised account obj once passed json with meta data"""
        meta = json.loads(account_json['note'])['meta']
        if meta['asset'] == "cash":
            acct_instance = Cash(account_json['id'], account_json['name'],
                                 meta['asset'], meta['cls'],
                                 meta['inst_id'], meta['acct_no'],
                                 meta['country'], meta['currency'],
                                 float(account_json['balance'])/1000,
                                 meta['bsb'])
            acct_instance.populate_cash_transaction_list(self.session,
                                                         self.budget_id)
        elif meta['asset'] == "sec":
            acct_instance = Security(account_json['id'], account_json['name'],
                                     meta['asset'], meta['cls'],
                                     meta['inst_id'], meta['acct_no'],
                                     meta['country'], meta['currency'],
                                     float(account_json['balance'])/1000,
                                     meta['HIN'], meta['symbol'],
                                     meta['valuator'], meta['sector'])
            acct_instance.populate_value_list(self.session, self.budget_id)
        acct_instance.populate_transaction_list(self.session, self.budget_id)
        self.account_list.append(acct_instance)

    def asset_allocation(self, at_date, classifier):
        allocation_dict = {}
        for account in self.account_list:
            value_at_date = round(account.ynab_value(at_date),2)
            if classifier is "cls":
                allocators = account.cls
            elif classifier is "country":
                allocators = account.country
            elif (classifier is "sector") and \
                 (account.__class__.__name__ is "Security"):
                allocators = account.sector
            else:
                allocators = {}
            for allocator, proportion in allocators.items():
                if allocator in allocation_dict:
                    allocation_dict[allocator] += value_at_date*proportion
                else:
                    allocation_dict[allocator] = value_at_date*proportion
        return allocation_dict

    def asset_allocation_percentage(self, allocation_dict):
        total = sum([allocation for asset, allocation in allocation_dict.items() if asset != "Allocated"])
        alloc_perc_dict = {}
        for asset, allocation in allocation_dict.items():
            if asset != "Allocated":
                alloc_perc_dict[asset] = round(allocation/total, 2)
        return alloc_perc_dict

    def net_worth(self, at_date):
        networth = 0
        asset_allocation = self.asset_allocation(at_date, 'cls')
        for asset, allocation in asset_allocation.items():
            if asset != "Allocated":
                networth += allocation
        return networth

    def update_sec_todayvalue_on_ynab(self, correct_thresh):
        logging.info("Making account corrections to update value")
        for account in self.account_list:
            if account.__class__.__name__ == "Security":
                today = datetime.now()
                actual_today = account.holdings_value_today(self.unit_evaluator)
                ynab_today = account.ynab_value(today)
                correction = actual_today - ynab_today
                if abs(correction) > correct_thresh:
                    txn_json = self.session.construct_value_update_txn(
                        account.acct_id, correction,
                        account.inst)
                    self.session.send_transaction_to_YNAB(self.budget_id, account.acct_id, txn_json)


class Account:

    def __init__(self, acct_id, name, asset, cls,
                 inst, acct_no, country, currency, balance):
        self.acct_id = acct_id
        self.name = name
        self.asset = asset
        self.cls = cls
        self.inst = inst
        self.acct_no = acct_no
        self.country = country
        self.currency = currency
        self.balance = balance
        self.current_value = balance
        self.transaction_list = []
        logging.info("Account created called {}"
                     .format(name))

    def __repr__(self):
        return "Account Object ({}) - Name: {}".format(self.asset, self.name)

    def populate_transaction_list(self, session, budget_id):
        """Retrieves json txns and adds to account txns as txn objects"""
        logging.debug('Populating transactions in {}'.format(self.name))
        json_txn_list = session.retrieve_txn_list(budget_id, self.acct_id)
        for json_txn in json_txn_list:
            if json_txn['memo'] is not None:
                if json_txn['memo'][:1] == '{':
                    meta = json.loads(json_txn['memo'])['meta']
                    txn_date = datetime.strptime(json_txn['date'], '%Y-%m-%d')
                    if (meta['action'] == 'BUY'
                        and json_txn['amount'] > 0) or \
                        (meta['action'] == 'SELL'
                         and json_txn['amount'] < 0):
                        txn_instance = Order(json_txn['id'],
                                             txn_date,
                                             json_txn['amount']/1000,
                                             json_txn['memo'], meta['action'],
                                             meta['units'], meta['price'])
                        self.transaction_list.append(txn_instance)
                        logging.debug("Added a {} to txn list"
                                      .format(txn_instance))


class Cash(Account):

    def __init__(self, acct_id, name, asset, cls, inst,
                 acct_no, country, currency, balance, bsb):
        super().__init__(acct_id, name, asset, cls, inst,
                         acct_no, country, currency, balance)
        self.bsb = bsb

    def __repr__(self):
        return "Cash - {} (Current Balance: {} ${})"\
                .format(self.name, self.currency, self.balance)

    def populate_cash_transaction_list(self, session, budget_id):
        """Retrieves json txns and adds to cash txns as txn objects"""
        logging.debug('Populating cash transactions in {}'.format(self.name))
        json_txn_list = session.retrieve_txn_list(budget_id, self.acct_id)
        for json_txn in json_txn_list:
            txn_date = datetime.strptime(json_txn['date'], '%Y-%m-%d')
            txn_instance = Transaction(json_txn['id'],
                                       txn_date,
                                       json_txn['amount'] / 1000,
                                       json_txn['memo'])
            self.transaction_list.append(txn_instance)
            logging.debug("Added a {} to cash txn list"
                          .format(txn_instance))

    def ynab_value(self, at_date):
        """finds ynab cash account value at date"""
        return sum(txn.amount for txn in self.transaction_list
                   if txn.date <= at_date)


class Security(Account):

    def __init__(self, acct_id, name, asset, cls, inst, acct_no,
                 country, currency, balance, HIN, symbol, valuator, sector):
        super().__init__(acct_id, name, asset, cls, inst,
                         acct_no, country, currency, balance)
        self.HIN = HIN
        self.symbol = symbol
        self.valuator = valuator
        self.sector = sector
        self.value_list = []

    def unit_balance(self, at_date):
        """Calculate the units on hand at a particular date"""
        orders = [txn for txn in self.transaction_list
                  if txn.__class__.__name__ is "Order" and txn.date <= at_date]
        units_bought = sum([order.units
                            for order in orders if order.action == 'BUY'])
        units_sold = sum([order.units
                          for order in orders if order.action == 'SELL'])
        logging.debug('{} was checked, {} units bought, {} units sold by {}'
                      .format(self.name, units_bought, units_sold, at_date))
        return units_bought - units_sold

    def unit_price_aud(self, at_date, unit_evaluator):
        """Calculate security unit price on a given date in AUD"""
        # TODO fix morning star evaluator to work for any date
        # TODO Error handling if valuator is wrong or doesnt exist
        exchange_rate = unit_evaluator.xrate_to_aud(at_date, self.currency)
        if self.valuator == 'AV':
            unit_price = unit_evaluator.av_unit_price(self.symbol, at_date)
        elif self.valuator == 'MS':
            logging.warning("Unit price retrieved for today only!")
            unit_price = unit_evaluator.ms_unit_price_now(self.symbol)
        elif self.valuator == 'ABC':
            # TODO Write ABC valuator
            unit_price = 2100
        try:
            logging.debug("Price for a unit of {} is ${}({}) or ${}(AUD)"
                          .format(self.symbol, unit_price, self.currency,
                                  (exchange_rate * unit_price)))
        except:
            logging.error("Unit price not located for {}".format(self.name))
            sys.exit(1)
        return exchange_rate*unit_price

    def populate_value_list(self, session, budget_id):
        """Retrieves json txns and adds to cash txns as txn objects"""
        logging.info('Populating security value txns in {}'.format(self.name))
        json_txn_list = session.retrieve_txn_list(budget_id, self.acct_id)
        for json_txn in json_txn_list:
            txn_date = datetime.strptime(json_txn['date'], '%Y-%m-%d')
            txn_instance = Transaction(json_txn['id'],
                                       txn_date,
                                       json_txn['amount'] / 1000,
                                       json_txn['memo'])
            self.value_list.append(txn_instance)
            logging.debug("Added a {} to value list"
                          .format(txn_instance))

    def ynab_value(self, at_date):
        """finds ynab cash account value at date"""
        return sum(txn.amount for txn in self.value_list
                   if txn.date <= at_date)

    def holdings_value_today(self, unit_evaluator):
        today = datetime.now()
        unit_balance = self.unit_balance(today)
        unit_price_aud = self.unit_price_aud(today, unit_evaluator)
        return unit_balance * unit_price_aud


class Evaluation:

    def __init__(self, av_key):
        self.av_key = av_key

    def av_unit_price(self, symbol, at_date):
        # TODO improve error handling
        # TODO improve multiple attempt failure handling
        """Uses AlphaVantage to find the unit price of a symbol at a date"""

        url = "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&"\
              "outputsize=full&symbol={0}&apikey={1}"\
              .format(symbol, self.av_key)
        fail = True
        attempt = 0
        while (fail is True) and (attempt < 10):
            try:
                r = requests.get(url)
                time_series = json.loads(r.text)["Time Series (Daily)"]
                fail = False
                logging.info("Time series retreival was successful")
            except:
                fail = True
                time.sleep(10)
                attempt += 1
                logging.warning("Time series unsuccessful. Attempt {}"
                                .format(attempt))
            check_date_strings = [(at_date-tdelta(days=3)).strftime("%Y-%m-%d"),
                                  (at_date-tdelta(days=2)).strftime("%Y-%m-%d"),
                                  (at_date-tdelta(days=1)).strftime("%Y-%m-%d"),
                                  (at_date+tdelta(days=1)).strftime("%Y-%m-%d"),
                                  at_date.strftime("%Y-%m-%d")]
        for check_date in check_date_strings:
            try:
                unit_price = time_series[check_date]['4. close']
            except Exception as e:
                logging.warning("Unit price not recorded for {}"
                                .format(check_date))
                logging.error(e)
        try:
            logging.debug("Unit price for {} on {} is ${} (using AlphaVantage)"
                          .format(symbol, at_date, unit_price))
        except:
            logging.error("Unit price not located for {}".format(symbol))
            sys.exit(1)

        return float(unit_price)

    def xrate_to_aud(self, at_date, from_currency):
        """Uses AlphaVantage to find X rate from currency to AUD on date"""
        # TODO Find more elegant solution than wait 15 seconds
        if from_currency == "AUD":
            exchange_rate = 1
        else:
            url = "https://www.alphavantage.co/query?function=FX_DAILY&"\
                  "from_symbol={}&to_symbol=AUD&outputsize=full&apikey={}"\
                  .format(from_currency, self.av_key)
            fail = True
            attempt = 0
            while (fail is True) and (attempt < 10):
                try:
                    r = requests.get(url)
                    time_series = json.loads(r.text)["Time Series FX (Daily)"]
                    fail = False
                    logging.info("Time series retreival was successful")
                except:
                    fail = True
                    time.sleep(10)
                    attempt += 1
                    logging.warning("Time series unsuccessful. Attempt {}"
                                    .format(attempt))
            check_date_strings = [(at_date-tdelta(days=1)).strftime("%Y-%m-%d"),
                                  (at_date+tdelta(days=1)).strftime("%Y-%m-%d"),
                                   at_date.strftime("%Y-%m-%d")]
            for check_date in check_date_strings:
                try:
                    exchange_rate = time_series[check_date]['4. close']
                except:
                    pass
        logging.debug("Exchange rate from {} to AUD on {} is {}"
                      .format(from_currency, at_date, exchange_rate))
        return float(exchange_rate)

    def ms_unit_price_now(self, fund_number):
        # TODO Review, docstring, tidy
        url = "https://www.morningstar.com.au/Funds/FundReport/{0}"\
              .format(fund_number)
        tables = pd.read_html(url)
        quickstats = tables[5]
        close_price = float(quickstats[1][5])

        return close_price

    def fortunaoz_unit_price_now():
        # TODO Review, docstring, tidy
        header = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.75"
                  "Safari/537.36", "X-Requested-With": "XMLHttpRequest"}
        url = "https://www.australianbullioncompany.com.au/todays-prices/"
        r = requests.get(url, headers=header)
        tables = pd.read_html(r.text)
        pamp_table = tables[1]
        fort_buy_price = float(pamp_table['Buy Back'][8][1:].replace(',', ''))
        return fort_buy_price


class Transaction:
    def __init__(self, txn_id, date, amount, memo):
        self.txn_id = txn_id
        self.date = date
        self.amount = float(amount)
        self.memo = memo

    def __repr__(self):
        return "Transaction for ${}({})".format(self.amount, self.date)


class Order(Transaction):

    def __init__(self, txn_id, date, amount, memo, action, units, price):
        super().__init__(txn_id, date, amount, memo)
        self.action = action
        self.units = units
        self.price = price

    def __repr__(self):
        return "{} order for {} units (at ${}/unit)".format(self.action,
                                                            self.units,
                                                            self.price)


class Distribution(Transaction):
    def __init__(self, txn_id, date, amount, memo, action, units, price):
        super().__init__(txn_id, date, amount, memo)
        logging.debug("Creating transaction: ", self.__dict__)
