import configparser
import os
import logging
import sys
import requests
import json
from datetime import datetime
import time
from context import BudgetSession, Book, AlphaVantage, fortunaoz_unit_price

logging.basicConfig(level=logging.DEBUG)

logging.info("Loading configuration file")
config_path = os.path.join(os.path.dirname(__file__),'config.ini')

if os.path.exists(config_path) is False:
    logging.error("The config file does not exist. Make sure you have written the config.ini")
    sys.exit(1)

config = configparser.ConfigParser()
config.read(config_path)

ynab_api_token = config['YNAB']['API_token']
budget_id = config['YNAB']['budget_id']

session = BudgetSession(ynab_api_token)

ledger = Book(config, session)

at_date = datetime(2019, 8, 1)
date_from = datetime(2017, 8, 13)
date_to = datetime(2019, 10, 1)

#av = AlphaVantage(config)
#av.unit_price_at_date('HACK', datetime(2019, 3, 13))
#symbol = ledger.security_account_list[1].symbol
#valuator = ledger.security_account_list[1].valuator
#country = ledger.security_account_list[1].country

#av_session = AlphaVantage(config)

#order = ledger.security_account_list[1].order_list[0]
#print(ledger.security_account_list[1].name)
#print(ledger.security_account_list[1].unit_price(av_session, at_date))
#print(ledger.security_account_list[1].order_value(av_session, order, at_date))
#print(ledger.security_account_list[1].account_investment_return(av_session, date_from, date_to))

#ledger.parse_ynab_accounts()
#ledger.update_account_value()
#ledger.update_account_balance(100)

#ledger.calculate_asset_allocations()
#print(ledger.asset_allocation)
#[print(alloc.cls, alloc.total) for alloc in ledger.asset_allocation]
