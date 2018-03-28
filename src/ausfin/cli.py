import json

import click
from tabulate import tabulate

from ausfin.sources import TwentyEightDegreesSource, UbankSource, SuncorpBankSource, IngBankSource, \
    CommbankBankSource, CommbankSharesSource, RatesetterSource, AcornsSource


@click.group()
def cli():
    pass


sources = {
    '28degrees': TwentyEightDegreesSource,
    'acorns': AcornsSource,
    'commbank-bank': CommbankBankSource,
    'commbank-shares': CommbankSharesSource,
    'ing-bank': IngBankSource,
    'ratesetter': RatesetterSource,
    'suncorp-bank': SuncorpBankSource,
    'ubank-bank': UbankSource,
}


@cli.command(name='balance')
@click.argument('source')
@click.option('--username', '-u', required=True)
@click.option('--password', '-p', required=True)
def balance(source, username, password):
    source = sources.get(source)()
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
        source = sources.get(account['source'])()
        balance = source.fetch_balance(account['username'], account['password'])

        balance_data.append([account['source'], account['type'], balance])

    print(tabulate(balance_data, headers=['Source', 'Type', 'Balance'], floatfmt='.2f'))

    net_worth = sum([balance[2] for balance in balance_data])

    print('='*40)
    print(f'Net worth is {net_worth}')


def main():
    cli()
