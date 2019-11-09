import configparser
import logging
import os
import glob
import codecs
from ofxparse import OfxParser
from context import BudgetSession
from anzapi.sdriver import BankingSession
import datetime

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

account_list = [
'4be706e3-6443-4e2f-94ba-2b29657f46f7',
'0eae96b6-3ab5-4d78-a570-5ecd96c29a5f',
'a6d76618-cf55-b693-2ec6-02471c25627b',
'bb25c9bb-e8e3-49ce-a36a-d1d1f5d7c319',
'9e5de04c-fee5-4b98-90ec-1700dd311389',
'ea06aa86-dfdd-dd45-33a9-02471c25dd1a',
'3d6b5c89-76ef-4d98-4f6d-02471c25c28b',
'cb1dcc46-7cc1-10a6-9c12-02471c251504',
'0b80c649-ad31-418c-a16e-fa33589ed1d6',
'fd770d7c-e196-4f24-a3a6-7571fe9e14d1',
'49a06e4b-1b2c-413c-8aa5-db20c8f0c79e',
'cec70cec-e94d-4e48-8eb6-cc5afc4a6635',
'2eea73e1-6f92-0525-35ee-02471c25b85d',
'e30476d1-5bf2-0473-5b40-02471c25ae8b',
'673171da-fd12-b416-6b44-02471c257fd6',
'6cc4619d-ed82-4eeb-8974-fe14b542fa73',
'c6a067b1-34ab-45fb-abe1-fe9c09d52108',
]

date_list = [
datetime.date(2019,8,30),
datetime.date(2019,9,30),
datetime.date(2019,10,30),
]

bal_hist = session.multiple_account_bal_history(budget_id, account_list, date_list)
print(bal_hist)
