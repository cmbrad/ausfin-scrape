# Australian Finance Scrapers

This repository provides a number of scrapers which connect to various Australian financial
institutions to get the current account balance. Available scrapers are:

* 28 Degrees
* Acorns
* Commbank (Bank)
* Commbank (Shares)
* ING Direct
* Ratesetter
* Suncorp Bank
* Ubank

## Prerequisites
* Python 3.6
* Google Chrome

## Installation

1. Install Chrome Driver (https://github.com/SeleniumHQ/selenium/wiki/ChromeDriver)
2. Install this package with `pip install -e .`

## Usage
Run as follows:

```bash
ausfin scrape [source] -u [username] -p [password]
```

eg.

```bash
ausfin scrape acorns -u username -p password
```

Source must be one of:
* 28degrees 
* ubank-bank
* suncorp-bank
* ing-bank
* commbank-bank
* commbank-shares
* ratesetter
* acorns
