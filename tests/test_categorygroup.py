from context import BudgetSession, CategoryGroup
import os
import glob
import configparser

config_path = os.path.join(os.path.dirname(__file__),'config.ini')
config = configparser.ConfigParser()
config.read(config_path)

crn = config['ANZ']['crn']
pswd = config['ANZ']['pass']
download_path = config['TEMP']['path']

API_token = config['YNAB']['API_token']
budget_id = config['YNAB']['budget_id']

session = BudgetSession(API_token)

session.retrieve_category_list(budget_id)

print(session.category_list)
