from context import ynapi
import unittest
import configparser
import os

class APITest(unittest.TestCase):

    def setUp(self):

        config_path = os.path.join(os.path.dirname(__file__),'config.ini')
        config = configparser.ConfigParser()
        config.read(config_path)

        self.API_token = config['YNAB']['API_token']
        self.budget_id = config['YNAB']['budget_id']
        self.session = ynapi.BudgetSession(self.API_token)

    def test_accountlist_islist(self):
        account_list = self.session.retrieve_account_list(self.budget_id)
        self.assertTrue(isinstance(account_list, list))
        pass

#    def test_txnlist_islist(self):
#        txn_list = self.session.retrieve_txn_list(self.budget_id, self.acct_id)
#        self.assertTrue(isinstance(account_list, list))


#    def test_split(self):
#        s = 'hello world'
#        self.assertEqual(s.split(), ['hello', 'world'])
#        # check that s.split fails when the separator is not a string
#        with self.assertRaises(TypeError):
#            s.split(2)

if __name__ == '__main__':
    unittest.main()
