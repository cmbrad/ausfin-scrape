import json

import click
from tabulate import tabulate

from ausfin.sources import TwentyEightDegreesSource, UbankSource, SuncorpBankSource, IngBankSource, \
    CommbankBankSource, CommbankSharesSource, RatesetterSource, AcornsSource, driver, SuncorpSuperSource, \
    BtcMarketsSource, UniSuperSource


@click.group()
def cli():
    pass


sources = {
    '28degrees-credit': TwentyEightDegreesSource,
    'acorns-investment': AcornsSource,
    'btcmarkets-investment': BtcMarketsSource,
    'commbank-bank': CommbankBankSource,
    'commbank-investment': CommbankSharesSource,
    'ing-bank': IngBankSource,
    'ratesetter-investment': RatesetterSource,
    'suncorpbank-bank': SuncorpBankSource,
    'suncorpbank-super': SuncorpSuperSource,
    'ubank-bank': UbankSource,
    'unisuper-super': UniSuperSource,
}


@cli.command(name='balance')
@click.argument('source')
@click.option('--username', '-u', required=True)
@click.option('--password', '-p', required=True)
def balance(source, username, password):
    with driver(implicit_wait_secs=10) as d:
        source = sources.get(source)(driver=d)
        print(source.fetch_balance(username, password))


@cli.command(name='net-worth')
@click.option('--config-filename', '-c', default='config.json')
def net_worth(config_filename):
    with open(config_filename, 'r') as f:
        config = json.load(f)
    accounts = config['accounts']

    balance_data = []
    for account in accounts:
        print(f'Loading data from {account["source"]}')
        # For now don't use shared drivers as can cause sources which share sites
        # to fail as they're already logged in previously. Need to fix by adding login detection
        with driver(implicit_wait_secs=10) as d:
            source = sources.get(account['source'])(driver=d)
            balance = source.fetch_balance(account['username'], account['password'])

        balance_data.append([account['source'], account['type'], balance])

    print(tabulate(balance_data, headers=['Source', 'Type', 'Balance'], floatfmt='.2f'))

    net_worth = sum([balance[2] for balance in balance_data])

    print('='*40)
    print(f'Net worth is ${net_worth:.2f}')


def main():
    cli()
