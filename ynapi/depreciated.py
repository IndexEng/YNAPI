'''Initialise the book with the variables it needs to start. Will only pass variables when they are needed (if they are needed).

With the session initialised, we need to get to work populating the account list. Will create a single account list, and accoutn types is differentiated by class.

The question is, should we manage the YNAB api session internally or externally. For simplicity, we should probably manage it internally.

I can also simplify the book object by only having to store some of the variables from the config file.'''

## DEPRECIATED ##


    def create_new_account(self, account_json):
        account_meta = json.loads(account_json['note'])['meta']

            account_inst.populate_transaction_list(self.config)
            account_inst.find_unit_balance(self.config, datetime.now())
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
        #TODO depreciated, convert to using holding evaluations (inside txn method)
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
                unit_price = av_session.av_unit_price(account.symbol)
                #TODO: DRY THIS
                account_value = account.unit_balance * unit_price * account.exchange_rate
                logging.info("{} is currently worth AUD ${}".format(account.name, account_value))
                account.current_value = account_value
            if account.valuator == 'MS':
                logging.debug("Identifying unit price using Morningstar")
                #TODO: Add morningstar fund number fields
                unit_price = morningstar_unit_price(account.symbol)
                #TODO: DRY THIS
                account_value = account.unit_balance * unit_price * account.exchange_rate
                logging.info("{} is currently worth AUD ${}".format(account.name, account_value))
                account.current_value = account_value
            if account.valuator == 'ABC':
                logging.debug("Identifying unit price using Australian Bullion Company")
                unit_price = fortunaoz_unit_price()
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
                txn_json = session.construct_value_update_txn(account.acct_id, correction, self.config['YNAB']['investment_category_id'])
                session.send_transaction_to_YNAB(self.config['YNAB']['budget_id'], account.acct_id, txn_json)
            else:
                logging.info("Value of {} has not changed by more than {}".format(account.name, correct_thresh))






    def populate_transaction_list(self, config):
        session = BudgetSession(config['YNAB']['API_token'])
        raw_transaction_list = session.retrieve_txn_list(config['YNAB']['budget_id'], self.acct_id)
        for raw_transaction in raw_transaction_list:
            memo = raw_transaction['memo']
            if memo != None:
                if memo[:1] == '{':
                    transaction_meta = json.loads(raw_transaction['memo'])['meta']
                    txn_id = raw_transaction['id']
                    tx_date = datetime.strptime(raw_transaction['date'],'%Y-%m-%d')
                    action = transaction_meta['action']
                    amount = raw_transaction['amount']/1000
                    units = transaction_meta['units']
                    price = transaction_meta['price']

                    if transaction_meta['action'] == 'DIST':
                        logging.info("Distribution recorded in {}".format(self.name))
                        self.distribution_list.append(Distribution(txn_id, tx_date, action, amount, units, price))
                    elif (transaction_meta['action'] == 'SELL' or transaction_meta['action'] == 'BUY') and self.asset == 'sec':
                        logging.info("{} order recorded in {} account".format(action, self.name))
                        self.order_list.append(Order(txn_id, tx_date, amount, memo, action, units, price))
                else:
                    self.transaction_list.append(Transaction(raw_transaction['id'],
                                                             raw_transaction['date'],
                                                             raw_transaction['amount'],
                                                             raw_transaction['memo']))


    def get_balance_at_date(self, config, before_date):
        try:
            self.transaction_list
        except AttributeError:
            self.populate_transaction_list(self.config)
        finally:
            balance = float(0)
            for transaction in self.transaction_list:
                if transaction.tx_date <= before_date:
                    balance += float(transaction.amount)
        logging.debug("Balance of {} at {} is ${}".format(self.name, before_date, round(balance,2)))
        return balance


    def period_investment_return(self, period_start, period_end):
        # find period return for each order object in this account
        pass






class Security(Account):

    def __init__(self, acct_id, name, asset, cls, inst, acct_no, country, balance, HIN, symbol, valuator):
        super().__init__(acct_id, name, asset, cls, inst, acct_no, country, balance)
        self.HIN = HIN
        self.symbol = symbol
        self.valuator = valuator
        self.unit_balance = 0
        self.order_list = []


    def __repr__(self):
        return "Security - {} ({} Units)".format(self.symbol, self.unit_balance)


    def find_unit_balance(self, config, at_date):
                session = BudgetSession(config['YNAB']['API_token'])
        for transaction in self.order_list:
            if transaction.date <= at_date:
                if transaction.action == "BUY":
                    self.unit_balance += transaction.units
                elif transaction.action == "SELL":
                    self.unit_balance -= transaction.units
        logging.debug("{} has {} units on hand".format(self.name, self.unit_balance))


    def order_unit_balance(self, at_date, order):

        #TODO Add functionality for units sold
        if order.date <= at_date:
            balance = order.units
        else:
            balance = 0
        logging.debug('{} units in order {}.'.format(order.units, order.txn_id))
        return balance


    def unit_price(self, av_session, at_date):
        '''calculate the unit price of security in AUD'''
        #TODO Valuators need to work at a given date
        rate = self.exchange_rate(av_session)
        if self.valuator == 'AV':
            price = av_session.unit_price_at_date(self.symbol, at_date)
        if self.valuator == 'MS':
            logging.error('Price by date not supported for MS, retreiving latest')
            price = morningstar_unit_price(self.symbol)
        if self.valuator == 'ABC':
            price = fortunaoz_unit_price()
        unit_price_aud = price * rate
        logging.debug('Per unit price in AUD for {} is {}. Evaluated using {}'.format(self.symbol, unit_price_aud, self.valuator))
        return unit_price_aud


    def exchange_rate(self, av_session):
        '''calculate exchange rate of target to AUD using AlphaVantage'''
        if self.country == "Australia":
            exchange_rate = 1
        elif self.country == "United States":
            exchange_rate = av_session.find_exchange_rate(from_currency="USD", to_currency="AUD")
        logging.debug('Unit value to AUD exchange rate is {}. Country of origin is {}'.format(exchange_rate, self.country))
        return exchange_rate


    def order_value(self, av_session, order, at_date):
        '''calculate total value of an order at a given date'''
        unit_price = self.unit_price(av_session, at_date)
        order_value = unit_price * self.order_unit_balance(at_date, order)
        logging.debug("Total value of Order {} on {} is ${}".format(order.txn_id, at_date, order_value))
        return order_value


    def individual_order_return(self, av_session, order, date_from, date_to):
        '''determine the investment return of an individual order'''
        if order.date >= date_from:
            date_from = order.date
        value_start = self.order_value(av_session, order, date_from)
        value_end = self.order_value(av_session, order, date_to)
        raw_return = (value_end - value_start) / value_start
        days = (date_to-date_from).total_seconds() / 60 / 60 / 24
        return {'raw_return':raw_return, 'value_at_start':value_start, 'days':days}


    def account_investment_return(self, av_session, date_from, date_to):
        logging.debug('Calculating investment return for account')
        for order in self.order_list:
            self.individual_order_return(av_session, order, date_from, date_to)
        return


class Transaction:
    def __init__(self, txn_id, date, amount, memo):
        self.txn_id = txn_id
        self.date = date
        self.amount = float(amount)
        self.memo = memo



class Order(Transaction):

    def __init__(self, txn_id, date, amount, memo, action, units, price):
        super().__init__(txn_id, date, amount, memo)
        self.action = action
        self.units = units
        self.price = price


    def __repr__(self):
        return "Order to {} {} units for ${}".format(self.action, self.units, self.price)



class Distribution(Transaction):
    def __init__(self, txn_id, date, amount, memo, action, units, price):
        super().__init__(txn_id, date, amount, memo)



class AlphaVantage:


    def __init__(self, config):
        self.apikey = config['ALPHA VANTAGE']['API_token']


    def av_unit_price(self, symbol):
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


    def unit_price_at_date(self, symbol, at_date):
        '''returns the unit price of symbol at specified date'''
        #TODO improve exception handling
        #TODO improve prettyness and DRY, could replace try^3 with for try
        url = "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&outputsize=full&symbol={0}&apikey={1}".format(symbol, self.apikey)
        r = requests.get(url)
        r_dict = json.loads(r.text)
        one_day = timedelta(days=1)
        date_list = [at_date, at_date+one_day, at_date-one_day]
        date_list_string = [date.strftime("%Y-%m-%d") for date in date_list]
        time_series = r_dict["Time Series (Daily)"]
        try:
            unit_price = time_series[date_list_string[0]]['4. close']
        except Exception as e:
            logging.debug("Unit price not found for date desired, checking day before")
            try:
                unit_price = time_series[date_list_string[1]]['4. close']
            except Exception as e:
                logging.debug("Unit price not found for day before, checking day after")
                try:
                    unit_price = time_series[date_list_string[2]]['4. close']
                except Exception as e:
                    logging.error("Unit price not found!")
        logging.debug("Unit price of {} on {} is ${}".format(symbol, at_date.strftime('%d-%m-%Y'), unit_price))
        return float(unit_price)


    def find_exchange_rate(self, from_currency, to_currency):
        url = "https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={}&to_currency={}&apikey={}".format(from_currency, to_currency, self.apikey)
        r = requests.get(url)
        r_dict = json.loads(r.text)
        try:
            exchange_rate = r_dict["Realtime Currency Exchange Rate"]["5. Exchange Rate"]
        except Exception as e:
            logging.error("Invalid API call {}".format(e))
            sys.exit(1)
        logging.debug("Exchange rate is {}".format(exchange_rate))
        return float(exchange_rate)



def morningstar_unit_price(fund_number):
    url = "https://www.morningstar.com.au/Funds/FundReport/{0}".format(fund_number)
    tables = pd.read_html(url) # Returns list of all tables on page
    quickstats = tables[5] # Select table of interest
    close_price = float(quickstats[1][5])

    return close_price


def fortunaoz_unit_price():
    header = {
      "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.75 Safari/537.36",
      "X-Requested-With": "XMLHttpRequest"
    }
    url = "https://www.australianbullioncompany.com.au/todays-prices/"
    r = requests.get(url, headers=header)
    tables = pd.read_html(r.text) # Returns list of all tables on page
    pamp_table = tables[1] # Select table of interest
    fortuna_buy_back = float(pamp_table['Buy Back'][8][1:].replace(',', ''))
    return fortuna_buy_back


class Allocation:

    def __init__(self, cls, total):
        self.cls = cls
        self.total = total
        '''
