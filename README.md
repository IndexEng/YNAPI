# You Need An API (ynapi)
A wrapper written in Python to access the YNAB RESTFUL API

## Configuring test case
In order to run unit tests of YNAPI, it is important to set up a configuration
file. This provides the unit test script with the variables it needs to access
real API values and confirm it is effective. The config file should be dropped
in the tests directory and should be named config.ini

Internally,  config file format is:

```
[YNAB]
API_token =
budget_id =
investment_category_id =

[ALPHA VANTAGE]
API_token =
```
