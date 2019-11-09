import os
import json
from datetime import datetime
import logging
import configparser
import locale
import requests
import time
import ynapi
import sys
import pandas as pd

from ynapi.ynapi import BudgetSession

locale.setlocale( locale.LC_ALL, '')


class Transaction:
    def __init__(self, txn_id, date, amount, memo):
        self.txn_id = txn_id
        self.date = datetime.strptime(date,'%Y-%m-%d')
        self.amount = float(amount)
        self.memo = memo


class SecurityTxn(Transaction):
    def __init__(self, txn_id, date, amount, memo, action, units, price):
        super().__init__(txn_id, date, amount, memo)
        self.action = action
        self.units = units
        self.price = price


class Account:

    def __init__(self, acct_id, name, asset, cls, inst, acct_no, country, balance):
        self.acct_id = acct_id
        self.name = name
        self.asset = asset
        self.cls = cls
        self.inst = inst
        self.acct_no = acct_no
        self.country = country
        self.balance = balance
        self.current_value = balance
        self.transaction_list = []

    def __str__(self):
        return "Account Object ({}) - Name: {}".format(self.asset, self.name)

    def get_balance_at_date(self, config, before_date):

        try:
            self.transaction_list
        except AttributeError:
            self.get_transaction_list(self.config, acct_id)
        finally:
            balance = float(0)
            for transaction in self.transaction_list:
                if transaction.tx_date <= before_date:
                    balance += float(transaction.amount)

        print("Balance of {} at {} is ${}".format(self.name, before_date, round(balance,2)))

    def get_transaction_list(self, config, account_id):
        session = BudgetSession(config['YNAB']['API_token'])
        budget_id = config['YNAB']['budget_id']
        logging.info("Transferring YNAB transactions from {} into transaction list".format(self.name))
        ynab_txn_dict_list = session.retrieve_txn_list(budget_id, account_id)
        for txn_dict in ynab_txn_dict_list:
            txn_memo = txn_dict['memo']
            if txn_memo != None:
                if txn_memo[:1] == "{":
                    try:
                        meta = json.loads(txn_memo)['meta']
                    except KeyError:
                        logging.error(  "Meta tag not found; need to ensure all transactions"
                                        " with metadata in the memo has a meta index in the"
                                        " JSON code")

                    txn_inst = SecurityTxn(txn_dict['id'], txn_dict['date'], txn_dict['amount'],
                                        txn_dict['memo'], meta['action'], meta['units'],
                                        meta['price'])

                    logging.debug(txn_inst)
                    self.transaction_list.append(txn_inst)
            else:
                self.transaction_list.append(Transaction(txn_dict['id'], txn_dict['date'],
                                                txn_dict['amount'], txn_dict['memo']))


class Cash(Account):

    def __init__(self, acct_id, name, asset, cls, inst, acct_no, country, balance, bsb, currency):
        super().__init__(acct_id, name, asset, cls, inst, acct_no, country, balance)
        self.bsb = bsb
        self.currency = currency


class Security(Account):

    def __init__(self, acct_id, name, asset, cls, inst, acct_no, country, balance, HIN, symbol, valuator):
        super().__init__(acct_id, name, asset, cls, inst, acct_no, country, balance)
        self.HIN = HIN
        self.symbol = symbol
        self.valuator = valuator
        self.unit_balance = 0

    def get_order_list(self, config):
        session = BudgetSession(config['YNAB']['API_token'])
        raw_transaction_list = session.retrieve_account_transactions(self.acct_id)
        refined_transaction_list = []
        for raw_transaction in raw_transaction_list:
            if raw_transaction['memo'] != None:
                if raw_transaction['memo'][:1] == "{":
                    transaction_meta = json.loads(raw_transaction['memo'])['meta']
                    tx_date = datetime.strptime(raw_transaction['date'],'%Y-%m-%d')
                    action = transaction_meta['action']
                    amount = raw_transaction['amount']/1000
                    units = transaction_meta['units']
                    price = transaction_meta['price']
                    refined_transaction_list.append(Order(tx_date, action, amount, units, price))
        self.transaction_list = refined_transaction_list

    def find_unit_balance(self, config):
        session = BudgetSession(config['YNAB']['API_token'])
        for transaction in self.transaction_list:
            if transaction.__class__.__name__ == 'SecurityTxn':
                if transaction.action == "BUY":
                    self.unit_balance += transaction.units
                elif transaction.action == "SELL":
                    self.unit_balance -= transaction.units

        logging.debug("{} has {} units on hand".format(self.name, self.unit_balance))

class Allocation:

    def __init__(self, cls, total):
        self.cls = cls
        self.total = total


class Book:

    def __init__(self, config):
        self.config = config
        self.cash_account_list = []
        self.security_account_list = []

    def parse_ynab_accounts(self):
        session = BudgetSession(self.config['YNAB']['API_token'])
        ynab_account_list = session.retrieve_account_list(self.config['YNAB']['budget_id'])
        for account in ynab_account_list:
            if account['note'] != None:
                if account['note'][:1] == "{":
                    logging.debug('Dictionary detected, extracting meta data')
                    account_meta = json.loads(account['note'])['meta']
                    acct_id = account['id']
                    name = account['name']
                    inst = account_meta['inst']
                    acct_no = account_meta['acct_no']
                    asset = account_meta['asset']
                    cls = account_meta['cls']
                    country = account_meta['country']
                    balance = float(account['balance'])/1000
                    if asset == "cash":
                        bsb = account_meta['bsb']
                        currency = account_meta['currency']
                        account_inst = Cash(acct_id, name, asset, cls, inst, acct_no, country, balance, bsb, currency)
                        account_inst.get_transaction_list(self.config, acct_id)
                        self.cash_account_list.append(account_inst)
                    if asset == "sec":
                        HIN = account_meta['HIN']
                        symbol = account_meta['symbol']
                        valuator = account_meta['valuator']
                        account_inst = Security(acct_id, name, asset, cls, inst, acct_no, country, balance, HIN, symbol, valuator)
                        account_inst.get_transaction_list(self.config, acct_id)
                        account_inst.find_unit_balance(self.config)
                        self.security_account_list.append(account_inst)

    def calculate_asset_allocations(self):
        self.asset_allocation = {}
        try:
            self.cash_account_list
        except:
            self.parse_ynab_accounts()
        finally:
            cash_total = 0
            fixedinterest_total = 0
            property_total = 0
            shares_total = 0
            for account in self.cash_account_list:
                if account.cls == "cash":
                    cash_total += account.balance
            self.asset_allocation['cash'] = (Allocation("cash", total=cash_total))
        try:
            self.security_account_list
        except:
            self.parse_ynab_accounts()
        finally:
            for account in self.security_account_list:
                if account.cls == "fixed_interest":
                    fixedinterest_total += account.balance
                elif account.cls == "property":
                    property_total += account.balance
                elif account.cls == "shares":
                    shares_total += account.balance
            self.asset_allocation['fixed_interest'] = Allocation("Fixed Interest", total=fixedinterest_total)
            self.asset_allocation['property'] = Allocation("Property", total=property_total)
            self.asset_allocation['shares'] = Allocation("Shares", total=shares_total)
            self.total_assets = cash_total + fixedinterest_total + property_total + shares_total

    def update_account_value(self):
        av_session = AlphaVantage(self.config)
        logging.info("Determining current value of accounts")
        USDAUD = av_session.find_exchange_rate(from_currency="USD", to_currency="AUD")
        for account in self.security_account_list:
            if account.country == "Australia":
                account.exchange_rate=1
            elif account.country == "United States":
                account.exchange_rate= USDAUD
            if account.valuator == 'AV':
                time.sleep(20)
                logging.debug("Identifying unit price using Alpha Vantage")
                unit_price = av_session.find_unit_price(account.symbol)
                #TODO: DRY THIS
                account_value = account.unit_balance * unit_price * account.exchange_rate
                logging.info("{} is currently worth AUD ${}".format(account.name, account_value))
                account.current_value = account_value
            if account.valuator == 'MS':
                logging.debug("Identifying unit price using Morningstar")
                #TODO: Add morningstar fund number fields
                unit_price = morningstar.find_unit_price(account.symbol)
                #TODO: DRY THIS
                account_value = account.unit_balance * unit_price * account.exchange_rate
                logging.info("{} is currently worth AUD ${}".format(account.name, account_value))
                account.current_value = account_value

    def update_account_balance(self, correct_thresh):
        session = BudgetSession(self.config['YNAB']['API_token'])
        logging.info("Making account corrections to update value")
        for account in self.security_account_list:
            correction = account.current_value-account.balance
            if abs(correction) > correct_thresh:
                txn_json = session.construct_value_update_txn(account.account_id, correction, account.inst_id)
                session.send_transaction_to_YNAB(self.budget_id, account.account_id, txn_json)
            else:
                logging.info("Value of {} has not changed by more than {}".format(account.name, correct_thresh))


class AlphaVantage:
    def __init__(self, config):
        self.apikey = config['ALPHA VANTAGE']['API_token']

    def find_unit_price(self, symbol):
        url = "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={0}&apikey={1}".format(symbol, self.apikey)
        r = requests.get(url)
        r_dict = json.loads(r.text)
        try:
            time_series = r_dict["Time Series (Daily)"]
            most_recent = next(iter(time_series))
            unit_price = float(time_series[most_recent]['4. close'])
        except Exception as e:
            logging.error("Invalid API call. Either symbol ({}) is wrong or key expired, {}".format(symbol, e))
            sys.exit(1)
        return unit_price

    def find_exchange_rate(self, from_currency, to_currency):
        url = "https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={}&to_currency={}&apikey={}".format(from_currency, to_currency, self.apikey)
        r = requests.get(url)
        r_dict = json.loads(r.text)
        try:
            exchange_rate = r_dict["Realtime Currency Exchange Rate"]["5. Exchange Rate"]
        except Exception as e:
            logging.error("Invalid API call {}".format(e))
            sys.exit(1)
        return float(exchange_rate)

def find_unit_price(fund_number):
    url = "https://www.morningstar.com.au/Funds/FundReport/{0}".format(fund_number)
    tables = pd.read_html(url) # Returns list of all tables on page
    quickstats = tables[5] # Select table of interest
    close_price = float(quickstats[1][5])

    return close_price
