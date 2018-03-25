import click

from ausfin.sources import TwentyEightDegreesSource, UbankSource, SuncorpBankSource, IngBankSource, \
    CommbankBankSource, CommbankSharesSource, RatesetterSource, AcornsSource


@click.group()
def cli():
    pass


sources = {
    '28degrees': TwentyEightDegreesSource,
    'ubank-bank': UbankSource,
    'suncorp-bank': SuncorpBankSource,
    'ing-bank': IngBankSource,
    'commbank-bank': CommbankBankSource,
    'commbank-shares': CommbankSharesSource,
    'ratesetter': RatesetterSource,
    'acorns': AcornsSource,
}


@cli.command()
@click.argument('source')
@click.option('--username', '-u', required=True)
@click.option('--password', '-p', required=True)
def balance(source, username, password):
    source = sources.get(source)()
    print(source.fetch_balance(username, password))


def main():
    cli()
