import unittest
import configparser
import logging
from datetime import datetime
import os
from context import Book, Evaluation

logging.basicConfig(level=logging.DEBUG)


class TestStringMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
        if os.path.exists(config_path) is False:
            logging.error("The config file does not exist. Make sure you have " 
                          "written the config.ini")
            sys.exit(1)
        config = configparser.ConfigParser()
        config.read(config_path)
        ynab_api_token = config['YNAB']['API_token']
        av_key = config['ALPHA VANTAGE']['API_token']
        cls.budget_id = config['YNAB']['budget_id']
        cls.value = Evaluation(av_key)
        cls.ledger = Book(ynab_api_token, av_key, cls.budget_id)

    def test_av_unit_price(self):
        unit_price = float(self.value.av_unit_price('AAPL', datetime(2019, 2, 12)))
        self.assertEqual(unit_price, 170.89)

    def test_xrate(self):

        at_date = datetime(2019, 2, 12)
        currency_list = ["USD", "NZD", "AUD"]
        for currency in currency_list:
            self.value.xrate_to_aud(at_date, currency)

    def test_ynab_cash_value(self):
        at_date = datetime(2019, 10, 15)
        target_balance_at_date = 57075.91
        # TODO Make so it finds Invested Saver without index
        balance_at_date = self.ledger.account_list[12].ynab_value(at_date)
        self.assertEqual(round(balance_at_date, 2), target_balance_at_date)

    def test_asset_allocation(self):
        at_date = datetime(2019, 11, 20)
        classifier = 'country'
        allocation = self.ledger.asset_allocation(at_date, classifier)
        logging.info(allocation)
        classifier = 'cls'
        allocation = self.ledger.asset_allocation(at_date, classifier)
        logging.info(allocation)
        alloc_perc = self.ledger.asset_allocation_percentage(allocation)
        logging.info(alloc_perc)
        classifier = 'sector'
        allocation = self.ledger.asset_allocation(at_date, classifier)
        logging.info(allocation)

    def test_networth(self):
        at_date = datetime(2019, 9, 30)
        networth = self.ledger.net_worth(at_date)
        logging.info("Net worth at {} is {}".format(at_date, networth))
        self.assertEqual(round(networth, 2), 331280.16)

    def test_holdings_value_today(self):
        self.ledger.account_list[9].holdings_value_today(self.ledger.unit_evaluator)

    def test_update_sec_todayvalue_on_ynab(self):
        self.ledger.update_sec_todayvalue_on_ynab(100)

if __name__ == '__main__':
    unittest.main()

