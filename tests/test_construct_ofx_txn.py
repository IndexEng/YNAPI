'''Script to synchronise bank accounts and budget accounts'''
import configparser
import logging
import os
import glob
import codecs
import time
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

list_of_ofx_paths = glob.glob('{}/*.ofx'.format(download_path))

session = BudgetSession(API_token)

for ofx_path in list_of_ofx_paths:

    with codecs.open(ofx_path) as account_file:
        acct_dat_raw = OfxParser.parse(account_file)
        acct_dat = acct_dat_raw.accounts[0]

        account_number = acct_dat.account_id

        YNAB_account_list = session.retrieve_account_list(budget_id)
        account_id = session.find_account_id(YNAB_account_list, account_number)

        transactions = acct_dat.statement.transactions

        json_txn_list = []
        for ofx_txn in transactions:
            json_txn = session.construct_ofx_child_transaction(account_id, ofx_txn)

            json_txn_list.append(json_txn)

        payload = session.construct_transaction_list_json(json_txn_list)
        session.send_transaction_to_YNAB(budget_id, account_id, payload)
