import datetime
import json
import logging
import sys

import click
from tabulate import tabulate

from ausfin.sources import TwentyEightDegreesSource, UbankSource, SuncorpBankSource, IngBankSource, \
    CommbankBankSource, CommbankSharesSource, RatesetterSource, AcornsSource, driver, SuncorpSuperSource, \
    BtcMarketsSource, UniSuperSource


@click.group()
def cli():
    setup_logging()


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
@click.option('--out-filename', '-o')
def net_worth(config_filename, out_filename):
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

        balance_data.append([account['source'], balance])

    print(tabulate(balance_data, headers=['Source', 'Balance'], floatfmt='.2f'))

    net_worth = sum([balance[1] for balance in balance_data])

    print('='*40)
    print(f'Net worth is ${net_worth:.2f}')

    if out_filename is not None:
        out_data = {
            'extract_time': datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat(),
            'balances': []
        }
        for row in balance_data:
            out_data['balances'].append({
                'source': row[0],
                'balance': row[1]
            })

        with open(out_filename, 'w', newline='') as f:
            json.dump(out_data, f)


def setup_logging():
    # create logger with 'spam_application'
    logger = logging.getLogger('ausfin')
    logger.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.ERROR)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(ch)


def main():
    cli()
