import base64
import hashlib
import hmac
import logging

from contextlib import contextmanager
from typing import List, Optional

import time

import requests
from selenium import webdriver


@contextmanager
def driver(implicit_wait_secs):
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--log-level=3')

    d = webdriver.Chrome(chrome_options=options)
    d.implicitly_wait(time_to_wait=implicit_wait_secs)

    try:
        yield d
    finally:
        d.quit()


class Source:
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self.logger = logging.getLogger(__name__)

    def fetch_balance(self, username, password, base_url=None):
        pass

    def _balance_to_num(self, balance):
        return float(balance[1:].replace(',', '').replace(' ', ''))


class TwentyEightDegreesSource(Source):
    def fetch_balance(self, username, password, base_url='https://28degrees-online.latitudefinancial.com.au/'):
        self.driver.get(base_url)

        username_field = self.driver.find_element_by_id('AccessToken_Username')
        password_field = self.driver.find_element_by_id('AccessToken_Password')
        login_btn = self.driver.find_element_by_id('login-submit')

        username_field.send_keys(username)
        password_field.send_keys(password)
        login_btn.click()

        balance_field = self.driver.find_element_by_id('current-expenses-value')

        # Negate balance as credit card = debts
        return -1 * self._balance_to_num(balance_field.text)


class UbankSource(Source):
    def fetch_balance(self, username, password, base_url='https://www.ubank.com.au/NAGAuthn/ubank.secgate.action'):
        self.driver.get(base_url)

        username_field = self.driver.find_element_by_id('username')
        password_field = self.driver.find_element_by_id('password')
        login_btn = self.driver.find_element_by_name('Login')

        username_field.send_keys(username)
        password_field.send_keys(password)
        login_btn.click()

        # actual id name has a lot of strange IDs. Not sure if these change, so do a partial match
        balance_field = self.driver.find_element_by_xpath('//*[contains(@id, "uipt1:sf1:a3:itAmount::content")]')

        return self._balance_to_num(balance_field.text)


class SuncorpBankSource(Source):
    def fetch_balance(self, username, password, base_url='https://internetbanking.suncorpbank.com.au/'):
        self.driver.get(base_url)

        username_field = self.driver.find_element_by_id('UserId')
        password_field = self.driver.find_element_by_id('password')
        login_btn = self.driver.find_element_by_id('login-button')

        username_field.send_keys(username)
        password_field.send_keys(password)
        login_btn.click()

        # Doesn't have a summary balance field so calculate it ourselves
        balance_table = self.driver.find_element_by_id('BalanceTable').find_element_by_tag_name('tbody')
        balance_rows = balance_table.find_elements_by_tag_name('tr')

        # table goes account name, account number, current balance, available funds, balance alerts
        balances = [self._balance_to_num(balance_row.find_elements_by_tag_name('td')[2].text)
                    for balance_row in balance_rows]

        return sum(balances)


class SuncorpSuperSource(Source):
    def fetch_balance(self, username, password, base_url='https://internetbanking.suncorpbank.com.au/'):
        self.driver.get(base_url)

        username_field = self.driver.find_element_by_id('UserId')
        password_field = self.driver.find_element_by_id('password')
        login_btn = self.driver.find_element_by_id('login-button')

        username_field.send_keys(username)
        password_field.send_keys(password)
        login_btn.click()

        # Doesn't have a summary balance field so calculate it ourselves
        # There are two balance tables, and the super table is the 2nd one
        balance_table = self.driver.find_elements_by_id('BalanceTable')[1].find_element_by_tag_name('tbody')
        balance_rows = balance_table.find_elements_by_tag_name('tr')

        # table goes account name, account number, current balance, available funds, balance alerts
        balances = [self._balance_to_num(balance_row.find_elements_by_tag_name('td')[2].text)
                    for balance_row in balance_rows]

        return sum(balances)


class KeypadButton:
    def __init__(self, data):
        self.text = None
        self.element = None
        self.data = data

    def __repr__(self):
        return f'KeypadButton(text={self.text},element={self.element})'


class IngBankSource(Source):
    # PNG data fields from one set of page loads of the keypad
    num_pad_btns = {
        '0': 'iVBORw0KGgoAAAANSUhEUgAAALQAAABuCAYAAACOaDl7AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DA'
             'cdvqGQAAAPgSURBVHhe7dyxShxRGIbhcQu9CPtcSO5BSLUiSJqgadIGvICkT5EuXSB10qYIFhYqpBJsA4rEQiHaeDLfOBNk88/uOntWZj'
             '7eHx5017NbvRzOzu5aNJM2itXzzdHu+Xi0X/68KiWgx67qVnfVbp3x/VyMi/Xyj4cTDwCGoWxXDVcxVztzHfPl1ijdbK+ku5dFSkCPqVG'
             '1qmbrqI9Odoq14mxztNPETMgYGjXbRK2Wi/ocUtUePQDoO7Vb79L72qFvdYPdGUOlduugb4rql1K0EBiKpmOChgWChhWChhWChhWChhWC'
             'hhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWChhWCf'
             'krvXqT04dW9vefxGiyEoJdN8f78kcL5c53SwTfizoigl+XNs/aQJ0dhf3kfPw8ehaCXQTH/Oq1rfcQQ9cIIehl0jOg6OqJEz4m5EHRuCr'
             'JtdAT5+jGl759T+n1W3zkxuj96XsyFoHM7Pa7LnJjJnXfasYSjR2cEnZMuy0WjXTlar6j1gnBytJNH6zETQeeko0Q0CjdaL23n7WgtZiL'
             'onKIjxKzd9tPbeuHE8OKwE4LOKZq240ZDu3c0sx6HEEHn0nZ1Y56dNhqC7oSgc2kLWi8Uo/UPRUcVXS2J1mIqgs5FO2o00dpJ0aU+gu6E'
             'oHMh6F4g6FwIuhcIOheC7gWCzoWge4Ggc1kk6OiDSnrXMVqLqQg6F65D9wJB59I16LYPNOkt8Wg9piLonKKZtdPqo6LR8D3DTgg6p+gdP'
             '90XrW1E3zvkQ/6dEXRObR8fbdttdX80vCDsjKBzajsPa5eOPhMdXa7TcNzojKBza4tUUeu8rBeJ+hkdTzT6wH/0vJgLQefWtkvPM/o6Fr'
             'vzQgh6GdquXMwaLtUtjKCX5TFR85+TsiHoZdJ5ue1M3Qz/2y4rgn4KClbHCb3J0lDs074Njk4IGlYIGlYIGlYIGlYIGlYIGlYIGlYIGsO'
             'wF9wXIGhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhYIWhY'
             'IWhYIWhY+Rf02eboVr/cBYuAIVC7ddBXxfl4tK8bN9sr4WKg79RuFXTZso4cu7pxucUujeFRs2q3CrpsuTjZKdbKso+aqFU7YaPv1Khaf'
             'RDzsVouNBfjYr2M+rD+AzAs5YashquYm0kbxWr5h9fli8SDctH1fw8C+uW6arVsVu3eV1wUfwGlbXvWLa8bmgAAAABJRU5ErkJggg==',

        '1': 'iVBORw0KGgoAAAANSUhEUgAAALQAAABuCAYAAACOaDl7AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DA'
             'cdvqGQAAAM3SURBVHhe7dyxattQFIfxGw3JQ2Tvg/QdAp1sAqFLsbt0LeQB2r1Dt26Fzu3ayUOGJGugD2ATmsGGOktu75Gl1jg3OHGkg/'
             'TnO/Ajlixp+rjIJnKoJx6F/dmwGM8GxST9nScR6LB51erY2q0yXs31IBymN883TgD6IbVrDZcxlytzFfPNcRGXJ3vx7nWIEegwa9RatWa'
             'rqC+uRuEgTIfFqI6ZkNE31mwdtbUcqvuQsvbcCUDXWbvVKj2xFfrWNlid0VfWbhX0MpQvktyBQF/UHRM0JBA0pBA0pBA0pBA0pBA0pBA0'
             'pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBC0p'
             'w+vYvz5NcZfl/+dvswfi50QtIdvH1fx5ubTm/w52AlBt8lC/j2tyn1gCLpRBN20dy9i/P55e8j1EHSjCLpJdo/8Z1GV+sgh6EYRdJPsA9'
             '5Th6AbRdBNy334s3327UZuCLpRBN00C7Sesx+r25DN/etD0I0i6DZ8eX//+2WCdkHQXgjaBUF7IWgXBO2FoF0QtBeCdkHQXgjaBUF7IWg'
             'XBO2FoF0QtBeCdkHQXgjaBUF7IWgXBO2FoF0QtBeCdkHQXgjaBUF7IWgXBO2FoF0QdBvsn/ot1HX24GxubP/msfagbe662Iqg2/DUB2U3'
             'x37+IHddbEXQbXju2Kqduy62Iug2PHcIemcE3YbH/sjMQ2PPJOaui60IGlL8gz7N7AMa4h800CKChhSChhSChhSChhSChhSChhSChhSCh'
             'hSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChhSChpR/QU'
             '+Hxa29uMscBPSBtVsFPQ+zQTGxjeXJXvZgoOus3TLo1LLdcoxt4+aYVRr9Y81au2XQqeVwNQoHqeyLOmqrnbDRddaotboW86W1HGyuB+E'
             'wRX1evQH0S1qQreEy5nriUdhPb7xNHxLP0kGLeycB3bIoW03NWrurikP4C0tw0zbqOK1MAAAAAElFTkSuQmCC',

        '2': 'iVBORw0KGgoAAAANSUhEUgAAALQAAABuCAYAAACOaDl7AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DA'
             'cdvqGQAAAOvSURBVHhe7dsxS9xgHMfxxxv0Rbj3hfQ9CJ1OBOlStEvXgi+g3Tt061bo3K4dioODCp0E14IidVCoLj7NL5eUIz6hOZNcLj'
             '++f/hQr5fL9PXhSS6GcuJWWL/cnuxfTieH2b83mQissJui1X21W2Q8m6tp2MzePK58ABiHrF01nMecr8xFzNc7k3i3uxYfXoYYgRWmRtW'
             'qmi2iPjnbCxvhYnuyV8ZMyBgbNVtGrZZDsQ/Ja099AFh1ardYpQ+1Qt/rBaszxkrtFkHfhfyHTOpAYCzKjgkaFggaVggaVggaVggaVgga'
             'VggaVggaVggaVggaVoYL+iDxf0BLwwUN9ICgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgY'
             'YWgYYWgl+Xdixg/vJrRz6lj0BpB9+XNsxi/vI/x/DTWzs8fs8BTn8eTEHQfvn6M8c9tUW2DOfo2+wVInQsLIeguKcpf50WlC45W69Q5sR'
             'CC7tLB86LOJ462KKnzojGC7ppW2upoH61tiKTeL+f3RfqcaIygu6ZVutw/K2C9rh6juxx1e2zugLRC0H3QnYtUyPO0vUiNfglSx6MRgh6'
             'KLiBTQ9CtEPSQUkPQrRD0UFihe0HQQ/n0tii4MlwUtkLQQ9G3g9XRnY/UsWiMoIdQ9wUM243WCHoIqQeWtDrzPEdrBL1sWoVTw+rcCYJe'
             'prpvCPVAU+p4LIygl0XbCT2rUR0Fzp2NzhD0stQ96M8Tdp0i6GX4/rmotzK6dZc6Hk9G0H2rewhJK3bqeLRC0H3S3jg1ugjkFl0vCLov8'
             '89Fzw/3m3tF0H1QsKm/LeSORu8Iug91f2ZFzL0j6K7VfROo1VkXgv+jOyKp86IRgu5S3UXgIqOoU+dGIwTdpbpbdIsMQbdC0F2q224sMg'
             'TdCkF3iRV6cAQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQ'
             'NKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNK/+Cvtie3OuHh8RBwBio3SLom3A5nRzqxd3uWvJgYNWp3TzorGVtOfb1'
             '4nqHVRrjo2bVbh501nI42wsbWdknZdSqnbCx6tSoWp2L+VQtB83VNGxmUR8XbwDjki3IajiPuZy4FdazN15nF4lH2UG3jz4ErJbbvNWsW'
             'bU7qziEv7tA+ppiVxUwAAAAAElFTkSuQmCC',

        '3': 'iVBORw0KGgoAAAANSUhEUgAAALQAAABuCAYAAACOaDl7AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DA'
             'cdvqGQAAAPXSURBVHhe7dyxShxBAMbx8Qp9CPs8SN5BSHUiSJqgadIGfICkT5EuXSB10qYIFhYqpBJsA4rEQiHaONlv3U2Oy6zOubvu3Z'
             'f/wA89b3arP8Pc7p6hHnEtLJ+uj7ZPx6Pd4udFIQJz7KJqdVvtVhnfjrNxWC3e3J86AFgMRbtquIy5XJmrmM83RvFqcynePA8xAnNMjap'
             'VNVtFfXC0FVbCyfpoq46ZkLFo1GwdtVoO1T6krD11ADDv1G61Su9qhb7WC1ZnLCq1WwV9FcpfCqmJwKKoOyZoWCBoWCFoWCFoWCFoWCFo'
             'WCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCFoWCHox'
             '/DqSYzvXvy18zQ9D60RdF/ePIvx68cYf57E5Ph1GePeF+LuGEF3TYEeH1bVZo5Pb9PnwswIumuf31eVzjh0XOp8mAlBd00r9EOHtimpcy'
             'IbQfdBe+N6fP92u6WoPxBqX639c2pobup8yEbQfdBVDW0h9DP1vlbipqhT85GNoIfStNfWKp6ajywEPRSFmxoE3QpBD4Wge0HQQ9GHw+m'
             'hfXVqLrIR9BCaPhQq8tR8ZCPox6TtRNNlux/HzVdFkI2g+/ThdVXrPUMx80xHJwi6Tzm3wXUTJnUsHoSg+5T7XIeiZrvRCYLuk2555w7t'
             'q3mWozWC7tP0g/1asbUaN9321l46dR5kI+ghKHTFmxo8G90KQQ9FUadWan05IDUfWQh6SJOPmU6O1FxkIeghNV0FSc1FFoIeUup5Do3UX'
             'GQh6KFoD536RjhXOloh6K5pXyx33cpWzE37Z/09dQyyEHSXdK15cmi11T55+lp00//q0NCc1LmRhaC7pC+5thlcsmuNoLvUZuiatLYiqf'
             'MiG0F3SduJptvadw0eH+0MQXdNq+x9++R6KGRudXeKoPukVbf+IDhJf2NF7gVBwwpBwwpBwwpBwwpBw4pv0DuJv8Geb9D4LxE0rBA0rBA'
             '0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rBA0rPwJ'
             '+mR9dK1fbhKTgEWgdqugL8LpeLSrF1ebS8nJwLxTu2XQRcvacmzrxfkGqzQWj5pVu2XQRcvhaCusFGUf1FGrdsLGvFOjanUi5kO1HDTOx'
             'mG1iHq/egNYLMWCrIbLmOsR18Jy8cbL4kPiXjHp8p+DgPlyWbZaNKt2bysO4Td5PwaE+ZHC9gAAAABJRU5ErkJggg==',

        '4': 'iVBORw0KGgoAAAANSUhEUgAAALQAAABuCAYAAACOaDl7AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DA'
             'cdvqGQAAAN8SURBVHhe7dsxTxRBGIfx4Qr4EPR+EL8DidUREmJjwMbWhA+gvYWdnYm1thaGggJIrEhoTe5CpIBEaFjnXWbNubwYvJlld/'
             '953uQXOW4uNo+Tnb01NFNthNX55mR3Pp3sxz8vogoYsIvU6q61mzK+nbNpWI9vHrY+AIxDbNcarmOud+YU8/nWpLraXqlunoeqAgbMGrV'
             'WrdkU9dHJTlgLs83JThMzIWNsrNkmams5pOuQunbvA8DQWbtpl963HfraXrA7Y6ys3RT0Vah/iLyFwFg0HRM0JBA0pBA0pBA0pBA0pBA0'
             'pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pPQT9J7zO6CAfoIGOkLQkELQkELQkELQk'
             'ELQkELQkELQj+XgS1WdHv/t3Qt/LZZG0I/hw+vKnb2n/nosjaAfw/dvqeCFsR3aW4ssBN0124W9+fTWX48sBN21z+9TwQvz69Jfi2wE3T'
             'WLtz0WubcW2Qi6S3ZZ4Q2Hwc4QdJfs4NceOyB6a1EEQXflvsMg9547RdBd+foxFbwwP2f+WhRD0F3hMNgLgu7CfYfBV0/89SiGoLvgHQb'
             'tWY7FNfZ1uO3YDftHwN2PbARd2ptnqeDW2O8X13nDJUk2gi7NduL2/Di9u84bgs5G0CXZNbJ3GPSe2/CGoLMRdEneYdAC9w6D3hB0NoIu'
             'yS4t2mP3o7213hB0NoIu5b7D4LLDE3lLIehSbHctPd7fg38i6FIIehAIuhSCHgSCLsW++Wv+N/dDeGMPLzXvt79ZxIMQdF+84S5HNoLui'
             'zcEnY2g++INQWcj6L54Q9DZCLov3hB0NoLui93RaI/3EBP+C0FDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCk'
             'FDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDCkFDyp+gZ5uTa/vhxlkEjIG'
             '1m4K+CPPpZN9eXG2vuIuBobN266Bjy3bJsWsvzrfYpTE+1qy1WwcdWw4nO2Etln3URG21EzaGzhq1VhdiPraWg83ZNKzHqA/TG8C4xA3Z'
             'Gq5jbqbaCKvxjZfxkHgQF13e+RAwLJd1q7FZa/e24hB+A8jP8ETGs1otAAAAAElFTkSuQmC',

        '5': 'iVBORw0KGgoAAAANSUhEUgAAALQAAABuCAYAAACOaDl7AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DA'
             'cdvqGQAAAOGSURBVHhe7dqxTttQGIbhQwa4CPZeSO8BqVMQEupSQZeulbiAdu/QrVulzu3KlIEBWJFYK4FQGUAqLLjnc+wqoifgOD51/O'
             'n9pUeNie3p7ZFjO9RTbIX1y+3R/uV4NIn/3kQFsMJuqlb31W6V8XSuxmEzfnn86ABgGGK7ariMuVyZq5ivd0bF3e5a8fA6FAWwwtSoWlW'
             'zVdQnZ3thI1xsj/bqmAkZQ6Nm66jVcqiuQ8raUwcAq07tVqv0RCv0vTZYnTFUarcK+i6UH6LUjsBQ1B0TNCwQNKwQNKwQNKwQNKwQNKwQ'
             'NKwQNKwQNKwQNKwQNKwMK+iDxN+AGcMKGngGQcMKQcMKQcMKQcMKQcMKQcMKQcMKQcMKQcMKQcMKQcMKQcMKQcMKQcMKQcMKQcMKQcMKQ'
             'cMKQcMKQefw/XNRnJ+28+5F+pxohKBzUJht59Ob9DnRCEHnQNC9IegcCLo3BJ3DMkEfvEyfE40QdA6poFl5/wuCzoGge0PQORB0bwg6B4'
             'LuDUHnQNC9IegcUkEf/Zg+QawReBYEnUMq6Hmj0LlV1xmCzmGRoDW/b4vi28f0ubAQgs5h0aDr+fI+fT40RtA5zAb983y6Lfr81Gil5m2'
             '7pRB0DromnnddrGD1o1DxpkbfpY5DIwTdlw+vqoIfza+L9P5ohKD7pDscqeGyozWC7pPubKSGe9StEXSfFG5qCLo1gu4TQXeOoPukOxqp'
             '4Rq6NYLui6LVHY3Hw12OpRB01w6/Th+iPPV+hmKed4dDx6eOQSME3SVFPDt6Mli/WVfTdmplrocXlZZC0F2at+o2HZ4SLo2gu/TUyvvc6'
             'D9D6pxYCEF3SZcUbaLmurkzBJ2DngA+92adRquy3ulInQOtEHRO+oFX/xCcpb+l9sfSCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCB'
             'pWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpWCBpW/gZ'
             '9sT2614eHxE7AEKjdKuibcDkeTbRxt7uW3BlYdWq3DDq2rEuOfW1c77BKY3jUrNotg44th7O9sBHLPqmjVu2EjVWnRtXqTMynajlorsZh'
             'M0Z9XH0BDEtckNVwGXM9xVZYj1+8jT8Sj+JOt/8cBKyW27LV2KzanVYcwh+mrxqi1nBysQAAAABJRU5ErkJggg==',

        '6': 'iVBORw0KGgoAAAANSUhEUgAAALQAAABuCAYAAACOaDl7AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DA'
             'cdvqGQAAAPzSURBVHhe7duxThRdHIbxwxZwEfReiPdAYgUhITYGbGxNuADtLezsTKy1tTAUFEBiRUJrAiFSQCI0jPMuM7pZ/7PszpzB3Z'
             'fnJL98y+7ZrZ7v5MyZMdWjWEvLZxuDnbP1wV7538tSAcyxy6rVHbVbZXw3ztfTavnhwdgXgMVQtquGhzEPV+Yq5ovNQXG9tVTcPk9FAcw'
             'xNapW1WwV9eHxdlpJpxuD7TpmQsaiUbN11Go5VfuQYe3RF4B5p3arVXpPK/SN/mB1xqJSu1XQ12n4ohRNBBZF3TFBwwJBwwpBwwpBwwpB'
             'wwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBwwpBw4pX0LvBe3hUvILGo0fQsELQs'
             'ELQsELQsELQ/8O7F3+9ehLPQSsE/VA+vS2KHydFOH6eFsXn98SdAUH37c2z5pDHx6+ru1U7+h1MhaD7pJgV6SxDK3X0W5gKQfelTcyaz7'
             'ajE4LuS9M2Q+9rFa4vCvW6nsvq3BlB90EXgNHY/xLPF63o0fuYCUH3QacW40OrcDQXWRF0bh9eVwWPDb0fzUdWBJ2bthXjQxd70VxkR9C'
             '5RScbk/bOyIqgc9KFXTRGTy/qk40aN1KyIuicJu2fFW/TubTe1+ecQXdG0DkpymhEpx7R0EkIUXdC0Dl9/ViV2WFwvNcJQed0clRV2XFo'
             'pY9+H/ci6Jyagq4fDx29G6jX379VE8aG5o/+LqZG0DlFQd+3hWj6n4Bb4a0QdE5RnHovmltrOhnR8yDRfExE0Dm1CVqiwT66FYLOKTrlm'
             'GY/HA2CboWgc2o6h47mjooGQbdC0DnpNnY0Jj1p1/Qdbom3QtA56S5fNCY9nBQ9nafBHcNWCDq3WY7hmh5m4um81gg6t6Z/fqUHkOqjOK'
             '2+et30sBLbjdYIug9Nq/Q0Qycl0W9iKgTdB20lmlbfSYMHkzoj6L7MGrX2zVwIdkbQfVKgCnVS2FqV2TNnQ9APRdHqZklNF4W7T+O5aI2'
             'gYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWg'
             'YYWgYYWgYYWgYYWgYYWgYYWgYYWgYYWgYeVP0Kcbgxu9uA0mAYtA7VZBX6az9cGe/rjeWgonA/NO7Q6DLlvWlmNHf1xsskpj8ahZtTsMu'
             'mw5HW+nlbLswzpq1U7YmHdqVK2OxHyklpPG+XpaLaM+qD4AFku5IKvhYcz1KNbScvnBy/Iicb+cdPXPl4D5cjVstWxW7d5VnNJvStllsp'
             'BxMtQAAAAASUVORK5CYII=',

        '7': 'iVBORw0KGgoAAAANSUhEUgAAALQAAABuCAYAAACOaDl7AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DA'
             'cdvqGQAAAN0SURBVHhe7dsxS1tRGIfxYwb9EO79IP0OQqeIIF1K7NK14Ado9w7duhU6t6tDcXBQoZPgWohIHRSqi6fnvZ60IX2jxpxzb/'
             'LneeGHxpzo8nC4yT2G0cSNsHq22ds56/f209fLJAIL7DK3umPt5ozv5rwf1tOThxMvAJZDatcabmJuduYc88VWL15vr8TblyFGYIFZo9a'
             'qNZujPjoZhLUw3OwNRjETMpaNNTuK2loO+Tqkqd17AbDorN28S+/bDn1jD9idsays3Rz0dWi+SbyFwLIYdUzQkEDQkELQkELQkELQkELQ'
             'kELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQkELQk'
             'ELQJe0+j/H0eH4/vsf45pn/N3Avgi7pw6tYbOx3eX8D9yLokgi6cwRdUsmgueR4EoIu6d2LXOOc8/PU//14EEF37dcwVzw2X977a/Eggu'
             '7Sp7e54LH5fcXlxhwIukv2Ed3kHHzz1+JRCLor06637efeejwKQXfFduLJsR3bW4tHI+gu2DWyN7wZnBtBd+Hrx1zw2NibQW8tZkLQXbB'
             '4J8ci99ZiJgTdNrus8MYONnnrMROCbpt3I8VO13lrMTOCbtO0sx4cRCqGoNvk3UixHdtbiych6LbYNbI3vBksiqDb4t1I4dxGcQTdBovW'
             '+6iOcxvFEXQbvBspNpzbKI6g2+B9VMch/ioIurZpN1I4t1EFQddmO/HkcG6jGoKuadqNlL3P/nrMjaBrslva3nBuoxqCrmXajRTObVRF0'
             'LXYZYU39o+x3noUQdC1eB/V8S9W1RE0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pB'
             'A0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pBA0pPwNerjZu7Fvbp1FwDKwdnPQl+Gs39u3B9fbK+5'
             'iYNFZu03QqWW75NixBxdb7NJYPtastdsEnVoOJ4Owlso+GkVttRM2Fp01aq2OxXxsLQeb835YT1Ef5ieAIuLuvzdrVaUN2RpuYh5N3Air'
             '6YnX6U3iQVp09d+LgMVy1bSamrV27yoO4Q94hbaeggnUCAAAAABJRU5ErkJggg==',

        '8': 'iVBORw0KGgoAAAANSUhEUgAAALQAAABuCAYAAACOaDl7AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DA'
             'cdvqGQAAAQNSURBVHhe7duxShxRGIbhcQu9CPtcSO5BSLUiSJqgadIGvICkT5EuXSB10qYIFhYqpBJsA4rEQiHaOJlvnUmW9T/u7OwZ2f'
             '14f3iIurNTvRzOntkUzZQbxer55mD3fDjYr/69qpTAAruqW91Vu3XG93MxLNarFw8n3gAsh6pdNTyKebQy1zFfbg3Km+2V8u5lUZbAAlO'
             'jalXN1lEfnewUa8XZ5mCniZmQsWzUbBO1Wi7qfcio9ugNwKJTu/Uqva8V+la/sDpjWandOuibYvRDJboQWBZNxwQNCwQNKwQNKwQNKwQN'
             'KwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwQNKwSNp7cX/C0TgoYVgoYVgoYVgoYVgoYVgoYVgoYVgoYVgoYVgoYVgoYVgoYVgoYVgoYVg'
             'oYVgoYVgn5Ke8/L8sOr/6JrMBeC7psiPvhWlr/PynB+nZbl149l+eZZ/H7MhKD7pFDbjoJ/9yK+D1oj6L5oVZ51/lwT9ZwIug+f3taFdh'
             'htQaJ7ohWC7kNqv6wtSHONoteKHI1eG78fWiPo3LRliGY85mnXfv/88Fq0QtC5pT4Ipk4xtMWYnNPj+FpMRdC5pYKOrhXFOzkE3RlB55Y'
             'KOrUvjvbRbDk6I+jcUicc2lpMbjtS8fMUsTOCzk1PBlOj048mVn0gjFbnnz8e3hOtEXQfpj1U0R45ijlaxTETgu6DVunUGXNqtDIT89wI'
             'ui/aWrSNmpU5G4Luk04r2o7i58Pg3Ai6D1pto/PlNvPlfXxPtELQuSnm6Omf/qYjvTah8427zgg6tyjYyT2ythaPha3Xxu+J1gg6J20Xo'
             'tGpR3R96sGKJvUePIqgc9LR2+RMW21TUbOX7oSgc4qO6RRsdG1DW5Fopr0PIYLOKZo2YUZD0J0QdE7RTNty6ANiNATdCUHnFB3XaVL74d'
             'QRn4aju04IOietqqnRSq2wtSKLniKmHo3rW3nR/TEVQeekFXfWLyVFw3+S7Yygc0t9wb/t6Kun0X3RCkH3QVF3Wan5IDg3gu6Lth8KdFr'
             'Yel2rMk8GsyDop6ATC30gVOAN/c5JRnYEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsE'
             'DSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSv/gj7bHNzqh7vgImAZqN066KvifDjY1y832yvhx'
             'cCiU7ujoKuWteXY1S+XW6zSWD5qVu2Ogq5aLk52irWq7KMmatVO2Fh0alStjsV8rJYLzcWwWK+iPqxfAJZLtSCr4VHMzZQbxWr1wuvqQ+'
             'JBddH1gzcBi+V61GrVrNq9r7go/gKUcKnLxazZhgAAAABJRU5ErkJggg==',

        '9': 'iVBORw0KGgoAAAANSUhEUgAAALQAAABuCAYAAACOaDl7AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DA'
             'cdvqGQAAAP7SURBVHhe7dy9ThRRHIbxwxZwEfReiPdAYgUhITYGbGxNuADtLezsTKy1tTAUFEBiRUJrAiFSQCI0jPMuM0rW/+zszp5xd9'
             '88J/kFlj2z1ePJmY811aPYSKsXW4O9i83BQfnzulQAC+y6anVP7VYZP4zLzbRevnk0cgCwHMp21fAw5uHKXMV8tT0obndWivvnqSiABaZ'
             'G1aqaraI+Pt1Na+l8a7Bbx0zIWDZqto5aLadqHzKsPToAWHRqt1qlD7RC3+kFqzOWldqtgr5Nw19K0URgWdQdEzQsEDSsEDSsEDSsEDSs'
             'EDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsEDSsE'
             'PT/8upJUbx78ZdeR/MwE4Luk6L9/L4ofp4X4dDf9T5xZ0PQffnwuih+3VTltgzN+/Q2/hxMhaD7oDi7DKKeGUHn9uZZVWfHoeOjz8VECD'
             'q3s5OqzJHx4+xhBdYJoX7qdTR0fPS5mAhB56RYo/H9Wzy/KX5W6c4IOqevH6siR0bTVYz9p9WEkaErH9F8tCLonKJtRNPqXIuOYdvRGUH'
             'nFI221bZpVY/mohVB5xSNtqD1fjSiuWhF0DlF4/BLPLfWdCKpv0fzMRZB5xTth3UXcNytbYLOiqBzatoPa5WOotZVDp00RoOgOyHonJou'
             'w2lopVbY2jMr/KYbK/Ug6E4IOremVXraQdCdEHQftBLPOrhb2AlB90Vbi7bHRxV+05N50WeiFUH3SSeCClbh6u6f6CRQsWu/rTnRdWj9Q'
             'xj9LEyEoOct2nNz67szgp636Ik7RR7NRSuCnidtSaKhr29F89GKoOcpOiFk/zwTgp6n6NvgOoGM5mIiBD0vTdequaEyE4Lug6LUULTaDz'
             '9+jkOvoxNBjbYvA6AVQfeh6T+WGTe0d66vTaMzgs5NK3CXwZWNLAg6t2mD1srMvjkbgu6Dtg7aP497lkPvac64h/8xNYLum1ZfPa/xGCt'
             'ybwgaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVggaVgga'
             'VggaVggaVggaVggaVggaVggaVggaVgh6WvvB37AwCBpW/gR9vjW40y/3wSRgGajdKujrdLE5ONCL252VcDKw6NTuMOiyZW059vTiaptVG'
             'stHzardYdBly+l0N62VZR/XUat2wsaiU6Nq9VHMJ2o5aVxupvUy6qPqDWC5lAuyGh7GXI9iI62Wb7wsTxIPy0k3/xwELJabYatls2r3oe'
             'KUfgN5mGB2BUP+xQAAAABJRU5ErkJggg==',
    }

    def fetch_balance(self, username, password, base_url='https://www.ing.com.au/securebanking/'):
        self.driver.get(base_url)

        client_number_field = self.driver.find_element_by_id('cifField')
        login_btn = self.driver.find_element_by_id('login-btn')

        client_number_field.send_keys(username)

        # Keypad positions are randomised, we have to find which order the butotns are in
        keypad = self._keypad()

        # Press all the correct key pad numbers based off what we just calculated
        for character in password:
            keypad[character].click()

        login_btn.click()

        balance_field = self.driver.find_element_by_xpath('//*[@id="summary-container"]/div[3]/div/div/div/div[2]/span')
        return self._balance_to_num(balance_field.text)

    def _keypad(self):
        keypad = self.driver.find_element_by_id('keypad')
        keypad_buttons = keypad.find_elements_by_xpath('//*[@id="keypad"]/div/div/div')

        buttons = []
        for keypad_button in keypad_buttons:
            data = keypad_button.find_element_by_tag_name('img').get_attribute('src')[22:]
            button = self._button_by_data(data, buttons)
            if button is None:
                button = KeypadButton(data=data)
                buttons.append(button)
            button.element = keypad_button

        for button in buttons:
            self._set_button_value(button)

        return {key.text: key.element for key in buttons}

    def _button_by_data(self, data: str, buttons: List[KeypadButton]) -> Optional[KeypadButton]:
        for button in buttons:
            if button.data == data:
                return button
        return None

    def _set_button_value(self, button: KeypadButton):
        # the exact value of the png data seems to change between page loads, but the general
        # relative length of the fields stays the same. As long as the fields are relatively the
        # same length then we can guess which number they are
        closest_val = None
        closest_diff = 20
        for k, v in self.num_pad_btns.items():
            length_diff = abs(len(v) - len(button.data))
            if length_diff < closest_diff:
                closest_val = k
                closest_diff = length_diff

        button.text = closest_val


class CommbankBankSource(Source):
    def fetch_balance(self, username, password, base_url='https://www.my.commbank.com.au/netbank/Logon/Logon.aspx'):
        self.driver.get(base_url)

        username_field = self.driver.find_element_by_id('txtMyClientNumber_field')
        password_field = self.driver.find_element_by_id('txtMyPassword_field')
        login_btn = self.driver.find_element_by_id('btnLogon_field')

        username_field.send_keys(username)
        password_field.send_keys(password)
        login_btn.click()

        # Provides a table with both commsec data and netbank data - we need to separate the two
        balance_table = self.driver.find_element_by_id('MyPortfolioGrid1_a').find_element_by_tag_name('tbody')
        # skip last row it's a summary row
        balance_rows = balance_table.find_elements_by_tag_name('tr')[:-1]

        total_balance = 0

        # table goes account name, account number, current balance, available funds, balance alerts
        for balance_row in balance_rows:
            cells = balance_row.find_elements_by_tag_name('td')
            # nickname = cells[0].text
            bsb = cells[1].text
            # acc = cells[2].text
            balance = cells[3].text
            # available_funds = cells[4].text

            # commsec acocunts show this instead of a bsb
            is_bank_acc = bsb != 'View in Portfolio'

            balance_is_credit = balance[0] == '+'
            balance_num = self._balance_to_num(balance[1:])
            balance_num = balance_num * -1 if not balance_is_credit else balance_num

            if is_bank_acc:
                total_balance += balance_num

        return total_balance


class CommbankSharesSource(Source):
    def fetch_balance(self, username, password, base_url='https://www.my.commbank.com.au/netbank/Logon/Logon.aspx'):
        self.driver.get(base_url)

        username_field = self.driver.find_element_by_id('txtMyClientNumber_field')
        password_field = self.driver.find_element_by_id('txtMyPassword_field')
        login_btn = self.driver.find_element_by_id('btnLogon_field')

        username_field.send_keys(username)
        password_field.send_keys(password)
        login_btn.click()

        balance_table = self.driver.find_element_by_id('MyPortfolioGrid1_a').find_element_by_tag_name('tbody')
        # skip last row it's a summary row
        balance_rows = balance_table.find_elements_by_tag_name('tr')[:-1]

        total_balance = 0

        # table goes account name, account number, current balance, available funds, balance alerts
        for balance_row in balance_rows:
            cells = balance_row.find_elements_by_tag_name('td')
            # nickname = cells[0].text
            bsb = cells[1].text
            # acc = cells[2].text
            balance = cells[3].text
            # available_funds = cells[4].text

            # commsec acocunts show this instead of a bsb
            is_bank_acc = bsb != 'View in Portfolio'

            balance_is_credit = balance[0] == '+'
            balance_num = self._balance_to_num(balance[1:])
            balance_num = balance_num * -1 if not balance_is_credit else balance_num

            if not is_bank_acc:
                total_balance += balance_num

        return total_balance


class RatesetterSource(Source):
    def fetch_balance(self, username, password, base_url='https://members.ratesetter.com.au/login.aspx'):
        self.driver.get(base_url)

        username_field = self.driver.find_element_by_id('ctl00_cphContentArea_cphForm_txtEmail')
        password_field = self.driver.find_element_by_id('ctl00_cphContentArea_cphForm_txtPassword')
        login_btn = self.driver.find_element_by_id('ctl00_cphContentArea_cphForm_btnLogin')

        username_field.send_keys(username)
        password_field.send_keys(password)
        login_btn.click()

        balance_field = self.driver.find_element_by_xpath(
            '//*[@id="ctl00_cphContentArea_cphForm_expSummary_ExpanderContent"]/div/table/tbody/tr[4]/td[2]')
        return self._balance_to_num(balance_field.text)


class AcornsSource(Source):
    def fetch_balance(self, username, password, base_url='https://app.raizinvest.com.au/auth/login'):
        self.driver.get(base_url)

        self.logger.debug(self.driver.page_source)

        username_field = self.driver.find_element_by_class_name('spec-login-email-input')
        password_field = self.driver.find_element_by_class_name('spec-login-password-input')
        login_btn = self.driver.find_element_by_class_name('spec-login-button')

        username_field.send_keys(username)
        time.sleep(1)  # need a short wait otherwise the fields get confused
        password_field.send_keys(password)
        login_btn.click()

        balance_field = self.driver.find_element_by_tag_name('output')

        self.logger.debug(self.driver.page_source)
        self.logger.debug(balance_field.text)

        return self._balance_to_num(balance_field.text)


class BtcMarketsSource(Source):
    def fetch_balance(self, username, password, base_url='https://api.btcmarkets.net'):
        balances = self.get_api(username, password, base_url, '/account/balance')

        total_balance = 0.0
        for coin in balances:
            # conversion factor
            balance = coin['balance'] / 100000000
            currency = coin['currency']

            # Can't convert AUD to AUD, so just take it as is
            if currency == 'AUD':
                total_balance += balance
                continue

            if balance > 0:
                # get balance in AUD
                tick = self.get_api(username, password, base_url, f'/market/{currency}/AUD/tick')
                last_price = tick['lastPrice']

                aud_balance = balance * last_price
                total_balance += aud_balance

        return round(total_balance, 2)

    def get_api(self, username, password, base_url, path):
        key = username
        secret = base64.b64decode(password)

        # Needs to be a string for the headers
        now_ms = str(int(time.time() * 1000))
        sign_str = f'{path}\n{now_ms}\n'.encode('utf8')
        signature = base64.b64encode(hmac.new(secret, sign_str, digestmod=hashlib.sha512).digest())

        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'btc markets python client',
            'accept-charset': 'utf-8',
            'apikey': key,
            'signature': signature,
            'timestamp': now_ms,
        }

        response = requests.get(f'{base_url}/{path}', headers=headers)
        return response.json()


class UniSuperSource(Source):
    def fetch_balance(self, username, password, base_url='https://memberonline.unisuper.com.au/'):
        self.driver.get(base_url)

        username_field = self.driver.find_element_by_id('username')
        password_field = self.driver.find_element_by_id('password')
        login_btn = self.driver.find_element_by_xpath('//*[@id="loginForm"]/p/input')

        username_field.send_keys(username)
        password_field.send_keys(password)
        login_btn.click()

        balance_field = self.driver.find_element_by_xpath('//*[@id="main"]/div[2]/div/div/div[3]')

        return self._balance_to_num(balance_field.text)
