from context import BudgetSession, CategoryGroup, Ledger
import os
import glob
import configparser
import logging

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
budget = Ledger(api_key=ynab_api_token, budget_id=budget_id)
budget.load_account_list(session)
