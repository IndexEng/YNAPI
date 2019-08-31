import configparser
import logging
import os
import glob
import codecs
from ofxparse import OfxParser

from context import BudgetSession
from anzapi.sdriver import BankingSession

logging.basicConfig(level=logging.DEBUG)

config_path = os.path.join(os.path.dirname(__file__),'config.ini')
config = configparser.ConfigParser()
config.read(config_path)

crn = config['ANZ']['crn']
pswd = config['ANZ']['pass']
download_path = config['TEMP']['path']

API_token = config['YNAB']['API_token']
budget_id = config['YNAB']['budget_id']

session = BudgetSession(API_token)

acct_list = session.retrieve_account_list(budget_id)
print(session.find_account_id(acct_list, '555794334'))
