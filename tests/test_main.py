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

list_of_ofx_paths = glob.glob('{}/*.ofx'.format(download_path))

ofx_path = list_of_ofx_paths[0]

with codecs.open(ofx_path) as account_file:
    acct_dat_raw = OfxParser.parse(account_file)
    acct_dat = acct_dat_raw.accounts[0]
    transactions = acct_dat.statement.transactions
    transaction = transactions[0]

    ynab_accounts = session.retrieve_account_list(budget_id)

    account_id = ynab_accounts[7]['id']

    txn_json = session.construct_ofx_transaction(account_id, transaction)
    session.send_transaction_to_YNAB(budget_id, account_id, txn_json)



    print("{}, {}, {}".format(transaction.date,transaction.amount,transaction.memo))
