from setuptools import setup, find_packages

setup(
    name='ausfin',
    version='0.1',
    description='Account balance scraping for Australian financial institutions',
    author='Chris Braldey',
    author_email='chris.bradley@cy.id.au',
    url='https://github.com/cmbrad/ausfin-scrape',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=['click>=6.7,<6.8', 'selenium>=3.11,<3.12'],
    entry_points={
        'console_scripts': [
            'ausfin = ausfin.cli:main',
        ],
    }
)
