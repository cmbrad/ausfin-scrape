from setuptools import setup, find_packages


def read(filename):
    with open(filename, 'r') as f:
        return f.read()


setup(
    name='ausfin',
    version='0.2.2',
    description='Account balance scraping for Australian financial institutions',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    author='Chris Braldey',
    author_email='chris.bradley@cy.id.au',
    url='https://github.com/cmbrad/ausfin-scrape',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[
        'click>=6.7,<6.8',
        'selenium>=3.11,<3.12',
        'tabulate>=0.8,<0.9',
        'requests>=2.18,<2.19'
    ],
    extras_require={
        'test': [
            'pytest>=3.5,<3.6',
            'pytest-flake8>=1.0,<1.1',
        ]
    },
    entry_points={
        'console_scripts': [
            'ausfin = ausfin.cli:main',
        ],
    }
)
